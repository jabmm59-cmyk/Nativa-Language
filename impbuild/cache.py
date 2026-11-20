import hashlib
import json
import os
import shutil
import time


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    with open(path, "rb") as handle:
        return sha256_bytes(handle.read())


class BuildCache:
    def __init__(self, cache_dir, libraries_dir):
        self.cache_dir = cache_dir
        self.libraries_dir = libraries_dir

    def index_path(self, library):
        return os.path.join(self.cache_dir, library + ".json")

    def load(self, library):
        try:
            with open(self.index_path(library), encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def save(self, library, data):
        os.makedirs(self.cache_dir, exist_ok=True)
        temporary = self.index_path(library) + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
        os.replace(temporary, self.index_path(library))

    def make_key(self, source_bytes, *extras):
        digest = hashlib.sha256()
        for extra in extras:
            digest.update(str(extra).encode("utf-8"))
            digest.update(b"\0")
        digest.update(source_bytes)
        return digest.hexdigest()

    def artifact_path(self, module):
        return os.path.join(self.libraries_dir, *module.split(".")) + ".nac"

    def is_fresh(self, entry, key, artifact):
        if not isinstance(entry, dict) or entry.get("key") != key:
            return False
        if not os.path.isfile(artifact):
            return False
        return sha256_file(artifact) == entry.get("artifact_sha")

    def make_entry(self, key, artifact, imports, source_path):
        return {
            "key": key,
            "artifact_sha": sha256_file(artifact),
            "imports": imports,
            "source": os.path.abspath(source_path),
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

    def clear(self, library=None):
        removed = []
        if library is None:
            for directory in (self.cache_dir, self.libraries_dir):
                if os.path.isdir(directory):
                    for entry in os.listdir(directory):
                        full = os.path.join(directory, entry)
                        if os.path.isdir(full):
                            shutil.rmtree(full)
                        else:
                            os.remove(full)
                        removed.append(entry)
            return removed
        index = self.index_path(library)
        if os.path.isfile(index):
            os.remove(index)
            removed.append(os.path.basename(index))
        target = os.path.join(self.libraries_dir, library)
        if os.path.isdir(target):
            shutil.rmtree(target)
            removed.append(library)
        single = target + ".nac"
        if os.path.isfile(single):
            os.remove(single)
            removed.append(os.path.basename(single))
        return removed

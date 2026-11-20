import json
import os
from dataclasses import dataclass, field

from src.errors import NativaRuntimeError


@dataclass
class LibraryInfo:
    name: str
    path: str
    kind: str
    manifest: dict = field(default_factory=dict)

    @property
    def version(self):
        return self.manifest.get("version", "0.0.0")

    @property
    def dependencies(self):
        return list(self.manifest.get("dependencies", []))


class Registry:
    def __init__(self, search_dirs):
        self.search_dirs = []
        for directory in search_dirs:
            self.add_search_dir(directory)

    def add_search_dir(self, directory, first=False):
        directory = os.path.abspath(directory)
        if directory in self.search_dirs:
            return
        if first:
            self.search_dirs.insert(0, directory)
        else:
            self.search_dirs.append(directory)

    def read_manifest(self, package_dir, name):
        path = os.path.join(package_dir, "library.json")
        if not os.path.isfile(path):
            return {}
        try:
            with open(path, encoding="utf-8") as handle:
                manifest = json.load(handle)
        except (OSError, ValueError) as e:
            raise NativaRuntimeError(f"manifesto inválido da biblioteca '{name}': {e}", error_class="ImportError")
        if not isinstance(manifest, dict):
            raise NativaRuntimeError(f"manifesto inválido da biblioteca '{name}'", error_class="ImportError")
        deps = manifest.get("dependencies", [])
        if not isinstance(deps, list) or not all(isinstance(d, str) for d in deps):
            raise NativaRuntimeError(
                f"manifesto inválido da biblioteca '{name}': 'dependencies' deve ser uma lista de nomes",
                error_class="ImportError",
            )
        if "version" in manifest and not isinstance(manifest["version"], str):
            raise NativaRuntimeError(
                f"manifesto inválido da biblioteca '{name}': 'version' deve ser texto",
                error_class="ImportError",
            )
        return manifest

    def find_library(self, name):
        if not name or "/" in name or "\\" in name or name.startswith("."):
            return None
        for directory in self.search_dirs:
            package = os.path.join(directory, name)
            if os.path.isfile(os.path.join(package, "__init__.na")):
                return LibraryInfo(name, package, "package", self.read_manifest(package, name))
            single = os.path.join(directory, name + ".na")
            if os.path.isfile(single):
                return LibraryInfo(name, single, "file")
        return None

    def list_libraries(self):
        found = {}
        for directory in self.search_dirs:
            if not os.path.isdir(directory):
                continue
            for entry in sorted(os.listdir(directory)):
                full = os.path.join(directory, entry)
                if os.path.isdir(full) and os.path.isfile(os.path.join(full, "__init__.na")):
                    name = entry
                elif os.path.isfile(full) and entry.endswith(".na") and entry != "__init__.na":
                    name = entry[:-3]
                else:
                    continue
                if name not in found:
                    info = self.find_library(name)
                    if info is not None:
                        found[name] = info
        return list(found.values())

    def list_modules(self, info):
        if info.kind == "file":
            return {info.name: info.path}
        modules = {}
        for root, dirs, files in os.walk(info.path):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for filename in sorted(files):
                if not filename.endswith(".na"):
                    continue
                relative = os.path.relpath(os.path.join(root, filename), info.path)
                parts = relative[:-3].split(os.sep)
                if parts[-1] == "__init__":
                    parts = parts[:-1]
                modules[".".join([info.name] + parts)] = os.path.join(root, filename)
        return modules

    def is_namespace(self, dotted):
        parts = dotted.split(".")
        info = self.find_library(parts[0])
        if info is None or info.kind != "package" or len(parts) < 2:
            return False
        return os.path.isdir(os.path.join(info.path, *parts[1:]))

    def resolve_module(self, dotted):
        parts = dotted.split(".")
        info = self.find_library(parts[0])
        if info is None:
            return None
        if len(parts) == 1:
            path = info.path if info.kind == "file" else os.path.join(info.path, "__init__.na")
            return info, dotted, path
        if info.kind == "file":
            return None
        base = os.path.join(info.path, *parts[1:])
        for candidate in (base + ".na", os.path.join(base, "__init__.na")):
            if os.path.isfile(candidate):
                return info, dotted, candidate
        return None

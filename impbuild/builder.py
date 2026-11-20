import json
import os
import pickle
from dataclasses import dataclass, field

from src.errors import NativaRuntimeError

from .compiler import FORMAT_VERSION, LANGUAGE_VERSION


@dataclass
class BuildResult:
    library: str
    built: list = field(default_factory=list)
    cached: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)


class Builder:
    def __init__(self, registry, compiler, cache, is_external):
        self.registry = registry
        self.compiler = compiler
        self.cache = cache
        self.is_external = is_external
        self.done = {}

    def error(self, message):
        return NativaRuntimeError(message, error_class="ImportError")

    def invalidate(self, library=None):
        if library is None:
            self.done.clear()
        else:
            self.done.pop(library, None)

    def build(self, library, force=False, stack=()):
        if library in stack:
            chain = " -> ".join(stack + (library,))
            raise self.error(f"dependência circular entre bibliotecas: {chain}")
        if not force and library in self.done:
            return self.done[library]
        info = self.registry.find_library(library)
        if info is None:
            raise self.error(f"não foi possível importar '{library}': biblioteca não encontrada")
        result = BuildResult(library)
        for dependency in info.dependencies:
            self.require_dependency(info, dependency, "manifesto", force, stack, result)
        modules = self.registry.list_modules(info)
        index = self.cache.load(library)
        manifest_text = json.dumps(info.manifest, sort_keys=True)
        new_index = {}
        for name, path in sorted(modules.items()):
            with open(path, "rb") as handle:
                data = handle.read()
            key = self.cache.make_key(data, FORMAT_VERSION, LANGUAGE_VERSION, manifest_text)
            artifact = self.cache.artifact_path(name)
            entry = index.get(name)
            if not force and self.cache.is_fresh(entry, key, artifact):
                imports = entry.get("imports", [])
                new_index[name] = entry
                result.cached.append(name)
            else:
                compiled = self.compiler.compile(name, path)
                imports = compiled.imports
                self.write_artifact(artifact, compiled)
                new_index[name] = self.cache.make_entry(key, artifact, imports, path)
                result.built.append(name)
            for imported in imports:
                self.require_dependency(info, imported, f"módulo '{name}'", force, stack, result)
        self.cache.save(library, new_index)
        self.done[library] = result
        return result

    def require_dependency(self, info, dotted, origin, force, stack, result):
        top = dotted.split(".")[0]
        if top == info.name:
            if self.registry.resolve_module(dotted) is None:
                raise self.error(f"dependência '{dotted}' não encontrada (usada em {origin} de '{info.name}')")
            return
        if self.registry.find_library(top) is not None:
            if self.registry.resolve_module(dotted) is None:
                raise self.error(f"dependência '{dotted}' não encontrada (usada em {origin} de '{info.name}')")
            self.build(top, force, stack + (info.name,))
            if top not in result.dependencies:
                result.dependencies.append(top)
            return
        if not self.is_external(dotted):
            raise self.error(f"dependência '{dotted}' não encontrada (usada em {origin} de '{info.name}')")

    def write_artifact(self, artifact, compiled):
        os.makedirs(os.path.dirname(artifact), exist_ok=True)
        payload = {
            "format": FORMAT_VERSION,
            "language": LANGUAGE_VERSION,
            "name": compiled.name,
            "source_hash": compiled.source_hash,
            "imports": compiled.imports,
            "program": compiled.program,
        }
        temporary = artifact + ".tmp"
        with open(temporary, "wb") as handle:
            pickle.dump(payload, handle, protocol=4)
        os.replace(temporary, artifact)

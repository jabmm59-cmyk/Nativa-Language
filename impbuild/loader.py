import importlib
import importlib.util
import os
import pickle
import sys

from src.errors import NativaRuntimeError
from src.runtime import BuiltinFunction, Environment, NativaBuiltinError, NativeModule

from .builder import Builder
from .cache import BuildCache, sha256_file
from .compiler import FORMAT_VERSION, Compiler
from .registry import Registry

DEFAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def internal_modules():
    from backends import stdlib

    return stdlib.MODULES


def _compatible_in(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [_compatible_in(v) for v in value]
    if isinstance(value, dict):
        return {_compatible_in(k): _compatible_in(v) for k, v in value.items()}
    raise NativaBuiltinError("argumento incompatível com bibliotecas Python", "TypeError")


def _compatible_out(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_compatible_out(v) for v in value]
    if isinstance(value, dict):
        return {_compatible_out(k): _compatible_out(v) for k, v in value.items()}
    raise NativaBuiltinError("a função Python retornou um tipo incompatível com a Nativa", "TypeError")


def wrap_python_module(name, module):
    attrs = {}
    for key in dir(module):
        if key.startswith("_"):
            continue
        value = getattr(module, key)
        if value is None or isinstance(value, (bool, int, float, str)):
            attrs[key] = value
        elif callable(value) and not isinstance(value, type):
            attrs[key] = BuiltinFunction(f"{name}.{key}", _python_callable(value, f"{name}.{key}"))
    return NativeModule(name, attrs)


def _python_callable(function, label):
    def call(*args, **kwargs):
        args = [_compatible_in(a) for a in args]
        kwargs = {k: _compatible_in(v) for k, v in kwargs.items()}
        try:
            result = function(*args, **kwargs)
        except TypeError:
            raise NativaBuiltinError(f"{label}: argumentos inválidos", "TypeError")
        except ValueError:
            raise NativaBuiltinError(f"{label}: valor inválido", "ValueError")
        except OSError as e:
            raise NativaBuiltinError(f"{label}: {e.strerror or 'erro de sistema'}", "RuntimeError")
        return _compatible_out(result)

    return call


class Loader:
    def __init__(self, root=None, search_dirs=None, build_dir=None):
        self.root = os.path.abspath(root or DEFAULT_ROOT)
        build_dir = os.path.abspath(build_dir or os.path.join(self.root, "build"))
        if search_dirs is None:
            search_dirs = [os.path.join(self.root, "libraries")]
        self.registry = Registry(search_dirs)
        self.cache = BuildCache(os.path.join(build_dir, "cache"), os.path.join(build_dir, "libraries"))
        self.compiler = Compiler()
        self.builder = Builder(self.registry, self.compiler, self.cache, self.is_external)
        self.loaded = {}
        if self.root not in sys.path:
            sys.path.insert(0, self.root)

    def error(self, node, message, interp=None):
        if interp is not None:
            return interp.error(node, message, "ImportError")
        return NativaRuntimeError(message, error_class="ImportError")

    def native_path(self, dotted):
        parts = dotted.split(".")[1:]
        base = os.path.join(self.root, "backends", *parts)
        return base + ".py", base

    def is_external(self, dotted):
        if dotted in internal_modules():
            return True
        if dotted.split(".")[0] == "native":
            if dotted == "native":
                return True
            file_path, directory = self.native_path(dotted)
            return os.path.isfile(file_path) or os.path.isdir(directory)
        try:
            return importlib.util.find_spec(dotted) is not None
        except (ImportError, ValueError, AttributeError):
            return False

    def add_search_dir(self, directory):
        self.registry.add_search_dir(directory, first=True)

    def import_dotted(self, path, interp, node):
        parts = path.split(".")
        top = parent = module = None
        for index in range(len(parts)):
            dotted = ".".join(parts[: index + 1])
            module = self.load(dotted, interp, node)
            if parent is None:
                top = module
            else:
                parent.attrs[parts[index]] = module
            parent = module
        return top, module

    def load(self, dotted, interp, node=None):
        if dotted in self.loaded:
            return self.loaded[dotted]
        if dotted.split(".")[0] == "native":
            module = self.load_native(dotted, interp, node)
        elif dotted in internal_modules():
            module = self.load_internal(dotted)
        else:
            resolved = self.registry.resolve_module(dotted)
            if resolved is not None:
                return self.load_na(dotted, resolved, interp)
            if self.registry.is_namespace(dotted):
                module = NativeModule(dotted, {})
            else:
                module = self.load_python(dotted, interp, node)
        self.loaded[dotted] = module
        return module

    def load_internal(self, dotted):
        exports = internal_modules()[dotted]()
        return NativeModule(dotted, self.wrap_exports(dotted, exports))

    def wrap_exports(self, dotted, exports):
        attrs = {}
        for key, value in exports.items():
            if callable(value) and not isinstance(value, type):
                attrs[key] = BuiltinFunction(f"{dotted}.{key}", value)
            else:
                attrs[key] = value
        return attrs

    def load_native(self, dotted, interp, node):
        if dotted == "native":
            return NativeModule("native", {})
        file_path, directory = self.native_path(dotted)
        if os.path.isfile(file_path):
            module_name = "backends." + dotted.split(".", 1)[1]
            try:
                python_module = importlib.import_module(module_name)
            except ImportError as e:
                raise self.error(node, f"não foi possível importar '{dotted}': {e}", interp)
            factory = getattr(python_module, "exports", None)
            exports = factory(interp) if factory is not None else getattr(python_module, "EXPORTS", None)
            if not isinstance(exports, dict):
                raise self.error(node, f"não foi possível importar '{dotted}': backend sem 'exports'", interp)
            return NativeModule(dotted, self.wrap_exports(dotted, exports))
        if os.path.isdir(directory):
            return NativeModule(dotted, {})
        raise self.error(node, f"não foi possível importar '{dotted}': backend não encontrado", interp)

    def load_python(self, dotted, interp, node):
        try:
            if importlib.util.find_spec(dotted) is None:
                raise ImportError(dotted)
            python_module = importlib.import_module(dotted)
        except (ImportError, ValueError, AttributeError):
            raise self.error(node, f"não foi possível importar '{dotted}'", interp)
        return wrap_python_module(dotted, python_module)

    def read_artifact(self, name, library):
        entry = self.cache.load(library).get(name)
        artifact = self.cache.artifact_path(name)
        if entry is None or not os.path.isfile(artifact) or sha256_file(artifact) != entry.get("artifact_sha"):
            raise self.error(None, f"artefato de '{name}' ausente ou corrompido; reconstrua com 'nativa build {library} --force'")
        with open(artifact, "rb") as handle:
            payload = pickle.load(handle)
        if payload.get("format") != FORMAT_VERSION:
            raise self.error(None, f"artefato de '{name}' em formato incompatível; reconstrua a biblioteca")
        return payload

    def load_na(self, dotted, resolved, interp):
        info, name, path = resolved
        self.builder.build(info.name)
        payload = self.read_artifact(name, info.name)
        env = Environment(interp.builtins, is_module=True)
        module = NativeModule(name, env.vars)
        self.loaded[name] = module
        saved = interp.filename
        interp.filename = os.path.relpath(path, os.path.dirname(info.path)) if info.kind == "package" else os.path.basename(path)
        try:
            interp.exec_block(payload["program"].body, env)
        except BaseException:
            self.loaded.pop(name, None)
            raise
        finally:
            interp.filename = saved
        return module

    def unload(self, dotted):
        removed = [n for n in self.loaded if n == dotted or n.startswith(dotted + ".")]
        for name in removed:
            del self.loaded[name]
        if removed:
            self.builder.invalidate(dotted.split(".")[0])
        return bool(removed)

    def loaded_modules(self):
        return sorted(self.loaded)

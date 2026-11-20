MISSING = object()


class NativaBuiltinError(Exception):
    def __init__(self, message, error_class="ValueError"):
        super().__init__(message)
        self.error_class = error_class


class NativaThrow(Exception):
    def __init__(self, value, node=None):
        super().__init__("exceção Nativa")
        self.value = value
        self.node = node


class Environment:
    def __init__(self, parent=None, is_class=False, is_module=False):
        self.vars = {}
        self.parent = parent
        self.is_class = is_class
        self.is_module = is_module
        self.global_names = None
        self.nonlocal_names = None

    def module_env(self):
        env = self
        while env.parent is not None and not env.is_module:
            env = env.parent
        return env

    def define(self, name, value):
        if self.global_names and name in self.global_names:
            self.module_env().vars[name] = value
            return
        if self.nonlocal_names and name in self.nonlocal_names:
            env = self.parent
            while env is not None and not env.is_module:
                if name in env.vars and not env.is_class:
                    env.vars[name] = value
                    return
                env = env.parent
        self.vars[name] = value

    def remove(self, name):
        target = self.module_env() if self.global_names and name in self.global_names else self
        if name in target.vars:
            del target.vars[name]
            return True
        return False

    def lookup(self, name):
        env = self
        while env is not None:
            if name in env.vars:
                return True, env.vars[name]
            env = env.parent
        return False, None


class NativaFunction:
    def __init__(self, name, params, body, closure, defaults, is_async=False, filename=None):
        self.filename = filename
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure
        self.defaults = defaults
        self.is_async = is_async


class BuiltinFunction:
    def __init__(self, name, fn, needs_env=False):
        self.name = name
        self.fn = fn
        self.needs_env = needs_env


class NativeModule:
    def __init__(self, name, attrs):
        self.name = name
        self.attrs = attrs


class Coroutine:
    def __init__(self, fn, args, kwargs, node):
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.node = node
        self.task = None


class Task:
    def __init__(self, kind="coro", coro=None):
        import threading

        self.kind = kind
        self.coro = coro
        self.started = False
        self.done = False
        self.result = None
        self.error = None
        self.waiting_on = None
        self.wake = None
        self.children = []
        self.thread = None
        self.event = threading.Event()
        self.depth = 0
        self.filename = None


class SleepAwaitable:
    def __init__(self, seconds):
        self.seconds = seconds


class GatherAwaitable:
    def __init__(self, items):
        self.items = items


class NativaClass:
    def __init__(self, name, bases, attrs):
        self.name = name
        self.bases = bases
        self.attrs = attrs

    def find(self, name):
        if name in self.attrs:
            return self.attrs[name]
        for base in self.bases:
            found = base.find(name)
            if found is not MISSING:
                return found
        return MISSING


class NativaInstance:
    def __init__(self, cls):
        self.cls = cls
        self.fields = {}


class BoundMethod:
    def __init__(self, instance, func):
        self.instance = instance
        self.func = func


class BreakSignal(Exception):
    def __init__(self, node=None):
        self.node = node


class ContinueSignal(Exception):
    def __init__(self, node=None):
        self.node = node


class ReturnSignal(Exception):
    def __init__(self, value=None, node=None):
        self.value = value
        self.node = node


STR_METHODS = {
    "upper", "lower", "strip", "lstrip", "rstrip", "split", "join", "replace",
    "startswith", "endswith", "find", "count", "title", "capitalize",
    "isdigit", "isalpha",
}
LIST_METHODS = {
    "append", "pop", "insert", "remove", "index", "count", "sort", "reverse", "extend",
}
DICT_METHODS = {"keys", "values", "items", "get", "pop"}

METHODS = {str: STR_METHODS, list: LIST_METHODS, dict: DICT_METHODS}

_KEYS_TYPE = type({}.keys())
_VALUES_TYPE = type({}.values())
_ITEMS_TYPE = type({}.items())


def inherits(cls, base):
    if cls is base:
        return True
    return any(inherits(b, base) for b in cls.bases)


def adapt_result(result):
    if isinstance(result, (_KEYS_TYPE, _VALUES_TYPE)):
        return list(result)
    if isinstance(result, _ITEMS_TYPE):
        return [[k, v] for k, v in result]
    return result


def type_name(value):
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    if isinstance(value, range):
        return "rang"
    if isinstance(value, NativaInstance):
        return value.cls.name
    if isinstance(value, NativeModule):
        return "módulo"
    if isinstance(value, Coroutine):
        return "corrotina"
    if isinstance(value, (Task, SleepAwaitable, GatherAwaitable)):
        return "tarefa"
    if isinstance(value, NativaClass):
        return "classe"
    if isinstance(value, (NativaFunction, BuiltinFunction, BoundMethod)):
        return "função"
    return "objeto"


def describe_exception(error):
    if isinstance(error, ZeroDivisionError):
        return "divisão por zero"
    if isinstance(error, IndexError):
        return "índice fora do intervalo"
    if isinstance(error, KeyError):
        return "chave não encontrada"
    if isinstance(error, TypeError):
        return "tipo de argumento inválido"
    if isinstance(error, ValueError):
        return "valor inválido"
    if isinstance(error, OverflowError):
        return "resultado grande demais"
    return "falha na operação"


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def make_builtins(to_str):
    def b_len(x):
        if isinstance(x, (str, list, dict, range)):
            return len(x)
        raise NativaBuiltinError(f"len() não aceita valores do tipo {type_name(x)}", "TypeError")

    def b_int(x=0):
        if isinstance(x, (bool, int, float)):
            return int(x)
        if isinstance(x, str):
            try:
                return int(x.strip())
            except ValueError:
                raise NativaBuiltinError(f"não foi possível converter {x!r} para int")
        raise NativaBuiltinError(f"não foi possível converter {type_name(x)} para int", "TypeError")

    def b_float(x=0.0):
        if isinstance(x, (bool, int, float)):
            return float(x)
        if isinstance(x, str):
            try:
                return float(x.strip().replace(",", "."))
            except ValueError:
                raise NativaBuiltinError(f"não foi possível converter {x!r} para float")
        raise NativaBuiltinError(f"não foi possível converter {type_name(x)} para float", "TypeError")

    def b_str(x=""):
        return to_str(x)

    def b_bool(x=False):
        return bool(x)

    def b_abs(x):
        if not is_number(x):
            raise NativaBuiltinError(f"abs() não aceita valores do tipo {type_name(x)}", "TypeError")
        return abs(x)

    def _extremum(name, pick, args):
        values = list(args[0]) if len(args) == 1 and isinstance(args[0], (list, range)) else list(args)
        if not values:
            raise NativaBuiltinError(f"{name}() requer ao menos um valor")
        try:
            return pick(values)
        except TypeError:
            raise NativaBuiltinError(f"{name}() não consegue comparar esses valores")

    def b_min(*args):
        return _extremum("min", min, args)

    def b_max(*args):
        return _extremum("max", max, args)

    def b_round(x, digits=None):
        if not is_number(x):
            raise NativaBuiltinError(f"round() não aceita valores do tipo {type_name(x)}", "TypeError")
        if digits is None:
            return round(x)
        return round(x, digits)

    def b_list(x=()):
        if isinstance(x, dict):
            return list(x.keys())
        if isinstance(x, (list, str, range)):
            return list(x)
        raise NativaBuiltinError(f"list() não aceita valores do tipo {type_name(x)}", "TypeError")

    def b_rang(*args):
        if not 1 <= len(args) <= 3:
            raise NativaBuiltinError("rang() aceita de 1 a 3 argumentos")
        for a in args:
            if isinstance(a, bool) or not isinstance(a, int):
                raise NativaBuiltinError("rang() requer números inteiros", "TypeError")
        if len(args) == 3 and args[2] == 0:
            raise NativaBuiltinError("o passo de rang() não pode ser zero")
        return range(*args)

    return {
        "len": b_len, "int": b_int, "float": b_float, "str": b_str,
        "bool": b_bool, "abs": b_abs, "min": b_min, "max": b_max,
        "round": b_round, "list": b_list, "rang": b_rang,
    }

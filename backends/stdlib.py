import math as _math
import random as _random
import time as _time

from src.runtime import NativaBuiltinError, is_number


def _number(name, value):
    if not is_number(value):
        raise NativaBuiltinError(f"{name}() requer números", "TypeError")
    return value


def _math_function(name, function):
    def call(*args):
        for arg in args:
            _number(name, arg)
        try:
            return function(*args)
        except (ValueError, OverflowError, ZeroDivisionError):
            raise NativaBuiltinError(f"{name}(): argumento fora do domínio", "ValueError")
        except TypeError:
            raise NativaBuiltinError(f"{name}(): quantidade de argumentos inválida", "TypeError")

    return call


def make_math():
    functions = {
        "sqrt": _math.sqrt, "sin": _math.sin, "cos": _math.cos, "tan": _math.tan,
        "asin": _math.asin, "acos": _math.acos, "atan": _math.atan, "atan2": _math.atan2,
        "exp": _math.exp, "log": _math.log, "log10": _math.log10, "pow": _math.pow,
        "floor": _math.floor, "ceil": _math.ceil, "trunc": _math.trunc,
        "hypot": _math.hypot, "radians": _math.radians, "degrees": _math.degrees,
        "fabs": _math.fabs,
    }
    exports = {name: _math_function(name, fn) for name, fn in functions.items()}
    exports.update({"pi": _math.pi, "e": _math.e, "tau": _math.tau, "inf": _math.inf})
    return exports


def make_random():
    generator = _random.Random()

    def seed(value=None):
        if value is not None and not isinstance(value, (int, float, str)):
            raise NativaBuiltinError("seed() requer número ou texto", "TypeError")
        generator.seed(value)

    def rand():
        return generator.random()

    def randint(low, high):
        for value in (low, high):
            if isinstance(value, bool) or not isinstance(value, int):
                raise NativaBuiltinError("randint() requer números inteiros", "TypeError")
        if low > high:
            raise NativaBuiltinError("randint(): o mínimo não pode ser maior que o máximo", "ValueError")
        return generator.randint(low, high)

    def uniform(low, high):
        _number("uniform", low)
        _number("uniform", high)
        return generator.uniform(low, high)

    def choice(items):
        if not isinstance(items, (list, str, range)):
            raise NativaBuiltinError("choice() requer lista, texto ou rang", "TypeError")
        if len(items) == 0:
            raise NativaBuiltinError("choice(): sequência vazia", "ValueError")
        return generator.choice(items)

    def shuffle(items):
        if not isinstance(items, list):
            raise NativaBuiltinError("shuffle() requer uma lista", "TypeError")
        generator.shuffle(items)

    def sample(items, count):
        if not isinstance(items, list):
            raise NativaBuiltinError("sample() requer uma lista", "TypeError")
        if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= len(items):
            raise NativaBuiltinError("sample(): quantidade inválida", "ValueError")
        return generator.sample(items, count)

    return {
        "seed": seed, "rand": rand, "randint": randint, "uniform": uniform,
        "choice": choice, "shuffle": shuffle, "sample": sample,
    }


def make_time():
    def now():
        return _time.time()

    def monotonic():
        return _time.monotonic()

    def sleep(seconds):
        if not is_number(seconds) or seconds < 0:
            raise NativaBuiltinError("sleep() requer um número não negativo", "ValueError")
        _time.sleep(seconds)

    return {"now": now, "monotonic": monotonic, "sleep": sleep}


MODULES = {"math": make_math, "random": make_random, "time": make_time}

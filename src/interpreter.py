import importlib
import operator
import sys
import types

from . import ast_nodes as A
from .errors import NativaError, NativaRuntimeError, NativaSyntaxError
from .runtime import (
    METHODS, MISSING, BoundMethod, BreakSignal, BuiltinFunction, ContinueSignal,
    Environment, NativaBuiltinError, NativaClass, NativaException, NativaFunction, NativaInstance,
    ReturnSignal, adapt_result, describe_exception, make_builtins, type_name,
)

MAX_CALL_DEPTH = 400

BINOPS = {
    "+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv,
    "//": operator.floordiv, "%": operator.mod, "**": operator.pow,
}

COMPARATORS = {
    "==": operator.eq, "!=": operator.ne, "<": operator.lt, ">": operator.gt,
    "<=": operator.le, ">=": operator.ge, "is": operator.is_, "is not": operator.is_not,
}


class NativaModuleWrapper:
    """Wrap a Nativa library's exports as a module-like object."""
    def __init__(self, exports, name, interpreter):
        self._exports = exports
        self._name = name
        self._interpreter = interpreter

    def __getattr__(self, name):
        if name in self._exports:
            return self._interpreter._wrap_python_value(self._exports[name])
        raise AttributeError(f"módulo '{self._name}' não possui '{name}'")

    def __dir__(self):
        return list(self._exports.keys())


class Interpreter:
    def __init__(self, filename="<principal>", out=None, input_fn=None):
        sys.setrecursionlimit(max(sys.getrecursionlimit(), 20000))
        self.filename = filename
        self.out = out if out is not None else sys.stdout
        self.input_fn = input_fn if input_fn is not None else input
        self.depth = 0
        self.globals = Environment()
        for name, fn in make_builtins(self.to_str).items():
            self.globals.define(name, BuiltinFunction(name, fn))

    def error(self, node, message):
        return NativaRuntimeError(
            message, getattr(node, "line", None), getattr(node, "col", None), self.filename
        )

    def run(self, program):
        try:
            self.exec_block(program.body, self.globals)
        except (BreakSignal, ContinueSignal) as signal:
            word = "brk" if isinstance(signal, BreakSignal) else "continue"
            raise self.error(signal.node, f"'{word}' fora de um laço")
        except RecursionError:
            raise self.error(None, "limite de recursão excedido")

    def to_str(self, value, top=True):
        if value is None:
            return "None"
        if isinstance(value, bool):
            return "True" if value else "False"
        if isinstance(value, str):
            return value if top else "'" + value + "'"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, list):
            return "[" + ", ".join(self.to_str(v, False) for v in value) + "]"
        if isinstance(value, dict):
            items = (f"{self.to_str(k, False)}: {self.to_str(v, False)}" for k, v in value.items())
            return "{" + ", ".join(items) + "}"
        if isinstance(value, range):
            if value.step == 1:
                return f"rang({value.start}, {value.stop})"
            return f"rang({value.start}, {value.stop}, {value.step})"
        if isinstance(value, NativaInstance):
            method = value.cls.find("__str__")
            if isinstance(method, NativaFunction):
                result = self.call_function(method, [value], {}, None)
                return result if isinstance(result, str) else self.to_str(result)
            return f"<{value.cls.name} instância>"
        if isinstance(value, NativaClass):
            return f"<classe {value.name}>"
        if isinstance(value, NativaFunction):
            return f"<função {value.name}>"
        if isinstance(value, NativaExceptionWrapper):
            return str(value)
        if isinstance(value, BoundMethod):
            return f"<método {value.func.name}>"
        if isinstance(value, BuiltinFunction):
            return f"<função nativa {value.name}>"
        return "<objeto>"

    def exec_block(self, statements, env):
        for stmt in statements:
            self.execute(stmt, env)

    def execute(self, node, env):
        return getattr(self, "exec_" + type(node).__name__)(node, env)

    def evaluate(self, node, env):
        return getattr(self, "eval_" + type(node).__name__)(node, env)

    def exec_ExprStmt(self, node, env):
        self.evaluate(node.expr, env)

    def exec_Assign(self, node, env):
        value = self.evaluate(node.value, env)
        target = node.target
        if isinstance(target, A.Name):
            env.define(target.id, value)
        elif isinstance(target, A.Attr):
            obj = self.evaluate(target.obj, env)
            self.set_attr(obj, target.name, value, target)
        else:
            obj = self.evaluate(target.obj, env)
            index = self.evaluate(target.index, env)
            self.set_index(obj, index, value, target)

    def exec_Shw(self, node, env):
        args = [self.to_str(self.evaluate(a, env)) for a in node.args]
        options = {"sep": " ", "end": "\n"}
        for name, expr in node.kwargs:
            if name not in options:
                raise self.error(node, f"shw não aceita o argumento '{name}'")
            value = self.evaluate(expr, env)
            if not isinstance(value, str):
                raise self.error(expr, f"'{name}' de shw deve ser texto")
            options[name] = value
        self.out.write(options["sep"].join(args) + options["end"])

    def exec_If(self, node, env):
        if self.evaluate(node.test, env):
            self.exec_block(node.body, env)
        else:
            self.exec_block(node.orelse, env)

    def exec_While(self, node, env):
        while self.evaluate(node.test, env):
            try:
                self.exec_block(node.body, env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def exec_For(self, node, env):
        iterable = self.evaluate(node.iterable, env)
        if not isinstance(iterable, (list, str, dict, range)):
            raise self.error(node.iterable, f"valores do tipo {type_name(iterable)} não são iteráveis")
        if isinstance(iterable, dict):
            iterable = list(iterable.keys())
        for item in iterable:
            env.define(node.var, item)
            try:
                self.exec_block(node.body, env)
            except BreakSignal:
                break
            except ContinueSignal:
                continue

    def exec_Break(self, node, env):
        raise BreakSignal(node)

    def exec_Continue(self, node, env):
        raise ContinueSignal(node)

    def exec_Return(self, node, env):
        if self.depth == 0:
            raise self.error(node, "'ret' fora de uma função")
        value = None if node.value is None else self.evaluate(node.value, env)
        raise ReturnSignal(value, node)

    def exec_Try(self, node, env):
        try:
            self.exec_block(node.body, env)
        except Exception as e:
            caught = False
            for handler in node.handlers:
                if self._match_exception(e, handler, env):
                    caught = True
                    break
            if not caught:
                raise
        finally:
            if node.finalbody:
                self.exec_block(node.finalbody, env)

    def _match_exception(self, exc, handler, env):
        # Check if exception type matches
        if handler.type is not None:
            exc_type_val = self.evaluate(handler.type, env)
            # Handle NativaClass as exception type
            if isinstance(exc_type_val, NativaClass):
                # Check if exc is NativaException wrapping matching instance
                if isinstance(exc, NativaException):
                    if not isinstance(exc.args[0], NativaInstance):
                        return False
                    if not self._is_instance_of(exc.args[0], exc_type_val):
                        return False
                else:
                    return False
            elif isinstance(exc_type_val, type):
                if not isinstance(exc, exc_type_val):
                    return False
            else:
                raise self.error(handler.type, "tipo de exceção inválido")
        # Bind exception to variable if specified
        if handler.name is not None:
            env.define(handler.name, self._wrap_exception(exc))
        # Execute handler body
        try:
            self.exec_block(handler.body, env)
        except (BreakSignal, ContinueSignal, ReturnSignal):
            # Re-raise control flow signals
            raise
        return True

    def _is_instance_of(self, instance, cls):
        """Check if a NativaInstance is an instance of a NativaClass (including inheritance)."""
        current = instance.cls
        while current is not None:
            if current == cls:
                return True
            current = current.bases[0] if current.bases else None
        return False

    def _wrap_exception(self, exc):
        """Wrap a Python exception in a Nativa-accessible object."""
        if isinstance(exc, NativaRuntimeError):
            return NativaExceptionWrapper(exc, self)
        elif isinstance(exc, NativaError):
            return NativaExceptionWrapper(exc, self)
        elif isinstance(exc, NativaException):
            return NativaExceptionWrapper(exc, self)
        else:
            return NativaExceptionWrapper(NativaRuntimeError(str(exc), None, None, self.filename), self)
        # Execute handler body
        try:
            self.exec_block(handler.body, env)
        except (BreakSignal, ContinueSignal, ReturnSignal):
            # Re-raise control flow signals
            raise
        return True

    def exec_Raise(self, node, env):
        if node.exc is None:
            # Re-raise - not supported at top level, need context
            raise self.error(node, "'perror' sem argumento só permitido dentro de 'xcept'")
        exc_val = self.evaluate(node.exc, env)
        # If it's a Nativa class instance, wrap in NativaException
        if isinstance(exc_val, NativaInstance):
            raise NativaException(exc_val)
        # If it's a string, raise as runtime error
        if isinstance(exc_val, str):
            raise NativaRuntimeError(exc_val, node.line, node.col, self.filename)
        # Otherwise convert to string
        raise NativaRuntimeError(str(exc_val), node.line, node.col, self.filename)

    def exec_FuncDef(self, node, env):
        defaults = {}
        for param in node.params:
            if param.default is not None:
                defaults[param.name] = self.evaluate(param.default, env)
        closure = env.parent if env.is_class else env
        env.define(node.name, NativaFunction(node.name, node.params, node.body, closure, defaults))

    def exec_ClassDef(self, node, env):
        bases = []
        for expr in node.bases:
            base = self.evaluate(expr, env)
            if not isinstance(base, NativaClass):
                raise self.error(expr, "a base de uma classe deve ser outra classe")
            bases.append(base)
        class_env = Environment(env, is_class=True)
        self.exec_block(node.body, class_env)
        env.define(node.name, NativaClass(node.name, bases, dict(class_env.vars)))

    def exec_Import(self, node, env):
        for module_name, alias in node.names:
            # Try to load as Nativa library via impbuild first
            try:
                from impbuild.loader import load_library
                loaded_lib = load_library(module_name)
                # Wrap the loaded library's exports as a module-like object
                nativa_module = NativaModuleWrapper(loaded_lib.exports, module_name, self)
                name = alias if alias else module_name
                env.define(name, nativa_module)
                continue
            except (ImportError, FileNotFoundError, AttributeError):
                # Fall back to Python import
                pass

            # Try Python import
            try:
                module = importlib.import_module(module_name)
            except ImportError as e:
                raise self.error(node, f"não foi possível importar o módulo '{module_name}': {e}")
            name = alias if alias else module_name
            env.define(name, self._wrap_python_module(module))

    def exec_ImportFrom(self, node, env):
        module_name = node.module
        if node.level > 0:
            # Relative import - for now, treat as absolute
            raise self.error(node, "importações relativas não são suportadas ainda")

        # Try to load as Nativa library via impbuild first
        loaded_lib = None
        try:
            from impbuild.loader import load_library
            loaded_lib = load_library(module_name)
        except (ImportError, FileNotFoundError, AttributeError):
            # Fall back to Python import
            pass

        if loaded_lib is None:
            # Try Python import
            try:
                module = importlib.import_module(module_name)
            except ImportError as e:
                raise self.error(node, f"não foi possível importar o módulo '{module_name}': {e}")
            for name, alias in node.names:
                if not hasattr(module, name):
                    raise self.error(node, f"o módulo '{module_name}' não possui o atributo '{name}'")
                value = getattr(module, name)
                wrapped = self._wrap_python_value(value)
                env.define(alias if alias else name, wrapped)
        else:
            # Use Nativa library exports
            for name, alias in node.names:
                if name not in loaded_lib.exports:
                    raise self.error(node, f"o módulo '{module_name}' não exporta '{name}'")
                value = loaded_lib.exports[name]
                wrapped = self._wrap_python_value(value)
                env.define(alias if alias else name, wrapped)

    def _wrap_python_module(self, module):
        """Wrap a Python module as a Nativa-accessible object."""
        return PythonModuleWrapper(module, self)

    def _wrap_python_value(self, value):
        """Convert a Python value to a Nativa-compatible value."""
        # Handle Nativa's own types first (don't wrap them)
        from .runtime import NativaClass, NativaFunction, NativaInstance, NativaException
        if isinstance(value, (NativaClass, NativaFunction, NativaInstance, NativaException)):
            return value

        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple)):
            return [self._wrap_python_value(v) for v in value]
        if isinstance(value, dict):
            return {self._wrap_python_value(k): self._wrap_python_value(v) for k, v in value.items()}
        if isinstance(value, range):
            return value
        if isinstance(value, types.FunctionType):
            return PythonFunctionWrapper(value, self)
        if isinstance(value, type):
            return PythonClassWrapper(value, self)
        if hasattr(value, '__call__'):
            return PythonCallableWrapper(value, self)
        # For other objects, wrap them
        return PythonObjectWrapper(value, self)

    def eval_Num(self, node, env):
        return node.value

    def eval_Str(self, node, env):
        return node.value

    def eval_Const(self, node, env):
        return node.value

    def eval_Interp(self, node, env):
        out = []
        for part in node.parts:
            out.append(part if isinstance(part, str) else self.to_str(self.evaluate(part, env)))
        return "".join(out)

    def eval_Name(self, node, env):
        found, value = env.lookup(node.id)
        if not found:
            raise self.error(node, f"nome '{node.id}' não está definido")
        return value

    def eval_ListLit(self, node, env):
        return [self.evaluate(item, env) for item in node.items]

    def eval_DictLit(self, node, env):
        result = {}
        for key_node, value_node in node.pairs:
            key = self.evaluate(key_node, env)
            try:
                result[key] = self.evaluate(value_node, env)
            except TypeError:
                raise self.error(key_node, f"valores do tipo {type_name(key)} não podem ser chaves")
        return result

    def eval_Utype(self, node, env):
        prompt = "" if node.prompt is None else self.to_str(self.evaluate(node.prompt, env))
        self.out.write(prompt)
        flush = getattr(self.out, "flush", None)
        if flush:
            flush()
        try:
            line = self.input_fn("")
        except EOFError:
            raise self.error(node, "entrada encerrada ao executar utype")
        return line.rstrip("\n")

    def eval_Unary(self, node, env):
        value = self.evaluate(node.operand, env)
        if node.op == "not":
            return not value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise self.error(node, f"operador '{node.op}' não suporta {type_name(value)}")
        return -value if node.op == "-" else +value

    def eval_BinOp(self, node, env):
        left = self.evaluate(node.left, env)
        right = self.evaluate(node.right, env)
        try:
            return BINOPS[node.op](left, right)
        except ZeroDivisionError:
            raise self.error(node, "divisão por zero")
        except TypeError:
            raise self.error(
                node,
                f"operação '{node.op}' não suportada entre {type_name(left)} e {type_name(right)}",
            )
        except OverflowError:
            raise self.error(node, "resultado grande demais")

    def eval_BoolOp(self, node, env):
        left = self.evaluate(node.left, env)
        if node.op == "and":
            return self.evaluate(node.right, env) if left else left
        return left if left else self.evaluate(node.right, env)

    def eval_Compare(self, node, env):
        left = self.evaluate(node.left, env)
        for op, right_node in zip(node.ops, node.rights):
            right = self.evaluate(right_node, env)
            if not self.compare(op, left, right, node):
                return False
            left = right
        return True

    def compare(self, op, left, right, node):
        try:
            if op == "in":
                return left in right
            if op == "not in":
                return left not in right
            return COMPARATORS[op](left, right)
        except TypeError:
            raise self.error(
                node,
                f"operação '{op}' não suportada entre {type_name(left)} e {type_name(right)}",
            )

    def eval_Index(self, node, env):
        obj = self.evaluate(node.obj, env)
        index = self.evaluate(node.index, env)
        if not isinstance(obj, (list, str, dict, range)):
            raise self.error(node, f"valores do tipo {type_name(obj)} não são indexáveis")
        if not isinstance(obj, dict) and (isinstance(index, bool) or not isinstance(index, int)):
            raise self.error(node, "o índice deve ser um número inteiro")
        try:
            return obj[index]
        except IndexError:
            raise self.error(node, f"índice {index} fora do intervalo")
        except KeyError:
            raise self.error(node, f"chave {self.to_str(index, False)} não encontrada")
        except TypeError:
            raise self.error(node, "chave inválida")

    def set_index(self, obj, index, value, node):
        if not isinstance(obj, (list, dict)):
            raise self.error(node, f"valores do tipo {type_name(obj)} não aceitam alteração por índice")
        if isinstance(obj, list) and (isinstance(index, bool) or not isinstance(index, int)):
            raise self.error(node, "o índice deve ser um número inteiro")
        try:
            obj[index] = value
        except IndexError:
            raise self.error(node, f"índice {index} fora do intervalo")
        except TypeError:
            raise self.error(node, "chave inválida")

    def eval_Attr(self, node, env):
        return self.get_attr(self.evaluate(node.obj, env), node.name, node)

    def get_attr(self, obj, name, node):
        if isinstance(obj, NativaInstance):
            if name in obj.fields:
                return obj.fields[name]
            found = obj.cls.find(name)
            if found is not MISSING:
                return BoundMethod(obj, found) if isinstance(found, NativaFunction) else found
            raise self.error(node, f"'{obj.cls.name}' não possui o atributo '{name}'")
        if isinstance(obj, NativaClass):
            found = obj.find(name)
            if found is not MISSING:
                return found
            raise self.error(node, f"a classe '{obj.name}' não possui o atributo '{name}'")
        if isinstance(obj, str) and name == "dr":
            return obj.strip().lower()
        # Handle Python wrapper objects and Nativa module wrapper
        if isinstance(obj, (PythonModuleWrapper, PythonClassWrapper, PythonObjectWrapper, PythonFunctionWrapper, PythonCallableWrapper, NativaExceptionWrapper, NativaModuleWrapper)):
            try:
                return getattr(obj, name)
            except AttributeError:
                raise self.error(node, f"objeto Python não possui o atributo '{name}'")
        allowed = METHODS.get(type(obj))
        if allowed is not None and name in allowed:
            method = getattr(obj, name)

            def call(*args, **kwargs):
                return adapt_result(method(*args, **kwargs))

            return BuiltinFunction(f"{type_name(obj)}.{name}", call)
        raise self.error(node, f"valores do tipo {type_name(obj)} não possuem o atributo '{name}'")

    def set_attr(self, obj, name, value, node):
        if isinstance(obj, NativaInstance):
            obj.fields[name] = value
        elif isinstance(obj, NativaClass):
            obj.attrs[name] = value
        else:
            raise self.error(node, f"valores do tipo {type_name(obj)} não aceitam atributos")

    def eval_Call(self, node, env):
        func = self.evaluate(node.func, env)
        args = [self.evaluate(a, env) for a in node.args]
        kwargs = {}
        for name, expr in node.kwargs:
            if name in kwargs:
                raise self.error(expr, f"argumento '{name}' repetido")
            kwargs[name] = self.evaluate(expr, env)
        return self.call_value(func, args, kwargs, node)

    def call_value(self, func, args, kwargs, node):
        if isinstance(func, NativaFunction):
            return self.call_function(func, args, kwargs, node)
        if isinstance(func, BoundMethod):
            return self.call_function(func.func, [func.instance] + args, kwargs, node)
        if isinstance(func, BuiltinFunction):
            try:
                return func.fn(*args, **kwargs)
            except NativaError:
                raise
            except NativaBuiltinError as e:
                raise self.error(node, str(e))
            except RecursionError:
                raise
            except Exception as e:
                raise self.error(node, f"{func.name}: {describe_exception(e)}")
        if isinstance(func, NativaClass):
            return self.instantiate(func, args, kwargs, node)
        # Handle Python wrapper callables
        if isinstance(func, (PythonFunctionWrapper, PythonClassWrapper, PythonCallableWrapper, PythonObjectWrapper)):
            try:
                return func(*args, **kwargs)
            except NativaError:
                raise
            except NativaBuiltinError as e:
                raise self.error(node, str(e))
            except RecursionError:
                raise
            except Exception as e:
                raise self.error(node, f"{func.name}: {describe_exception(e)}")
        raise self.error(node, f"valores do tipo {type_name(func)} não são chamáveis")

    def instantiate(self, cls, args, kwargs, node):
        instance = NativaInstance(cls)
        init = cls.find("__init__")
        if isinstance(init, NativaFunction):
            self.call_function(init, [instance] + args, kwargs, node)
        elif args or kwargs:
            raise self.error(node, f"a classe '{cls.name}' não aceita argumentos")
        return instance

    def call_function(self, fn, args, kwargs, node):
        if self.depth >= MAX_CALL_DEPTH:
            raise self.error(node, "profundidade máxima de chamadas excedida")
        env = Environment(fn.closure)
        regular = [p for p in fn.params if not p.vararg]
        vararg = next((p for p in fn.params if p.vararg), None)
        if len(args) > len(regular) and vararg is None:
            raise self.error(
                node,
                f"'{fn.name}' espera no máximo {len(regular)} argumento(s), recebeu {len(args)}",
            )
        for param, value in zip(regular, args):
            env.define(param.name, value)
        if vararg is not None:
            env.define(vararg.name, list(args[len(regular):]))
        names = {p.name for p in regular}
        for name, value in kwargs.items():
            if name not in names:
                raise self.error(node, f"'{fn.name}' não possui o parâmetro '{name}'")
            if name in env.vars:
                raise self.error(node, f"'{fn.name}' recebeu múltiplos valores para '{name}'")
            env.define(name, value)
        for param in regular:
            if param.name not in env.vars:
                if param.name in fn.defaults:
                    env.define(param.name, fn.defaults[param.name])
                else:
                    raise self.error(node, f"'{fn.name}' requer o argumento '{param.name}'")
        self.depth += 1
        try:
            self.exec_block(fn.body, env)
        except ReturnSignal as signal:
            return signal.value
        except (BreakSignal, ContinueSignal) as signal:
            word = "brk" if isinstance(signal, BreakSignal) else "continue"
            raise self.error(signal.node, f"'{word}' fora de um laço")
        finally:
            self.depth -= 1
        return None


class PythonModuleWrapper:
    """Wrapper for Python modules to make them accessible from Nativa."""
    def __init__(self, module, interpreter):
        self._module = module
        self._interpreter = interpreter

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        value = getattr(self._module, name)
        return self._interpreter._wrap_python_value(value)

    def __dir__(self):
        return [name for name in dir(self._module) if not name.startswith('_')]


class PythonFunctionWrapper:
    """Wrapper for Python functions to make them callable from Nativa."""
    def __init__(self, func, interpreter):
        self._func = func
        self._interpreter = interpreter
        self.name = getattr(func, '__name__', 'função_python')

    def __call__(self, *args, **kwargs):
        py_args = [self._unwrap_for_python(arg) for arg in args]
        py_kwargs = {k: self._unwrap_for_python(v) for k, v in kwargs.items()}
        try:
            result = self._func(*py_args, **py_kwargs)
            return self._interpreter._wrap_python_value(result)
        except Exception as e:
            raise NativaBuiltinError(f"{self.name}: {describe_exception(e)}")

    def _unwrap_for_python(self, value):
        if isinstance(value, (NativaInstance, NativaClass, NativaFunction, BoundMethod, BuiltinFunction)):
            return value
        return value


class PythonClassWrapper:
    """Wrapper for Python classes to make them instantiable from Nativa."""
    def __init__(self, cls, interpreter):
        self._cls = cls
        self._interpreter = interpreter
        self.name = getattr(cls, '__name__', 'ClassePython')

    def __call__(self, *args, **kwargs):
        py_args = [self._unwrap_for_python(arg) for arg in args]
        py_kwargs = {k: self._unwrap_for_python(v) for k, v in kwargs.items()}
        try:
            instance = self._cls(*py_args, **py_kwargs)
            return PythonObjectWrapper(instance, self._interpreter)
        except Exception as e:
            raise NativaBuiltinError(f"{self.name}: {describe_exception(e)}")

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        value = getattr(self._cls, name)
        return self._interpreter._wrap_python_value(value)

    def _unwrap_for_python(self, value):
        if isinstance(value, (NativaInstance, NativaClass, NativaFunction, BoundMethod, BuiltinFunction)):
            return value
        return value


class PythonCallableWrapper:
    """Wrapper for generic Python callables."""
    def __init__(self, callable_obj, interpreter):
        self._callable = callable_obj
        self._interpreter = interpreter
        self.name = getattr(callable_obj, '__name__', 'callable_python')

    def __call__(self, *args, **kwargs):
        py_args = [self._unwrap_for_python(arg) for arg in args]
        py_kwargs = {k: self._unwrap_for_python(v) for k, v in kwargs.items()}
        try:
            result = self._callable(*py_args, **py_kwargs)
            return self._interpreter._wrap_python_value(result)
        except Exception as e:
            raise NativaBuiltinError(f"{self.name}: {describe_exception(e)}")

    def _unwrap_for_python(self, value):
        if isinstance(value, (NativaInstance, NativaClass, NativaFunction, BoundMethod, BuiltinFunction)):
            return value
        return value


class PythonObjectWrapper:
    """Wrapper for generic Python objects."""
    def __init__(self, obj, interpreter):
        self._obj = obj
        self._interpreter = interpreter

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        try:
            value = getattr(self._obj, name)
            return self._interpreter._wrap_python_value(value)
        except AttributeError:
            raise NativaRuntimeError(f"objeto Python não possui o atributo '{name}'", None, None, self._interpreter.filename)

    def __setattr__(self, name, value):
        if name in ('_obj', '_interpreter'):
            super().__setattr__(name, value)
        else:
            try:
                if hasattr(value, '_obj'):
                    value = value._obj
                setattr(self._obj, name, value)
            except Exception as e:
                raise NativaRuntimeError(f"erro ao definir atributo '{name}': {e}", None, None, self._interpreter.filename)

    def __call__(self, *args, **kwargs):
        py_args = [self._unwrap_for_python(arg) for arg in args]
        py_kwargs = {k: self._unwrap_for_python(v) for k, v in kwargs.items()}
        try:
            result = self._obj(*py_args, **py_kwargs)
            return self._interpreter._wrap_python_value(result)
        except Exception as e:
            raise NativaBuiltinError(f"chamada falhou: {describe_exception(e)}")

    def _unwrap_for_python(self, value):
        if isinstance(value, (NativaInstance, NativaClass, NativaFunction, BoundMethod, BuiltinFunction)):
            return value
        return value


class NativaExceptionWrapper:
    """Wrapper for exceptions to make them accessible from Nativa."""
    def __init__(self, exc, interpreter):
        self._exc = exc
        self._interpreter = interpreter

    def __getattr__(self, name):
        if name == "msg":
            return getattr(self._exc, 'message', str(self._exc))
        if name == "message":
            return getattr(self._exc, 'message', str(self._exc))
        if name == "args":
            return getattr(self._exc, 'args', ())
        raise NativaRuntimeError(f"exceção não possui o atributo '{name}'", None, None, self._interpreter.filename)

    def __str__(self):
        # Return just the message without location info
        msg = getattr(self._exc, 'message', str(self._exc))
        # Remove location prefix if present (e.g., "Erro de execução em file, linha X, coluna Y: ")
        if ": " in msg and "linha" in msg:
            parts = msg.split(": ", 2)
            if len(parts) >= 3:
                return parts[2]
        return msg

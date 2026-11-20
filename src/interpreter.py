import operator
import sys

from . import ast_nodes as A
from .asyncrt import Scheduler
from .errors import NativaError, NativaRuntimeError, classify_message
from .parser import parse
from .prelude import PRELUDE
from .runtime import (
    METHODS, MISSING, BoundMethod, BreakSignal, BuiltinFunction, ContinueSignal,
    Coroutine, Environment, GatherAwaitable, NativaBuiltinError, NativaClass,
    NativaFunction, NativaInstance, NativaThrow, NativeModule, SleepAwaitable,
    Task, ReturnSignal, adapt_result, describe_exception, inherits, is_number,
    make_builtins, type_name,
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


class Interpreter:
    def __init__(self, filename="<principal>", out=None, input_fn=None, loader=None, script_dir=None):
        sys.setrecursionlimit(max(sys.getrecursionlimit(), 20000))
        self.filename = filename
        self.loader = loader
        self.script_dir = script_dir
        self.out = out if out is not None else sys.stdout
        self.input_fn = input_fn if input_fn is not None else input
        self.depth = 0
        self.builtins = Environment()
        self.globals = Environment(self.builtins, is_module=True)
        for name, fn in make_builtins(self.to_str).items():
            self.builtins.define(name, BuiltinFunction(name, fn))
        self.scheduler = Scheduler(self)
        self.install_async_builtins()
        self.exec_block(parse(PRELUDE, "<prelude>").body, self.builtins)

    def install_async_builtins(self):
        def b_sleep(seconds=0):
            if not is_number(seconds) or seconds < 0:
                raise NativaBuiltinError("sleep() requer um número não negativo", "ValueError")
            return SleepAwaitable(float(seconds))

        def b_gather(*items):
            if len(items) == 1 and isinstance(items[0], list):
                items = items[0]
            return GatherAwaitable(list(items))

        def b_spawn(coro):
            if not isinstance(coro, Coroutine):
                raise NativaBuiltinError("spawn() requer uma corrotina", "TypeError")
            return self.scheduler.spawn(coro)

        def b_runasync(awaitable):
            if self.scheduler.current is not None:
                raise NativaBuiltinError("runasync() não pode ser usado dentro de uma corrotina", "RuntimeError")
            return self.scheduler.await_(awaitable, None)

        def b_reexport(env, module):
            if not isinstance(module, NativeModule):
                raise NativaBuiltinError("reexport() requer um módulo", "TypeError")
            target = env.module_env().vars
            for key, value in module.attrs.items():
                if not key.startswith("_"):
                    target[key] = value

        for name, fn in (("sleep", b_sleep), ("gather", b_gather), ("spawn", b_spawn), ("runasync", b_runasync)):
            self.builtins.define(name, BuiltinFunction(name, fn))
        self.builtins.define("reexport", BuiltinFunction("reexport", b_reexport, needs_env=True))

        def b_typeof(value):
            return type_name(value)

        def b_hasattr(obj, name):
            if not isinstance(name, str):
                raise NativaBuiltinError("hasattr() requer o nome do atributo como texto", "TypeError")
            if isinstance(obj, NativaInstance):
                return name in obj.fields or obj.cls.find(name) is not MISSING
            if isinstance(obj, NativaClass):
                return obj.find(name) is not MISSING
            if isinstance(obj, NativeModule):
                return name in obj.attrs
            if isinstance(obj, str) and name == "dr":
                return True
            allowed = METHODS.get(type(obj))
            return allowed is not None and name in allowed

        self.builtins.define("typeof", BuiltinFunction("typeof", b_typeof))
        self.builtins.define("hasattr", BuiltinFunction("hasattr", b_hasattr))

    def get_loader(self):
        if self.loader is None:
            from impbuild.loader import Loader

            self.loader = Loader()
            if self.script_dir:
                self.loader.add_search_dir(self.script_dir)
        return self.loader

    def exec_Import(self, node, env):
        loader = self.get_loader()
        for item in node.items:
            try:
                top, leaf = loader.import_dotted(item.path, self, item)
            except NativaRuntimeError as e:
                if e.line is None:
                    e.line, e.col, e.filename = item.line, item.col, self.filename
                raise
            if item.alias:
                env.define(item.alias, leaf)
            else:
                env.define(item.path.split(".")[0], top)

    def error(self, node, message, error_class=None):
        return NativaRuntimeError(
            message, getattr(node, "line", None), getattr(node, "col", None), self.filename,
            error_class or classify_message(message),
        )

    def make_exception(self, class_name, message, line=None, col=None):
        found, cls = self.builtins.lookup(class_name)
        if not found:
            found, cls = self.builtins.lookup("RuntimeError")
        instance = NativaInstance(cls)
        instance.fields["message"] = message
        instance.fields["line"] = line
        instance.fields["col"] = col
        return instance

    def throw(self, class_name, message, node):
        raise NativaThrow(
            self.make_exception(class_name, message, getattr(node, "line", None), getattr(node, "col", None)),
            node,
        )

    def to_exception(self, caught):
        if isinstance(caught, NativaThrow):
            return caught.value
        if isinstance(caught, NativaRuntimeError):
            return self.make_exception(caught.error_class, caught.message, caught.line, caught.col)
        return self.make_exception("RuntimeError", "limite de recursão excedido")

    def uncaught(self, signal):
        instance = signal.value
        node = signal.node
        line = getattr(node, "line", None) or instance.fields.get("line")
        col = getattr(node, "col", None) or instance.fields.get("col")
        return NativaRuntimeError(
            f"{instance.cls.name}: {self.to_str(instance)}", line, col, self.filename, instance.cls.name
        )

    def run(self, program):
        try:
            self.exec_block(program.body, self.globals)
        except (BreakSignal, ContinueSignal) as signal:
            word = "brk" if isinstance(signal, BreakSignal) else "continue"
            raise self.error(signal.node, f"'{word}' fora de um laço")
        except NativaThrow as signal:
            raise self.uncaught(signal)
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
        if isinstance(value, NativeModule):
            return f"<módulo {value.name}>"
        if isinstance(value, Coroutine):
            return f"<corrotina {value.fn.name}>"
        if isinstance(value, (Task, SleepAwaitable, GatherAwaitable)):
            return "<tarefa>"
        if isinstance(value, NativaClass):
            return f"<classe {value.name}>"
        if isinstance(value, NativaFunction):
            return f"<função {value.name}>"
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

    def exec_FuncDef(self, node, env):
        defaults = {}
        for param in node.params:
            if param.default is not None:
                defaults[param.name] = self.evaluate(param.default, env)
        closure = env.parent if env.is_class else env
        env.define(
            node.name,
            NativaFunction(node.name, node.params, node.body, closure, defaults, node.is_async, self.filename),
        )

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
        if isinstance(obj, NativeModule):
            if name in obj.attrs:
                return obj.attrs[name]
            raise self.error(node, f"o módulo '{obj.name}' não possui o atributo '{name}'")
        if isinstance(obj, str) and name == "dr":
            return obj.strip().lower()
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
        return self.call_value(func, args, kwargs, node, env)

    def call_value(self, func, args, kwargs, node, env=None):
        if isinstance(func, NativaFunction):
            return self.call_function(func, args, kwargs, node)
        if isinstance(func, BoundMethod):
            return self.call_function(func.func, [func.instance] + args, kwargs, node)
        if isinstance(func, BuiltinFunction):
            if func.needs_env:
                args = [env] + args
            try:
                return func.fn(*args, **kwargs)
            except (NativaError, NativaThrow):
                raise
            except NativaBuiltinError as e:
                raise self.error(node, str(e), e.error_class)
            except RecursionError:
                raise
            except Exception as e:
                raise self.error(node, f"{func.name}: {describe_exception(e)}")
        if isinstance(func, NativaClass):
            return self.instantiate(func, args, kwargs, node)
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
        if fn.is_async:
            return Coroutine(fn, args, kwargs, node)
        return self.invoke(fn, args, kwargs, node)

    def invoke(self, fn, args, kwargs, node):
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
        saved_file = self.filename
        if fn.filename:
            self.filename = fn.filename
        try:
            self.exec_block(fn.body, env)
        except ReturnSignal as signal:
            return signal.value
        except (BreakSignal, ContinueSignal) as signal:
            word = "brk" if isinstance(signal, BreakSignal) else "continue"
            raise self.error(signal.node, f"'{word}' fora de um laço")
        finally:
            self.depth -= 1
            self.filename = saved_file
        return None

    def exec_Pass(self, node, env):
        return None

    def exec_Try(self, node, env):
        try:
            try:
                self.exec_block(node.body, env)
            except (NativaThrow, NativaRuntimeError, RecursionError) as caught:
                instance = self.to_exception(caught)
                for handler in node.handlers:
                    if self.handler_matches(handler, instance, env):
                        if handler.name:
                            env.define(handler.name, instance)
                        self.exec_block(handler.body, env)
                        break
                else:
                    raise
        finally:
            if node.final is not None:
                self.exec_block(node.final, env)

    def handler_matches(self, handler, instance, env):
        if not handler.types:
            return True
        for expr in handler.types:
            cls = self.evaluate(expr, env)
            if not isinstance(cls, NativaClass):
                raise self.error(expr, "'xcept' requer uma classe de exceção")
            if inherits(instance.cls, cls):
                return True
        return False

    def exec_Perror(self, node, env):
        value = self.evaluate(node.value, env)
        base = self.builtins.lookup("Exception")[1]
        if isinstance(value, NativaClass) and inherits(value, base):
            value = self.instantiate(value, [], {}, node)
        if not (isinstance(value, NativaInstance) and inherits(value.cls, base)):
            raise self.error(node, "'perror' requer uma exceção (instância de Exception)")
        value.fields.setdefault("line", node.line)
        value.fields.setdefault("col", node.col)
        raise NativaThrow(value, node)

    def exec_Verf(self, node, env):
        if not self.evaluate(node.test, env):
            message = "verificação falhou"
            if node.message is not None:
                message = self.to_str(self.evaluate(node.message, env))
            self.throw("AssertionError", message, node)

    def exec_Del(self, node, env):
        for target in node.targets:
            if isinstance(target, A.Name):
                if not env.remove(target.id):
                    raise self.error(target, f"nome '{target.id}' não está definido")
            elif isinstance(target, A.Attr):
                obj = self.evaluate(target.obj, env)
                if not isinstance(obj, NativaInstance) or target.name not in obj.fields:
                    raise self.error(target, f"não há o atributo '{target.name}' para excluir")
                del obj.fields[target.name]
            else:
                obj = self.evaluate(target.obj, env)
                index = self.evaluate(target.index, env)
                if not isinstance(obj, (list, dict)):
                    raise self.error(target, f"valores do tipo {type_name(obj)} não aceitam exclusão por índice")
                try:
                    del obj[index]
                except IndexError:
                    raise self.error(target, f"índice {index} fora do intervalo")
                except KeyError:
                    raise self.error(target, f"chave {self.to_str(index, False)} não encontrada")
                except TypeError:
                    raise self.error(target, "chave inválida")

    def exec_Glob(self, node, env):
        if env.global_names is None:
            env.global_names = set()
        env.global_names.update(node.names)

    def exec_Nolocal(self, node, env):
        for name in node.names:
            scope = env.parent
            found = False
            while scope is not None and not scope.is_module:
                if name in scope.vars and not scope.is_class:
                    found = True
                    break
                scope = scope.parent
            if not found:
                raise self.error(node, f"nolocal '{name}': nenhuma variável encontrada em escopo envolvente")
            if env.nonlocal_names is None:
                env.nonlocal_names = set()
            env.nonlocal_names.add(name)

    def exec_With(self, node, env):
        self.run_with(node, 0, env)

    def run_with(self, node, index, env):
        if index == len(node.items):
            self.exec_block(node.body, env)
            return
        item = node.items[index]
        manager = self.evaluate(item.expr, env)
        if not (
            isinstance(manager, NativaInstance)
            and isinstance(manager.cls.find("__enter__"), NativaFunction)
            and isinstance(manager.cls.find("__exit__"), NativaFunction)
        ):
            raise self.error(item, "'wth' requer um gerenciador de contexto (com __enter__ e __exit__)")
        enter = self.get_attr(manager, "__enter__", item)
        leave = self.get_attr(manager, "__exit__", item)
        value = self.call_value(enter, [], {}, item)
        if item.name:
            env.define(item.name, value)
        try:
            self.run_with(node, index + 1, env)
        except (NativaThrow, NativaRuntimeError, RecursionError) as caught:
            if not self.call_value(leave, [self.to_exception(caught)], {}, item):
                raise
        except (BreakSignal, ContinueSignal, ReturnSignal):
            self.call_value(leave, [None], {}, item)
            raise
        else:
            self.call_value(leave, [None], {}, item)

    def eval_Lambda(self, node, env):
        defaults = {}
        for param in node.params:
            if param.default is not None:
                defaults[param.name] = self.evaluate(param.default, env)
        body = [A.Return(node.body, line=node.line, col=node.col)]
        return NativaFunction("<afction>", node.params, body, env, defaults, False, self.filename)

    def eval_Await(self, node, env):
        return self.scheduler.await_(self.evaluate(node.value, env), node)

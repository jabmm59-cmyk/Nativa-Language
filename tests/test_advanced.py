import time
import unittest
from textwrap import dedent

from tests.helpers import run
from src.errors import NativaRuntimeError, NativaSyntaxError


def na(code):
    return dedent(code).lstrip("\n")


class TestExceptions(unittest.TestCase):
    def test_catch_perror(self):
        code = na("""
            try: (
                perror ValueError("ruim")
            )
            xcept ValueError as e: (
                shw "pegou", e
            )
        """)
        self.assertEqual(run(code), "pegou ruim\n")

    def test_catch_by_base_class(self):
        code = na("""
            try: (
                perror KeyError("k")
            )
            xcept Exception as e: (
                shw "base", e.message
            )
        """)
        self.assertEqual(run(code), "base k\n")

    def test_handler_order_and_bare(self):
        code = na("""
            df t(err): (
                try: (
                    perror err
                )
                xcept ValueError: (
                    ret "value"
                )
                xcept TypeError, KeyError: (
                    ret "type-or-key"
                )
                xcept: (
                    ret "outro"
                )
            )
            shw t(ValueError("a")), t(KeyError("b")), t(IndexError("c"))
        """)
        self.assertEqual(run(code), "value type-or-key outro\n")

    def test_internal_errors_are_catchable(self):
        cases = {
            "1 / 0": "ZeroDivisionError",
            "[1][5]": "IndexError",
            "{'a': 1}['b']": "KeyError",
            "nope": "NameError",
            "1 + 'a'": "TypeError",
            "int('x')": "ValueError",
            "'a'.foo": "AttributeError",
        }
        for expr, name in cases.items():
            code = na(f"""
                try: (
                    x = {expr}
                )
                xcept {name} as e: (
                    shw "ok"
                )
            """)
            self.assertEqual(run(code), "ok\n", expr)

    def test_error_not_matching_propagates(self):
        code = na("""
            try: (
                x = 1 / 0
            )
            xcept KeyError: (
                shw "errado"
            )
        """)
        with self.assertRaises(NativaRuntimeError) as ctx:
            run(code)
        self.assertIn("divisão por zero", str(ctx.exception))

    def test_finally_always_runs(self):
        code = na("""
            try: (
                shw "a"
            )
            idgafatc: (
                shw "fim"
            )
            try: (
                try: (
                    perror ValueError("x")
                )
                idgafatc: (
                    shw "limpeza"
                )
            )
            xcept ValueError: (
                shw "externo"
            )
        """)
        self.assertEqual(run(code), "a\nfim\nlimpeza\nexterno\n")

    def test_finally_runs_on_return_and_break(self):
        code = na("""
            df f(): (
                try: (
                    ret 1
                )
                idgafatc: (
                    shw "f"
                )
            )
            shw f()
            for i in rang(3): (
                try: (
                    brk
                )
                idgafatc: (
                    shw "loop"
                )
            )
        """)
        self.assertEqual(run(code), "f\n1\nloop\n")

    def test_xcept_with_finally(self):
        code = na("""
            try: (
                perror Exception("e")
            )
            xcept Exception as err: (
                shw "c", err
            )
            idgafatc: (
                shw "f"
            )
        """)
        self.assertEqual(run(code), "c e\nf\n")

    def test_custom_exception(self):
        code = na("""
            classify MeuErro(Exception): (
                df __init__(urself, code): (
                    urself.code = code
                    urself.message = "codigo {code}"
                )
            )
            try: (
                perror MeuErro(42)
            )
            xcept MeuErro as e: (
                shw e.code, e
            )
        """)
        self.assertEqual(run(code), "42 codigo 42\n")

    def test_perror_class_directly(self):
        code = 'try: (\n    perror ValueError\n)\nxcept ValueError as e: (\n    shw "[{e}]"\n)'
        self.assertEqual(run(code), "[]\n")

    def test_perror_invalid(self):
        for bad in ('perror "texto"', "perror 5"):
            with self.assertRaises(NativaRuntimeError):
                run(bad)

    def test_uncaught_perror_message(self):
        with self.assertRaises(NativaRuntimeError) as ctx:
            run('shw 1\nperror ValueError("falhou")')
        self.assertIn("ValueError: falhou", str(ctx.exception))
        self.assertEqual(ctx.exception.line, 2)

    def test_reraise(self):
        code = na("""
            try: (
                try: (
                    perror ValueError("x")
                )
                xcept ValueError as e: (
                    shw "interno"
                    perror e
                )
            )
            xcept ValueError as e2: (
                shw "externo", e2
            )
        """)
        self.assertEqual(run(code), "interno\nexterno x\n")

    def test_error_carries_position(self):
        code = 'try: (\n    x = 1 / 0\n)\nxcept ZeroDivisionError as e: (\n    shw e.line\n)'
        self.assertEqual(run(code), "2\n")

    def test_recursion_is_catchable(self):
        code = na("""
            df f(): (
                ret f()
            )
            try: (
                f()
            )
            xcept RuntimeError as e: (
                shw "recursão"
            )
        """)
        self.assertEqual(run(code), "recursão\n")

    def test_try_requires_handler(self):
        with self.assertRaises(NativaSyntaxError):
            run("try: (\n    shw 1\n)")

    def test_bare_xcept_must_be_last(self):
        code = "try: (\n    shw 1\n)\nxcept: (\n    shw 2\n)\nxcept ValueError: (\n    shw 3\n)"
        with self.assertRaises(NativaSyntaxError):
            run(code)

    def test_xcept_requires_class(self):
        code = "try: (\n    perror ValueError()\n)\nxcept 5: (\n    shw 1\n)"
        with self.assertRaises(NativaRuntimeError):
            run(code)


class TestSmallCommands(unittest.TestCase):
    def test_tpvfetc(self):
        code = "if True: (\n    tpvfetc\n)\nclassify A: (\n    tpvfetc\n)\nshw 1"
        self.assertEqual(run(code), "1\n")

    def test_verf(self):
        self.assertEqual(run("verf 1 == 1\nverf True, 'm'\nshw 'ok'"), "ok\n")
        with self.assertRaises(NativaRuntimeError) as ctx:
            run('verf 1 == 2, "números diferentes"')
        self.assertIn("AssertionError: números diferentes", str(ctx.exception))

    def test_verf_catchable(self):
        code = 'try: (\n    verf False\n)\nxcept AssertionError as e: (\n    shw e\n)'
        self.assertEqual(run(code), "verificação falhou\n")

    def test_dlt_variable(self):
        code = "x = 1\ndlt x\ntry: (\n    shw x\n)\nxcept NameError: (\n    shw 'apagada'\n)"
        self.assertEqual(run(code), "apagada\n")

    def test_dlt_items(self):
        code = "n = [1, 2, 3]\nd = {'a': 1, 'b': 2}\ndlt n[0], d['a']\nshw n, d"
        self.assertEqual(run(code), "[2, 3] {'b': 2}\n")

    def test_dlt_attribute(self):
        code = "classify A: (\n    df __init__(urself): (\n        urself.x = 1\n    )\n)\na = A()\ndlt a.x\nshw 'ok'"
        self.assertEqual(run(code), "ok\n")

    def test_dlt_errors(self):
        for bad in ("dlt nada", "n = [1]\ndlt n[5]", "d = {}\ndlt d['x']"):
            with self.assertRaises(NativaRuntimeError):
                run(bad)

    def test_glob(self):
        code = na("""
            counter = 0
            df inc(): (
                glob counter
                counter = counter + 1
            )
            inc()
            inc()
            shw counter
        """)
        self.assertEqual(run(code), "2\n")

    def test_glob_creates_global(self):
        code = "df f(): (\n    glob novo\n    novo = 7\n)\nf()\nshw novo"
        self.assertEqual(run(code), "7\n")

    def test_without_glob_is_local(self):
        code = "c = 0\ndf f(): (\n    c = 5\n)\nf()\nshw c"
        self.assertEqual(run(code), "0\n")

    def test_nolocal(self):
        code = na("""
            df counter(): (
                n = 0
                df inc(): (
                    nolocal n
                    n = n + 1
                    ret n
                )
                ret inc
            )
            c = counter()
            c()
            c()
            shw c()
        """)
        self.assertEqual(run(code), "3\n")

    def test_nolocal_without_binding(self):
        for bad in ("nolocal x", "df f(): (\n    nolocal zz\n)\nf()"):
            with self.assertRaises(NativaRuntimeError):
                run(bad)

    def test_afction(self):
        code = na("""
            dobro = afction x: x * 2
            soma = afction a, b = 10: a + b
            shw dobro(4), soma(1), soma(1, 2)
            shw (afction: 99)()
        """)
        self.assertEqual(run(code), "8 11 3\n99\n")

    def test_afction_as_argument_and_closure(self):
        code = na("""
            df aplicar(f, v): (
                ret f(v)
            )
            n = 5
            shw aplicar(afction x: x + n, 1)
            shw aplicar(afction x: x * x, 7)
        """)
        self.assertEqual(run(code), "6\n49\n")

    def test_afction_varargs(self):
        self.assertEqual(run("f = afction *xs: len(xs)\nshw f(1, 2, 3)"), "3\n")

    def test_afction_in_collections(self):
        code = "fs = [afction x: x + 1, afction x: x * 3]\nshw fs[0](1), fs[1](2)"
        self.assertEqual(run(code), "2 6\n")


class TestWith(unittest.TestCase):
    MANAGER = na("""
        classify Gerente: (
            df __init__(urself, nome, suprime = False): (
                urself.nome = nome
                urself.suprime = suprime
            )
            df __enter__(urself): (
                shw "entra", urself.nome
                ret urself.nome
            )
            df __exit__(urself, erro): (
                shw "sai", urself.nome, erro
                ret urself.suprime
            )
        )
    """)

    def test_basic(self):
        code = self.MANAGER + 'wth Gerente("a") as g: (\n    shw "dentro", g\n)\n'
        self.assertEqual(run(code), "entra a\ndentro a\nsai a None\n")

    def test_exit_on_error_propagates(self):
        code = self.MANAGER + 'try: (\n    wth Gerente("a"): (\n        perror ValueError("x")\n    )\n)\nxcept ValueError: (\n    shw "fora"\n)\n'
        self.assertEqual(run(code), "entra a\nsai a x\nfora\n")

    def test_suppress(self):
        code = self.MANAGER + 'wth Gerente("a", True): (\n    perror ValueError("x")\n)\nshw "seguiu"\n'
        self.assertEqual(run(code), "entra a\nsai a x\nseguiu\n")

    def test_multiple_items_exit_order(self):
        code = self.MANAGER + 'wth Gerente("a"), Gerente("b"): (\n    shw "x"\n)\n'
        self.assertEqual(run(code), "entra a\nentra b\nx\nsai b None\nsai a None\n")

    def test_exit_on_return_and_break(self):
        code = self.MANAGER + 'df f(): (\n    wth Gerente("a"): (\n        ret 5\n    )\n)\nshw f()\nfor i in rang(2): (\n    wth Gerente("l"): (\n        brk\n    )\n)\n'
        self.assertEqual(run(code), "entra a\nsai a None\n5\nentra l\nsai l None\n")

    def test_invalid_manager(self):
        with self.assertRaises(NativaRuntimeError):
            run("wth 5: (\n    shw 1\n)")


class TestAsync(unittest.TestCase):
    def test_basic_await(self):
        code = na("""
            dsync df soma(a, b): (
                ret a + b
            )
            dsync df principal(): (
                r = dwait soma(1, 2)
                ret r * 10
            )
            shw runasync(principal())
        """)
        self.assertEqual(run(code), "30\n")

    def test_top_level_dwait(self):
        code = "dsync df f(): (\n    ret 7\n)\nshw dwait f()"
        self.assertEqual(run(code), "7\n")

    def test_call_returns_coroutine_without_running(self):
        code = 'dsync df f(): (\n    shw "rodou"\n    ret 1\n)\nc = f()\nshw "antes"\nshw dwait c'
        self.assertEqual(run(code), "antes\nrodou\n1\n")

    def test_gather_runs_concurrently(self):
        code = na("""
            dsync df tarefa(nome, espera): (
                shw "inicio", nome
                dwait sleep(espera)
                shw "fim", nome
                ret nome
            )
            dsync df principal(): (
                r = dwait gather(tarefa("lenta", 0.06), tarefa("rapida", 0.01))
                ret r
            )
            shw runasync(principal())
        """)
        start = time.monotonic()
        out = run(code)
        elapsed = time.monotonic() - start
        self.assertEqual(out, "inicio lenta\ninicio rapida\nfim rapida\nfim lenta\n['lenta', 'rapida']\n")
        self.assertLess(elapsed, 0.2)

    def test_spawn(self):
        code = na("""
            dsync df bg(): (
                dwait sleep(0.01)
                shw "bg"
                ret 5
            )
            dsync df principal(): (
                t = spawn(bg())
                shw "principal"
                v = dwait t
                ret v
            )
            shw runasync(principal())
        """)
        self.assertEqual(run(code), "principal\nbg\n5\n")

    def test_exception_propagates_through_await(self):
        code = na("""
            dsync df falha(): (
                perror ValueError("async")
            )
            dsync df principal(): (
                try: (
                    dwait falha()
                )
                xcept ValueError as e: (
                    ret "pegou {e}"
                )
            )
            shw runasync(principal())
        """)
        self.assertEqual(run(code), "pegou async\n")

    def test_uncaught_async_error(self):
        code = "dsync df f(): (\n    perror ValueError('x')\n)\nrunasync(f())"
        with self.assertRaises(NativaRuntimeError) as ctx:
            run(code)
        self.assertIn("ValueError: x", str(ctx.exception))

    def test_async_method(self):
        code = na("""
            classify S: (
                dsync df dobra(urself, x): (
                    dwait sleep(0)
                    ret x * 2
                )
            )
            shw dwait S().dobra(21)
        """)
        self.assertEqual(run(code), "42\n")

    def test_recursion_depth_tracked_per_task(self):
        code = na("""
            dsync df rec(n): (
                if n == 0: (
                    ret 0
                )
                ret 1 + dwait rec(n - 1)
            )
            shw dwait rec(30)
        """)
        self.assertEqual(run(code), "30\n")

    def test_dwait_invalid(self):
        with self.assertRaises(NativaRuntimeError):
            run("dwait 5")

    def test_sleep_validation(self):
        with self.assertRaises(NativaRuntimeError):
            run("sleep(-1)")

    def test_dsync_requires_df(self):
        with self.assertRaises(NativaSyntaxError):
            run("dsync x = 1")


if __name__ == "__main__":
    unittest.main()

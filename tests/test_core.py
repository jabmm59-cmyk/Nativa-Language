import unittest
from textwrap import dedent

from tests.helpers import run
from src.errors import NativaRuntimeError, NativaSyntaxError


def na(code):
    return dedent(code).lstrip("\n")


class TestOutputAndVariables(unittest.TestCase):
    def test_shw_basic(self):
        self.assertEqual(run('shw "Hello, World!"'), "Hello, World!\n")

    def test_shw_multiple_and_sep(self):
        self.assertEqual(run('shw "Olá", "Mundo", sep = "-"'), "Olá-Mundo\n")
        self.assertEqual(run('shw 1, 2, 3'), "1 2 3\n")

    def test_shw_end(self):
        self.assertEqual(run('shw "a", end = ""\nshw "b"'), "ab\n")

    def test_shw_empty(self):
        self.assertEqual(run("shw"), "\n")

    def test_shw_unknown_kwarg(self):
        with self.assertRaises(NativaRuntimeError):
            run('shw 1, foo = "x"')

    def test_variables(self):
        self.assertEqual(run('name = "João"\nage = 12\nnumber = 10.5\nshw name, age, number'), "João 12 10.5\n")

    def test_utype(self):
        code = 'name = utype "Qual é seu nome? "\nshw name'
        self.assertEqual(run(code, ["Ana"]), "Qual é seu nome? Ana\n")

    def test_utype_eof(self):
        with self.assertRaises(NativaRuntimeError):
            run('x = utype "?"')

    def test_booleans_and_none(self):
        self.assertEqual(run("shw True, False, None"), "True False None\n")


class TestStringsAndComments(unittest.TestCase):
    def test_interpolation(self):
        self.assertEqual(run('name = "João"\nshw "Olá, {name}!"'), "Olá, João!\n")

    def test_interpolation_expression(self):
        self.assertEqual(run('shw "Resultado: {10 + 20}"'), "Resultado: 30\n")

    def test_interpolation_with_string_inside(self):
        self.assertEqual(run('d = {"a": 1}\nshw "v={d[\'a\']}"'), "v=1\n")

    def test_interpolation_escape_braces(self):
        self.assertEqual(run('shw "{{x}}"'), "{x}\n")

    def test_interpolation_errors(self):
        for bad in ('shw "{x"', 'shw "{}"', 'shw "a}"'):
            with self.assertRaises(NativaSyntaxError):
                run(bad)

    def test_dr(self):
        self.assertEqual(run('name = "  JOÃO  "\nname = name.dr\nshw name'), "joão\n")

    def test_comment(self):
        self.assertEqual(run("# comentário #\nshw 1 # outro # \nshw 2"), "1\n2\n")

    def test_multiline_comment(self):
        self.assertEqual(run("# a\nb\nc #\nshw 1"), "1\n")

    def test_unclosed_comment(self):
        with self.assertRaises(NativaSyntaxError):
            run("# aberto\nshw 1")

    def test_hash_inside_string_is_not_comment(self):
        self.assertEqual(run('shw "a#b"'), "a#b\n")

    def test_escapes(self):
        self.assertEqual(run('shw "a\\tb"'), "a\tb\n")

    def test_string_methods(self):
        self.assertEqual(run('shw "a,b".split(","), "ab".upper()'), "['a', 'b'] AB\n")


class TestOperators(unittest.TestCase):
    def test_arithmetic(self):
        self.assertEqual(run("shw 7 + 3, 7 - 3, 7 * 3, 7 / 2, 7 // 2, 7 % 3, 2 ** 10"), "10 4 21 3.5 3 1 1024\n")

    def test_precedence(self):
        self.assertEqual(run("shw 2 + 3 * 4, (2 + 3) * 4, 2 ** 3 ** 2, -2 ** 2, 10 - 4 - 3"), "14 20 512 -4 3\n")

    def test_comparison(self):
        self.assertEqual(run("shw 1 == 1, 1 != 1, 1 < 2, 2 > 3, 2 <= 2, 3 >= 4"), "True False True False True False\n")

    def test_chained_comparison(self):
        self.assertEqual(run("shw 1 < 2 < 3, 1 < 3 < 2"), "True False\n")

    def test_logic(self):
        self.assertEqual(run("shw True and False, True or False, not True"), "False True False\n")

    def test_logic_precedence_and_short_circuit(self):
        self.assertEqual(run("shw True or False and False"), "True\n")
        self.assertEqual(run("shw False and (1 / 0)"), "False\n")
        self.assertEqual(run("shw 0 or 5"), "5\n")

    def test_in_and_is(self):
        code = 'shw 2 in [1, 2], 5 not in [1, 2], "a" in "abc", None is None, 1 is not None'
        self.assertEqual(run(code), "True True True True True\n")

    def test_division_by_zero(self):
        with self.assertRaises(NativaRuntimeError) as ctx:
            run("shw 1 / 0")
        self.assertIn("divisão por zero", str(ctx.exception))

    def test_type_error(self):
        with self.assertRaises(NativaRuntimeError):
            run('shw 1 + "a"')

    def test_string_concat_and_repeat(self):
        self.assertEqual(run('shw "a" + "b", "ab" * 2'), "ab abab\n")


class TestControlFlow(unittest.TestCase):
    def test_if_else_chain(self):
        code = na("""
            df classify_age(age): (
                if age >= 18: (
                    ret "adulto"
                )
                else if age >= 13: (
                    ret "adolescente"
                )
                else: (
                    ret "menor"
                )
            )
            shw classify_age(20), classify_age(15), classify_age(5)
        """)
        self.assertEqual(run(code), "adulto adolescente menor\n")

    def test_multiple_else_if(self):
        code = na("""
            x = 3
            if x == 1: (
                shw "um"
            )
            else if x == 2: (
                shw "dois"
            )
            else if x == 3: (
                shw "três"
            )
            else: (
                shw "outro"
            )
        """)
        self.assertEqual(run(code), "três\n")

    def test_if_without_else_followed_by_statement(self):
        code = na("""
            if False: (
                shw "não"
            )
            shw "sim"
        """)
        self.assertEqual(run(code), "sim\n")

    def test_one_line_block(self):
        self.assertEqual(run('if True: ( shw "ok" )'), "ok\n")

    def test_while(self):
        code = na("""
            x = 0
            while x < 3: (
                shw x
                x = x + 1
            )
        """)
        self.assertEqual(run(code), "0\n1\n2\n")

    def test_for_rang(self):
        code = na("""
            for x in rang(0, 3): (
                shw x
            )
        """)
        self.assertEqual(run(code), "0\n1\n2\n")

    def test_for_rang_variants(self):
        self.assertEqual(run("for i in rang(3): ( shw i )"), "0\n1\n2\n")
        self.assertEqual(run("for i in rang(0, 10, 5): ( shw i )"), "0\n5\n")

    def test_brk_and_continue(self):
        code = na("""
            for x in rang(0, 10): (
                if x == 2: (
                    continue
                )
                if x == 4: (
                    brk
                )
                shw x
            )
        """)
        self.assertEqual(run(code), "0\n1\n3\n")

    def test_brk_in_while_nested(self):
        code = na("""
            i = 0
            while True: (
                i = i + 1
                for j in rang(0, 5): (
                    if j == 1: (
                        brk
                    )
                )
                if i == 3: (
                    brk
                )
            )
            shw i
        """)
        self.assertEqual(run(code), "3\n")

    def test_for_over_list_string_dict(self):
        self.assertEqual(run("for x in [1, 2]: ( shw x )"), "1\n2\n")
        self.assertEqual(run('for c in "ab": ( shw c )'), "a\nb\n")
        self.assertEqual(run('for k in {"a": 1, "b": 2}: ( shw k )'), "a\nb\n")

    def test_brk_outside_loop(self):
        with self.assertRaises(NativaRuntimeError):
            run("brk")


class TestFunctions(unittest.TestCase):
    def test_basic(self):
        code = na("""
            df sum(a, b): (
                ret a + b
            )
            result = sum(10, 20)
            shw result
        """)
        self.assertEqual(run(code), "30\n")

    def test_defaults_and_kwargs(self):
        code = na("""
            df greet(name, greeting = "Olá"): (
                ret "{greeting}, {name}"
            )
            shw greet("Ana")
            shw greet("Ana", "Oi")
            shw greet(greeting = "E aí", name = "Beto")
        """)
        self.assertEqual(run(code), "Olá, Ana\nOi, Ana\nE aí, Beto\n")

    def test_varargs(self):
        code = na("""
            df total(*nums): (
                t = 0
                for n in nums: (
                    t = t + n
                )
                ret t
            )
            shw total(1, 2, 3), total()
        """)
        self.assertEqual(run(code), "6 0\n")

    def test_no_return_is_none(self):
        self.assertEqual(run("df f(): (\n    x = 1\n)\nshw f()"), "None\n")

    def test_recursion(self):
        code = na("""
            df fib(n): (
                if n < 2: (
                    ret n
                )
                ret fib(n - 1) + fib(n - 2)
            )
            shw fib(15)
        """)
        self.assertEqual(run(code), "610\n")

    def test_deep_recursion(self):
        code = na("""
            df down(n): (
                if n == 0: (
                    ret 0
                )
                ret 1 + down(n - 1)
            )
            shw down(300)
        """)
        self.assertEqual(run(code), "300\n")

    def test_infinite_recursion_is_error(self):
        with self.assertRaises(NativaRuntimeError):
            run("df f(): (\n    ret f()\n)\nf()")

    def test_closure(self):
        code = na("""
            df make(n): (
                df add(x): (
                    ret x + n
                )
                ret add
            )
            add5 = make(5)
            shw add5(10)
        """)
        self.assertEqual(run(code), "15\n")

    def test_local_scope_does_not_leak(self):
        code = na("""
            df f(): (
                hidden = 1
            )
            f()
            shw hidden
        """)
        with self.assertRaises(NativaRuntimeError):
            run(code)

    def test_argument_errors(self):
        with self.assertRaises(NativaRuntimeError):
            run("df f(a): (\n    ret a\n)\nf()")
        with self.assertRaises(NativaRuntimeError):
            run("df f(a): (\n    ret a\n)\nf(1, 2)")
        with self.assertRaises(NativaRuntimeError):
            run("df f(a): (\n    ret a\n)\nf(b = 1)")

    def test_ret_outside_function(self):
        with self.assertRaises(NativaRuntimeError):
            run("ret 1")

    def test_function_can_shadow_builtin(self):
        self.assertEqual(run("df len(x): (\n    ret 42\n)\nshw len([1])"), "42\n")


class TestClasses(unittest.TestCase):
    def test_spec_example(self):
        code = na("""
            classify Person: (
                df __init__(urself, name): (
                    urself.name = name
                )

                df greet(urself): (
                    shw "Olá, {urself.name}"
                )
            )

            person = Person("João")
            person.greet()
        """)
        self.assertEqual(run(code), "Olá, João\n")

    def test_attributes_and_state(self):
        code = na("""
            classify Counter: (
                df __init__(urself): (
                    urself.n = 0
                )
                df inc(urself, by = 1): (
                    urself.n = urself.n + by
                    ret urself
                )
            )
            c = Counter()
            c.inc()
            c.inc(5)
            shw c.n
        """)
        self.assertEqual(run(code), "6\n")

    def test_instances_are_independent(self):
        code = na("""
            classify Box: (
                df __init__(urself, v): (
                    urself.v = v
                )
            )
            a = Box(1)
            b = Box(2)
            a.v = 10
            shw a.v, b.v
        """)
        self.assertEqual(run(code), "10 2\n")

    def test_class_attribute(self):
        code = na("""
            classify K: (
                kind = "animal"
            )
            k = K()
            shw k.kind, K.kind
        """)
        self.assertEqual(run(code), "animal animal\n")

    def test_inheritance_and_override(self):
        code = na("""
            classify Animal: (
                df __init__(urself, name): (
                    urself.name = name
                )
                df speak(urself): (
                    shw "{urself.name} faz um som"
                )
                df kind(urself): (
                    shw "animal"
                )
            )
            classify Dog(Animal): (
                df speak(urself): (
                    shw "{urself.name} late"
                )
            )
            d = Dog("Rex")
            d.speak()
            d.kind()
        """)
        self.assertEqual(run(code), "Rex late\nanimal\n")

    def test_str_method(self):
        code = na("""
            classify P: (
                df __str__(urself): (
                    ret "P!"
                )
            )
            shw P()
        """)
        self.assertEqual(run(code), "P!\n")

    def test_methods_do_not_see_class_scope_names(self):
        code = na("""
            classify K: (
                x = 1
                df f(urself): (
                    ret x
                )
            )
            K().f()
        """)
        with self.assertRaises(NativaRuntimeError):
            run(code)

    def test_missing_attribute(self):
        with self.assertRaises(NativaRuntimeError):
            run("classify A: (\n    x = 1\n)\nshw A().y")

    def test_args_without_init(self):
        with self.assertRaises(NativaRuntimeError):
            run("classify A: (\n    x = 1\n)\nA(1)")


class TestCollections(unittest.TestCase):
    def test_list_index_and_assignment(self):
        self.assertEqual(run("n = [1, 2, 3]\nn[0] = 99\nshw n, n[1], n[-1]"), "[99, 2, 3] 2 3\n")

    def test_dict(self):
        code = 'p = {"name": "João", "age": 12}\np["age"] = 13\np["x"] = 1\nshw p["name"], p["age"], p'
        self.assertEqual(run(code), "João 13 {'name': 'João', 'age': 13, 'x': 1}\n")

    def test_methods(self):
        code = "n = [3, 1, 2]\nn.append(0)\nn.sort()\nshw n, len(n)\nd = {'a': 1}\nshw d.keys(), d.values(), d.items()"
        self.assertEqual(run(code), "[0, 1, 2, 3] 4\n['a'] [1] [['a', 1]]\n")

    def test_multiline_literals(self):
        code = na("""
            n = [
                1,
                2,
            ]
            d = {
                "a": 1,
                "b": 2
            }
            shw n, d
        """)
        self.assertEqual(run(code), "[1, 2] {'a': 1, 'b': 2}\n")

    def test_index_errors(self):
        for bad in ("[1][5]", "{'a': 1}['b']", "5[0]", "[1]['a']"):
            with self.assertRaises(NativaRuntimeError):
                run(f"shw {bad}")

    def test_builtins(self):
        self.assertEqual(run('shw int("42"), float("1.5"), str(3), len("abc"), abs(-2), min(3, 1), max([1, 9])'),
                         "42 1.5 3 3 2 1 9\n")

    def test_builtin_error(self):
        with self.assertRaises(NativaRuntimeError):
            run('shw int("abc")')


class TestErrorsWithPosition(unittest.TestCase):
    def test_runtime_error_position(self):
        with self.assertRaises(NativaRuntimeError) as ctx:
            run("shw 1\nshw 2\nshw unknown")
        e = ctx.exception
        self.assertEqual((e.line, e.col), (3, 5))
        self.assertIn("linha 3, coluna 5", str(e))

    def test_syntax_error_position(self):
        with self.assertRaises(NativaSyntaxError) as ctx:
            run("x = 1\ny = = 2")
        self.assertEqual(ctx.exception.line, 2)

    def test_unclosed_block(self):
        with self.assertRaises(NativaSyntaxError) as ctx:
            run("if True: (\n    shw 1\n")
        self.assertIn("falta ')'", str(ctx.exception))

    def test_missing_paren_after_colon(self):
        with self.assertRaises(NativaSyntaxError):
            run("if True:\n    shw 1")

    def test_unclosed_string(self):
        with self.assertRaises(NativaSyntaxError):
            run('shw "abc')

    def test_error_inside_function_points_to_line(self):
        code = "df f(): (\n    ret 1 / 0\n)\nf()"
        with self.assertRaises(NativaRuntimeError) as ctx:
            run(code)
        self.assertEqual(ctx.exception.line, 2)

    def test_error_inside_interpolation_points_to_line(self):
        with self.assertRaises(NativaRuntimeError) as ctx:
            run('shw 1\nshw "a {nope}"')
        self.assertEqual(ctx.exception.line, 2)

    def test_pending_keywords_are_reserved(self):
        # xcept, idgafatc, perror are now implemented but restricted to try blocks
        with self.assertRaises(NativaSyntaxError) as ctx:
            run("xcept = 1")
        self.assertIn("'xcept' deve ser usado dentro de 'try'", str(ctx.exception))

        with self.assertRaises(NativaSyntaxError) as ctx:
            run("idgafatc = 1")
        self.assertIn("'idgafatc' deve ser usado dentro de 'try'", str(ctx.exception))

        # perror is now implemented
        with self.assertRaises(NativaRuntimeError):
            run("perror 'test'")

    def test_invalid_assignment_target(self):
        with self.assertRaises(NativaSyntaxError):
            run("1 = 2")

    def test_unexpected_character(self):
        with self.assertRaises(NativaSyntaxError):
            run("x = 1 @ 2")

    def test_no_python_eval(self):
        with self.assertRaises(NativaRuntimeError):
            run('eval("1")')
        with self.assertRaises(NativaRuntimeError):
            run('shw "x".__class__')


if __name__ == "__main__":
    unittest.main()

import contextlib
import io
import os
import tempfile
import unittest
from textwrap import dedent
from unittest import mock

from tests.helpers import run
from impbuild import Loader
from impbuild.loader import DEFAULT_ROOT
from src.errors import NativaRuntimeError, NativaSyntaxError
from src.main import main, run_source


def na(code):
    return dedent(code).lstrip("\n")


class Workspace:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.libs = os.path.join(self.root, "libraries")
        self.build = os.path.join(self.root, "build")
        os.makedirs(self.libs)

    def write(self, relative, text):
        path = os.path.join(self.libs, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(na(text) if text.startswith("\n") else text)
        return path

    def loader(self, extra=()):
        return Loader(root=DEFAULT_ROOT, search_dirs=[self.libs, *extra], build_dir=self.build)

    def run(self, source, loader=None, inputs=()):
        out = io.StringIO()
        run_source(source, out=out, loader=loader or self.loader())
        return out.getvalue()

    def cleanup(self):
        self.tmp.cleanup()


class ImportTestCase(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace()
        self.addCleanup(self.ws.cleanup)


class TestInternalAndPython(ImportTestCase):
    def test_math(self):
        out = run("NA imp math\nshw math.sqrt(9), math.floor(2.7), math.pi > 3.14, math.hypot(3, 4)")
        self.assertEqual(out, "3.0 2 True 5.0\n")

    def test_math_domain_error_is_catchable(self):
        code = na("""
            NA imp math
            try: (
                math.sqrt(-1)
            )
            xcept ValueError as e: (
                shw "dominio"
            )
        """)
        self.assertEqual(run(code), "dominio\n")

    def test_random_is_seedable(self):
        code = na("""
            NA imp random
            random.seed(7)
            a = [random.randint(1, 100), random.randint(1, 100), random.rand()]
            random.seed(7)
            b = [random.randint(1, 100), random.randint(1, 100), random.rand()]
            shw a == b, len(a)
        """)
        self.assertEqual(run(code), "True 3\n")

    def test_random_helpers(self):
        code = na("""
            NA imp random
            items = [1, 2, 3, 4]
            random.shuffle(items)
            shw len(items), random.choice([5]), len(random.sample(items, 2))
        """)
        self.assertEqual(run(code), "4 5 2\n")

    def test_alias_and_multiple(self):
        out = run("NA imp math as m, random\nshw m.sqrt(4), random.randint(2, 2)")
        self.assertEqual(out, "2.0 2\n")

    def test_python_library(self):
        out = run('NA imp json\nshw json.dumps({"a": [1, 2]}), json.loads("[1, 2]")')
        self.assertEqual(out, '{"a": [1, 2]} [1, 2]\n')

    def test_python_incompatible_return(self):
        code = na("""
            NA imp collections
            shw "x"
        """)
        self.assertEqual(run(code), "x\n")
        with self.assertRaises(NativaRuntimeError):
            run("NA imp datetime\nshw datetime.datetime")

    def test_missing_module_is_catchable_import_error(self):
        code = na("""
            try: (
                NA imp biblioteca_que_nao_existe
            )
            xcept ImportError as e: (
                shw "falhou"
            )
        """)
        self.assertEqual(self.ws.run(code), "falhou\n")

    def test_missing_module_position(self):
        with self.assertRaises(NativaRuntimeError) as ctx:
            self.ws.run("shw 1\nNA imp nada_aqui")
        self.assertEqual(ctx.exception.line, 2)
        self.assertIn("não foi possível importar", str(ctx.exception))

    def test_module_has_no_attribute(self):
        with self.assertRaises(NativaRuntimeError):
            run("NA imp math\nshw math.nao_existe")

    def test_import_is_a_statement_not_a_python_import(self):
        with self.assertRaises(NativaSyntaxError):
            run("NA imp")

    def test_na_is_still_a_valid_name(self):
        self.assertEqual(run("NA = 5\nshw NA"), "5\n")


class TestNativaLibraries(ImportTestCase):
    def test_single_file_library(self):
        self.ws.write("util.na", '\ndf dobro(x): (\n    ret x * 2\n)\nVERSAO = "1.0"\n')
        out = self.ws.run("NA imp util\nshw util.dobro(21), util.VERSAO")
        self.assertEqual(out, "42 1.0\n")

    def test_package_with_submodules(self):
        self.ws.write("pacote/__init__.na", "NA imp pacote.a\n")
        self.ws.write("pacote/a.na", "\ndf ola(): (\n    ret \"a\"\n)\n")
        self.ws.write("pacote/sub/b.na", "\ndf ola(): (\n    ret \"b\"\n)\n")
        out = self.ws.run("NA imp pacote\nNA imp pacote.sub.b as b\nshw pacote.a.ola(), b.ola()")
        self.assertEqual(out, "a b\n")

    def test_dotted_import_binds_top_package(self):
        self.ws.write("pk/__init__.na", "x = 1\n")
        self.ws.write("pk/m.na", "y = 2\n")
        out = self.ws.run("NA imp pk.m\nshw pk.m.y, pk.x")
        self.assertEqual(out, "2 1\n")

    def test_reexport(self):
        self.ws.write("lib/__init__.na", "NA imp lib.parte\nreexport(lib.parte)\n")
        self.ws.write("lib/parte.na", "df oi(): (\n    ret \"oi\"\n)\n_privado = 1\n")
        out = self.ws.run("NA imp lib\nshw lib.oi()")
        self.assertEqual(out, "oi\n")
        with self.assertRaises(NativaRuntimeError):
            self.ws.run("NA imp lib\nshw lib._privado")

    def test_module_executes_once(self):
        self.ws.write("unico.na", 'shw "carregou"\n')
        out = self.ws.run("NA imp unico\nNA imp unico\nNA imp unico as outro\nshw 1")
        self.assertEqual(out, "carregou\n1\n")

    def test_library_can_import_other_library_and_internal(self):
        self.ws.write("base.na", "NA imp math\ndf raiz(x): (\n    ret math.sqrt(x)\n)\n")
        self.ws.write("topo.na", "NA imp base\ndf dobro_raiz(x): (\n    ret base.raiz(x) * 2\n)\n")
        self.assertEqual(self.ws.run("NA imp topo\nshw topo.dobro_raiz(16)"), "8.0\n")

    def test_circular_modules_inside_a_library(self):
        self.ws.write("ciclo/__init__.na", "NA imp ciclo.a\n")
        self.ws.write("ciclo/a.na", "NA imp ciclo.b\ndf fa(): (\n    ret 'a'\n)\n")
        self.ws.write("ciclo/b.na", "NA imp ciclo.a\ndf fb(): (\n    ret 'b'\n)\n")
        out = self.ws.run("NA imp ciclo\nshw ciclo.a.fa(), ciclo.b.fb()")
        self.assertEqual(out, "a b\n")

    def test_library_state_is_shared(self):
        self.ws.write("estado.na", "n = 0\ndf inc(): (\n    glob n\n    n = n + 1\n    ret n\n)\n")
        out = self.ws.run("NA imp estado\nestado.inc()\nshw estado.inc(), estado.n")
        self.assertEqual(out, "2 2\n")

    def test_script_directory_modules(self):
        local = tempfile.TemporaryDirectory()
        self.addCleanup(local.cleanup)
        with open(os.path.join(local.name, "meu.na"), "w", encoding="utf-8") as handle:
            handle.write('df oi(): (\n    ret "local"\n)\n')
        out = self.ws.run("NA imp meu\nshw meu.oi()", loader=self.ws.loader(extra=[local.name]))
        self.assertEqual(out, "local\n")

    def test_runtime_error_in_library_reports_library_file(self):
        self.ws.write("falha.na", "df quebra(): (\n    ret 1 / 0\n)\n")
        with self.assertRaises(NativaRuntimeError) as ctx:
            self.ws.run("NA imp falha\nfalha.quebra()")
        self.assertEqual(ctx.exception.filename, "falha.na")
        self.assertEqual(ctx.exception.line, 2)

    def test_filename_restored_after_call(self):
        self.ws.write("ok.na", "df f(): (\n    ret 1\n)\n")
        with self.assertRaises(NativaRuntimeError) as ctx:
            self.ws.run("NA imp ok\nok.f()\nshw 1 / 0")
        self.assertEqual(ctx.exception.filename, "<principal>")

    def test_classes_in_libraries(self):
        self.ws.write("formas.na", 'classify Q: (\n    df __init__(urself, l): (\n        urself.l = l\n    )\n    df area(urself): (\n        ret urself.l ** 2\n    )\n)\n')
        out = self.ws.run("NA imp formas\nshw formas.Q(3).area()")
        self.assertEqual(out, "9\n")


class TestImpbuild(ImportTestCase):
    def test_build_creates_artifacts_and_cache(self):
        self.ws.write("pk/__init__.na", "x = 1\n")
        self.ws.write("pk/m.na", "y = 2\n")
        loader = self.ws.loader()
        result = loader.builder.build("pk")
        self.assertEqual(sorted(result.built), ["pk", "pk.m"])
        self.assertTrue(os.path.isfile(os.path.join(self.ws.build, "libraries", "pk", "m.nac")))
        self.assertTrue(os.path.isfile(os.path.join(self.ws.build, "libraries", "pk.nac")))
        self.assertTrue(os.path.isfile(os.path.join(self.ws.build, "cache", "pk.json")))

    def test_second_build_uses_cache(self):
        self.ws.write("u.na", "x = 1\n")
        self.ws.loader().builder.build("u")
        again = self.ws.loader().builder.build("u")
        self.assertEqual(again.built, [])
        self.assertEqual(again.cached, ["u"])

    def test_changed_source_is_rebuilt(self):
        path = self.ws.write("u.na", "x = 1\n")
        self.ws.loader().builder.build("u")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("x = 2\n")
        result = self.ws.loader().builder.build("u")
        self.assertEqual(result.built, ["u"])
        self.assertEqual(self.ws.run("NA imp u\nshw u.x"), "2\n")

    def test_only_changed_module_is_rebuilt(self):
        self.ws.write("pk/__init__.na", "x = 1\n")
        path = self.ws.write("pk/m.na", "y = 2\n")
        self.ws.loader().builder.build("pk")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("y = 3\n")
        result = self.ws.loader().builder.build("pk")
        self.assertEqual(result.built, ["pk.m"])
        self.assertEqual(result.cached, ["pk"])

    def test_force_rebuilds(self):
        self.ws.write("u.na", "x = 1\n")
        loader = self.ws.loader()
        loader.builder.build("u")
        self.assertEqual(loader.builder.build("u", force=True).built, ["u"])

    def test_corrupted_artifact_is_rebuilt(self):
        self.ws.write("u.na", "x = 5\n")
        self.ws.loader().builder.build("u")
        artifact = os.path.join(self.ws.build, "libraries", "u.nac")
        with open(artifact, "wb") as handle:
            handle.write(b"corrompido")
        self.assertEqual(self.ws.run("NA imp u\nshw u.x"), "5\n")

    def test_validation_catches_top_level_ret(self):
        self.ws.write("ruim.na", "ret 1\n")
        with self.assertRaises(NativaSyntaxError) as ctx:
            self.ws.run("NA imp ruim")
        self.assertIn("'ret' fora de uma função", str(ctx.exception))
        self.assertEqual(ctx.exception.filename, "ruim.na")

    def test_validation_catches_break_outside_loop(self):
        self.ws.write("ruim.na", "df f(): (\n    brk\n)\n")
        with self.assertRaises(NativaSyntaxError):
            self.ws.run("NA imp ruim")

    def test_validation_allows_valid_control_flow(self):
        self.ws.write("bom.na", "df f(): (\n    for i in rang(3): (\n        if i == 1: (\n            brk\n        )\n    )\n    ret 1\n)\n")
        self.assertEqual(self.ws.run("NA imp bom\nshw bom.f()"), "1\n")

    def test_syntax_error_in_library(self):
        self.ws.write("sint.na", "x = = 1\n")
        with self.assertRaises(NativaSyntaxError) as ctx:
            self.ws.run("NA imp sint")
        self.assertEqual(ctx.exception.filename, "sint.na")
        self.assertFalse(os.path.exists(os.path.join(self.ws.build, "libraries", "sint.nac")))

    def test_missing_dependency_detected_at_build(self):
        self.ws.write("dep.na", "NA imp inexistente_xyz\n")
        with self.assertRaises(NativaRuntimeError) as ctx:
            self.ws.loader().builder.build("dep")
        self.assertIn("dependência 'inexistente_xyz' não encontrada", str(ctx.exception))
        self.assertEqual(ctx.exception.error_class, "ImportError")

    def test_manifest_dependencies(self):
        self.ws.write("a/__init__.na", "x = 1\n")
        self.ws.write("a/library.json", '{"version": "2.1.0", "dependencies": ["b"]}')
        with self.assertRaises(NativaRuntimeError) as ctx:
            self.ws.loader().builder.build("a")
        self.assertIn("'b'", str(ctx.exception))
        self.ws.write("b.na", "y = 1\n")
        result = self.ws.loader().builder.build("a")
        self.assertEqual(result.dependencies, ["b"])
        self.assertEqual(self.ws.loader().registry.find_library("a").version, "2.1.0")

    def test_invalid_manifest(self):
        self.ws.write("m/__init__.na", "x = 1\n")
        self.ws.write("m/library.json", "{ nao é json")
        with self.assertRaises(NativaRuntimeError):
            self.ws.loader().builder.build("m")

    def test_circular_library_dependency(self):
        self.ws.write("ca.na", "NA imp cb\n")
        self.ws.write("cb.na", "NA imp ca\n")
        with self.assertRaises(NativaRuntimeError) as ctx:
            self.ws.loader().builder.build("ca")
        self.assertIn("circular", str(ctx.exception))

    def test_dependency_library_is_built_too(self):
        self.ws.write("base.na", "x = 1\n")
        self.ws.write("topo.na", "NA imp base\n")
        loader = self.ws.loader()
        loader.builder.build("topo")
        self.assertTrue(os.path.isfile(os.path.join(self.ws.build, "libraries", "base.nac")))

    def test_unload_and_reload(self):
        self.ws.write("rec.na", 'shw "carregando"\nv = 1\n')
        loader = self.ws.loader()
        out = io.StringIO()
        run_source("NA imp rec\nNA imp rec", out=out, loader=loader)
        self.assertEqual(out.getvalue(), "carregando\n")
        self.assertEqual(loader.loaded_modules(), ["rec"])
        self.assertTrue(loader.unload("rec"))
        self.assertEqual(loader.loaded_modules(), [])
        run_source("NA imp rec", out=out, loader=loader)
        self.assertEqual(out.getvalue(), "carregando\ncarregando\n")
        self.assertFalse(loader.unload("nao_carregado"))

    def test_registry_lists_libraries_and_modules(self):
        self.ws.write("l1.na", "x = 1\n")
        self.ws.write("l2/__init__.na", "x = 1\n")
        self.ws.write("l2/s.na", "x = 1\n")
        registry = self.ws.loader().registry
        self.assertEqual([i.name for i in registry.list_libraries()], ["l1", "l2"])
        info = registry.find_library("l2")
        self.assertEqual(sorted(registry.list_modules(info)), ["l2", "l2.s"])
        self.assertIsNone(registry.find_library("../fora"))

    def test_artifact_contains_real_ast_not_source_copy(self):
        import pickle

        self.ws.write("u.na", "x = 1\n")
        self.ws.loader().builder.build("u")
        with open(os.path.join(self.ws.build, "libraries", "u.nac"), "rb") as handle:
            payload = pickle.load(handle)
        self.assertEqual(type(payload["program"]).__name__, "Program")
        self.assertEqual(payload["format"], 1)


class TestCli(ImportTestCase):
    def call(self, *args):
        out, err = io.StringIO(), io.StringIO()
        fake_root = self.ws.root
        os.makedirs(os.path.join(fake_root, "build"), exist_ok=True)
        with mock.patch("impbuild.loader.DEFAULT_ROOT", fake_root):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_build_libs_clean(self):
        self.ws.write("cli.na", "x = 1\n")
        code, out, _ = self.call("build", "cli")
        self.assertEqual(code, 0)
        self.assertIn("construídos: cli", out)
        code, out, _ = self.call("build", "cli")
        self.assertIn("em cache:    cli", out)
        code, out, _ = self.call("libs")
        self.assertIn("cli 0.0.0", out)
        code, out, _ = self.call("clean", "cli")
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(os.path.join(self.ws.build, "libraries", "cli.nac")))

    def test_build_unknown(self):
        code, _, err = self.call("build", "inexistente")
        self.assertEqual(code, 1)
        self.assertIn("biblioteca não encontrada", err)

    def test_run_script_with_local_module(self):
        project = tempfile.TemporaryDirectory()
        self.addCleanup(project.cleanup)
        with open(os.path.join(project.name, "aux.na"), "w", encoding="utf-8") as handle:
            handle.write('df f(): (\n    ret "do aux"\n)\n')
        script = os.path.join(project.name, "prog.na")
        with open(script, "w", encoding="utf-8") as handle:
            handle.write("NA imp aux\nshw aux.f()\n")
        code, out, err = self.call(script)
        self.assertEqual((code, out), (0, "do aux\n"), err)


if __name__ == "__main__":
    unittest.main()

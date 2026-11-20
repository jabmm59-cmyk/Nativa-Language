import io
import os
import sys
import tempfile
import types
import unittest

from backends.NAgame import state
from impbuild import Loader
from impbuild.loader import DEFAULT_ROOT
from src.main import run_source
from tests.fake_pygame import KEY_CODES, make_fake_pygame

EXAMPLES = os.path.join(DEFAULT_ROOT, "examples")

EXPECTED = {
    "ola.na": "Hello, World!\nOlá-Mundo\nOlá, joão! Resultado: 30\n",
    "idade.na": "Menor de idade\n0\n1\n2\n0\n1\n3\n4\n",
    "classes.na": "30\nOlá, João\n[99, 2, 3] João 2\n",
    "excecoes.na": (
        "saldo: 70\noperacao 30 encerrada\nerro: faltam 400 reais (400)\noperacao 500 encerrada\n"
        "invalido: o valor deve ser positivo\noperacao -5 encerrada\n"
        "invalido: o valor deve ser positivo\noperacao 0 encerrada\ndivisao por zero capturada\n"
    ),
    "recursos.na": (
        "total: 15\ncontador: 3\nfuncoes: 42 49\n[2, 3, 4]\n"
        "abrindo dados.txt\nusando dados.txt\nfechando dados.txt\n"
    ),
    "assincrono.na": (
        "iniciando a\niniciando b\niniciando c\npronto b\npronto c\npronto a\n['A', 'B', 'C']\n"
    ),
    "bibliotecas.na": (
        "raiz de 144: 12.0\npi arredondado: 3.1416\ndado entre 1 e 6: True\n"
        '{"linguagem": "Nativa", "versao": 1}\n'
    ),
}


def execute(name, **kwargs):
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as handle:
        source = handle.read()
    out = io.StringIO()
    run_source(source, name, out=out, **kwargs)
    return out.getvalue()


class TestExamples(unittest.TestCase):
    def test_every_example_produces_the_expected_output(self):
        for name, expected in EXPECTED.items():
            with self.subTest(example=name):
                self.assertEqual(execute(name), expected)

    def test_all_deterministic_examples_are_covered(self):
        listed = {f for f in os.listdir(EXAMPLES) if f.endswith(".na")}
        self.assertEqual(listed - set(EXPECTED), {"jogo.na"})


class TestGameExample(unittest.TestCase):
    def setUp(self):
        self.previous = sys.modules.get("pygame")
        self.pg = make_fake_pygame()
        sys.modules["pygame"] = self.pg
        state.reset()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def tearDown(self):
        state.reset()
        if self.previous is None:
            sys.modules.pop("pygame", None)
        else:
            sys.modules["pygame"] = self.previous

    def play(self, jump_frames):
        pg = self.pg
        counter = {"frame": 0}

        def get_events():
            counter["frame"] += 1
            frame = counter["frame"]
            events = []
            if frame == 1:
                events.append(types.SimpleNamespace(type=pg.KEYDOWN, key=KEY_CODES["right"]))
            if frame in jump_frames:
                events.append(types.SimpleNamespace(type=pg.KEYDOWN, key=KEY_CODES["space"]))
            if frame >= 400:
                events.append(types.SimpleNamespace(type=pg.QUIT))
            return events

        pg.event.get = get_events
        loader = Loader(
            root=DEFAULT_ROOT,
            search_dirs=[os.path.join(DEFAULT_ROOT, "libraries")],
            build_dir=os.path.join(self.tmp.name, "build"),
        )
        return execute("jogo.na", loader=loader)

    def test_running_through_collects_every_coin_and_ends_the_game(self):
        output = self.play(())
        pg = self.pg
        self.assertEqual(output, "pontuação final: 6\n")
        self.assertIsNone(state.screen)
        self.assertEqual(pg.quit_calls, 1)
        self.assertEqual(pg.captions[-1], "Nativa - Coletor de moedas")
        self.assertGreaterEqual(pg.flips, 399)

    def test_jumping_over_coins_is_possible(self):
        output = self.play((120,))
        score = int(output.split(":")[1])
        self.assertTrue(0 < score < 6, output)


if __name__ == "__main__":
    unittest.main()

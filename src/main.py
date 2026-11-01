import os
import sys

from . import __version__
from .errors import NativaError
from .interpreter import Interpreter
from .parser import parse


def run_source(source, filename="<principal>", out=None, input_fn=None):
    program = parse(source, filename)
    interpreter = Interpreter(filename, out=out, input_fn=input_fn)
    interpreter.run(program)
    return interpreter


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in ("--version", "-v"):
        print(f"Nativa {__version__}")
        return 0
    if len(argv) != 1:
        print("uso: nativa arquivo.na", file=sys.stderr)
        return 2
    path = argv[0]
    if not path.endswith(".na"):
        print("erro: arquivos Nativa devem ter a extensão .na", file=sys.stderr)
        return 2
    try:
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
    except OSError as e:
        print(f"erro: não foi possível abrir '{path}': {e.strerror}", file=sys.stderr)
        return 2
    try:
        run_source(source, os.path.basename(path))
    except NativaError as e:
        sys.stdout.flush()
        print(e, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())

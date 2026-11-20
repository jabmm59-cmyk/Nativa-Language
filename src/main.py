import os
import sys

from . import __version__
from .errors import NativaError
from .interpreter import Interpreter
from .parser import parse

USAGE = """uso:
  nativa arquivo.na           executa um programa
  nativa build NOME [--force] constrói uma biblioteca
  nativa libs                 lista as bibliotecas disponíveis
  nativa clean [NOME]         limpa o cache e os artefatos construídos
  nativa --version"""


def run_source(source, filename="<principal>", out=None, input_fn=None, loader=None, script_dir=None):
    program = parse(source, filename)
    interpreter = Interpreter(filename, out=out, input_fn=input_fn, loader=loader, script_dir=script_dir)
    interpreter.run(program)
    return interpreter


def command_build(args):
    from impbuild.loader import Loader

    force = "--force" in args
    names = [a for a in args if not a.startswith("--")]
    if len(names) != 1:
        print("uso: nativa build NOME [--force]", file=sys.stderr)
        return 2
    loader = Loader()
    result = loader.builder.build(names[0], force=force)
    print(f"biblioteca '{result.library}'")
    print(f"  construídos: {', '.join(result.built) or '-'}")
    print(f"  em cache:    {', '.join(result.cached) or '-'}")
    if result.dependencies:
        print(f"  dependências: {', '.join(result.dependencies)}")
    return 0


def command_libs():
    from impbuild.loader import Loader

    loader = Loader()
    libraries = loader.registry.list_libraries()
    if not libraries:
        print("nenhuma biblioteca encontrada")
    for info in libraries:
        modules = len(loader.registry.list_modules(info))
        print(f"{info.name} {info.version}  ({modules} módulo(s))")
    return 0


def command_clean(args):
    from impbuild.loader import Loader

    loader = Loader()
    removed = loader.cache.clear(args[0] if args else None)
    print(f"removidos: {', '.join(removed) or '-'}")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in ("--version", "-v"):
        print(f"Nativa {__version__}")
        return 0
    try:
        if argv and argv[0] == "build":
            return command_build(argv[1:])
        if argv and argv[0] == "libs":
            return command_libs()
        if argv and argv[0] == "clean":
            return command_clean(argv[1:])
    except NativaError as e:
        print(e, file=sys.stderr)
        return 1
    if len(argv) != 1:
        print(USAGE, file=sys.stderr)
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
        run_source(source, os.path.basename(path), script_dir=os.path.dirname(os.path.abspath(path)))
    except NativaError as e:
        sys.stdout.flush()
        print(e, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())

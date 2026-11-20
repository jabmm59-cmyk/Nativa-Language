import hashlib
import os
from dataclasses import dataclass, fields, is_dataclass

from src import __version__ as LANGUAGE_VERSION
from src import ast_nodes as A
from src.errors import NativaSyntaxError
from src.parser import parse

FORMAT_VERSION = 1


@dataclass
class CompiledModule:
    name: str
    source_path: str
    source_hash: str
    imports: list
    program: object
    format_version: int
    language_version: str


class Validator:
    def __init__(self, filename):
        self.filename = filename

    def fail(self, node, message):
        return NativaSyntaxError(message, node.line, node.col, self.filename)

    def check(self, program):
        self.visit(program, False, False)

    def visit(self, node, in_func, in_loop):
        if isinstance(node, (list, tuple)):
            for item in node:
                self.visit(item, in_func, in_loop)
            return
        if not is_dataclass(node) or isinstance(node, type):
            return
        kind = type(node)
        if kind is A.FuncDef:
            for param in node.params:
                self.visit(param.default, in_func, in_loop)
            self.visit(node.body, True, False)
            return
        if kind is A.Lambda:
            for param in node.params:
                self.visit(param.default, in_func, in_loop)
            self.visit(node.body, True, False)
            return
        if kind is A.ClassDef:
            self.visit(node.bases, in_func, in_loop)
            self.visit(node.body, False, False)
            return
        if kind is A.While:
            self.visit(node.test, in_func, in_loop)
            self.visit(node.body, in_func, True)
            return
        if kind is A.For:
            self.visit(node.iterable, in_func, in_loop)
            self.visit(node.body, in_func, True)
            return
        if kind is A.Return and not in_func:
            raise self.fail(node, "'ret' fora de uma função")
        if kind in (A.Break, A.Continue) and not in_loop:
            word = "brk" if kind is A.Break else "continue"
            raise self.fail(node, f"'{word}' fora de um laço")
        if kind is A.Nolocal and not in_func:
            raise self.fail(node, "'nolocal' fora de uma função")
        for field in fields(node):
            self.visit(getattr(node, field.name), in_func, in_loop)


def collect_imports(node, found=None):
    if found is None:
        found = []
    if isinstance(node, (list, tuple)):
        for item in node:
            collect_imports(item, found)
    elif is_dataclass(node) and not isinstance(node, type):
        if isinstance(node, A.Import):
            for item in node.items:
                if item.path not in found:
                    found.append(item.path)
        for field in fields(node):
            collect_imports(getattr(node, field.name), found)
    return found


class Compiler:
    def compile(self, name, source_path):
        display = os.path.basename(source_path)
        with open(source_path, "rb") as handle:
            data = handle.read()
        try:
            source = data.decode("utf-8")
        except UnicodeDecodeError:
            raise NativaSyntaxError("o arquivo não está em UTF-8", 1, 1, display)
        program = parse(source, display)
        Validator(display).check(program)
        return CompiledModule(
            name=name,
            source_path=os.path.abspath(source_path),
            source_hash=hashlib.sha256(data).hexdigest(),
            imports=collect_imports(program),
            program=program,
            format_version=FORMAT_VERSION,
            language_version=LANGUAGE_VERSION,
        )

"""
impbuild.compiler - Compilador/Validador de módulos Nativa
Responsável por validar e preparar módulos para execução.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ValidationLevel(Enum):
    """Níveis de validação."""
    SYNTAX_ONLY = "syntax"
    SEMANTIC = "semantic"
    FULL = "full"


@dataclass
class ValidationError:
    """Erro de validação."""
    file: str
    line: int
    column: int
    message: str
    level: str = "error"


@dataclass
class ValidationResult:
    """Resultado da validação."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class ModuleInfo:
    """Informações de um módulo compilado."""
    name: str
    file_path: str
    exports: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    constants: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


class Compiler:
    """Compila e valida módulos Nativa."""

    def __init__(self, stdlib_path: Optional[str] = None):
        self.stdlib_path = Path(stdlib_path) if stdlib_path else None
        self._imported_modules: Dict[str, ModuleInfo] = {}

    def validate_file(self, file_path: str, level: ValidationLevel = ValidationLevel.FULL) -> ValidationResult:
        """Valida um único arquivo."""
        path = Path(file_path)
        if not path.exists():
            return ValidationResult(
                valid=False,
                errors=[ValidationError(file_path, 0, 0, f"Arquivo não encontrado: {file_path}")]
            )

        # Ler arquivo
        try:
            source = path.read_text(encoding="utf-8")
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[ValidationError(file_path, 0, 0, f"Erro ao ler arquivo: {e}")]
            )

        return self.validate_source(source, file_path, level)

    def validate_source(self, source: str, filename: str = "<string>",
                        level: ValidationLevel = ValidationLevel.FULL) -> ValidationResult:
        """Valida código fonte."""
        from src.lexer import Lexer
        from src.parser import parse
        from src.errors import NativaSyntaxError

        result = ValidationResult(valid=True)

        # 1. Validação léxica
        try:
            lexer = Lexer(source, filename)
            tokens = lexer.tokenize()
        except NativaSyntaxError as e:
            result.valid = False
            result.errors.append(ValidationError(
                filename, e.line or 0, e.col or 0, str(e), "error"
            ))
            return result

        # 2. Validação sintática
        try:
            ast = parse(source, filename)
        except NativaSyntaxError as e:
            result.valid = False
            result.errors.append(ValidationError(
                filename, e.line or 0, e.col or 0, str(e), "error"
            ))
            return result

        # 3. Validação semântica (se solicitado)
        if level in (ValidationLevel.SEMANTIC, ValidationLevel.FULL):
            semantic_result = self._validate_semantics(ast, filename, source)
            result.errors.extend(semantic_result.errors)
            result.warnings.extend(semantic_result.warnings)
            if semantic_result.errors:
                result.valid = False

        return result

    def _validate_semantics(self, ast, filename: str, source: str) -> ValidationResult:
        """Validação semântica básica."""
        result = ValidationResult(valid=True)

        # Coletar definições
        defined_names: Set[str] = set()
        imported_names: Set[str] = set()
        used_names: Set[str] = set()

        self._collect_names(ast, defined_names, imported_names, used_names)

        # Verificar nomes não definidos (exceto builtins e importados)
        builtins = {
            "shw", "utype", "if", "else", "while", "for", "in", "is", "and", "or",
            "not", "df", "ret", "brk", "continue", "classify", "True", "False", "None",
            "NA", "imp", "de", "como", "try", "xcept", "idgafatc", "perror", "as",
            "len", "int", "float", "str", "bool", "abs", "min", "max", "round",
            "list", "rang", "print", "input"
        }

        for name in used_names:
            if name not in defined_names and name not in imported_names and name not in builtins:
                result.warnings.append(ValidationError(
                    filename, 0, 0, f"Nome potencialmente não definido: '{name}'", "warning"
                ))

        return result

    def _collect_names(self, node, defined: Set[str], imported: Set[str], used: Set[str]):
        """Coleta nomes definidos, importados e usados na AST."""
        from src import ast_nodes as A

        if isinstance(node, A.Program):
            for stmt in node.body:
                self._collect_names(stmt, defined, imported, used)

        elif isinstance(node, A.Assign):
            if isinstance(node.target, A.Name):
                defined.add(node.target.id)
            self._collect_names(node.value, defined, imported, used)

        elif isinstance(node, A.Name):
            used.add(node.id)

        elif isinstance(node, A.FuncDef):
            defined.add(node.name)
            for param in node.params:
                defined.add(param.name)
            for stmt in node.body:
                self._collect_names(stmt, defined, imported, used)

        elif isinstance(node, A.ClassDef):
            defined.add(node.name)
            for stmt in node.body:
                self._collect_names(stmt, defined, imported, used)

        elif isinstance(node, A.Import):
            for name, alias in node.names:
                imported.add(alias if alias else name)

        elif isinstance(node, A.ImportFrom):
            for name, alias in node.names:
                imported.add(alias if alias else name)

        elif isinstance(node, A.Call):
            self._collect_names(node.func, defined, imported, used)
            for arg in node.args:
                self._collect_names(arg, defined, imported, used)
            for _, kwarg in node.kwargs:
                self._collect_names(kwarg, defined, imported, used)

        elif isinstance(node, A.Attr):
            self._collect_names(node.obj, defined, imported, used)

        elif isinstance(node, A.Index):
            self._collect_names(node.obj, defined, imported, used)
            self._collect_names(node.index, defined, imported, used)

        elif isinstance(node, A.BinOp):
            self._collect_names(node.left, defined, imported, used)
            self._collect_names(node.right, defined, imported, used)

        elif isinstance(node, A.Unary):
            self._collect_names(node.operand, defined, imported, used)

        elif isinstance(node, A.BoolOp):
            self._collect_names(node.left, defined, imported, used)
            self._collect_names(node.right, defined, imported, used)

        elif isinstance(node, A.Compare):
            self._collect_names(node.left, defined, imported, used)
            for right in node.rights:
                self._collect_names(right, defined, imported, used)

        elif isinstance(node, A.If):
            self._collect_names(node.test, defined, imported, used)
            for stmt in node.body:
                self._collect_names(stmt, defined, imported, used)
            for stmt in node.orelse:
                self._collect_names(stmt, defined, imported, used)

        elif isinstance(node, A.While):
            self._collect_names(node.test, defined, imported, used)
            for stmt in node.body:
                self._collect_names(stmt, defined, imported, used)

        elif isinstance(node, A.For):
            self._collect_names(node.iterable, defined, imported, used)
            defined.add(node.var)
            for stmt in node.body:
                self._collect_names(stmt, defined, imported, used)

        elif isinstance(node, A.Try):
            for stmt in node.body:
                self._collect_names(stmt, defined, imported, used)
            for handler in node.handlers:
                if handler.name:
                    defined.add(handler.name)
                for stmt in handler.body:
                    self._collect_names(stmt, defined, imported, used)
            for stmt in node.finalbody:
                self._collect_names(stmt, defined, imported, used)

        elif isinstance(node, A.Raise):
            if node.exc:
                self._collect_names(node.exc, defined, imported, used)

        elif isinstance(node, A.ExprStmt):
            self._collect_names(node.expr, defined, imported, used)

        elif isinstance(node, A.Shw):
            for arg in node.args:
                self._collect_names(arg, defined, imported, used)
            for _, kwarg in node.kwargs:
                self._collect_names(kwarg, defined, imported, used)

        elif isinstance(node, A.Return):
            if node.value:
                self._collect_names(node.value, defined, imported, used)

        elif isinstance(node, (A.Num, A.Str, A.Const, A.ListLit, A.DictLit)):
            pass  # Literais não têm nomes

        elif isinstance(node, A.Interp):
            for part in node.parts:
                if not isinstance(part, str):
                    self._collect_names(part, defined, imported, used)

        # Nós que não precisam de processamento especial
        elif isinstance(node, (A.Break, A.Continue, A.Utype)):
            pass

    def compile_module(self, file_path: str) -> ModuleInfo:
        """Compila um módulo e retorna informações sobre ele."""
        path = Path(file_path)
        source = path.read_text(encoding="utf-8")

        from src.parser import parse
        ast = parse(source, str(path))

        info = ModuleInfo(
            name=path.stem,
            file_path=str(path)
        )

        self._extract_module_info(ast, info)
        return info

    def _extract_module_info(self, ast, info: ModuleInfo):
        """Extrai informações do módulo da AST."""
        from src import ast_nodes as A

        def visit(node):
            if isinstance(node, A.FuncDef):
                info.functions.append(node.name)
            elif isinstance(node, A.ClassDef):
                info.classes.append(node.name)
            elif isinstance(node, A.Assign):
                if isinstance(node.target, A.Name):
                    if node.target.id.isupper():
                        info.constants.append(node.target.id)
                    else:
                        info.exports.append(node.target.id)
            elif isinstance(node, A.Import):
                for name, alias in node.names:
                    info.imports.append(alias if alias else name)
            elif isinstance(node, A.ImportFrom):
                for name, alias in node.names:
                    info.imports.append(alias if alias else name)

            # Visitar filhos
            for attr_name in dir(node):
                attr = getattr(node, attr_name)
                if isinstance(attr, A.Node):
                    visit(attr)
                elif isinstance(attr, list):
                    for item in attr:
                        if isinstance(item, A.Node):
                            visit(item)
                        elif isinstance(item, tuple):
                            for subitem in item:
                                if isinstance(subitem, A.Node):
                                    visit(subitem)

        visit(ast)


def validate_file(file_path: str) -> ValidationResult:
    """Função de conveniência para validar um arquivo."""
    compiler = Compiler()
    return compiler.validate_file(file_path)


def compile_module(file_path: str) -> ModuleInfo:
    """Função de conveniência para compilar um módulo."""
    compiler = Compiler()
    return compiler.compile_module(file_path)
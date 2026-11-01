"""
impbuild.loader - Carregador de bibliotecas Nativa
Responsável por carregar e descarregar bibliotecas em tempo de execução.
"""

import sys
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from contextlib import contextmanager


@dataclass
class LoadedLibrary:
    """Biblioteca carregada."""
    name: str
    version: str
    path: Path
    module: Any = None
    exports: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    loaded_at: float = 0.0


class Loader:
    """Carrega e gerencia bibliotecas Nativa."""

    def __init__(self, build_dir: str = "build/libraries"):
        self.build_dir = Path(build_dir)
        self.loaded: Dict[str, LoadedLibrary] = {}
        self._load_order: List[str] = []

    def load(self, library_name: str, force_reload: bool = False) -> LoadedLibrary:
        """Carrega uma biblioteca."""
        # Verificar se já está carregada
        if library_name in self.loaded and not force_reload:
            return self.loaded[library_name]

        # Carregar dependências primeiro
        lib_path = self.build_dir / library_name
        if not lib_path.exists():
            raise ImportError(f"Biblioteca '{library_name}' não encontrada em {lib_path}")

        # Ler metadados
        metadata = self._read_metadata(lib_path)
        dependencies = metadata.get("dependencies", [])

        # Carregar dependências
        for dep in dependencies:
            if dep not in self.loaded:
                self.load(dep)

        # Carregar a biblioteca
        loaded_lib = self._load_library(library_name, lib_path, metadata)
        self.loaded[library_name] = loaded_lib

        if library_name not in self._load_order:
            self._load_order.append(library_name)

        return loaded_lib

    def _read_metadata(self, lib_path: Path) -> Dict:
        """Lê metadados da biblioteca."""
        import json
        meta_file = lib_path / "library.json"
        if meta_file.exists():
            return json.loads(meta_file.read_text())
        return {}

    def _load_library(self, name: str, lib_path: Path, metadata: Dict) -> LoadedLibrary:
        """Carrega a biblioteca executando seus arquivos .na."""
        import time

        # Criar namespace para a biblioteca
        namespace = {}

        # Executar arquivo de inicialização
        init_file = lib_path / "__init__.na"
        if init_file.exists():
            self._execute_na_file(init_file, namespace, lib_path)

        # Executar outros arquivos na ordem
        for na_file in sorted(lib_path.rglob("*.na")):
            if na_file.name != "__init__.na":
                self._execute_na_file(na_file, namespace, lib_path)

        # Criar objeto de biblioteca carregada
        loaded = LoadedLibrary(
            name=name,
            version=metadata.get("version", "1.0.0"),
            path=lib_path,
            exports=namespace,
            dependencies=metadata.get("dependencies", []),
            loaded_at=time.time()
        )

        return loaded

    def _execute_na_file(self, file_path: Path, namespace: Dict, lib_path: Path):
        """Executa um arquivo .na no namespace dado."""
        from src.main import run_source

        source = file_path.read_text(encoding="utf-8")

        # Criar interpretador com namespace customizado
        from src.interpreter import Interpreter
        from src.parser import parse

        interpreter = Interpreter()
        # Injetar namespace existente
        for key, value in namespace.items():
            interpreter.globals.define(key, value)

        try:
            program = parse(source, str(file_path))
            interpreter.run(program)
        except Exception as e:
            raise ImportError(f"Erro ao carregar {file_path.relative_to(lib_path)}: {e}")

        # Extrair exports do namespace
        for key, value in interpreter.globals.vars.items():
            if not key.startswith("_"):
                namespace[key] = value

    def unload(self, library_name: str) -> bool:
        """Descarrega uma biblioteca."""
        if library_name not in self.loaded:
            return False

        # Verificar se outras bibliotecas dependem desta
        dependents = self._get_dependents(library_name)
        if dependents:
            raise RuntimeError(
                f"Não é possível descarregar '{library_name}': "
                f"bibliotecas dependentes: {', '.join(dependents)}"
            )

        # Remover do sys.modules se houver módulo Python
        lib = self.loaded[library_name]
        if lib.module and hasattr(lib.module, '__name__'):
            mod_name = lib.module.__name__
            if mod_name in sys.modules:
                del sys.modules[mod_name]

        del self.loaded[library_name]
        if library_name in self._load_order:
            self._load_order.remove(library_name)

        return True

    def _get_dependents(self, library_name: str) -> List[str]:
        """Retorna bibliotecas que dependem da biblioteca dada."""
        dependents = []
        for name, lib in self.loaded.items():
            if library_name in lib.dependencies:
                dependents.append(name)
        return dependents

    def get_export(self, library_name: str, export_name: str) -> Any:
        """Obtém um export específico de uma biblioteca."""
        if library_name not in self.loaded:
            self.load(library_name)

        lib = self.loaded[library_name]
        if export_name not in lib.exports:
            raise AttributeError(
                f"Biblioteca '{library_name}' não exporta '{export_name}'"
            )

        return lib.exports[export_name]

    def get_all_exports(self, library_name: str) -> Dict[str, Any]:
        """Retorna todos os exports de uma biblioteca."""
        if library_name not in self.loaded:
            self.load(library_name)

        return self.loaded[library_name].exports.copy()

    def is_loaded(self, library_name: str) -> bool:
        """Verifica se uma biblioteca está carregada."""
        return library_name in self.loaded

    def list_loaded(self) -> List[str]:
        """Lista bibliotecas carregadas em ordem de carregamento."""
        return self._load_order.copy()

    def reload(self, library_name: str) -> LoadedLibrary:
        """Recarrega uma biblioteca (descarrega e carrega novamente)."""
        if library_name in self.loaded:
            self.unload(library_name)
        return self.load(library_name, force_reload=True)

    @contextmanager
    def load_context(self, *libraries: str):
        """Context manager para carregar bibliotecas temporariamente."""
        loaded = []
        try:
            for lib in libraries:
                loaded.append(self.load(lib))
            yield loaded
        finally:
            for lib in reversed(loaded):
                self.unload(lib.name)


# Instância global do loader
_global_loader: Optional[Loader] = None


def get_loader() -> Loader:
    """Obtém o loader global."""
    global _global_loader
    if _global_loader is None:
        _global_loader = Loader()
    return _global_loader


def load_library(name: str) -> LoadedLibrary:
    """Carrega uma biblioteca usando o loader global."""
    return get_loader().load(name)


def unload_library(name: str) -> bool:
    """Descarrega uma biblioteca usando o loader global."""
    return get_loader().unload(name)


def get_export(library_name: str, export_name: str) -> Any:
    """Obtém um export de uma biblioteca."""
    return get_loader().get_export(library_name, export_name)
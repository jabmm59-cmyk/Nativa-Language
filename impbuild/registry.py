"""
impbuild.registry - Registro de bibliotecas Nativa
Responsável por registrar, descobrir e gerenciar metadados de bibliotecas.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import hashlib


@dataclass
class LibraryMetadata:
    """Metadados de uma biblioteca."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    keywords: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    dev_dependencies: List[str] = field(default_factory=list)
    entry_point: str = "__init__.na"
    source_files: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    platforms: List[str] = field(default_factory=lambda: ["linux"])
    python_requires: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'LibraryMetadata':
        return cls(**data)

    def compute_hash(self, lib_path: Path) -> str:
        """Computa hash dos arquivos fonte."""
        hasher = hashlib.sha256()
        for src_file in self.source_files:
            file_path = lib_path / src_file
            if file_path.exists():
                hasher.update(file_path.read_bytes())
        return hasher.hexdigest()


class Registry:
    """Registro de bibliotecas Nativa."""

    def __init__(self, libraries_dir: str = "libraries", registry_file: str = "registry.json"):
        self.libraries_dir = Path(libraries_dir)
        self.registry_file = self.libraries_dir / registry_file
        self._registry: Dict[str, LibraryMetadata] = {}
        self._load_registry()

    def _load_registry(self):
        """Carrega o registro do disco."""
        if self.registry_file.exists():
            try:
                data = json.loads(self.registry_file.read_text(encoding="utf-8"))
                for name, meta in data.items():
                    self._registry[name] = LibraryMetadata.from_dict(meta)
            except Exception:
                pass  # Ignorar erros de leitura

    def _save_registry(self):
        """Salva o registro no disco."""
        data = {name: meta.to_dict() for name, meta in self._registry.items()}
        self.registry_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def register(self, metadata: LibraryMetadata) -> bool:
        """Registra uma biblioteca."""
        self._registry[metadata.name] = metadata
        self._save_registry()
        return True

    def unregister(self, name: str) -> bool:
        """Remove uma biblioteca do registro."""
        if name in self._registry:
            del self._registry[name]
            self._save_registry()
            return True
        return False

    def get(self, name: str) -> Optional[LibraryMetadata]:
        """Obtém metadados de uma biblioteca."""
        return self._registry.get(name)

    def list_all(self) -> List[LibraryMetadata]:
        """Lista todas as bibliotecas registradas."""
        return list(self._registry.values())

    def search(self, query: str) -> List[LibraryMetadata]:
        """Busca bibliotecas por nome, descrição ou palavras-chave."""
        query = query.lower()
        results = []
        for meta in self._registry.values():
            if (query in meta.name.lower() or
                query in meta.description.lower() or
                any(query in kw.lower() for kw in meta.keywords)):
                results.append(meta)
        return results

    def get_dependencies(self, name: str, recursive: bool = True) -> List[str]:
        """Obtém dependências de uma biblioteca."""
        meta = self._registry.get(name)
        if not meta:
            return []

        deps = set(meta.dependencies)
        if recursive:
            for dep in meta.dependencies:
                deps.update(self.get_dependencies(dep, recursive=True))
        return list(deps)

    def get_dependents(self, name: str) -> List[str]:
        """Obtém bibliotecas que dependem desta."""
        dependents = []
        for meta in self._registry.values():
            if name in meta.dependencies:
                dependents.append(meta.name)
        return dependents

    def check_conflicts(self, name: str, version: str) -> List[str]:
        """Verifica conflitos de versão."""
        conflicts = []
        meta = self._registry.get(name)
        if meta and meta.version != version:
            conflicts.append(f"Versão registrada: {meta.version}, solicitada: {version}")
        return conflicts

    def auto_discover(self) -> int:
        """Descobre automaticamente bibliotecas no diretório."""
        count = 0
        for lib_dir in self.libraries_dir.iterdir():
            if lib_dir.is_dir() and not lib_dir.name.startswith("."):
                if lib_dir.name not in self._registry:
                    meta = self._create_metadata_from_dir(lib_dir)
                    if meta:
                        self.register(meta)
                        count += 1
        return count

    def _create_metadata_from_dir(self, lib_dir: Path) -> Optional[LibraryMetadata]:
        """Cria metadados a partir do diretório da biblioteca."""
        # Procurar por arquivo de especificação
        spec_files = [
            lib_dir / "library.json",
            lib_dir / "library.na",
            lib_dir / "spec.na",
        ]

        metadata = None
        for spec_file in spec_files:
            if spec_file.exists():
                if spec_file.suffix == ".json":
                    try:
                        data = json.loads(spec_file.read_text(encoding="utf-8"))
                        metadata = LibraryMetadata.from_dict(data)
                        break
                    except Exception:
                        pass

        if not metadata:
            # Criar metadados básicos
            source_files = [str(f.relative_to(lib_dir)) for f in lib_dir.rglob("*.na")]
            if not source_files:
                return None

            metadata = LibraryMetadata(
                name=lib_dir.name,
                source_files=source_files,
            )

        return metadata

    def export_graph(self, output_file: str):
        """Exporta grafo de dependências para Graphviz DOT."""
        lines = ["digraph dependencies {"]
        for meta in self._registry.values():
            for dep in meta.dependencies:
                lines.append(f'  "{meta.name}" -> "{dep}";')
        lines.append("}")
        Path(output_file).write_text("\n".join(lines))


# Instância global do registry
_global_registry: Optional[Registry] = None


def get_registry() -> Registry:
    """Obtém o registry global."""
    global _global_registry
    if _global_registry is None:
        _global_registry = Registry()
    return _global_registry


def register_library(metadata: LibraryMetadata) -> bool:
    """Registra uma biblioteca no registry global."""
    return get_registry().register(metadata)


def get_library_metadata(name: str) -> Optional[LibraryMetadata]:
    """Obtém metadados de uma biblioteca."""
    return get_registry().get(name)


def list_libraries() -> List[LibraryMetadata]:
    """Lista todas as bibliotecas registradas."""
    return get_registry().list_all()


def discover_libraries() -> int:
    """Descobre bibliotecas automaticamente."""
    return get_registry().auto_discover()
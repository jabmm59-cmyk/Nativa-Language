"""
impbuild.builder - Construtor de bibliotecas Nativa
Responsável por construir bibliotecas a partir do código fonte.
"""

import os
import shutil
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BuildResult:
    """Resultado de uma construção."""
    success: bool
    library_name: str
    output_path: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class LibrarySpec:
    """Especificação de uma biblioteca."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    entry_point: str = "__init__.na"
    source_files: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


class Builder:
    """Constrói bibliotecas Nativa."""

    def __init__(self, libraries_dir: str = "libraries", build_dir: str = "build"):
        self.libraries_dir = Path(libraries_dir)
        self.build_dir = Path(build_dir)
        self.build_libraries_dir = self.build_dir / "libraries"
        self.cache_dir = self.build_dir / "cache"

        # Criar diretórios se não existirem
        self.build_libraries_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def build_library(self, lib_name: str, force: bool = False) -> BuildResult:
        """Constrói uma biblioteca específica."""
        lib_path = self.libraries_dir / lib_name
        if not lib_path.exists():
            return BuildResult(
                success=False,
                library_name=lib_name,
                errors=[f"Biblioteca '{lib_name}' não encontrada em {lib_path}"]
            )

        # Verificar se precisa reconstruir
        if not force and self._is_up_to_date(lib_name):
            return BuildResult(
                success=True,
                library_name=lib_name,
                output_path=str(self.build_libraries_dir / lib_name),
                metadata={"cached": True}
            )

        # Ler especificação
        spec = self._read_spec(lib_path)
        if not spec:
            return BuildResult(
                success=False,
                library_name=lib_name,
                errors=[f"Não foi possível ler especificação de '{lib_name}'"]
            )

        # Validar dependências
        dep_errors = self._validate_dependencies(spec)
        if dep_errors:
            return BuildResult(
                success=False,
                library_name=lib_name,
                errors=dep_errors
            )

        # Construir
        return self._do_build(spec, lib_path)

    def _read_spec(self, lib_path: Path) -> Optional[LibrarySpec]:
        """Lê a especificação da biblioteca."""
        # Procurar por arquivo de especificação
        spec_files = [
            lib_path / "library.na",
            lib_path / "spec.na",
            lib_path / "__init__.na",
        ]

        for spec_file in spec_files:
            if spec_file.exists():
                return self._parse_spec(spec_file)

        # Fallback: criar spec padrão baseado no diretório
        return LibrarySpec(
            name=lib_path.name,
            source_files=[str(f.relative_to(lib_path)) for f in lib_path.rglob("*.na")]
        )

    def _parse_spec(self, spec_file: Path) -> LibrarySpec:
        """Parseia arquivo de especificação."""
        # Por enquanto, retorna spec básica
        # TODO: Implementar parser completo de spec
        content = spec_file.read_text(encoding="utf-8")

        spec = LibrarySpec(name=spec_file.parent.name)
        spec.source_files = [str(f.relative_to(spec_file.parent))
                           for f in spec_file.parent.rglob("*.na")]
        return spec

    def _validate_dependencies(self, spec: LibrarySpec) -> List[str]:
        """Valida se todas as dependências estão disponíveis."""
        errors = []
        for dep in spec.dependencies:
            dep_path = self.libraries_dir / dep
            if not dep_path.exists():
                # Verificar se está no cache/build
                build_dep = self.build_libraries_dir / dep
                if not build_dep.exists():
                    errors.append(f"Dependência '{dep}' não encontrada")
        return errors

    def _is_up_to_date(self, lib_name: str) -> bool:
        """Verifica se a biblioteca está atualizada."""
        lib_path = self.libraries_dir / lib_name
        build_path = self.build_libraries_dir / lib_name

        if not build_path.exists():
            return False

        # Comparar hashes dos arquivos fonte
        src_hash = self._compute_source_hash(lib_path)
        cache_file = self.cache_dir / f"{lib_name}.hash"

        if cache_file.exists():
            cached_hash = cache_file.read_text().strip()
            return cached_hash == src_hash

        return False

    def _compute_source_hash(self, lib_path: Path) -> str:
        """Computa hash dos arquivos fonte."""
        hasher = hashlib.sha256()
        for na_file in sorted(lib_path.rglob("*.na")):
            rel_path = na_file.relative_to(lib_path)
            hasher.update(str(rel_path).encode())
            hasher.update(na_file.read_bytes())
        return hasher.hexdigest()

    def _do_build(self, spec: LibrarySpec, lib_path: Path) -> BuildResult:
        """Executa a construção efetiva."""
        output_path = self.build_libraries_dir / spec.name

        # Limpar build anterior se existir
        if output_path.exists():
            shutil.rmtree(output_path)

        output_path.mkdir(parents=True)

        # Copiar arquivos fonte
        copied_files = []
        for src_file in spec.source_files:
            src = lib_path / src_file
            dst = output_path / src_file
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied_files.append(src_file)

        # Atualizar cache
        cache_file = self.cache_dir / f"{spec.name}.hash"
        cache_file.write_text(self._compute_source_hash(lib_path))

        # Gerar metadados
        metadata = {
            "name": spec.name,
            "version": spec.version,
            "built_at": datetime.now().isoformat(),
            "files": copied_files,
            "dependencies": spec.dependencies,
        }

        import json
        (output_path / "library.json").write_text(json.dumps(metadata, indent=2))

        return BuildResult(
            success=True,
            library_name=spec.name,
            output_path=str(output_path),
            metadata=metadata
        )

    def build_all(self, force: bool = False) -> Dict[str, BuildResult]:
        """Constrói todas as bibliotecas."""
        results = {}
        for lib_dir in self.libraries_dir.iterdir():
            if lib_dir.is_dir() and not lib_dir.name.startswith("."):
                results[lib_dir.name] = self.build_library(lib_dir.name, force)
        return results

    def clean(self, lib_name: Optional[str] = None):
        """Limpa builds."""
        if lib_name:
            build_path = self.build_libraries_dir / lib_name
            if build_path.exists():
                shutil.rmtree(build_path)
            cache_file = self.cache_dir / f"{lib_name}.hash"
            if cache_file.exists():
                cache_file.unlink()
        else:
            if self.build_libraries_dir.exists():
                shutil.rmtree(self.build_libraries_dir)
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
            self.build_libraries_dir.mkdir(parents=True)
            self.cache_dir.mkdir(parents=True)


def build(library_name: str, libraries_dir: str = "libraries", build_dir: str = "build") -> BuildResult:
    """Função de conveniência para construir uma biblioteca."""
    builder = Builder(libraries_dir, build_dir)
    return builder.build_library(library_name)
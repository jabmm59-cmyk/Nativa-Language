"""
impbuild.cache - Sistema de cache do impbuild
Responsável por verificar alterações e armazenar resultados de builds.
"""

import json
import hashlib
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import shutil


class CacheEntryType(Enum):
    """Tipos de entrada no cache."""
    SOURCE_HASH = "source_hash"
    BUILD_RESULT = "build_result"
    VALIDATION_RESULT = "validation_result"
    DEPENDENCY_GRAPH = "dependency_graph"


@dataclass
class CacheEntry:
    """Entrada do cache."""
    key: str
    type: CacheEntryType
    value: Any
    created_at: float
    expires_at: Optional[float] = None
    metadata: Dict = field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class Cache:
    """Sistema de cache para impbuild."""

    def __init__(self, cache_dir: str = "build/cache", max_size_mb: int = 100, default_ttl: int = 86400):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.default_ttl = default_ttl
        self._index_file = self.cache_dir / "index.json"
        self._index: Dict[str, Dict] = {}
        self._load_index()

    def _load_index(self):
        """Carrega índice do cache."""
        if self._index_file.exists():
            try:
                self._index = json.loads(self._index_file.read_text(encoding="utf-8"))
            except Exception:
                self._index = {}

    def _save_index(self):
        """Salva índice do cache."""
        self._index_file.write_text(json.dumps(self._index, indent=2))

    def _get_entry_path(self, key: str) -> Path:
        """Obtém caminho do arquivo de entrada."""
        # Usar hash da chave para evitar problemas com nomes de arquivo
        hashed = hashlib.sha256(key.encode()).hexdigest()[:32]
        return self.cache_dir / f"{hashed}.cache"

    def get(self, key: str, entry_type: Optional[CacheEntryType] = None) -> Optional[Any]:
        """Obtém valor do cache."""
        if key not in self._index:
            return None

        entry_info = self._index[key]
        if entry_type and entry_info.get("type") != entry_type.value:
            return None

        entry_path = self._get_entry_path(key)
        if not entry_path.exists():
            # Limpar índice órfão
            del self._index[key]
            self._save_index()
            return None

        try:
            entry_data = json.loads(entry_path.read_text(encoding="utf-8"))
            entry = CacheEntry(**entry_data)
            if entry.is_expired():
                self.delete(key)
                return None
            return entry.value
        except Exception:
            self.delete(key)
            return None

    def set(self, key: str, value: Any, entry_type: CacheEntryType = CacheEntryType.SOURCE_HASH,
            ttl: Optional[int] = None, metadata: Optional[Dict] = None) -> bool:
        """Define valor no cache."""
        # Verificar tamanho do cache
        self._enforce_size_limit()

        entry = CacheEntry(
            key=key,
            type=entry_type,
            value=value,
            created_at=time.time(),
            expires_at=time.time() + (ttl or self.default_ttl) if ttl is not None else None,
            metadata=metadata or {}
        )

        entry_path = self._get_entry_path(key)
        try:
            entry_path.write_text(json.dumps(asdict(entry), default=str), encoding="utf-8")
            self._index[key] = {
                "type": entry_type.value,
                "created_at": entry.created_at,
                "expires_at": entry.expires_at,
                "size": entry_path.stat().st_size
            }
            self._save_index()
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """Remove entrada do cache."""
        if key in self._index:
            entry_path = self._get_entry_path(key)
            if entry_path.exists():
                entry_path.unlink()
            del self._index[key]
            self._save_index()
            return True
        return False

    def clear(self, entry_type: Optional[CacheEntryType] = None) -> int:
        """Limpa cache."""
        if entry_type is None:
            # Limpar tudo
            count = len(self._index)
            for key in list(self._index.keys()):
                self.delete(key)
            return count
        else:
            # Limpar apenas tipo específico
            count = 0
            for key in list(self._index.keys()):
                if self._index[key].get("type") == entry_type.value:
                    self.delete(key)
                    count += 1
            return count

    def _enforce_size_limit(self):
        """Aplica limite de tamanho do cache."""
        total_size = sum(info.get("size", 0) for info in self._index.values())
        if total_size > self.max_size_bytes:
            # Remover entradas mais antigas até ficar dentro do limite
            sorted_entries = sorted(
                self._index.items(),
                key=lambda x: x[1].get("created_at", 0)
            )
            for key, _ in sorted_entries:
                if total_size <= self.max_size_bytes * 0.8:  # 80% do limite
                    break
                entry_path = self._get_entry_path(key)
                if entry_path.exists():
                    total_size -= entry_path.stat().st_size
                self.delete(key)

    def get_stats(self) -> Dict:
        """Retorna estatísticas do cache."""
        total_size = sum(info.get("size", 0) for info in self._index.values())
        by_type: Dict[str, int] = {}
        for info in self._index.values():
            t = info.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1

        return {
            "entries": len(self._index),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_type": by_type,
            "max_size_mb": self.max_size_bytes / (1024 * 1024)
        }

    def cleanup_expired(self) -> int:
        """Remove entradas expiradas."""
        count = 0
        for key in list(self._index.keys()):
            entry_path = self._get_entry_path(key)
            if entry_path.exists():
                try:
                    entry_data = json.loads(entry_path.read_text(encoding="utf-8"))
                    entry = CacheEntry(**entry_data)
                    if entry.is_expired():
                        self.delete(key)
                        count += 1
                except Exception:
                    self.delete(key)
                    count += 1
        return count


class SourceTracker:
    """Rastreia alterações em arquivos fonte."""

    def __init__(self, cache: Cache):
        self.cache = cache

    def compute_hash(self, file_path: Path) -> str:
        """Computa hash de um arquivo."""
        hasher = hashlib.sha256()
        hasher.update(file_path.read_bytes())
        return hasher.hexdigest()

    def compute_dir_hash(self, dir_path: Path, pattern: str = "*.na") -> str:
        """Computa hash combinado de todos os arquivos no diretório."""
        hasher = hashlib.sha256()
        for file_path in sorted(dir_path.rglob(pattern)):
            rel_path = file_path.relative_to(dir_path)
            hasher.update(str(rel_path).encode())
            hasher.update(file_path.read_bytes())
        return hasher.hexdigest()

    def has_changed(self, key: str, file_path: Path) -> bool:
        """Verifica se arquivo mudou desde último cache."""
        cached_hash = self.cache.get(key, CacheEntryType.SOURCE_HASH)
        current_hash = self.compute_hash(file_path)
        return cached_hash != current_hash

    def has_dir_changed(self, key: str, dir_path: Path, pattern: str = "*.na") -> bool:
        """Verifica se diretório mudou."""
        cached_hash = self.cache.get(key, CacheEntryType.SOURCE_HASH)
        current_hash = self.compute_dir_hash(dir_path, pattern)
        return cached_hash != current_hash

    def update_hash(self, key: str, file_path: Path) -> str:
        """Atualiza hash no cache e retorna novo hash."""
        new_hash = self.compute_hash(file_path)
        self.cache.set(key, new_hash, CacheEntryType.SOURCE_HASH)
        return new_hash

    def update_dir_hash(self, key: str, dir_path: Path, pattern: str = "*.na") -> str:
        """Atualiza hash do diretório no cache."""
        new_hash = self.compute_dir_hash(dir_path, pattern)
        self.cache.set(key, new_hash, CacheEntryType.SOURCE_HASH)
        return new_hash


# Instância global do cache
_global_cache: Optional[Cache] = None
_global_tracker: Optional[SourceTracker] = None


def get_cache() -> Cache:
    """Obtém cache global."""
    global _global_cache
    if _global_cache is None:
        _global_cache = Cache()
    return _global_cache


def get_source_tracker() -> SourceTracker:
    """Obtém source tracker global."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = SourceTracker(get_cache())
    return _global_tracker


def cache_get(key: str, entry_type: Optional[CacheEntryType] = None) -> Optional[Any]:
    """Obtém valor do cache global."""
    return get_cache().get(key, entry_type)


def cache_set(key: str, value: Any, entry_type: CacheEntryType = CacheEntryType.SOURCE_HASH,
              ttl: Optional[int] = None) -> bool:
    """Define valor no cache global."""
    return get_cache().set(key, value, entry_type, ttl)


def cache_delete(key: str) -> bool:
    """Remove entrada do cache global."""
    return get_cache().delete(key)


def cache_stats() -> Dict:
    """Retorna estatísticas do cache global."""
    return get_cache().get_stats()
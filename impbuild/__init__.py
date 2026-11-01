"""
impbuild - Sistema de construção e gerenciamento de bibliotecas Nativa
"""

import importlib
import sys
from types import ModuleType

# Importar submódulos
from . import builder
from . import compiler
from . import loader
from . import registry
from . import cache

# Exportar classes principais para uso conveniente
from .builder import Builder, BuildResult, LibrarySpec, build
from .compiler import Compiler, ValidationResult, ModuleInfo, ValidationLevel, validate_file, compile_module
from .loader import Loader, LoadedLibrary, get_loader, load_library, unload_library, get_export
from .registry import Registry, LibraryMetadata, get_registry, register_library, get_library_metadata, list_libraries, discover_libraries
from .cache import Cache, SourceTracker, CacheEntry, CacheEntryType, get_cache, get_source_tracker, cache_get, cache_set, cache_delete, cache_stats


def criar_import(modulo_nome, apelido=None):
    """
    Cria um import dinamicamente.

    Uso em Nativa:
        NA imp impbuild
        impbuild.criar_import("os", "sistema")
        # Agora 'sistema' está disponível como o módulo os

    Args:
        modulo_nome: Nome do módulo Python para importar (ex: "os", "sys", "time")
        apelido: Nome opcional para o módulo no escopo Nativa

    Returns:
        O módulo importado
    """
    modulo = importlib.import_module(modulo_nome)
    nome = apelido if apelido else modulo_nome
    # Injeta no globals do chamador - isso é feito via interpreter
    return modulo


def importar_modulos(*modulos):
    """
    Importa múltiplos módulos de uma vez.

    Uso:
        impbuild.importar_modulos("os", "sys", "time")
        # ou com apelidos:
        impbuild.importar_modulos(("os", "sis"), ("sys", "sistema"))

    Args:
        *modulos: Strings ou tuplas (modulo, apelido)

    Returns:
        Dicionário com os módulos importados
    """
    resultado = {}
    for item in modulos:
        if isinstance(item, tuple):
            mod, alias = item
            resultado[alias] = importlib.import_module(mod)
        else:
            resultado[item] = importlib.import_module(item)
    return resultado


def criar_wrapper(nome, modulo):
    """
    Cria um wrapper personalizado para um módulo.
    Útil para adicionar métodos abreviados.
    """
    class ModuloWrapper:
        def __init__(self, mod):
            self._mod = mod

        def __getattr__(self, attr):
            return getattr(self._mod, attr)

        def __dir__(self):
            return [x for x in dir(self._mod) if not x.startswith('_')]

    return ModuloWrapper(modulo)


# Módulos pré-definidos comuns
MODULOS_COMUNS = {
    "os": "os",
    "sys": "sys",
    "time": "time",
    "json": "json",
    "random": "random",
    "math": "math",
    "datetime": "datetime",
    "pathlib": "pathlib",
    "collections": "collections",
    "itertools": "itertools",
    "functools": "functools",
}


def importar_comuns(*nomes):
    """
    Importa módulos comuns pelo nome abreviado.

    Uso:
        impbuild.importar_comuns("os", "sys", "time")
    """
    modulos = {}
    for nome in nomes:
        if nome in MODULOS_COMUNS:
            modulos[nome] = importlib.import_module(MODULOS_COMUNS[nome])
        else:
            modulos[nome] = importlib.import_module(nome)
    return modulos


"""
impbuild - Sistema de build e gerenciamento de bibliotecas Nativa
Permite criar, compilar, carregar e gerenciar bibliotecas Nativa.
"""

# Exportar apenas a infraestrutura de build
from .builder import (
    Builder,
    LibrarySpec,
    BuildResult,
    build,
)
from .compiler import (
    Compiler,
    ValidationResult,
    ModuleInfo,
    compile_library,
)
from .loader import (
    Loader,
    LoadedLibrary,
    load_library,
    unload_library,
    get_export,
    get_loader,
)
from .registry import (
    Registry,
    LibraryMetadata,
    get_registry,
    register_library,
    get_library_metadata,
    list_libraries,
    discover_libraries,
)
from .cache import (
    Cache,
    CacheEntry,
    CacheEntryType,
    get_cache,
)

__all__ = [
    # Builder
    'Builder',
    'LibrarySpec',
    'BuildResult',
    'build',
    'build_all',
    # Compiler
    'Compiler',
    'ValidationResult',
    'ModuleInfo',
    'compile_library',
    # Loader
    'Loader',
    'LoadedLibrary',
    'load_library',
    'unload_library',
    'get_export',
    'get_loader',
    # Registry
    'Registry',
    'LibraryMetadata',
    'get_registry',
    'register_library',
    'get_library_metadata',
    'list_libraries',
    'discover_libraries',
    # Cache
    'Cache',
    'CacheEntry',
    'CacheEntryType',
    'get_cache',
    # Utilitários comuns
    'criar_import',
    'importar_modulos',
    'criar_wrapper',
    'importar_comuns',
    'MODULOS_COMUNS',
]
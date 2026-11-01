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


# ============================================================
# NAgame - Biblioteca de jogos estilo pygame mas simplificada
# ============================================================

class NAgame:
    """
    Biblioteca de jogos simplificada estilo pygame.
    Comandos abreviados para criar jogos 2D facilmente.
    """

    def __init__(self, largura=800, altura=600, titulo="Jogo Nativa"):
        self.largura = largura
        self.altura = altura
        self.titulo = titulo
        self._iniciado = False
        self._rodando = False
        self._tela = None
        self._relogio = None
        self._eventos = []
        self._sprites = []
        self._teclas = {}
        self._cor_fundo = (0, 0, 0)

    def iniciar(self):
        """Inicializa o pygame e cria a janela."""
        try:
            import pygame
            self._pygame = pygame
            pygame.init()
            self._tela = pygame.display.set_mode((self.largura, self.altura))
            pygame.display.set_caption(self.titulo)
            self._relogio = pygame.time.Clock()
            self._iniciado = True
            self._rodando = True
            return True
        except ImportError:
            print("pygame não instalado. Instale com: pip install pygame")
            return False

    # --- Métodos abreviados ---

    def rodar(self, funcao_atualizar, funcao_desenhar):
        """
        Loop principal do jogo.

        Args:
            funcao_atualizar: Função chamada cada frame (dt)
            funcao_desenhar: Função chamada para desenhar (tela)
        """
        if not self._iniciado:
            self.iniciar()

        while self._rodando:
            dt = self._relogio.tick(60) / 1000.0  # delta time em segundos

            # Eventos
            for evento in self._pygame.event.get():
                if evento.type == self._pygame.QUIT:
                    self._rodando = False
                elif evento.type == self._pygame.KEYDOWN:
                    self._teclas[evento.key] = True
                elif evento.type == self._pygame.KEYUP:
                    self._teclas[evento.key] = False

            # Atualizar
            funcao_atualizar(dt)

            # Desenhar
            self._tela.fill(self._cor_fundo)
            funcao_desenhar(self._tela)

            self._pygame.display.flip()

        self._pygame.quit()

    def parar(self):
        """Para o loop do jogo."""
        self._rodando = False

    # --- Entrada (teclado) ---

    def tecla(self, tecla):
        """Verifica se tecla está pressionada. Use: 'espaço', 'esquerda', 'direita', 'cima', 'baixo', 'esc', 'enter'."""
        mapa = {
            'espaço': self._pygame.K_SPACE,
            'esquerda': self._pygame.K_LEFT,
            'direita': self._pygame.K_RIGHT,
            'cima': self._pygame.K_UP,
            'baixo': self._pygame.K_DOWN,
            'esc': self._pygame.K_ESCAPE,
            'enter': self._pygame.K_RETURN,
            'w': self._pygame.K_w,
            'a': self._pygame.K_a,
            's': self._pygame.K_s,
            'd': self._pygame.K_d,
        }
        key = mapa.get(tecla.lower(), getattr(self._pygame, f'K_{tecla}', None))
        if key is not None:
            return self._teclas.get(key, False)
        return False

    # --- Gráficos abreviados ---

    def limpar(self, cor=None):
        """Limpa a tela com cor (r, g, b) ou preto."""
        if cor:
            self._tela.fill(cor)
        else:
            self._tela.fill(self._cor_fundo)

    def retangulo(self, x, y, largura, altura, cor=(255, 255, 255), preenchido=True):
        """Desenha retângulo. retangulo(x, y, w, h, cor, preenchido=True)"""
        rect = self._pygame.Rect(x, y, largura, altura)
        if preenchido:
            self._pygame.draw.rect(self._tela, cor, rect)
        else:
            self._pygame.draw.rect(self._tela, cor, rect, 2)

    def circ(self, x, y, raio, cor=(255, 255, 255), preenchido=True):
        """Desenha círculo. circ(x, y, raio, cor, preenchido=True)"""
        if preenchido:
            self._pygame.draw.circle(self._tela, cor, (int(x), int(y)), int(raio))
        else:
            self._pygame.draw.circle(self._tela, cor, (int(x), int(y)), int(raio), 2)

    def linha(self, x1, y1, x2, y2, cor=(255, 255, 255), espessura=1):
        """Desenha linha."""
        self._pygame.draw.line(self._tela, cor, (x1, y1), (x2, y2), espessura)

    def texto(self, texto, x, y, tamanho=24, cor=(255, 255, 255), fonte=None):
        """Desenha texto na tela."""
        if fonte is None:
            fonte = self._pygame.font.Font(None, tamanho)
        superficie = fonte.render(str(texto), True, cor)
        self._tela.blit(superficie, (x, y))

    def img(self, caminho, x, y, largura=None, altura=None):
        """Carrega e desenha imagem. Retorna a surface para reuso."""
        try:
            surface = self._pygame.image.load(caminho).convert_alpha()
            if largura and altura:
                surface = self._pygame.transform.scale(surface, (largura, altura))
            self._tela.blit(surface, (x, y))
            return surface
        except:
            return None

    # --- Utilitários ---

    def fps(self):
        """Retorna FPS atual."""
        return int(self._relogio.get_fps())

    def tempo(self):
        """Retorna tempo em segundos desde o início."""
        return self._pygame.time.get_ticks() / 1000.0

    def centralizar(self, obj_largura, obj_altura):
        """Retorna (x, y) para centralizar objeto na tela."""
        return ((self.largura - obj_largura) // 2, (self.altura - obj_altura) // 2)


# Função auxiliar para criar jogo rápido
def jogo(nome="Jogo", largura=800, altura=600):
    """Cria uma instância do NAgame."""
    return NAgame(largura, altura, nome)


# Exportar tudo
__all__ = [
    'criar_import',
    'importar_modulos',
    'criar_wrapper',
    'importar_comuns',
    'NAgame',
    'jogo',
    'MODULOS_COMUNS',
    # Novos módulos do impbuild
    'builder',
    'compiler',
    'loader',
    'registry',
    'cache',
    # Classes principais
    'Builder',
    'Compiler',
    'Loader',
    'Registry',
    'Cache',
    'SourceTracker',
    'LibrarySpec',
    'BuildResult',
    'LibraryMetadata',
    'ValidationResult',
    'ModuleInfo',
    'LoadedLibrary',
    'CacheEntry',
    'CacheEntryType',
]
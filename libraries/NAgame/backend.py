"""
NAgame - Biblioteca de jogos simplificada estilo pygame.
Backend Python para a biblioteca NAgame.
"""

import sys
from typing import Optional, Tuple, Any, Dict, List


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
__all__ = ['NAgame', 'jogo']
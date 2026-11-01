"""
NAgame Animation Backend - Sistema de animação e sprites
"""

import pygame
import math


class Animacao:
    """Animação baseada em frames de sprite sheet."""

    def __init__(self, frames, duracao=0.1, loop=True, ping_pong=False):
        self.frames = frames  # lista de surfaces
        self.duracao = duracao  # segundos por frame
        self.loop = loop
        self.ping_pong = ping_pong
        self._tempo = 0.0
        self._frame_atual = 0
        self._direcao = 1
        self._terminou = False

    def atualizar(self, dt):
        if self._terminou and not self.loop:
            return

        self._tempo += dt
        if self._tempo >= self.duracao:
            self._tempo -= self.duracao
            self._frame_atual += self._direcao

            if self._frame_atual >= len(self.frames):
                if self.ping_pong:
                    self._direcao = -1
                    self._frame_atual = len(self.frames) - 2
                elif self.loop:
                    self._frame_atual = 0
                else:
                    self._frame_atual = len(self.frames) - 1
                    self._terminou = True
            elif self._frame_atual < 0:
                if self.ping_pong:
                    self._direcao = 1
                    self._frame_atual = 1
                elif self.loop:
                    self._frame_atual = len(self.frames) - 1
                else:
                    self._frame_atual = 0
                    self._terminou = True

    def frame_atual(self):
        return self.frames[self._frame_atual] if self.frames else None

    def indice_atual(self):
        return self._frame_atual

    def terminou(self):
        return self._terminou and not self.loop

    def reiniciar(self):
        self._tempo = 0.0
        self._frame_atual = 0
        self._direcao = 1
        self._terminou = False

    def definir_duracao(self, duracao):
        self.duracao = duracao


class AnimacaoSpriteSheet:
    """Cria animações a partir de sprite sheet."""

    def __init__(self, imagem, largura_frame, altura_frame, colunas, linhas=1, espacamento=0, margem=0):
        if isinstance(imagem, str):
            self.sheet = pygame.image.load(imagem).convert_alpha()
        else:
            self.sheet = imagem
        self.largura_frame = largura_frame
        self.altura_frame = altura_frame
        self.colunas = colunas
        self.linhas = linhas
        self.espacamento = espacamento
        self.margem = margem
        self._frames_cache = {}

    def obter_frames(self, linha=0, inicio=0, quantidade=None):
        """Extrai frames de uma linha."""
        chave = (linha, inicio, quantidade)
        if chave in self._frames_cache:
            return self._frames_cache[chave]

        frames = []
        max_frames = self.colunas
        if quantidade is None:
            quantidade = max_frames - inicio

        for i in range(quantidade):
            col = inicio + i
            if col >= self.colunas:
                break
            x = self.margem + col * (self.largura_frame + self.espacamento)
            y = self.margem + linha * (self.altura_frame + self.espacamento)
            rect = pygame.Rect(x, y, self.largura_frame, self.altura_frame)
            frame = self.sheet.subsurface(rect).copy()
            frames.append(frame)

        self._frames_cache[chave] = frames
        return frames

    def criar_animacao(self, linha=0, inicio=0, quantidade=None, duracao=0.1, loop=True, ping_pong=False):
        frames = self.obter_frames(linha, inicio, quantidade)
        return Animacao(frames, duracao, loop, ping_pong)


class Sprite:
    """Sprite animado com posição, rotação, escala."""

    def __init__(self, imagem=None, x=0, y=0):
        if isinstance(imagem, str):
            self._imagem_original = pygame.image.load(imagem).convert_alpha()
        elif isinstance(imagem, pygame.Surface):
            self._imagem_original = imagem
        else:
            self._imagem_original = pygame.Surface((32, 32))
            self._imagem_original.fill((255, 0, 255))

        self.x = float(x)
        self.y = float(y)
        self.rotacao = 0.0
        self.escala = 1.0
        self.origem = "centro"  # "centro", "canto", "baixo_centro"
        self.visivel = True
        self.alpha = 255
        self._animacao = None
        self._flip_x = False
        self._flip_y = False

    @property
    def imagem(self):
        if self._animacao:
            return self._animacao.frame_atual()
        return self._imagem_original

    @property
    def largura(self):
        img = self.imagem
        return int(img.get_width() * self.escala) if img else 0

    @property
    def altura(self):
        img = self.imagem
        return int(img.get_height() * self.escala) if img else 0

    @property
    def rect(self):
        w, h = self.largura, self.altura
        if self.origem == "centro":
            return pygame.Rect(int(self.x - w/2), int(self.y - h/2), w, h)
        elif self.origem == "baixo_centro":
            return pygame.Rect(int(self.x - w/2), int(self.y - h), w, h)
        else:
            return pygame.Rect(int(self.x), int(self.y), w, h)

    def definir_animacao(self, animacao):
        self._animacao = animacao
        if animacao:
            animacao.reiniciar()

    def atualizar(self, dt):
        if self._animacao:
            self._animacao.atualizar(dt)

    def desenhar(self, tela):
        if not self.visivel:
            return

        img = self.imagem
        if not img:
            return

        # Aplicar flip
        if self._flip_x or self._flip_y:
            img = pygame.transform.flip(img, self._flip_x, self._flip_y)

        # Aplicar escala
        if self.escala != 1.0:
            w = int(img.get_width() * self.escala)
            h = int(img.get_height() * self.escala)
            img = pygame.transform.scale(img, (w, h))

        # Aplicar rotação
        if self.rotacao != 0:
            img = pygame.transform.rotate(img, self.rotacao)

        # Aplicar alpha
        if self.alpha != 255:
            img.set_alpha(int(self.alpha))

        rect = img.get_rect()
        if self.origem == "centro":
            rect.center = (int(self.x), int(self.y))
        elif self.origem == "baixo_centro":
            rect.midbottom = (int(self.x), int(self.y))
        else:
            rect.topleft = (int(self.x), int(self.y))

        tela.blit(img, rect)

    def flip_x(self, valor=None):
        if valor is None:
            self._flip_x = not self._flip_x
        else:
            self._flip_x = valor

    def flip_y(self, valor=None):
        if valor is None:
            self._flip_y = not self._flip_y
        else:
            self._flip_y = valor

    def colide_com(self, outro):
        """Colisão retangular simples."""
        return self.rect.colliderect(outro.rect)


class Tween:
    """Interpolação suave de valores."""

    @staticmethod
    def linear(t): return t
    @staticmethod
    def ease_in(t): return t * t
    @staticmethod
    def ease_out(t): return 1 - (1 - t) * (1 - t)
    @staticmethod
    def ease_in_out(t): return 2*t*t if t < 0.5 else 1 - 2*(1-t)*(1-t)
    @staticmethod
    def bounce_out(t):
        if t < 1/2.75: return 7.5625*t*t
        elif t < 2/2.75: return 7.5625*(t-1.5/2.75)**2 + 0.75
        elif t < 2.5/2.75: return 7.5625*(t-2.25/2.75)**2 + 0.9375
        else: return 7.5625*(t-2.625/2.75)**2 + 0.984375

    def __init__(self, inicio, fim, duracao, easing=None, loop=False, ping_pong=False, ao_terminar=None):
        self.inicio = inicio
        self.fim = fim
        self.duracao = duracao
        self.easing = easing or Tween.linear
        self.loop = loop
        self.ping_pong = ping_pong
        self.ao_terminar = ao_terminar
        self._tempo = 0.0
        self._direcao = 1
        self._terminou = False
        self._valor = inicio

    def atualizar(self, dt):
        if self._terminou and not self.loop:
            return self._valor

        self._tempo += dt * self._direcao
        progresso = max(0, min(1, self._tempo / self.duracao))
        eased = self.easing(progresso)

        if isinstance(self.inicio, (int, float)) and isinstance(self.fim, (int, float)):
            self._valor = self.inicio + (self.fim - self.inicio) * eased
        elif hasattr(self.inicio, 'x'):  # Vetor2D-like
            self._valor = type(self.inicio)(
                self.inicio.x + (self.fim.x - self.inicio.x) * eased,
                self.inicio.y + (self.fim.y - self.inicio.y) * eased
            )

        if progresso >= 1.0:
            if self.ping_pong:
                self._direcao = -1
                self._tempo = self.duracao
                self.inicio, self.fim = self.fim, self.inicio
            elif self.loop:
                self._tempo = 0.0
            else:
                self._terminou = True
                if self.ao_terminar:
                    self.ao_terminar()

        return self._valor

    def valor(self):
        return self._valor

    def terminou(self):
        return self._terminou and not self.loop

    def reiniciar(self):
        self._tempo = 0.0
        self._direcao = 1
        self._terminou = False
        self._valor = self.inicio


class NAgameAnimation:
    """Gerenciador de animações."""

    def __init__(self):
        self.sprites = []
        self.tweens = []

    def criar_sprite(self, imagem, x, y):
        sprite = Sprite(imagem, x, y)
        self.sprites.append(sprite)
        return sprite

    def criar_sprite_sheet(self, caminho, largura, altura, colunas, linhas=1):
        return AnimacaoSpriteSheet(caminho, largura, altura, colunas, linhas)

    def criar_tween(self, inicio, fim, duracao, easing=None, loop=False, ping_pong=False, ao_terminar=None):
        tween = Tween(inicio, fim, duracao, easing, loop, ping_pong, ao_terminar)
        self.tweens.append(tween)
        return tween

    def atualizar(self, dt):
        for sprite in self.sprites[:]:
            if hasattr(sprite, '_removido') and sprite._removido:
                self.sprites.remove(sprite)
            else:
                sprite.atualizar(dt)

        for tween in self.tweens[:]:
            if tween.terminou() and not tween.loop:
                self.tweens.remove(tween)
            else:
                tween.atualizar(dt)

    def desenhar_todos(self, tela):
        for sprite in self.sprites:
            if sprite.visivel:
                sprite.desenhar(tela)

    def remover_sprite(self, sprite):
        if sprite in self.sprites:
            sprite._removido = True

    def limpar(self):
        self.sprites.clear()
        self.tweens.clear()
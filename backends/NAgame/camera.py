"""
NAgame Camera Backend - Sistema de câmera 2D com transformações
"""

import pygame
import math


class NAgameCamera:
    """Câmera 2D com follow, zoom, rotação, shake e limites."""

    def __init__(self, largura_tela, altura_tela, mundo_largura=None, mundo_altura=None):
        self.largura_tela = largura_tela
        self.altura_tela = altura_tela
        self.mundo_largura = mundo_largura
        self.mundo_altura = mundo_altura

        # Transformação
        self.x = 0.0
        self.y = 0.0
        self.zoom = 1.0
        self.rotacao = 0.0

        # Follow
        self.alvo = None
        self.suavidade = 0.1
        self.offset_x = 0
        self.offset_y = 0
        self.margem = 0  # dead zone

        # Shake
        self._shake_intensidade = 0
        self._shake_tempo = 0
        self._shake_duracao = 0
        self._shake_offset_x = 0
        self._shake_offset_y = 0

        # Limites
        self._limites = None  # (x, y, largura, altura)

        # Surface de renderização (para zoom/rotação)
        self._surface_mundo = None
        self._surface_rotacionada = None

    def definir_limites(self, x, y, largura, altura):
        """Define limites do mundo para a câmera."""
        self._limites = (x, y, largura, altura)

    def definir_tamanho_mundo(self, largura, altura):
        self.mundo_largura = largura
        self.mundo_altura = altura

    def seguir(self, alvo, suavidade=None, offset_x=0, offset_y=0, margem=0):
        """Define alvo para a câmera seguir."""
        self.alvo = alvo
        if suavidade is not None:
            self.suavidade = suavidade
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.margem = margem

    def parar_seguir(self):
        self.alvo = None

    def shake(self, intensidade, duracao):
        """Inicia shake da câmera."""
        self._shake_intensidade = intensidade
        self._shake_duracao = duracao
        self._shake_tempo = duracao

    def atualizar(self, dt):
        # Follow
        if self.alvo:
            # Posição desejada (centro do alvo + offset)
            if hasattr(self.alvo, 'x') and hasattr(self.alvo, 'y'):
                # Objeto com x, y
                alvo_x = self.alvo.x
                alvo_y = self.alvo.y
                if hasattr(self.alvo, 'largura') and hasattr(self.alvo, 'altura'):
                    alvo_x += self.alvo.largura / 2
                    alvo_y += self.alvo.altura / 2
            elif hasattr(self.alvo, 'pos'):
                # Objeto com vetor pos
                alvo_x = self.alvo.pos.x
                alvo_y = self.alvo.pos.y
            else:
                alvo_x, alvo_y = self.alvo

            desejado_x = alvo_x - self.largura_tela / (2 * self.zoom) + self.offset_x
            desejado_y = alvo_y - self.altura_tela / (2 * self.zoom) + self.offset_y

            # Dead zone
            if self.margem > 0:
                dx = desejado_x - self.x
                dy = desejado_y - self.y
                if abs(dx) < self.margem:
                    desejado_x = self.x
                if abs(dy) < self.margem:
                    desejado_y = self.y

            # Suavizar
            self.x += (desejado_x - self.x) * self.suavidade
            self.y += (desejado_y - self.y) * self.suavidade

        # Shake
        if self._shake_tempo > 0:
            self._shake_tempo -= dt
            progresso = 1.0 - (self._shake_tempo / self._shake_duracao)
            intensidade_atual = self._shake_intensidade * (1 - progresso)
            self._shake_offset_x = random.uniform(-intensidade_atual, intensidade_atual)
            self._shake_offset_y = random.uniform(-intensidade_atual, intensidade_atual)
        else:
            self._shake_offset_x = 0
            self._shake_offset_y = 0

        # Aplicar limites
        self._aplicar_limites()

    def _aplicar_limites(self):
        if self._limites:
            lx, ly, lw, lh = self._limites
            # Calcular limites visíveis considerando zoom
            vis_w = self.largura_tela / self.zoom
            vis_h = self.altura_tela / self.zoom

            min_x = lx
            max_x = lx + lw - vis_w
            min_y = ly
            max_y = ly + lh - vis_h

            self.x = max(min_x, min(max_x, self.x))
            self.y = max(min_y, min(max_y, self.y))
        elif self.mundo_largura and self.mundo_altura:
            vis_w = self.largura_tela / self.zoom
            vis_h = self.altura_tela / self.zoom
            self.x = max(0, min(self.mundo_largura - vis_w, self.x))
            self.y = max(0, min(self.mundo_altura - vis_h, self.y))

    def aplicar(self, tela):
        """Aplica transformação da câmera à tela."""
        # Criar surface do mundo se necessário
        if self._surface_mundo is None or \
           self._surface_mundo.get_width() != self.largura_tela or \
           self._surface_mundo.get_height() != self.altura_tela:
            self._surface_mundo = pygame.Surface((self.largura_tela, self.altura_tela), pygame.SRCALPHA)

        # A surface mundo será desenhada pelo jogo, nós apenas retornamos a transformação
        # O jogo deve desenhar na surface_mundo, depois chamar desenhar_final
        return self._surface_mundo

    def desenhar_final(self, tela, surface_mundo=None):
        """Desenha surface do mundo na tela com transformações da câmera."""
        if surface_mundo is None:
            surface_mundo = self._surface_mundo

        surface_trabalho = surface_mundo

        # Aplicar rotação
        if self.rotacao != 0:
            surface_trabalho = pygame.transform.rotate(surface_trabalho, math.degrees(self.rotacao))

        # Aplicar zoom
        if self.zoom != 1.0:
            w = int(surface_trabalho.get_width() * self.zoom)
            h = int(surface_trabalho.get_height() * self.zoom)
            surface_trabalho = pygame.transform.scale(surface_trabalho, (w, h))

        # Calcular posição de desenho (centralizar + shake)
        rect = surface_trabalho.get_rect()
        rect.centerx = self.largura_tela // 2 + int(self._shake_offset_x)
        rect.centery = self.altura_tela // 2 + int(self._shake_offset_y)

        # Offset da câmera
        rect.x -= int(self.x * self.zoom)
        rect.y -= int(self.y * self.zoom)

        tela.blit(surface_trabalho, rect)

    def mundo_para_tela(self, x, y):
        """Converte coordenadas do mundo para tela."""
        # Inverso da transformação
        rel_x = x - self.x
        rel_y = y - self.y

        # Rotacionar inverso
        if self.rotacao != 0:
            c = math.cos(-self.rotacao)
            s = math.sin(-self.rotacao)
            rx = rel_x * c - rel_y * s
            ry = rel_x * s + rel_y * c
            rel_x, rel_y = rx, ry

        # Zoom e centralizar
        tela_x = rel_x * self.zoom + self.largura_tela / 2 + self._shake_offset_x
        tela_y = rel_y * self.zoom + self.altura_tela / 2 + self._shake_offset_y

        return (int(tela_x), int(tela_y))

    def tela_para_mundo(self, x, y):
        """Converte coordenadas da tela para mundo."""
        # Remover shake e centralizar
        rel_x = (x - self.largura_tela / 2 - self._shake_offset_x) / self.zoom
        rel_y = (y - self.altura_tela / 2 - self._shake_offset_y) / self.zoom

        # Rotacionar
        if self.rotacao != 0:
            c = math.cos(self.rotacao)
            s = math.sin(self.rotacao)
            rx = rel_x * c - rel_y * s
            ry = rel_x * s + rel_y * c
            rel_x, rel_y = rx, ry

        # Adicionar posição da câmera
        mundo_x = rel_x + self.x
        mundo_y = rel_y + self.y

        return (mundo_x, mundo_y)

    def rect_mundo_para_tela(self, rect):
        """Converte rect do mundo para tela."""
        x, y = self.mundo_para_tela(rect.x, rect.y)
        w = int(rect.width * self.zoom)
        h = int(rect.height * self.zoom)
        return pygame.Rect(x, y, w, h)

    def esta_visivel(self, x, y, largura=0, altura=0):
        """Verifica se objeto está visível na câmera."""
        tela_x, tela_y = self.mundo_para_tela(x, y)
        w = largura * self.zoom
        h = altura * self.zoom
        return (tela_x + w >= 0 and tela_x <= self.largura_tela and
                tela_y + h >= 0 and tela_y <= self.altura_tela)

    def definir_zoom(self, zoom, suave=False, velocidade=5.0):
        if suave:
            # Implementar interpolação suave depois se necessário
            pass
        self.zoom = max(0.1, min(10.0, zoom))

    def definir_rotacao(self, rotacao):
        self.rotacao = rotacao

    def centralizar_em(self, x, y):
        self.x = x - self.largura_tela / (2 * self.zoom)
        self.y = y - self.altura_tela / (2 * self.zoom)
        self._aplicar_limites()


# Import random aqui para evitar circular import
import random
"""
NAgame Graphics Backend - Gráficos avançados usando Pygame
"""

import pygame
import math


class NAgameGraphics:
    """Sistema de gráficos avançados."""

    def __init__(self, tela):
        self.tela = tela
        self._fontes = {}
        self._imagens_cache = {}

    # --- Fontes ---
    def fonte(self, nome=None, tamanho=24):
        """Obtém ou cria uma fonte."""
        chave = (nome, tamanho)
        if chave not in self._fontes:
            if nome:
                self._fontes[chave] = pygame.font.Font(nome, tamanho)
            else:
                self._fontes[chave] = pygame.font.Font(None, tamanho)
        return self._fontes[chave]

    def texto(self, texto, x, y, tamanho=24, cor=(255, 255, 255), fonte_nome=None, alinhamento="esquerda"):
        """Desenha texto com alinhamento."""
        fonte = self.fonte(fonte_nome, tamanho)
        superficie = fonte.render(str(texto), True, cor)
        rect = superficie.get_rect()

        if alinhamento == "centro":
            rect.centerx = int(x)
            rect.y = int(y)
        elif alinhamento == "direita":
            rect.right = int(x)
            rect.y = int(y)
        else:
            rect.x = int(x)
            rect.y = int(y)

        self.tela.blit(superficie, rect)
        return rect

    def medir_texto(self, texto, tamanho=24, fonte_nome=None):
        """Retorna largura e altura do texto."""
        fonte = self.fonte(fonte_nome, tamanho)
        return fonte.size(str(texto))

    # --- Imagens ---
    def carregar_imagem(self, caminho):
        """Carrega imagem com cache."""
        if caminho not in self._imagens_cache:
            try:
                self._imagens_cache[caminho] = pygame.image.load(caminho).convert_alpha()
            except Exception as e:
                print(f"Erro ao carregar imagem {caminho}: {e}")
                # Criar surface placeholder
                surf = pygame.Surface((32, 32))
                surf.fill((255, 0, 255))
                self._imagens_cache[caminho] = surf
        return self._imagens_cache[caminho]

    def desenhar_imagem(self, imagem, x, y, largura=None, altura=None, rotacao=0, escala=1.0, origem="centro"):
        """Desenha imagem com transformações."""
        if isinstance(imagem, str):
            imagem = self.carregar_imagem(imagem)

        # Aplicar escala
        if escala != 1.0 or largura or altura:
            w = int(imagem.get_width() * escala)
            h = int(imagem.get_height() * escala)
            if largura: w = int(largura)
            if altura: h = int(altura)
            imagem = pygame.transform.scale(imagem, (w, h))

        # Aplicar rotação
        if rotacao != 0:
            imagem = pygame.transform.rotate(imagem, rotacao)

        rect = imagem.get_rect()

        if origem == "centro":
            rect.center = (int(x), int(y))
        elif origem == "canto":
            rect.topleft = (int(x), int(y))
        elif origem == "baixo_centro":
            rect.midbottom = (int(x), int(y))

        self.tela.blit(imagem, rect)
        return rect

    def cortar_imagem(self, imagem, x, y, largura, altura):
        """Retorna sub-surface de uma imagem (sprite sheet)."""
        if isinstance(imagem, str):
            imagem = self.carregar_imagem(imagem)
        return imagem.subsurface(pygame.Rect(int(x), int(y), int(largura), int(altura)))

    # --- Formas ---
    def retangulo(self, x, y, largura, altura, cor=(255, 255, 255), preenchido=True, borda=0, raio=0):
        """Desenha retângulo com cantos arredondados opcionais."""
        rect = pygame.Rect(int(x), int(y), int(largura), int(altura))
        if raio > 0 and preenchido:
            pygame.draw.rect(self.tela, cor, rect, border_radius=int(raio))
        elif preenchido:
            pygame.draw.rect(self.tela, cor, rect)
        else:
            pygame.draw.rect(self.tela, cor, rect, int(borda), border_radius=int(raio))

    def circulo(self, x, y, raio, cor=(255, 255, 255), preenchido=True, borda=1):
        centro = (int(x), int(y))
        r = int(raio)
        if preenchido:
            pygame.draw.circle(self.tela, cor, centro, r)
        else:
            pygame.draw.circle(self.tela, cor, centro, r, int(borda))

    def elipse(self, x, y, largura, altura, cor=(255, 255, 255), preenchido=True, borda=1):
        rect = pygame.Rect(int(x), int(y), int(largura), int(altura))
        if preenchido:
            pygame.draw.ellipse(self.tela, cor, rect)
        else:
            pygame.draw.ellipse(self.tela, cor, rect, int(borda))

    def linha(self, x1, y1, x2, y2, cor=(255, 255, 255), espessura=1):
        pygame.draw.line(self.tela, cor, (int(x1), int(y1)), (int(x2), int(y2)), int(espessura))

    def linhas(self, pontos, cor=(255, 255, 255), fechado=False, espessura=1):
        """Desenha múltiplas linhas conectadas."""
        pts = [(int(p[0]), int(p[1])) for p in pontos]
        if len(pts) >= 2:
            pygame.draw.lines(self.tela, cor, fechado, pts, int(espessura))

    def poligono(self, pontos, cor=(255, 255, 255), preenchido=True, borda=1):
        pts = [(int(p[0]), int(p[1])) for p in pontos]
        if len(pts) >= 3:
            if preenchido:
                pygame.draw.polygon(self.tela, cor, pts)
            else:
                pygame.draw.polygon(self.tela, cor, pts, int(borda))

    def arco(self, x, y, largura, altura, ang_inicio, ang_fim, cor=(255, 255, 255), espessura=1):
        rect = pygame.Rect(int(x), int(y), int(largura), int(altura))
        pygame.draw.arc(self.tela, cor, rect, ang_inicio, ang_fim, int(espessura))

    # --- Efeitos ---
    def superficie_com_alpha(self, largura, altura):
        """Cria surface com canal alpha."""
        return pygame.Surface((int(largura), int(altura)), pygame.SRCALPHA)

    def aplicar_alpha(self, surface, alpha):
        """Aplica transparência a uma surface."""
        surface.set_alpha(int(alpha * 255))
        return surface

    def mesclar(self, surface_destino, surface_origem, x, y, modo=pygame.BLEND_ALPHA_SDL2):
        """Mescla duas surfaces."""
        self.tela.blit(surface_origem, (int(x), int(y)), special_flags=modo)

    # --- Filtros/Shaders simples ---
    def cinza(self, surface):
        """Converte surface para escala de cinza."""
        arr = pygame.surfarray.pixels3d(surface)
        cinza = arr.mean(axis=2).astype('uint8')
        return pygame.surfarray.make_surface(cinza)

    def inverter_cores(self, surface):
        """Inverte cores da surface."""
        return pygame.transform.invert(surface)

    # --- Captura de tela ---
    def capturar_tela(self, x=0, y=0, largura=None, altura=None):
        """Captura região da tela como surface."""
        if largura is None:
            largura = self.tela.get_width()
        if altura is None:
            altura = self.tela.get_height()
        rect = pygame.Rect(int(x), int(y), int(largura), int(altura))
        return self.tela.subsurface(rect).copy()

    def salvar_captura(self, caminho, x=0, y=0, largura=None, altura=None):
        """Salva captura de tela em arquivo."""
        surface = self.capturar_tela(x, y, largura, altura)
        pygame.image.save(surface, caminho)

    # --- Limpeza ---
    def limpar_cache(self):
        self._imagens_cache.clear()
        self._fontes.clear()
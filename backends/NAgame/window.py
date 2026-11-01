"""
NAgame Window Backend - Janela principal usando Pygame
"""

import pygame
import math


class NAgameWindow:
    """Janela principal do jogo usando Pygame."""

    def __init__(self, largura=800, altura=600, titulo="Jogo Nativa"):
        self.largura = largura
        self.altura = altura
        self.titulo = titulo
        self._iniciado = False
        self._rodando = False
        self._tela = None
        self._relogio = None
        self._cor_fundo = (0, 0, 0)
        self._teclas = {}
        self._teclas_anteriores = {}
        self._mouse_pos = (0, 0)
        self._mouse_botoes = (False, False, False)
        self._mouse_botoes_anteriores = (False, False, False)

    def iniciar(self):
        """Inicializa o pygame e cria a janela."""
        try:
            pygame.init()
            self._tela = pygame.display.set_mode((self.largura, self.altura))
            pygame.display.set_caption(self.titulo)
            self._relogio = pygame.time.Clock()
            self._iniciado = True
            self._rodando = True
            return True
        except Exception as e:
            print(f"Erro ao inicializar pygame: {e}")
            return False

    def rodar(self, funcao_atualizar, funcao_desenhar):
        """Loop principal do jogo."""
        if not self._iniciado:
            self.iniciar()

        while self._rodando:
            dt = self._relogio.tick(60) / 1000.0  # delta time em segundos

            # Atualizar estados anteriores
            self._teclas_anteriores = self._teclas.copy()
            self._mouse_botoes_anteriores = self._mouse_botoes

            # Processar eventos
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    self._rodando = False
                elif evento.type == pygame.KEYDOWN:
                    self._teclas[evento.key] = True
                elif evento.type == pygame.KEYUP:
                    self._teclas[evento.key] = False
                elif evento.type == pygame.MOUSEMOTION:
                    self._mouse_pos = evento.pos
                elif evento.type == pygame.MOUSEBUTTONDOWN:
                    self._mouse_botoes = list(self._mouse_botoes)
                    if evento.button <= 3:
                        self._mouse_botoes[evento.button - 1] = True
                    self._mouse_botoes = tuple(self._mouse_botoes)
                elif evento.type == pygame.MOUSEBUTTONUP:
                    self._mouse_botoes = list(self._mouse_botoes)
                    if evento.button <= 3:
                        self._mouse_botoes[evento.button - 1] = False
                    self._mouse_botoes = tuple(self._mouse_botoes)

            # Chamar função de atualização
            try:
                funcao_atualizar(dt)
            except Exception as e:
                print(f"Erro na atualização: {e}")

            # Desenhar
            self._tela.fill(self._cor_fundo)
            try:
                funcao_desenhar(self._tela)
            except Exception as e:
                print(f"Erro no desenho: {e}")

            pygame.display.flip()

        pygame.quit()

    def parar(self):
        """Para o loop do jogo."""
        self._rodando = False

    # --- Propriedades ---
    @property
    def tela(self):
        return self._tela

    @property
    def rodando(self):
        return self._rodando

    # --- Entrada (Teclado) ---
    def tecla(self, tecla):
        """Verifica se tecla está pressionada."""
        mapa = {
            'espaço': pygame.K_SPACE,
            'esquerda': pygame.K_LEFT,
            'direita': pygame.K_RIGHT,
            'cima': pygame.K_UP,
            'baixo': pygame.K_DOWN,
            'esc': pygame.K_ESCAPE,
            'enter': pygame.K_RETURN,
            'w': pygame.K_w,
            'a': pygame.K_a,
            's': pygame.K_s,
            'd': pygame.K_d,
            'shift': pygame.K_LSHIFT,
            'ctrl': pygame.K_LCTRL,
            'alt': pygame.K_LALT,
            'tab': pygame.K_TAB,
        }
        key = mapa.get(tecla.lower(), getattr(pygame, f'K_{tecla}', None))
        if key is not None:
            return self._teclas.get(key, False)
        return False

    def tecla_pressionada(self, tecla):
        """Verifica se tecla foi pressionada neste frame."""
        mapa = {
            'espaço': pygame.K_SPACE,
            'esquerda': pygame.K_LEFT,
            'direita': pygame.K_RIGHT,
            'cima': pygame.K_UP,
            'baixo': pygame.K_DOWN,
            'esc': pygame.K_ESCAPE,
            'enter': pygame.K_RETURN,
        }
        key = mapa.get(tecla.lower(), getattr(pygame, f'K_{tecla}', None))
        if key is not None:
            return self._teclas.get(key, False) and not self._teclas_anteriores.get(key, False)
        return False

    # --- Mouse ---
    def mouse_pos(self):
        return self._mouse_pos

    def mouse_clicado(self, botao=1):
        if 1 <= botao <= 3:
            return self._mouse_botoes[botao - 1] and not self._mouse_botoes_anteriores[botao - 1]
        return False

    def mouse_pressionado(self, botao=1):
        if 1 <= botao <= 3:
            return self._mouse_botoes[botao - 1]
        return False

    # --- Controle FPS e Tempo ---
    def fps(self):
        return int(self._relogio.get_fps())

    def tempo(self):
        return pygame.time.get_ticks() / 1000.0

    # --- Gráficos Básicos ---
    def limpar(self, cor=None):
        if cor:
            self._tela.fill(cor)
        else:
            self._tela.fill(self._cor_fundo)

    def ret(self, x, y, largura, altura, cor=(255, 255, 255), preenchido=True):
        rect = pygame.Rect(int(x), int(y), int(largura), int(altura))
        if preenchido:
            pygame.draw.rect(self._tela, cor, rect)
        else:
            pygame.draw.rect(self._tela, cor, rect, 2)

    def circ(self, x, y, raio, cor=(255, 255, 255), preenchido=True):
        centro = (int(x), int(y))
        raio_int = int(raio)
        if preenchido:
            pygame.draw.circle(self._tela, cor, centro, raio_int)
        else:
            pygame.draw.circle(self._tela, cor, centro, raio_int, 2)

    def linha(self, x1, y1, x2, y2, cor=(255, 255, 255), espessura=1):
        pygame.draw.line(self._tela, cor, (int(x1), int(y1)), (int(x2), int(y2)), int(espessura))

    def texto(self, texto, x, y, tamanho=24, cor=(255, 255, 255), fonte=None):
        if fonte is None:
            fonte = pygame.font.Font(None, tamanho)
        superficie = fonte.render(str(texto), True, cor)
        self._tela.blit(superficie, (int(x), int(y)))

    def img(self, caminho, x, y, largura=None, altura=None):
        """Carrega e desenha imagem. Retorna a surface para reuso."""
        try:
            if isinstance(caminho, str):
                surface = pygame.image.load(caminho).convert_alpha()
            else:
                surface = caminho  # Já é uma surface
            if largura and altura:
                surface = pygame.transform.scale(surface, (int(largura), int(altura)))
            self._tela.blit(surface, (int(x), int(y)))
            return surface
        except Exception as e:
            print(f"Erro ao carregar imagem: {e}")
            return None

    def centralizar(self, obj_largura, obj_altura):
        return ((self.largura - obj_largura) // 2, (self.altura - obj_altura) // 2)

    def definir_fundo(self, cor):
        self._cor_fundo = cor
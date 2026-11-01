"""
NAgame Interface Backend - Sistema de UI (botões, painéis, menus, inputs)
"""

import pygame


class UIElemento:
    """Elemento base da UI."""

    def __init__(self, x, y, largura, altura):
        self.x = float(x)
        self.y = float(y)
        self.largura = float(largura)
        self.altura = float(altura)
        self.visivel = True
        self.ativo = True
        self._hover = False
        self._pressed = False
        self._foco = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), int(self.largura), int(self.altura))

    def contem_ponto(self, px, py):
        return self.rect.collidepoint(px, py)

    def atualizar(self, mouse_pos, mouse_clicado, dt=0):
        pass

    def desenhar(self, tela, graphics):
        pass

    def evento(self, evento):
        pass


class Botao(UIElemento):
    """Botão clicável."""

    def __init__(self, x, y, largura, altura, texto="", acao=None,
                 cor_normal=(100, 100, 100), cor_hover=(150, 150, 150),
                 cor_pressed=(200, 200, 200), cor_texto=(255, 255, 255),
                 fonte_tamanho=20, borda_raio=5):
        super().__init__(x, y, largura, altura)
        self.texto = texto
        self.acao = acao
        self.cor_normal = cor_normal
        self.cor_hover = cor_hover
        self.cor_pressed = cor_pressed
        self.cor_texto = cor_texto
        self.fonte_tamanho = fonte_tamanho
        self.borda_raio = borda_raio
        self.estado = "normal"
        self._fonte = None

    @property
    def fonte(self):
        if self._fonte is None:
            self._fonte = pygame.font.Font(None, self.fonte_tamanho)
        return self._fonte

    def atualizar(self, mouse_pos, mouse_clicado, dt=0):
        if not self.ativo:
            self.estado = "normal"
            return

        if self.contem_ponto(*mouse_pos):
            if mouse_clicado:
                self.estado = "pressed"
                self._pressed = True
            else:
                self.estado = "hover"
                self._hover = True
                if self._pressed and self.acao:
                    self.acao()
                    self._pressed = False
        else:
            self.estado = "normal"
            self._hover = False
            self._pressed = False

    def desenhar(self, tela, graphics=None):
        if not self.visivel:
            return

        if self.estado == "hover":
            cor = self.cor_hover
        elif self.estado == "pressed":
            cor = self.cor_pressed
        else:
            cor = self.cor_normal

        # Desenhar fundo
        if graphics:
            graphics.retangulo(self.x, self.y, self.largura, self.altura, cor, True, raio=self.borda_raio)
        else:
            pygame.draw.rect(tela, cor, self.rect, border_radius=self.borda_raio)

        # Desenhar texto
        if self.texto:
            texto_surf = self.fonte.render(self.texto, True, self.cor_texto)
            texto_rect = texto_surf.get_rect(center=self.rect.center)
            tela.blit(texto_surf, texto_rect)


class Painel(UIElemento):
    """Container para outros elementos UI."""

    def __init__(self, x, y, largura, altura, cor=(50, 50, 50, 200), borda_raio=0):
        super().__init__(x, y, largura, altura)
        self.cor = cor
        self.borda_raio = borda_raio
        self.elementos = []

    def add(self, elemento):
        self.elementos.append(elemento)
        return elemento

    def remover(self, elemento):
        if elemento in self.elementos:
            self.elementos.remove(elemento)

    def limpar(self):
        self.elementos.clear()

    def atualizar(self, mouse_pos, mouse_clicado, dt=0):
        for el in self.elementos:
            if el.visivel and el.ativo:
                # Ajustar posição do mouse relativa ao painel
                rel_mouse = (mouse_pos[0] - self.x, mouse_pos[1] - self.y)
                el.atualizar(rel_mouse, mouse_clicado, dt)

    def desenhar(self, tela, graphics=None):
        if not self.visivel:
            return

        # Desenhar fundo do painel
        if graphics:
            graphics.retangulo(self.x, self.y, self.largura, self.altura, self.cor, True, raio=self.borda_raio)
        else:
            if len(self.cor) == 4:
                surf = pygame.Surface((self.largura, self.altura), pygame.SRCALPHA)
                surf.fill(self.cor)
                tela.blit(surf, (self.x, self.y))
            else:
                pygame.draw.rect(tela, self.cor, self.rect, border_radius=self.borda_raio)

        # Desenhar elementos filhos
        for el in self.elementos:
            if el.visivel:
                # Salvar posição original
                orig_x, orig_y = el.x, el.y
                el.x += self.x
                el.y += self.y
                el.desenhar(tela, graphics)
                el.x, el.y = orig_x, orig_y


class CaixaTexto(UIElemento):
    """Campo de entrada de texto."""

    def __init__(self, x, y, largura, altura, texto="", placeholder="",
                 cor_fundo=(30, 30, 30), cor_borda=(100, 100, 100),
                 cor_borda_foco=(100, 200, 255), cor_texto=(255, 255, 255),
                 cor_placeholder=(150, 150, 150), fonte_tamanho=20, max_chars=100,
                 senha=False, apenas_numeros=False):
        super().__init__(x, y, largura, altura)
        self.texto = texto
        self.placeholder = placeholder
        self.cor_fundo = cor_fundo
        self.cor_borda = cor_borda
        self.cor_borda_foco = cor_borda_foco
        self.cor_texto = cor_texto
        self.cor_placeholder = cor_placeholder
        self.fonte_tamanho = fonte_tamanho
        self.max_chars = max_chars
        self.senha = senha
        self.apenas_numeros = apenas_numeros
        self._fonte = None
        self._cursor_pos = len(texto)
        self._cursor_timer = 0
        self._cursor_visivel = True

    @property
    def fonte(self):
        if self._fonte is None:
            self._fonte = pygame.font.Font(None, self.fonte_tamanho)
        return self._fonte

    def atualizar(self, mouse_pos, mouse_clicado, dt=0):
        # Foco
        if mouse_clicado:
            self._foco = self.contem_ponto(*mouse_pos)

        # Cursor blink
        self._cursor_timer += dt
        if self._cursor_timer >= 0.5:
            self._cursor_timer = 0
            self._cursor_visivel = not self._cursor_visivel

    def evento(self, evento):
        if not self._foco or evento.type != pygame.KEYDOWN:
            return

        if evento.key == pygame.K_BACKSPACE:
            if self._cursor_pos > 0:
                self.texto = self.texto[:self._cursor_pos-1] + self.texto[self._cursor_pos:]
                self._cursor_pos -= 1
        elif evento.key == pygame.K_DELETE:
            if self._cursor_pos < len(self.texto):
                self.texto = self.texto[:self._cursor_pos] + self.texto[self._cursor_pos+1:]
        elif evento.key == pygame.K_LEFT:
            self._cursor_pos = max(0, self._cursor_pos - 1)
        elif evento.key == pygame.K_RIGHT:
            self._cursor_pos = min(len(self.texto), self._cursor_pos + 1)
        elif evento.key == pygame.K_HOME:
            self._cursor_pos = 0
        elif evento.key == pygame.K_END:
            self._cursor_pos = len(self.texto)
        elif evento.unicode and len(self.texto) < self.max_chars:
            char = evento.unicode
            if self.apenas_numeros and not char.isdigit():
                return
            self.texto = self.texto[:self._cursor_pos] + char + self.texto[self._cursor_pos:]
            self._cursor_pos += 1

    def desenhar(self, tela, graphics=None):
        if not self.visivel:
            return

        # Fundo
        if graphics:
            graphics.retangulo(self.x, self.y, self.largura, self.altura, self.cor_fundo, True)
            cor_borda = self.cor_borda_foco if self._foco else self.cor_borda
            graphics.retangulo(self.x, self.y, self.largura, self.altura, cor_borda, False, borda=2)
        else:
            pygame.draw.rect(tela, self.cor_fundo, self.rect)
            cor_borda = self.cor_borda_foco if self._foco else self.cor_borda
            pygame.draw.rect(tela, cor_borda, self.rect, 2)

        # Texto
        texto_exibicao = "*" * len(self.texto) if self.senha else self.texto
        if texto_exibicao:
            cor = self.cor_texto
            txt_surf = self.fonte.render(texto_exibicao, True, cor)
        elif self.placeholder:
            cor = self.cor_placeholder
            txt_surf = self.fonte.render(self.placeholder, True, cor)
        else:
            txt_surf = None

        if txt_surf:
            # Área de texto (com padding)
            padding = 5
            txt_rect = txt_surf.get_rect()
            txt_rect.x = int(self.x + padding)
            txt_rect.centery = int(self.y + self.altura / 2)
            # Clipping
            clip_rect = pygame.Rect(int(self.x + padding), int(self.y),
                                  int(self.largura - 2*padding), int(self.altura))
            tela.set_clip(clip_rect)
            tela.blit(txt_surf, txt_rect)
            tela.set_clip(None)

        # Cursor
        if self._foco and self._cursor_visivel:
            txt_antes = self.texto[:self._cursor_pos]
            if self.senha:
                txt_antes = "*" * len(txt_antes)
            cursor_x = int(self.x + 5 + self.fonte.size(txt_antes)[0])
            cursor_y1 = int(self.y + 3)
            cursor_y2 = int(self.y + self.altura - 3)
            pygame.draw.line(tela, self.cor_texto, (cursor_x, cursor_y1), (cursor_x, cursor_y2), 2)


class Label(UIElemento):
    """Texto estático."""

    def __init__(self, x, y, texto="", tamanho=20, cor=(255, 255, 255),
                 alinhamento="esquerda", fonte_nome=None):
        super().__init__(x, y, 0, 0)
        self.texto = texto
        self.tamanho = tamanho
        self.cor = cor
        self.alinhamento = alinhamento
        self.fonte_nome = fonte_nome
        self._fonte = None
        self._atualizar_tamanho()

    @property
    def fonte(self):
        if self._fonte is None:
            if self.fonte_nome:
                self._fonte = pygame.font.Font(self.fonte_nome, self.tamanho)
            else:
                self._fonte = pygame.font.Font(None, self.tamanho)
        return self._fonte

    def _atualizar_tamanho(self):
        w, h = self.fonte.size(self.texto)
        self.largura = w
        self.altura = h

    def definir_texto(self, texto):
        self.texto = str(texto)
        self._atualizar_tamanho()

    def desenhar(self, tela, graphics=None):
        if not self.visivel:
            return

        if graphics:
            graphics.texto(self.texto, self.x, self.y, self.tamanho, self.cor,
                          self.fonte_nome, self.alinhamento)
        else:
            surf = self.fonte.render(self.texto, True, self.cor)
            rect = surf.get_rect()
            if self.alinhamento == "centro":
                rect.centerx = int(self.x)
                rect.y = int(self.y)
            elif self.alinhamento == "direita":
                rect.right = int(self.x)
                rect.y = int(self.y)
            else:
                rect.topleft = (int(self.x), int(self.y))
            tela.blit(surf, rect)


class BarraProgresso(UIElemento):
    """Barra de progresso."""

    def __init__(self, x, y, largura, altura, valor=0, max_valor=100,
                 cor_fundo=(50, 50, 50), cor_frente=(100, 200, 100),
                 cor_borda=(150, 150, 150), borda_raio=5):
        super().__init__(x, y, largura, altura)
        self.valor = max(0, min(max_valor, valor))
        self.max_valor = max_valor
        self.cor_fundo = cor_fundo
        self.cor_frente = cor_frente
        self.cor_borda = cor_borda
        self.borda_raio = borda_raio

    @property
    def porcentagem(self):
        return self.valor / self.max_valor if self.max_valor > 0 else 0

    def desenhar(self, tela, graphics=None):
        if not self.visivel:
            return

        if graphics:
            graphics.retangulo(self.x, self.y, self.largura, self.altura, self.cor_fundo, True, raio=self.borda_raio)
            if self.valor > 0:
                w = int(self.largura * self.porcentagem)
                graphics.retangulo(self.x, self.y, w, self.altura, self.cor_frente, True, raio=self.borda_raio)
            graphics.retangulo(self.x, self.y, self.largura, self.altura, self.cor_borda, False, borda=2, raio=self.borda_raio)
        else:
            pygame.draw.rect(tela, self.cor_fundo, self.rect, border_radius=self.borda_raio)
            if self.valor > 0:
                w = int(self.largura * self.porcentagem)
                frente_rect = pygame.Rect(int(self.x), int(self.y), w, int(self.altura))
                pygame.draw.rect(tela, self.cor_frente, frente_rect, border_radius=self.borda_raio)
            pygame.draw.rect(tela, self.cor_borda, self.rect, 2, border_radius=self.borda_raio)


class Menu(UIElemento):
    """Menu dropdown."""

    def __init__(self, x, y, largura, altura_opcao=30,
                 cor_fundo=(50, 50, 50), cor_hover=(80, 80, 120),
                 cor_texto=(255, 255, 255), fonte_tamanho=20):
        super().__init__(x, y, largura, 0)
        self.altura_opcao = altura_opcao
        self.cor_fundo = cor_fundo
        self.cor_hover = cor_hover
        self.cor_texto = cor_texto
        self.fonte_tamanho = fonte_tamanho
        self.opcoes = []  # lista de (texto, callback)
        self.aberto = False
        self._hover_idx = -1
        self._fonte = None

    @property
    def fonte(self):
        if self._fonte is None:
            self._fonte = pygame.font.Font(None, self.fonte_tamanho)
        return self._fonte

    def add_opcao(self, texto, callback=None):
        self.opcoes.append({"texto": texto, "callback": callback})
        self.altura = len(self.opcoes) * self.altura_opcao if self.aberto else self.altura_opcao

    def abrir(self):
        self.aberto = True
        self.altura = len(self.opcoes) * self.altura_opcao

    def fechar(self):
        self.aberto = False
        self.altura = self.altura_opcao

    def alternar(self):
        if self.aberto:
            self.fechar()
        else:
            self.abrir()

    def atualizar(self, mouse_pos, mouse_clicado, dt=0):
        if not self.aberto:
            # Verificar clique no botão principal
            if mouse_clicado and self.contem_ponto(*mouse_pos):
                self.alternar()
            return

        self._hover_idx = -1
        for i, op in enumerate(self.opcoes):
            opt_y = self.y + i * self.altura_opcao
            if (mouse_pos[0] >= self.x and mouse_pos[0] <= self.x + self.largura and
                mouse_pos[1] >= opt_y and mouse_pos[1] <= opt_y + self.altura_opcao):
                self._hover_idx = i
                if mouse_clicado and op["callback"]:
                    op["callback"]()
                    self.fechar()
                break

        # Fechar se clicar fora
        if mouse_clicado and not self.contem_ponto(*mouse_pos):
            self.fechar()

    def desenhar(self, tela, graphics=None):
        if not self.visivel:
            return

        # Botão principal (primeira opção ou placeholder)
        btn_rect = pygame.Rect(int(self.x), int(self.y), int(self.largura), self.altura_opcao)
        if graphics:
            graphics.retangulo(self.x, self.y, self.largura, self.altura_opcao, self.cor_fundo, True)
            graphics.retangulo(self.x, self.y, self.largura, self.altura_opcao, self.cor_hover, False, borda=1)
        else:
            pygame.draw.rect(tela, self.cor_fundo, btn_rect)
            pygame.draw.rect(tela, self.cor_hover, btn_rect, 1)

        txt = self.opcoes[0]["texto"] if self.opcoes else "Menu"
        txt_surf = self.fonte.render(txt, True, self.cor_texto)
        txt_rect = txt_surf.get_rect(midleft=(int(self.x + 10), int(self.y + self.altura_opcao/2)))
        tela.blit(txt_surf, txt_rect)

        # Seta
        seta_x = int(self.x + self.largura - 20)
        seta_y = int(self.y + self.altura_opcao/2)
        if self.aberto:
            pygame.draw.polygon(tela, self.cor_texto, [(seta_x, seta_y+3), (seta_x+10, seta_y+3), (seta_x+5, seta_y-3)])
        else:
            pygame.draw.polygon(tela, self.cor_texto, [(seta_x, seta_y-3), (seta_x+10, seta_y-3), (seta_x+5, seta_y+3)])

        if not self.aberto:
            return

        # Opções do dropdown
        for i, op in enumerate(self.opcoes):
            opt_y = self.y + i * self.altura_opcao
            opt_rect = pygame.Rect(int(self.x), int(opt_y), int(self.largura), self.altura_opcao)

            cor = self.cor_hover if i == self._hover_idx else self.cor_fundo
            if graphics:
                graphics.retangulo(self.x, opt_y, self.largura, self.altura_opcao, cor, True)
            else:
                pygame.draw.rect(tela, cor, opt_rect)

            txt_surf = self.fonte.render(op["texto"], True, self.cor_texto)
            txt_rect = txt_surf.get_rect(midleft=(int(self.x + 10), int(opt_y + self.altura_opcao/2)))
            tela.blit(txt_surf, txt_rect)


class NAgameInterface:
    """Gerenciador de UI."""

    def __init__(self, largura_tela, altura_tela):
        self.largura_tela = largura_tela
        self.altura_tela = altura_tela
        self.elementos = []
        self._foco_atual = None

    def adicionar(self, elemento):
        self.elementos.append(elemento)
        return elemento

    def remover(self, elemento):
        if elemento in self.elementos:
            self.elementos.remove(elemento)
            if self._foco_atual == elemento:
                self._foco_atual = None

    def limpar(self):
        self.elementos.clear()
        self._foco_atual = None

    def atualizar(self, mouse_pos, mouse_clicado, dt=0, eventos=None):
        for el in self.elementos:
            if el.visivel and el.ativo:
                el.atualizar(mouse_pos, mouse_clicado, dt)

        if eventos:
            for evento in eventos:
                for el in self.elementos:
                    if el.visivel and el.ativo:
                        el.evento(evento)

    def desenhar(self, tela, graphics=None):
        for el in self.elementos:
            if el.visivel:
                el.desenhar(tela, graphics)

    # Factory methods
    def criar_botao(self, x, y, w, h, texto="", acao=None, **kwargs):
        btn = Botao(x, y, w, h, texto, acao, **kwargs)
        self.adicionar(btn)
        return btn

    def criar_painel(self, x, y, w, h, **kwargs):
        p = Painel(x, y, w, h, **kwargs)
        self.adicionar(p)
        return p

    def criar_caixa_texto(self, x, y, w, h, **kwargs):
        ct = CaixaTexto(x, y, w, h, **kwargs)
        self.adicionar(ct)
        return ct

    def criar_label(self, x, y, texto="", **kwargs):
        l = Label(x, y, texto, **kwargs)
        self.adicionar(l)
        return l

    def criar_barra_progresso(self, x, y, w, h, **kwargs):
        bp = BarraProgresso(x, y, w, h, **kwargs)
        self.adicionar(bp)
        return bp

    def criar_menu(self, x, y, w, **kwargs):
        m = Menu(x, y, w, **kwargs)
        self.adicionar(m)
        return m
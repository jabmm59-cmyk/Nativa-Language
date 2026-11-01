"""
NAgame Input Backend - Sistema de entrada unificado (teclado, mouse, gamepad)
"""

import pygame


class NAgameInput:
    """Gerenciador de entrada unificado."""

    def __init__(self, janela=None):
        self.janela = janela
        self._teclas = {}
        self._teclas_anteriores = {}
        self._mouse_pos = (0, 0)
        self._mouse_pos_anterior = (0, 0)
        self._mouse_botoes = (False, False, False)
        self._mouse_botoes_anteriores = (False, False, False)
        self._mouse_scroll = (0, 0)
        self._gamepads = {}
        self._mapeamento_teclas = {
            # Nomes amigáveis -> pygame keys
            'espaço': pygame.K_SPACE, 'space': pygame.K_SPACE,
            'esquerda': pygame.K_LEFT, 'left': pygame.K_LEFT,
            'direita': pygame.K_RIGHT, 'right': pygame.K_RIGHT,
            'cima': pygame.K_UP, 'up': pygame.K_UP,
            'baixo': pygame.K_DOWN, 'down': pygame.K_DOWN,
            'esc': pygame.K_ESCAPE, 'escape': pygame.K_ESCAPE,
            'enter': pygame.K_RETURN, 'return': pygame.K_RETURN,
            'shift': pygame.K_LSHIFT, 'lshift': pygame.K_LSHIFT,
            'rshift': pygame.K_RSHIFT,
            'ctrl': pygame.K_LCTRL, 'lctrl': pygame.K_LCTRL,
            'rctrl': pygame.K_RCTRL,
            'alt': pygame.K_LALT, 'lalt': pygame.K_LALT,
            'ralt': pygame.K_RALT,
            'tab': pygame.K_TAB,
            'backspace': pygame.K_BACKSPACE,
            'delete': pygame.K_DELETE,
            'home': pygame.K_HOME,
            'end': pygame.K_END,
            'pageup': pygame.K_PAGEUP,
            'pagedown': pygame.K_PAGEDOWN,
            'insert': pygame.K_INSERT,
            'f1': pygame.K_F1, 'f2': pygame.K_F2, 'f3': pygame.K_F3,
            'f4': pygame.K_F4, 'f5': pygame.K_F5, 'f6': pygame.K_F6,
            'f7': pygame.K_F7, 'f8': pygame.K_F8, 'f9': pygame.K_F9,
            'f10': pygame.K_F10, 'f11': pygame.K_F11, 'f12': pygame.K_F12,
            '0': pygame.K_0, '1': pygame.K_1, '2': pygame.K_2, '3': pygame.K_3,
            '4': pygame.K_4, '5': pygame.K_5, '6': pygame.K_6, '7': pygame.K_7,
            '8': pygame.K_8, '9': pygame.K_9,
            'a': pygame.K_a, 'b': pygame.K_b, 'c': pygame.K_c, 'd': pygame.K_d,
            'e': pygame.K_e, 'f': pygame.K_f, 'g': pygame.K_g, 'h': pygame.K_h,
            'i': pygame.K_i, 'j': pygame.K_j, 'k': pygame.K_k, 'l': pygame.K_l,
            'm': pygame.K_m, 'n': pygame.K_n, 'o': pygame.K_o, 'p': pygame.K_p,
            'q': pygame.K_q, 'r': pygame.K_r, 's': pygame.K_s, 't': pygame.K_t,
            'u': pygame.K_u, 'v': pygame.K_v, 'w': pygame.K_w, 'x': pygame.K_x,
            'y': pygame.K_y, 'z': pygame.K_z,
            '`': pygame.K_BACKQUOTE, '-': pygame.K_MINUS, '=': pygame.K_EQUALS,
            '[': pygame.K_LEFTBRACKET, ']': pygame.K_RIGHTBRACKET,
            '\\': pygame.K_BACKSLASH, ';': pygame.K_SEMICOLON,
            '\'': pygame.K_QUOTE, ',': pygame.K_COMMA, '.': pygame.K_PERIOD,
            '/': pygame.K_SLASH,
            'kp0': pygame.K_KP0, 'kp1': pygame.K_KP1, 'kp2': pygame.K_KP2,
            'kp3': pygame.K_KP3, 'kp4': pygame.K_KP4, 'kp5': pygame.K_KP5,
            'kp6': pygame.K_KP6, 'kp7': pygame.K_KP7, 'kp8': pygame.K_KP8,
            'kp9': pygame.K_KP9, 'kp.': pygame.K_KP_PERIOD, 'kp/': pygame.K_KP_DIVIDE,
            'kp*': pygame.K_KP_MULTIPLY, 'kp-': pygame.K_KP_MINUS, 'kp+': pygame.K_KP_PLUS,
            'kpenter': pygame.K_KP_ENTER,
        }

    def atualizar(self):
        """Atualiza estados (chamar uma vez por frame)."""
        self._teclas_anteriores = self._teclas.copy()
        self._mouse_botoes_anteriores = self._mouse_botoes
        self._mouse_pos_anterior = self._mouse_pos
        self._mouse_scroll = (0, 0)

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pass  # Deixar a janela lidar com isso
            elif evento.type == pygame.KEYDOWN:
                self._teclas[evento.key] = True
            elif evento.type == pygame.KEYUP:
                self._teclas[evento.key] = False
            elif evento.type == pygame.MOUSEMOTION:
                self._mouse_pos = evento.pos
            elif evento.type == pygame.MOUSEBUTTONDOWN:
                b = list(self._mouse_botoes)
                if 1 <= evento.button <= 5:
                    if evento.button <= 3:
                        b[evento.button - 1] = True
                    elif evento.button == 4:
                        self._mouse_scroll = (0, 1)
                    elif evento.button == 5:
                        self._mouse_scroll = (0, -1)
                self._mouse_botoes = tuple(b)
            elif evento.type == pygame.MOUSEBUTTONUP:
                b = list(self._mouse_botoes)
                if 1 <= evento.button <= 3:
                    b[evento.button - 1] = False
                self._mouse_botoes = tuple(b)
            elif evento.type == pygame.MOUSEWHEEL:
                self._mouse_scroll = (evento.x, evento.y)
            elif evento.type == pygame.JOYDEVICEADDED:
                self._init_gamepad(evento.device_index)
            elif evento.type == pygame.JOYDEVICEREMOVED:
                if evento.instance_id in self._gamepads:
                    del self._gamepads[evento.instance_id]

        # Atualizar gamepads
        for gp in self._gamepads.values():
            gp.atualizar()

    def _init_gamepad(self, device_index):
        try:
            joy = pygame.joystick.Joystick(device_index)
            joy.init()
            gp = Gamepad(joy)
            self._gamepads[joy.get_instance_id()] = gp
        except Exception as e:
            print(f"Erro ao inicializar gamepad: {e}")

    # --- Teclado ---
    def _get_key(self, tecla):
        """Converte nome de tecla para código pygame."""
        if isinstance(tecla, int):
            return tecla
        tecla_lower = str(tecla).lower()
        return self._mapeamento_teclas.get(tecla_lower, getattr(pygame, f'K_{tecla_lower}', None))

    def tecla(self, tecla):
        """Tecla pressionada (hold)."""
        key = self._get_key(tecla)
        return self._teclas.get(key, False) if key else False

    def tecla_pressionada(self, tecla):
        """Tecla pressionada neste frame (edge)."""
        key = self._get_key(tecla)
        if key:
            return self._teclas.get(key, False) and not self._teclas_anteriores.get(key, False)
        return False

    def tecla_solta(self, tecla):
        """Tecla solta neste frame."""
        key = self._get_key(tecla)
        if key:
            return not self._teclas.get(key, False) and self._teclas_anteriores.get(key, False)
        return False

    def qualquer_tecla(self):
        return any(self._teclas.values())

    def teclas_pressionadas(self):
        """Lista de todas as teclas pressionadas."""
        return [k for k, v in self._teclas.items() if v]

    # --- Mouse ---
    def mouse_pos(self):
        return self._mouse_pos

    def mouse_delta(self):
        return (self._mouse_pos[0] - self._mouse_pos_anterior[0],
                self._mouse_pos[1] - self._mouse_pos_anterior[1])

    def mouse_botao(self, botao=1):
        """Botão do mouse pressionado (hold). 1=esq, 2=meio, 3=dir"""
        if 1 <= botao <= 3:
            return self._mouse_botoes[botao - 1]
        return False

    def mouse_clicado(self, botao=1):
        """Botão clicado neste frame."""
        if 1 <= botao <= 3:
            return (self._mouse_botoes[botao - 1] and
                    not self._mouse_botoes_anteriores[botao - 1])
        return False

    def mouse_solto(self, botao=1):
        """Botão solto neste frame."""
        if 1 <= botao <= 3:
            return (not self._mouse_botoes[botao - 1] and
                    self._mouse_botoes_anteriores[botao - 1])
        return False

    def mouse_scroll(self):
        return self._mouse_scroll

    # --- Gamepad ---
    def gamepad_conectado(self, indice=0):
        return len(self._gamepads) > indice

    def gamepad(self, indice=0):
        gamepads = list(self._gamepads.values())
        return gamepads[indice] if indice < len(gamepads) else None

    def num_gamepads(self):
        return len(self._gamepads)


class Gamepad:
    """Wrapper para joystick/gamepad."""

    def __init__(self, joystick):
        self.joy = joystick
        self._botoes = {}
        self._botoes_anteriores = {}
        self._eixos = {}
        self._hats = {}

    def atualizar(self):
        self._botoes_anteriores = self._botoes.copy()
        self._botoes = {i: self.joy.get_button(i) for i in range(self.joy.get_numbuttons())}
        self._eixos = {i: self.joy.get_axis(i) for i in range(self.joy.get_numaxes())}
        self._hats = {i: self.joy.get_hat(i) for i in range(self.joy.get_numhats())}

    def botao(self, indice):
        return self._botoes.get(indice, False)

    def botao_pressionado(self, indice):
        return self._botoes.get(indice, False) and not self._botoes_anteriores.get(indice, False)

    def botao_solto(self, indice):
        return not self._botoes.get(indice, False) and self._botoes_anteriores.get(indice, False)

    def eixo(self, indice, zona_morta=0.1):
        val = self._eixos.get(indice, 0)
        return 0 if abs(val) < zona_morta else val

    def hat(self, indice):
        return self._hats.get(indice, (0, 0))

    # Mapeamento comum (padrão Xbox/PS)
    @property
    def A(self): return self.botao(0)
    @property
    def B(self): return self.botao(1)
    @property
    def X(self): return self.botao(2) if self.joy.get_numbuttons() > 2 else self.botao(3)
    @property
    def Y(self): return self.botao(3) if self.joy.get_numbuttons() > 3 else self.botao(2)
    @property
    def LB(self): return self.botao(4)
    @property
    def RB(self): return self.botao(5)
    @property
    def BACK(self): return self.botao(6)
    @property
    def START(self): return self.botao(7)
    @property
    def LS(self): return self.botao(8)
    @property
    def RS(self): return self.botao(9)

    @property
    def left_stick_x(self): return self.eixo(0)
    @property
    def left_stick_y(self): return self.eixo(1)
    @property
    def right_stick_x(self): return self.eixo(2) if self.joy.get_numaxes() > 2 else 0
    @property
    def right_stick_y(self): return self.eixo(3) if self.joy.get_numaxes() > 3 else 0
    @property
    def LT(self): return max(0, self.eixo(4) if self.joy.get_numaxes() > 4 else 0)
    @property
    def RT(self): return max(0, self.eixo(5) if self.joy.get_numaxes() > 5 else 0)

    @property
    def dpad(self): return self.hat(0)
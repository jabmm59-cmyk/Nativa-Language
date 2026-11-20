from src.runtime import NativaBuiltinError


class State:
    def __init__(self):
        self.reset()

    def reset(self):
        self.pg = None
        self.screen = None
        self.clock = None
        self.width = 0
        self.height = 0
        self.title = "Nativa"
        self.background = (0, 0, 0)
        self.color = (255, 255, 255, 255)
        self.font_size = 24
        self.fonts = {}
        self.dt = 0.0
        self.start = None
        self.closed = False
        self.keys_down = set()
        self.keys_pressed = set()
        self.keys_released = set()
        self.mouse_pressed = set()
        self.mouse_released = set()
        self.camera = {"x": 0.0, "y": 0.0, "zoom": 1.0, "rot": 0.0}
        self.image_cache = {}
        self.sounds = {}
        self.music_file = None
        self.music_paused = False
        self.sfx_volume = 1.0
        self.joysticks = {}


state = State()


def get_pygame():
    if state.pg is None:
        try:
            import pygame
        except ImportError:
            raise NativaBuiltinError(
                "a NAgame requer o pacote 'pygame' (instale com: pip install pygame)", "ImportError"
            )
        state.pg = pygame
    return state.pg


def require_window():
    if state.screen is None:
        raise NativaBuiltinError(
            "crie a janela com window(largura, altura) antes de usar esta função", "RuntimeError"
        )
    return state.screen


def check_number(name, value, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NativaBuiltinError(f"{name} deve ser um número", "TypeError")
    if minimum is not None and value < minimum:
        raise NativaBuiltinError(f"{name} deve ser no mínimo {minimum}", "ValueError")
    if maximum is not None and value > maximum:
        raise NativaBuiltinError(f"{name} deve ser no máximo {maximum}", "ValueError")
    return value

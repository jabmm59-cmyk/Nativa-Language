from src.runtime import NativaBuiltinError

from . import check_number, get_pygame, state
from .window import KEY_ALIASES


def normalize(name):
    if not isinstance(name, str) or not name.strip():
        raise NativaBuiltinError("o nome da tecla deve ser um texto", "TypeError")
    lowered = name.strip().lower()
    return KEY_ALIASES.get(lowered, lowered)


def check_button(button):
    if isinstance(button, bool) or button not in (1, 2, 3):
        raise NativaBuiltinError("o botão do mouse deve ser 1 (esquerdo), 2 (meio) ou 3 (direito)", "ValueError")
    return button


def exports(interp):
    def key(name):
        return normalize(name) in state.keys_down

    def keyout(name):
        return normalize(name) in state.keys_released

    def keyhit(name):
        return normalize(name) in state.keys_pressed

    def mse():
        pos = get_pygame().mouse.get_pos()
        return [pos[0], pos[1]]

    def mseclk(button=1):
        return check_button(button) in state.mouse_pressed

    def mseout(button=1):
        return check_button(button) in state.mouse_released

    def controller(index=0):
        pg = get_pygame()
        check_number("índice do controle", index, 0)
        index = int(index)
        if index >= pg.joystick.get_count():
            return None
        if index not in state.joysticks:
            stick = pg.joystick.Joystick(index)
            stick.init()
            state.joysticks[index] = stick
        stick = state.joysticks[index]
        axes = [stick.get_axis(i) for i in range(stick.get_numaxes())]
        buttons = [bool(stick.get_button(i)) for i in range(stick.get_numbuttons())]
        return [axes, buttons]

    return {
        "key": key, "keyout": keyout, "keyhit": keyhit, "mse": mse,
        "mseclk": mseclk, "mseout": mseout, "controller": controller,
    }

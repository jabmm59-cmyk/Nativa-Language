import time

from src.runtime import NativaBuiltinError

from . import check_number, get_pygame, require_window, state
from .camera import reset_camera

KEY_ALIASES = {"enter": "return", "esc": "escape", "ctrl": "left ctrl", "shift": "left shift", "alt": "left alt"}


def key_name(pg, key):
    return str(pg.key.name(key)).lower()


def process_events():
    pg = get_pygame()
    state.keys_pressed.clear()
    state.keys_released.clear()
    state.mouse_pressed.clear()
    state.mouse_released.clear()
    for event in pg.event.get():
        if event.type == pg.QUIT:
            state.closed = True
        elif event.type == pg.KEYDOWN:
            name = key_name(pg, event.key)
            state.keys_down.add(name)
            state.keys_pressed.add(name)
        elif event.type == pg.KEYUP:
            name = key_name(pg, event.key)
            state.keys_down.discard(name)
            state.keys_released.add(name)
        elif event.type == pg.MOUSEBUTTONDOWN:
            state.mouse_pressed.add(event.button)
        elif event.type == pg.MOUSEBUTTONUP:
            state.mouse_released.add(event.button)


def exports(interp):
    def window(width, height):
        for name, value in (("largura", width), ("altura", height)):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise NativaBuiltinError(f"{name} da janela deve ser um inteiro positivo", "ValueError")
        pg = get_pygame()
        pg.init()
        state.screen = pg.display.set_mode((width, height))
        pg.display.set_caption(state.title)
        state.clock = pg.time.Clock()
        state.width, state.height = width, height
        state.start = time.monotonic()
        state.closed = False
        state.dt = 0.0
        state.keys_down.clear()
        reset_camera()
        state.screen.fill(state.background)

    def st_title(title):
        if not isinstance(title, str):
            raise NativaBuiltinError("o título deve ser texto", "TypeError")
        state.title = title
        if state.screen is not None:
            get_pygame().display.set_caption(title)

    def close():
        state.closed = True
        if state.pg is not None and state.screen is not None:
            state.pg.quit()
        state.screen = None

    def back(r, g, b):
        for value in (r, g, b):
            check_number("cor", value, 0, 255)
        state.background = (int(r), int(g), int(b))
        require_window().fill(state.background)

    def updt():
        screen = require_window()
        get_pygame().display.flip()
        screen.fill(state.background)

    def evn():
        if state.closed or state.screen is None:
            return False
        process_events()
        return not state.closed

    def tof(fps):
        check_number("fps", fps, 1)
        if state.clock is None:
            require_window()
        milliseconds = state.clock.tick(fps)
        state.dt = min(milliseconds / 1000.0, 0.1)
        return state.dt

    def dt():
        return state.dt

    def gettime():
        if state.start is None:
            return 0.0
        return time.monotonic() - state.start

    def size():
        require_window()
        return [state.width, state.height]

    return {
        "window": window, "st_title": st_title, "close": close, "back": back,
        "updt": updt, "evn": evn, "tof": tof, "dt": dt, "gettime": gettime, "size": size,
    }

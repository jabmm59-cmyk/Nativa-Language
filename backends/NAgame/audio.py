import os

from src.runtime import NativaBuiltinError

from . import check_number, get_pygame, state


def mixer():
    pg = get_pygame()
    if not pg.mixer.get_init():
        try:
            pg.mixer.init()
        except pg.error:
            raise NativaBuiltinError("áudio indisponível neste sistema", "RuntimeError")
    return pg.mixer


def check_file(path):
    if not isinstance(path, str):
        raise NativaBuiltinError("o caminho do arquivo de áudio deve ser texto", "TypeError")
    if not os.path.isfile(path):
        raise NativaBuiltinError(f"arquivo de áudio não encontrado: '{path}'", "RuntimeError")


def load_music(path):
    check_file(path)
    pg = get_pygame()
    mixer()
    try:
        pg.mixer.music.load(path)
    except pg.error:
        raise NativaBuiltinError(f"não foi possível carregar o áudio '{path}'", "RuntimeError")
    state.music_file = path
    state.music_paused = False


def start_music(path, loops):
    pg = get_pygame()
    mixer()
    if path is not None:
        load_music(path)
    elif state.music_file is None:
        raise NativaBuiltinError("nenhuma música carregada; use loadmsc(arquivo)", "RuntimeError")
    elif state.music_paused and loops == 0:
        pg.mixer.music.unpause()
        state.music_paused = False
        return
    pg.mixer.music.play(loops)
    state.music_paused = False


def play_music(path=None):
    start_music(path, 0)


def loop_music(path=None):
    start_music(path, -1)


def pause_music():
    mixer()
    get_pygame().mixer.music.pause()
    state.music_paused = True


def stop_music():
    mixer()
    get_pygame().mixer.music.stop()
    state.music_paused = False


def set_music_volume(value):
    check_number("volume", value, 0, 1)
    mixer()
    get_pygame().mixer.music.set_volume(float(value))


def set_sfx_volume(value):
    check_number("volume", value, 0, 100)
    state.sfx_volume = value / 100.0


def load_sound(path):
    check_file(path)
    pg = get_pygame()
    mixer()
    if path not in state.sounds:
        try:
            state.sounds[path] = pg.mixer.Sound(path)
        except pg.error:
            raise NativaBuiltinError(f"não foi possível carregar o som '{path}'", "RuntimeError")
    return state.sounds[path]


def play_sound(handle):
    mixer()
    handle.set_volume(state.sfx_volume)
    handle.play()


def exports(interp):
    return {
        "load_music": load_music, "play_music": play_music, "loop_music": loop_music,
        "pause_music": pause_music, "stop_music": stop_music,
        "set_music_volume": set_music_volume, "set_sfx_volume": set_sfx_volume,
        "load_sound": load_sound, "play_sound": play_sound,
    }

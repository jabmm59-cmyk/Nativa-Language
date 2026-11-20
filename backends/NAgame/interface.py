from src.runtime import NativaBuiltinError

from . import graphics

PANEL_FILL = [30, 34, 48, 220]
PANEL_BORDER = [120, 130, 170, 255]
BUTTON_COLORS = {
    "normal": [60, 70, 110, 255],
    "hover": [85, 100, 160, 255],
    "pressed": [40, 48, 80, 255],
}
TEXT_COLOR = [240, 240, 250, 255]


def draw_panel(x, y, width, height, title):
    graphics.draw_rec(x, y, width, height, 0, PANEL_FILL, True)
    graphics.draw_rec(x, y, width, height, 2, PANEL_BORDER, True)
    if title:
        graphics.draw_text(title, x + 10, y + 8, 28, TEXT_COLOR, True)


def draw_button(x, y, width, height, text, mode):
    if mode not in BUTTON_COLORS:
        raise NativaBuiltinError("estado de botão inválido", "ValueError")
    graphics.draw_rec(x, y, width, height, 0, BUTTON_COLORS[mode], True)
    graphics.draw_rec(x, y, width, height, 2, PANEL_BORDER, True)
    size = max(12, int(height * 0.5))
    text_width, text_height = graphics.text_size(text, size)
    graphics.draw_text(text, x + (width - text_width) / 2, y + (height - text_height) / 2, size, TEXT_COLOR, True)


def write_text(path, text):
    if not isinstance(path, str) or not isinstance(text, str):
        raise NativaBuiltinError("caminho e conteúdo devem ser texto", "TypeError")
    try:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
    except OSError as e:
        raise NativaBuiltinError(f"não foi possível gravar '{path}': {e.strerror}", "RuntimeError")


def read_text(path):
    if not isinstance(path, str):
        raise NativaBuiltinError("o caminho deve ser texto", "TypeError")
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as e:
        raise NativaBuiltinError(f"não foi possível ler '{path}': {e.strerror}", "RuntimeError")


def exports(interp):
    return {
        "draw_panel": draw_panel, "draw_button": draw_button,
        "write_text": write_text, "read_text": read_text,
    }

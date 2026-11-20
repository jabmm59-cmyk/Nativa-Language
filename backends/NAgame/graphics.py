import math

from src.runtime import NativaBuiltinError

from . import check_number, get_pygame, require_window, state
from .camera import rotation, to_screen, zoom_factor

COLOR_NAMES = {
    "white": (255, 255, 255), "black": (0, 0, 0), "red": (220, 40, 40),
    "green": (40, 180, 70), "blue": (50, 90, 220), "yellow": (240, 220, 50),
    "orange": (240, 140, 30), "purple": (150, 70, 200), "cyan": (40, 200, 220),
    "gray": (128, 128, 128), "pink": (240, 130, 180), "brown": (140, 90, 50),
}

IMAGE_CACHE_LIMIT = 256


def parse_color(red, green=None, blue=None, alpha=255):
    if isinstance(red, str):
        name = red.strip().lower()
        if name not in COLOR_NAMES:
            raise NativaBuiltinError(f"cor desconhecida: '{red}'", "ValueError")
        r, g, b = COLOR_NAMES[name]
        if green is not None:
            alpha = green
        return (r, g, b, int(check_number("alfa", alpha, 0, 255)))
    if green is None or blue is None:
        raise NativaBuiltinError("a cor requer r, g e b (ou um nome de cor)", "TypeError")
    for value in (red, green, blue, alpha):
        check_number("componente de cor", value, 0, 255)
    return (int(red), int(green), int(blue), int(alpha))


def color_tuple(color):
    if not isinstance(color, (list, tuple)) or len(color) not in (3, 4):
        raise NativaBuiltinError("cor inválida: use uma lista [r, g, b] ou [r, g, b, a]", "TypeError")
    return parse_color(*color) if len(color) == 4 else parse_color(color[0], color[1], color[2])


def get_font(size):
    pg = get_pygame()
    size = max(1, int(size))
    if size not in state.fonts:
        state.fonts[size] = pg.font.Font(None, size)
    return state.fonts[size]


def paint(bbox, painter, color):
    pg = get_pygame()
    screen = require_window()
    r, g, b, a = color
    if a >= 255:
        painter(screen, (r, g, b), 0, 0)
        return
    x0, y0, x1, y1 = bbox
    x0, y0 = int(math.floor(x0)) - 2, int(math.floor(y0)) - 2
    width = max(1, int(math.ceil(x1)) + 2 - x0)
    height = max(1, int(math.ceil(y1)) + 2 - y0)
    layer = pg.Surface((width, height), pg.SRCALPHA)
    painter(layer, (r, g, b, a), -x0, -y0)
    screen.blit(layer, (x0, y0))


def project(points, ui):
    if ui:
        return list(points)
    return [to_screen(x, y) for x, y in points]


def bounding_box(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def line_width(border, ui):
    if border <= 0:
        return 0
    return max(1, int(round(border * (1 if ui else zoom_factor()))))


def draw_rec(x, y, width, height, border, color, ui=False):
    pg = get_pygame()
    require_window()
    color = color_tuple(color)
    corners = project([(x, y), (x + width, y), (x + width, y + height), (x, y + height)], ui)
    w = line_width(border, ui)
    box = bounding_box(corners)
    if ui or rotation() % 360 == 0:
        x0, y0, x1, y1 = box
        rect = (int(round(x0)), int(round(y0)), int(round(x1 - x0)), int(round(y1 - y0)))

        def painter(surface, c, ox, oy):
            pg.draw.rect(surface, c, (rect[0] + ox, rect[1] + oy, rect[2], rect[3]), w)
    else:
        def painter(surface, c, ox, oy):
            pg.draw.polygon(surface, c, [(px + ox, py + oy) for px, py in corners], w)
    paint(box, painter, color)


def draw_circ(x, y, radius, border, color, ui=False):
    pg = get_pygame()
    require_window()
    color = color_tuple(color)
    (cx, cy), = project([(x, y)], ui)
    r = max(1, int(round(radius * (1 if ui else zoom_factor()))))
    w = line_width(border, ui)
    box = (cx - r, cy - r, cx + r, cy + r)

    def painter(surface, c, ox, oy):
        pg.draw.circle(surface, c, (int(round(cx)) + ox, int(round(cy)) + oy), r, w)

    paint(box, painter, color)


def draw_line(x1, y1, x2, y2, thickness, color, ui=False):
    pg = get_pygame()
    require_window()
    color = color_tuple(color)
    points = project([(x1, y1), (x2, y2)], ui)
    w = max(1, int(round(thickness * (1 if ui else zoom_factor()))))
    box = bounding_box(points)

    def painter(surface, c, ox, oy):
        start = (int(round(points[0][0])) + ox, int(round(points[0][1])) + oy)
        end = (int(round(points[1][0])) + ox, int(round(points[1][1])) + oy)
        pg.draw.line(surface, c, start, end, w)

    paint(box, painter, color)


def text_size(text, size):
    font = get_font(size)
    width, height = font.size(str(text))
    return [width, height]


def draw_text(text, x, y, size, color, ui=False):
    require_window()
    color = color_tuple(color)
    (sx, sy), = project([(x, y)], ui)
    font = get_font(size * (1 if ui else zoom_factor()))
    surface = font.render(str(text), True, color[:3])
    if color[3] < 255:
        surface.set_alpha(color[3])
    require_window().blit(surface, (int(round(sx)), int(round(sy))))


def remember(key, build):
    cache = state.image_cache
    if key not in cache:
        if len(cache) >= IMAGE_CACHE_LIMIT:
            cache.clear()
        cache[key] = build()
    return cache[key]


def load_image(path):
    pg = get_pygame()
    require_window()
    if not isinstance(path, str):
        raise NativaBuiltinError("o caminho da imagem deve ser texto", "TypeError")
    try:
        surface = pg.image.load(path)
    except (FileNotFoundError, OSError, pg.error):
        raise NativaBuiltinError(f"não foi possível carregar a imagem '{path}'", "RuntimeError")
    try:
        surface = surface.convert_alpha()
    except pg.error:
        pass
    return [surface, surface.get_width(), surface.get_height()]


def resize_image(handle, width, height):
    pg = get_pygame()
    check_number("largura", width, 1)
    check_number("altura", height, 1)
    surface = pg.transform.scale(handle, (int(width), int(height)))
    return [surface, int(width), int(height)]


def rotate_image(handle, angle):
    pg = get_pygame()
    check_number("ângulo", angle)
    surface = pg.transform.rotate(handle, angle)
    return [surface, surface.get_width(), surface.get_height()]


def flip_image(handle, horizontal, vertical):
    pg = get_pygame()
    surface = pg.transform.flip(handle, bool(horizontal), bool(vertical))
    return [surface, surface.get_width(), surface.get_height()]


def set_image_alpha(handle, value):
    check_number("alfa", value, 0, 255)
    surface = handle.copy()
    surface.set_alpha(int(value))
    return [surface, surface.get_width(), surface.get_height()]


def slice_sheet(handle, frame_width, frame_height):
    check_number("largura do quadro", frame_width, 1)
    check_number("altura do quadro", frame_height, 1)
    fw, fh = int(frame_width), int(frame_height)
    frames = []
    for top in range(0, handle.get_height() - fh + 1, fh):
        for left in range(0, handle.get_width() - fw + 1, fw):
            frames.append([handle.subsurface((left, top, fw, fh)).copy(), fw, fh])
    if not frames:
        raise NativaBuiltinError("a imagem é menor que um quadro da animação", "ValueError")
    return frames


def draw_image(handle, x, y, width, height, angle, alpha, flip_x, flip_y, ui=False):
    pg = get_pygame()
    screen = require_window()
    zoom = 1.0 if ui else zoom_factor()
    total_angle = float(angle) - (0.0 if ui else rotation())
    target_w = max(1, int(round(width * zoom)))
    target_h = max(1, int(round(height * zoom)))
    key = (id(handle), target_w, target_h, round(total_angle, 2), int(alpha), bool(flip_x), bool(flip_y))

    def build():
        surface = handle
        if surface.get_size() != (target_w, target_h):
            surface = pg.transform.scale(surface, (target_w, target_h))
        if flip_x or flip_y:
            surface = pg.transform.flip(surface, bool(flip_x), bool(flip_y))
        if total_angle % 360 != 0:
            surface = pg.transform.rotate(surface, total_angle)
        if alpha < 255:
            surface = surface.copy()
            surface.set_alpha(int(alpha))
        return surface

    surface = remember(key, build)
    (cx, cy), = project([(x + width / 2, y + height / 2)], ui)
    sw, sh = surface.get_size()
    screen.blit(surface, (int(round(cx - sw / 2)), int(round(cy - sh / 2))))


def draw_overlay_message(message):
    require_window()
    draw_rec(0, 0, state.width, state.height, 0, [0, 0, 0, 150], True)
    size = 64
    width, height = text_size(message, size)
    draw_text(message, (state.width - width) / 2, (state.height - height) / 2, size, [255, 255, 255, 255], True)


def exports(interp):
    def set_color(r, g=None, b=None, a=255):
        state.color = parse_color(r, g, b, a)
        return list(state.color)

    def get_color():
        return list(state.color)

    def set_font_size(size):
        check_number("tamanho da fonte", size, 1, 400)
        state.font_size = int(size)
        return state.font_size

    def get_font_size():
        return state.font_size

    return {
        "set_color": set_color, "get_color": get_color, "set_font_size": set_font_size,
        "get_font_size": get_font_size, "draw_rec": draw_rec, "draw_circ": draw_circ,
        "draw_line": draw_line, "draw_text": draw_text, "text_size": text_size,
        "load_image": load_image, "resize_image": resize_image, "rotate_image": rotate_image,
        "flip_image": flip_image, "set_image_alpha": set_image_alpha, "slice_sheet": slice_sheet,
        "draw_image": draw_image, "draw_overlay_message": draw_overlay_message,
    }

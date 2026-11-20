import math

from src.runtime import NativaBuiltinError

SHAPE_KINDS = ("rec", "circ")


def check_shape(shape):
    if not isinstance(shape, list) or len(shape) != 6 or shape[0] not in SHAPE_KINDS:
        raise NativaBuiltinError("forma inválida para colisão", "TypeError")
    for value in shape[1:]:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise NativaBuiltinError("a forma de colisão requer valores numéricos", "TypeError")
    return shape


def rect_rect(a, b, inclusive):
    ax, ay, aw, ah = a[1:5]
    bx, by, bw, bh = b[1:5]
    if inclusive:
        return not (ax + aw < bx or bx + bw < ax or ay + ah < by or by + bh < ay)
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def circ_circ(a, b, inclusive):
    distance = (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2
    limit = (a[5] + b[5]) ** 2
    return distance <= limit if inclusive else distance < limit


def rect_circ(rect, circ, inclusive):
    rx, ry, rw, rh = rect[1:5]
    nearest_x = min(max(circ[1], rx), rx + rw)
    nearest_y = min(max(circ[2], ry), ry + rh)
    distance = (circ[1] - nearest_x) ** 2 + (circ[2] - nearest_y) ** 2
    limit = circ[5] ** 2
    return distance <= limit if inclusive else distance < limit


def collide(a, b, inclusive):
    check_shape(a)
    check_shape(b)
    if a[0] == "rec" and b[0] == "rec":
        return rect_rect(a, b, inclusive)
    if a[0] == "circ" and b[0] == "circ":
        return circ_circ(a, b, inclusive)
    if a[0] == "rec":
        return rect_circ(a, b, inclusive)
    return rect_circ(b, a, inclusive)


def ray_rect(x1, y1, dx, dy, shape):
    rx, ry, rw, rh = shape[1:5]
    t_min, t_max = 0.0, 1.0
    for origin, delta, low, high in ((x1, dx, rx, rx + rw), (y1, dy, ry, ry + rh)):
        if delta == 0:
            if origin < low or origin > high:
                return None
            continue
        t1, t2 = (low - origin) / delta, (high - origin) / delta
        if t1 > t2:
            t1, t2 = t2, t1
        t_min, t_max = max(t_min, t1), min(t_max, t2)
        if t_min > t_max:
            return None
    return t_min


def ray_circ(x1, y1, dx, dy, shape):
    cx, cy, radius = shape[1], shape[2], shape[5]
    fx, fy = x1 - cx, y1 - cy
    a = dx * dx + dy * dy
    if a == 0:
        return 0.0 if fx * fx + fy * fy <= radius * radius else None
    b = 2 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - radius * radius
    if c <= 0:
        return 0.0
    discriminant = b * b - 4 * a * c
    if discriminant < 0:
        return None
    root = math.sqrt(discriminant)
    t = (-b - root) / (2 * a)
    return t if 0.0 <= t <= 1.0 else None


def raycast(x1, y1, x2, y2, shapes):
    for value in (x1, y1, x2, y2):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise NativaBuiltinError("ray() requer coordenadas numéricas", "TypeError")
    if not isinstance(shapes, list):
        raise NativaBuiltinError("ray() requer uma lista de obstáculos", "TypeError")
    dx, dy = x2 - x1, y2 - y1
    best = None
    for index, shape in enumerate(shapes):
        check_shape(shape)
        t = ray_rect(x1, y1, dx, dy, shape) if shape[0] == "rec" else ray_circ(x1, y1, dx, dy, shape)
        if t is not None and (best is None or t < best[0]):
            best = (t, index)
    if best is None:
        return None
    t, index = best
    return [index, x1 + dx * t, y1 + dy * t, math.hypot(dx, dy) * t]


def exports(interp):
    return {
        "collide": lambda a, b: collide(a, b, False),
        "touch": lambda a, b: collide(a, b, True),
        "raycast": raycast,
    }

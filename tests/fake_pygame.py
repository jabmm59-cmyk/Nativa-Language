import os
import types

KEY_CODES = {
    "a": 97, "d": 100, "w": 119, "space": 32, "return": 13, "escape": 27,
    "left": 1073741904, "right": 1073741903, "up": 1073741906, "down": 1073741905,
}
KEY_NAMES = {code: name for name, code in KEY_CODES.items()}


class FakeError(Exception):
    pass


class Surface:
    def __init__(self, size, flags=0):
        self.size = (int(size[0]), int(size[1]))
        self.flags = flags
        self.calls = []
        self.alpha = 255

    def get_size(self):
        return self.size

    def get_width(self):
        return self.size[0]

    def get_height(self):
        return self.size[1]

    def fill(self, color):
        self.calls.append(("fill", tuple(color)))

    def blit(self, source, position):
        self.calls.append(("blit", source.size, tuple(position), source.alpha, source))

    def copy(self):
        clone = Surface(self.size, self.flags)
        clone.alpha = self.alpha
        return clone

    def set_alpha(self, value):
        self.alpha = value

    def convert_alpha(self):
        return self

    def subsurface(self, rect):
        return Surface((rect[2], rect[3]))


class Font:
    def __init__(self, name, size):
        self.size_px = size

    def size(self, text):
        return (len(text) * max(1, self.size_px // 2), self.size_px)

    def render(self, text, antialias, color):
        surface = Surface(self.size(text))
        surface.text = text
        surface.color = tuple(color)
        return surface


class Clock:
    def __init__(self, fake):
        self.fake = fake

    def tick(self, fps):
        self.fake.ticks.append(fps)
        return self.fake.next_ms


class Sound:
    def __init__(self, path, fake):
        self.path = path
        self.fake = fake
        self.volume = 1.0

    def set_volume(self, value):
        self.volume = value

    def play(self):
        self.fake.audio_log.append(("sound", self.path, self.volume))


class Joystick:
    def __init__(self, index):
        self.index = index

    def init(self):
        pass

    def get_numaxes(self):
        return 2

    def get_numbuttons(self):
        return 3

    def get_axis(self, i):
        return [0.5, -1.0][i]

    def get_button(self, i):
        return 1 if i == 1 else 0


def make_fake_pygame():
    pg = types.ModuleType("pygame")
    pg.QUIT, pg.KEYDOWN, pg.KEYUP = 256, 768, 769
    pg.MOUSEBUTTONDOWN, pg.MOUSEBUTTONUP = 1025, 1026
    pg.SRCALPHA = 65536
    pg.error = FakeError
    pg.Surface = Surface
    pg.K = KEY_CODES
    pg.events = []
    pg.ticks = []
    pg.next_ms = 16
    pg.audio_log = []
    pg.mouse_pos = (0, 0)
    pg.joystick_count = 0
    pg.captions = []
    pg.flips = 0
    pg.screen = None
    pg.mixer_ready = False
    pg.quit_calls = 0

    pg.init = lambda: None

    def quit_():
        pg.quit_calls += 1

    pg.quit = quit_

    display = types.SimpleNamespace()

    def set_mode(size):
        pg.screen = Surface(size)
        return pg.screen

    display.set_mode = set_mode
    display.set_caption = lambda title: pg.captions.append(title)

    def flip():
        pg.flips += 1

    display.flip = flip
    pg.display = display

    def draw_recorder(name):
        def draw(surface, color, *args):
            surface.calls.append((name, tuple(color), args))

        return draw

    pg.draw = types.SimpleNamespace(
        rect=draw_recorder("rect"), circle=draw_recorder("circle"),
        line=draw_recorder("line"), polygon=draw_recorder("polygon"),
    )
    pg.font = types.SimpleNamespace(Font=Font)

    def load(path):
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        return Surface((64, 32))

    pg.image = types.SimpleNamespace(load=load)

    def scale(surface, size):
        out = Surface(size)
        out.alpha = surface.alpha
        return out

    def rotate(surface, angle):
        out = Surface((surface.size[1], surface.size[0]) if round(angle) % 180 == 90 else surface.size)
        out.angle = angle
        return out

    def flip_surface(surface, x, y):
        out = surface.copy()
        out.flipped = (x, y)
        return out

    pg.transform = types.SimpleNamespace(scale=scale, rotate=rotate, flip=flip_surface)

    def mixer_init():
        pg.mixer_ready = True

    music = types.SimpleNamespace(
        load=lambda path: pg.audio_log.append(("music_load", path)),
        play=lambda loops=0: pg.audio_log.append(("music_play", loops)),
        pause=lambda: pg.audio_log.append(("music_pause",)),
        unpause=lambda: pg.audio_log.append(("music_unpause",)),
        stop=lambda: pg.audio_log.append(("music_stop",)),
        set_volume=lambda v: pg.audio_log.append(("music_volume", v)),
    )
    pg.mixer = types.SimpleNamespace(
        get_init=lambda: (44100, -16, 2) if pg.mixer_ready else None,
        init=mixer_init, music=music, Sound=lambda path: Sound(path, pg),
    )
    pg.key = types.SimpleNamespace(name=lambda code: KEY_NAMES.get(code, "unknown"))
    pg.mouse = types.SimpleNamespace(get_pos=lambda: pg.mouse_pos)
    pg.joystick = types.SimpleNamespace(get_count=lambda: pg.joystick_count, Joystick=Joystick)
    pg.time = types.SimpleNamespace(Clock=lambda: Clock(pg))

    def get_events():
        events, pg.events = pg.events, []
        return events

    pg.event = types.SimpleNamespace(get=get_events)

    def post(event_type, **fields):
        pg.events.append(types.SimpleNamespace(type=event_type, **fields))

    pg.post = post
    return pg

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import run_source


def run(source, inputs=()):
    out = io.StringIO()
    queue = list(inputs)

    def fake_input(_):
        if not queue:
            raise EOFError
        return queue.pop(0)

    run_source(source, out=out, input_fn=fake_input)
    return out.getvalue()

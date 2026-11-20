EXCEPTION_NAMES = (
    "RuntimeError", "NameError", "TypeError", "ValueError", "ZeroDivisionError",
    "IndexError", "KeyError", "AttributeError", "AssertionError", "ImportError",
)

PRELUDE = """
classify Exception: (
    df __init__(urself, message = ""): (
        urself.message = message
    )

    df __str__(urself): (
        ret urself.message
    )
)
""" + "".join(
    f"""
classify {name}(Exception): (
    tpvfetc
)
"""
    for name in EXCEPTION_NAMES
)

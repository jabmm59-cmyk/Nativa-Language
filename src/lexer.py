from dataclasses import dataclass

from .errors import NativaSyntaxError

NUMBER = "NUMBER"
STRING = "STRING"
NAME = "NAME"
KEYWORD = "KEYWORD"
OP = "OP"
NEWLINE = "NEWLINE"
EOF = "EOF"

ACTIVE_KEYWORDS = {
    "shw", "utype", "if", "else", "while", "for", "in", "is", "and", "or",
    "not", "df", "ret", "brk", "continue", "classify", "True", "False", "None",
    "NA", "imp", "de", "como",
    "try", "xcept", "idgafatc", "perror", "as",
    # Portuguese keywords
    "se", "senao", "enquanto", "para", "em", "e", "ou", "nao",
}

PENDING_KEYWORDS = {
    "tpvfetc", "dlt", "glob", "nolocal",
    "afction", "verf", "wth", "dsync", "dwait",
}

KEYWORDS = ACTIVE_KEYWORDS | PENDING_KEYWORDS

TWO_CHAR_OPS = {"==", "!=", "<=", ">=", "//", "**"}
ONE_CHAR_OPS = set("+-*/%<>=()[]{}:,.")

ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", "'": "'", '"': '"', "0": "\0"}


@dataclass
class Token:
    type: str
    value: object
    line: int
    col: int


class Lexer:
    def __init__(self, source, filename="<principal>", line_offset=0, col_offset=0):
        self.src = source
        self.filename = filename
        self.pos = 0
        self.first_line = 1 + line_offset
        self.line = self.first_line
        self.line_start = 0
        self.col_offset = col_offset

    def column(self, pos=None):
        if pos is None:
            pos = self.pos
        extra = self.col_offset if self.line == self.first_line else 0
        return pos - self.line_start + 1 + extra

    def error(self, message, line=None, col=None):
        return NativaSyntaxError(
            message,
            self.line if line is None else line,
            self.column() if col is None else col,
            self.filename,
        )

    def tokenize(self):
        tokens = []
        src = self.src
        n = len(src)
        while self.pos < n:
            ch = src[self.pos]
            if ch in " \t\r":
                self.pos += 1
            elif ch == "\n":
                if tokens and tokens[-1].type != NEWLINE:
                    tokens.append(Token(NEWLINE, "\n", self.line, self.column()))
                self.pos += 1
                self.line += 1
                self.line_start = self.pos
            elif ch == "#":
                self.skip_comment()
            elif ch.isdigit():
                tokens.append(self.read_number())
            elif ch.isalpha() or ch == "_":
                tokens.append(self.read_name())
            elif ch in "\"'":
                tokens.append(self.read_string())
            else:
                tokens.append(self.read_operator())
        tokens.append(Token(EOF, None, self.line, self.column()))
        return tokens

    def skip_comment(self):
        start_line, start_col = self.line, self.column()
        end = self.src.find("#", self.pos + 1)
        if end == -1:
            raise self.error("comentário não fechado: falta o '#' final", start_line, start_col)
        for i in range(self.pos, end):
            if self.src[i] == "\n":
                self.line += 1
                self.line_start = i + 1
        self.pos = end + 1

    def read_number(self):
        src = self.src
        n = len(src)
        start = self.pos
        line, col = self.line, self.column()
        while self.pos < n and src[self.pos].isdigit():
            self.pos += 1
        is_float = False
        if self.pos + 1 < n and src[self.pos] == "." and src[self.pos + 1].isdigit():
            is_float = True
            self.pos += 1
            while self.pos < n and src[self.pos].isdigit():
                self.pos += 1
        if self.pos < n and (src[self.pos].isalpha() or src[self.pos] == "_"):
            raise self.error("número inválido", line, col)
        text = src[start:self.pos]
        return Token(NUMBER, float(text) if is_float else int(text), line, col)

    def read_name(self):
        src = self.src
        n = len(src)
        start = self.pos
        line, col = self.line, self.column()
        while self.pos < n and (src[self.pos].isalnum() or src[self.pos] == "_"):
            self.pos += 1
        text = src[start:self.pos]
        return Token(KEYWORD if text in KEYWORDS else NAME, text, line, col)

    def read_string(self):
        src = self.src
        n = len(src)
        quote = src[self.pos]
        line, col = self.line, self.column()
        self.pos += 1
        buf = []
        while True:
            if self.pos >= n or src[self.pos] == "\n":
                raise self.error("string não fechada", line, col)
            c = src[self.pos]
            if c == quote:
                self.pos += 1
                break
            if c == "\\":
                self.pos += 1
                if self.pos >= n:
                    raise self.error("string não fechada", line, col)
                e = src[self.pos]
                buf.append(ESCAPES.get(e, "\\" + e))
                self.pos += 1
            else:
                buf.append(c)
                self.pos += 1
        return Token(STRING, "".join(buf), line, col)

    def read_operator(self):
        src = self.src
        line, col = self.line, self.column()
        two = src[self.pos:self.pos + 2]
        if two in TWO_CHAR_OPS:
            self.pos += 2
            return Token(OP, two, line, col)
        ch = src[self.pos]
        if ch in ONE_CHAR_OPS:
            self.pos += 1
            return Token(OP, ch, line, col)
        raise self.error(f"caractere inesperado {ch!r}", line, col)

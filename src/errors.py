class NativaError(Exception):
    kind = "Erro"

    def __init__(self, message, line=None, col=None, filename=None):
        super().__init__(message)
        self.message = message
        self.line = line
        self.col = col
        self.filename = filename

    def __str__(self):
        location = self.filename or "<principal>"
        if self.line is not None:
            location += f", linha {self.line}, coluna {self.col}"
        return f"{self.kind} em {location}: {self.message}"


class NativaSyntaxError(NativaError):
    kind = "Erro de sintaxe"


class NativaRuntimeError(NativaError):
    kind = "Erro de execução"

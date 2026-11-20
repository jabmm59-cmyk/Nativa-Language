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

    def __init__(self, message, line=None, col=None, filename=None, error_class="RuntimeError"):
        super().__init__(message, line, col, filename)
        self.error_class = error_class


MESSAGE_CLASSES = (
    ("divisão por zero", "ZeroDivisionError"),
    ("não está definido", "NameError"),
    ("fora do intervalo", "IndexError"),
    ("não encontrada", "KeyError"),
    ("possui o atributo", "AttributeError"),
    ("possuem o atributo", "AttributeError"),
    ("não suportada", "TypeError"),
    ("não suporta", "TypeError"),
    ("deve ser", "TypeError"),
    ("não são chamáveis", "TypeError"),
    ("não são iteráveis", "TypeError"),
    ("não são indexáveis", "TypeError"),
    ("não aceita", "TypeError"),
    ("não aceitam", "TypeError"),
    ("chave inválida", "TypeError"),
    ("não podem ser chaves", "TypeError"),
    ("espera no máximo", "TypeError"),
    ("não possui o parâmetro", "TypeError"),
    ("múltiplos valores", "TypeError"),
    ("requer o argumento", "TypeError"),
    ("gerenciador de contexto", "TypeError"),
    ("exceção", "TypeError"),
    ("aguardável", "TypeError"),
    ("não foi possível importar", "ImportError"),
    ("dependência", "ImportError"),
)


def classify_message(message):
    for fragment, name in MESSAGE_CLASSES:
        if fragment in message:
            return name
    return "RuntimeError"

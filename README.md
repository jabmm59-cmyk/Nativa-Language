# Nativa (NA)

Linguagem de programação interpretada, implementada em Python. Arquivos `.na`.

## Instalação e uso

Requer Python 3.10 ou superior (Linux). A NAgame também requer `pygame`.

    ./install.sh                        instala o comando nativa em ~/.local/bin
    pip install -r requirements.txt     opcional: pygame, para a NAgame
    ./nativa examples/ola.na            executa um programa
    ./nativa build NAgame               constrói uma biblioteca
    ./nativa libs                       lista as bibliotecas
    ./nativa clean                      limpa artefatos e cache
    python3 -m unittest discover -s tests -t .

## Documentação

- `docs/LINGUAGEM.md`: sintaxe, comandos, exceções, assíncrono.
- `docs/IMPBUILD.md`: importação, bibliotecas, construção e cache.
- `docs/NAgame.md`: API completa da biblioteca de jogos.

## Estado (versão 1.0.0)

Etapas 1 a 10 implementadas: lexer, parser, AST e runtime; variáveis, operadores, condicionais
e laços; funções e classes; exceções e recursos avançados (`xcept idgafatc perror tpvfetc dlt
glob nolocal afction verf wth dsync dwait`); Impbuild; `NA imp`; NAgame; testes e documentação.

A NAgame foi testada com um dublê do Pygame (veja `tests/fake_pygame.py`). Para validar com o Pygame
real, rode `NA_REAL_PYGAME=1 python3 -m unittest tests.test_nagame`.

## Decisões de linguagem tomadas além da especificação

Sintaxe e nomes novos não vieram da especificação; estão listados para revisão:

- `try` (não renomeado) abre o bloco protegido; `as` nomeia a exceção em `xcept` e `wth`.
- `afction x, y: expressão` para lambdas; `verf cond, "msg"`; `wth a as x, b: ( ... )`.
- Protocolo de `wth`: `__enter__()` e `__exit__(urself, erro)`.
- `dsync df`; builtins assíncronos `sleep gather spawn runasync`.
- `True`, `False`, `None`; builtins `rang len int float str bool abs min max round list typeof hasattr reexport`.
- Exceções embutidas com nomes familiares (`ValueError`, `TypeError`...).
- Bibliotecas externas Python são importadas pelo mesmo `NA imp`, depois das bibliotecas Nativa.
- `NA imp native.X.Y` carrega backends Python (uso interno das bibliotecas).
- NAgame: uso como `NAgame.window(...)`; parâmetros, retornos e significados de `mate`, `vlint`,
  `folw`, `camfolw`, `gameover` e demais nomes sem definição estão em `docs/NAgame.md`.
- Não implementados por não estarem na especificação: `+=`, fatiamento, desempacotamento, REPL.

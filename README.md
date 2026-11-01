# Nativa (NA)

Linguagem de programação interpretada, implementada em Python. Arquivos `.na`.

## Uso

    ./nativa examples/ola.na
    python3 -m unittest discover -s tests -t .

## Estado atual (versão 0.1.0)

Etapas 1 a 4 concluídas: lexer, parser (com precedência), AST, runtime com escopos,
variáveis, operadores, `if / else if / else`, `while`, `for`, `rang`, `brk`, `continue`,
funções (`df`, `ret`, padrões, argumentos nomeados, `*args`, closures) e classes
(`classify`, `urself`, herança).

Reservados e ainda não implementados (etapa 5): `xcept idgafatc perror tpvfetc dlt glob
nolocal afction verf wth dsync dwait`.

## Decisões de linguagem tomadas nesta versão (a confirmar)

- Constantes: `True`, `False`, `None`.
- `shw` aceita também `end = "..."`.
- Builtins: `rang len int float str bool abs min max round list`.
- Métodos de `str`, `list` e `dict` por lista fechada (sem acesso a internals do Python).
- `{{` e `}}` produzem chaves literais em strings; aspas internas à interpolação devem
  ser diferentes das externas.
- Blocos não criam escopo novo; funções sim (atribuição dentro de função cria variável local).
- Métodos não enxergam variáveis do corpo da classe sem `urself.`.
- Classes aceitam herança: `classify Cão(Animal): (`; `__str__` é usado por `shw`.
- Limite de profundidade de chamadas: 400.

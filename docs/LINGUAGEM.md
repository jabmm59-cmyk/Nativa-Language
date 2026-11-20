# Linguagem Nativa

Arquivos `.na`, executados com `nativa arquivo.na`.

## Saída, entrada, variáveis

    shw "Olá", "Mundo", sep = "-"        # vários argumentos, sep e end #
    name = utype "Qual é seu nome? "
    shw "Olá, {name.dr}! {10 + 20}"      # interpolação com expressões #

`.dr` aplica `strip()` e `lower()`. Use `{{` e `}}` para chaves literais; aspas dentro de
`{ }` devem ser diferentes das aspas da string. Comentários começam e terminam com `#`.
Constantes: `True`, `False`, `None`.

## Operadores

`+ - * / // % **`, `== != < > <= >=`, `and or not`, `in`, `not in`, `is`, `is not`.
Comparações encadeiam (`1 < x < 10`). `**` associa à direita.

## Blocos, condicionais e laços

Blocos usam `: ( ... )`. Blocos não criam escopo novo.

    if x > 1: (
        shw "grande"
    )
    else if x == 1: (
        shw "um"
    )
    else: (
        shw "pequeno"
    )

    while x < 10: ( x = x + 1 )
    for i in rang(0, 10, 2): (
        if i == 4: ( continue )
        if i == 8: ( brk )
    )

`rang` aceita 1 a 3 argumentos. `for` itera listas, textos, dicionários (chaves) e `rang`.

## Funções, classes

    df soma(a, b = 10, *resto): ( ret a + b )
    soma(1, b = 2)

    classify Animal: (
        df __init__(urself, nome): ( urself.nome = nome )
        df falar(urself): ( shw "{urself.nome} faz um som" )
    )
    classify Cao(Animal): (
        df falar(urself): ( shw "{urself.nome} late" )
    )

Funções são closures. Métodos acessam o corpo da classe apenas via `urself.`. `__str__`
define como `shw` exibe uma instância.

## Listas e dicionários

    n = [1, 2, 3]
    n[0] = 9
    p = {"nome": "João"}
    p["idade"] = 12

Métodos de texto: `upper lower strip lstrip rstrip split join replace startswith endswith
find count title capitalize isdigit isalpha`. Listas: `append pop insert remove index
count sort reverse extend`. Dicionários: `keys values items get pop`.

## Comandos avançados

| Comando | Uso |
|---|---|
| `try` / `xcept` / `idgafatc` | `try: ( ... ) xcept Tipo, Outro as e: ( ... ) xcept: ( ... ) idgafatc: ( ... )` |
| `perror` | `perror ValueError("msg")` ou `perror MinhaClasse` |
| `tpvfetc` | bloco vazio |
| `dlt` | `dlt x`, `dlt lista[0]`, `dlt obj.attr` (aceita vários, separados por vírgula) |
| `glob` / `nolocal` | `glob total` / `nolocal contador` dentro de funções |
| `afction` | `f = afction a, b = 2: a + b` |
| `verf` | `verf condicao, "mensagem"` lança `AssertionError` |
| `wth` | `wth Gerente() as g: ( ... )`, com `__enter__` e `__exit__(urself, erro)`; retornar verdadeiro em `__exit__` suprime o erro |
| `dsync` / `dwait` | `dsync df f(): ( ... )`; `dwait f()` |

Exceções embutidas: `Exception` (base, com `.message`, `.line`, `.col`), `RuntimeError`,
`NameError`, `TypeError`, `ValueError`, `ZeroDivisionError`, `IndexError`, `KeyError`,
`AttributeError`, `AssertionError`, `ImportError`. Erros internos (divisão por zero, índice
inválido, nome indefinido...) podem ser capturados com `xcept`.

### Assíncrono

Chamar uma função `dsync` devolve uma corrotina; ela só executa quando aguardada. O
agendador é cooperativo e determinístico. Funções embutidas: `sleep(segundos)`,
`gather(c1, c2, ...)`, `spawn(corrotina)` e `runasync(corrotina)` (inicia o laço a partir
de código síncrono; `dwait` no nível principal também funciona).

## Builtins

`len int float str bool abs min max round list rang typeof hasattr reexport`.
`typeof(x)` devolve o nome do tipo (ou da classe). `reexport(modulo)` copia os nomes
públicos de um módulo para o módulo atual (usado por pacotes como a NAgame).

## Erros

Todo erro mostra arquivo, linha e coluna, inclusive dentro de bibliotecas `.na`:

    Erro de execução em erro.na, linha 3, coluna 7: divisão por zero
    Erro de execução em jogo.na, linha 9, coluna 1: ValueError: material desconhecido: plasma

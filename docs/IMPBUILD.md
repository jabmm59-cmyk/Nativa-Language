# Impbuild e importação

## Importar

    NA imp math
    NA imp random as r
    NA imp NAgame
    NA imp NAgame.graphics
    NA imp math, json

A ordem de busca para `NA imp nome` é:

1. `native.*`: backends Python de `backends/` (usados pelas bibliotecas `.na`).
2. Bibliotecas internas: `math`, `random`, `time`.
3. Bibliotecas Nativa (`.na`): primeiro a pasta do script, depois `libraries/`.
4. Bibliotecas Python compatíveis (`json`, por exemplo).

Cada módulo executa uma única vez (cache em memória). `NA imp a.b` liga o nome `a`; use
`as` para ligar o submódulo. Falhas geram `ImportError`, que pode ser capturado.

Bibliotecas Python expõem apenas funções e constantes; argumentos e retornos devem ser
números, textos, booleanos, `None`, listas ou dicionários. Outros tipos geram `TypeError`.
Elas rodam sem isolamento, como qualquer código Python.

## Estrutura de uma biblioteca

    libraries/minha/__init__.na     (pacote)   ou   libraries/minha.na  (arquivo único)
    libraries/minha/outro.na        (submódulo: minha.outro)
    libraries/minha/library.json    (opcional)

    {"name": "minha", "version": "1.2.0", "dependencies": ["math", "outra"]}

## O que o Impbuild faz

`NA imp minha` localiza a biblioteca (`registry.py`), constrói se necessário (`builder.py`),
carrega o artefato (`loader.py`) e disponibiliza o módulo.

- **compiler.py**: lê o fonte, gera tokens e AST, e valida: `ret` fora de função, `brk` e
  `continue` fora de laço, `nolocal` fora de função. Coleta os imports do módulo.
- **builder.py**: resolve e constrói dependências primeiro; recusa dependências ausentes
  e ciclos entre bibliotecas; grava `build/libraries/<lib>/<modulo>.nac` (AST serializada).
- **cache.py**: guarda `build/cache/<lib>.json` com hash do fonte (+ versão do formato e
  manifesto) e hash do artefato. Fonte alterado, artefato corrompido ou formato
  incompatível causam reconstrução apenas do módulo afetado.
- **loader.py**: verifica o hash do artefato antes de carregá-lo, executa o módulo em um
  escopo próprio e mantém o cache de módulos carregados. `unload(nome)` descarrega.

## Linha de comando

    nativa build NOME [--force]   constrói (mostra o que foi construído e o que veio do cache)
    nativa libs                   lista as bibliotecas e suas versões
    nativa clean [NOME]           remove artefatos e cache

# NAgame

Biblioteca de jogos da Nativa. Usa Pygame por dentro; o programa só usa a API Nativa.

    NA imp NAgame
    NAgame.window(800, 450)
    while NAgame.evn(): (
        NAgame.back(20, 20, 40)
        NAgame.clr("white")
        NAgame.rec(100, 100, 50, 50)
        NAgame.updt()
        NAgame.tof(60)
    )
    NAgame.close()

Requer `pygame` (`pip install -r requirements.txt`). Sem ele, `window()` lança `ImportError`.
Funções e nomes seguem a especificação; os parâmetros abaixo foram definidos nesta versão.

## Modelo de desenho

Desenho em modo imediato: `rec`, `circ`, `lne` e `txt` desenham na hora com a cor atual
(`clr`) e devolvem um objeto (`Shape`) que pode ser redesenhado com `draw(obj)` e usado
em física. Objetos têm `x`, `y`, `width`, `height`, `radius`, `color` e os campos de
física. Em `rec` e sprites, `x, y` é o canto superior esquerdo; em `circ`, o centro.
O mundo passa pela câmera; elementos de interface (`btn`, `panel`, `menu`) ficam fixos na tela.

## Janela e controle

| Função | Descrição |
|---|---|
| `window(largura, altura)` | cria a janela |
| `st_title(texto)` | define o título |
| `close()` | fecha o jogo |
| `back(r, g, b)` | cor de fundo (aplicada na hora e a cada `updt`) |
| `updt()` | roda temporizadores, animações e partículas, desenha a tela de fim de jogo se houver, e atualiza a tela |
| `evn()` | processa eventos; devolve `False` quando a janela é fechada |
| `tof(fps)` | limita o FPS e devolve o delta time (máx. 0,1 s) |
| `dt()` | delta time do último `tof` |
| `gettime()` | segundos desde `window()` |

## Desenho

`clr(r, g, b, a = 255)` ou `clr("red")` (white black red green blue yellow orange purple cyan gray pink brown) ·
`fntsz(tamanho)` · `rec(x, y, w, h, borda = 0)` · `circ(x, y, raio, borda = 0)` ·
`lne(x1, y1, x2, y2, espessura = 1)` · `txt(texto, x, y)` · `draw(obj)`.
Cores com alfa menor que 255 são misturadas com a tela.

## Imagens

`loadimg(caminho)` devolve uma `Image` · `shwimg(img, x, y)` · `sprt(img, x = 0, y = 0)` devolve
um `Sprite` · `rsze(obj, l, a)` · `rttae(obj, graus)` · `alp(obj, 0..255)` · `flp(obj, horizontal = True, vertical = False)`.
Em imagens, `rsze/rttae/alp/flp` devolvem uma nova imagem; em sprites alteram o sprite.
`sprite.play(animacao)` faz o sprite exibir os quadros de uma animação.

## Áudio

`loadmsc(arquivo)` · `playmsc(arquivo = None)` (sem argumento, retoma a música pausada ou toca a carregada) ·
`loopmsc(arquivo = None)` · `pausemsc()` · `stopmsc()` · `volmsc(0.0..1.0)` volume da música ·
`vlint(0..100)` volume dos efeitos (inteiro, em porcentagem) · `loadsnd(arquivo)` · `playsnd(som_ou_caminho)`.

## Entrada

`key(nome, once = False)` tecla pressionada (com `once = True`, só no quadro em que foi pressionada) ·
`keyout(nome)` tecla solta neste quadro · `mse()` devolve `[x, y]` · `mseclk(botao = 1)` clique neste quadro ·
`mseout(botao = 1)` botão solto neste quadro · `controllr(indice = 0)` devolve
`{"index", "axes", "buttons"}` ou `None`. Nomes de tecla: `a`, `left`, `space`, `enter`, `esc`, `shift`...

## Física e colisões

Todo objeto tem `vx vy ax ay mass friction bounce gravity on_ground`.
`grv` (980) é a gravidade; `obj.gravity` é o multiplicador de cada corpo.

| Função | Descrição |
|---|---|
| `phys(obj, passo = None)` | integra um passo (usa `dt()` por padrão): gravidade, aceleração, atrito no chão, chão e quique |
| `grnd(y = None)` | define o chão; sem argumento devolve o atual; `grnd(False)` remove |
| `pos(obj, x, y)` / `getpos(obj)` | define / lê a posição |
| `spd(obj, vx, vy)` / `acc(obj, ax, ay)` | define velocidade / aceleração; sem valores, devolve `[x, y]` |
| `mass(obj, v)` `fric(obj, v)` `bounc(obj, v)` | define massa (>0), atrito (>=0, por segundo) e quique (0..1); sem `v`, devolve |
| `jmp(obj, forca)` | pula se estiver no chão (`vy = -forca / massa`); devolve se pulou |
| `colde(a, b)` | sobreposição (retângulos, círculos, mistos, sprites) |
| `tch(a, b)` | como `colde`, mas contando bordas encostadas |
| `mate(obj, nome)` / `mate(nome)` | aplica material (`rubber metal wood ice stone`) ou devolve o dicionário |
| `ray(x1, y1, x2, y2, obstaculos)` | primeiro obstáculo no segmento: `{"obj", "x", "y", "distance"}` ou `None` |

## Animação, partículas, temporizadores

`anm(quadros, fps = 10, loop = True, fw = None, fh = None)` aceita uma lista de imagens ou uma
imagem com `fw`/`fh` (recorta uma folha de sprites). Métodos: `index() frame() update(passo) reset()`.
`prt(x, y, count = 20, cor = None, velocidade = 150, vida = 1.0, tamanho = 3, gravidade = 200)`
cria e anima partículas automaticamente (cor atual por padrão).
`tmr(segundos, callback = None, repeat = False)` devolve um `Timer` (`cancel() reset()`).
Tudo isso avança sozinho a cada `updt()`.

## Câmera

`cam()` estado `{"x","y","zoom","rot"}` · `campos(x, y)` centro da visão · `camzoom(z)` ·
`camrot(graus)` · `camfolw(alvo, suavizacao = 0.1)` segue um objeto (1 = grudado; `camfolw(None)` solta) ·
`folw(seguidor, alvo, velocidade)` move um objeto em direção a outro e devolve a distância restante.
Sem argumentos, `campos/camzoom/camrot` devolvem o valor atual.

## Interface, cenas e estado

Interface em modo imediato (fixa na tela): `btn(texto, x, y, l = 160, a = 44, ao_clicar = None)` devolve
`True` no clique · `panel(x, y, l, a, titulo = "")` · `menu(itens, x, y, l = 220, a = 44, espaco = 10)` devolve o
índice clicado ou -1.
Cenas: `scn(nome)` ativa/cria (`scn()` devolve a atual; `cena.data` é um dicionário) ·
`savscn(caminho)` e `loadscn(caminho)` gravam/leem a cena em JSON.
`gameover(mensagem = "GAME OVER")` ativa a tela de fim de jogo; `gameover(None)` consulta · `restart()` limpa o estado
(fim de jogo, temporizadores, animações, partículas, câmera e dados da cena atual).

## Utilidades

`rnd()` real em [0, 1) · `rnd(n)` inteiro de 0 a n-1 · `rnd(a, b)` inteiro (ou real, se `a` ou `b` for real) ·
`rnd(lista)` item sorteado · `debug(...)` imprime `[debug] ...` e devolve o primeiro valor.

## Arquitetura

`libraries/NAgame/*.na` define a API em Nativa (objetos, valores padrão, física, câmera, animação,
partículas, interface). `backends/NAgame/*.py` faz a parte de Pygame (janela, desenho, imagens,
áudio, entrada) e a matemática de colisão/raycast.

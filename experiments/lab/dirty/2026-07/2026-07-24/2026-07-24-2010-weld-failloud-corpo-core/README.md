# 2026-07-24-2010 — Weld FAIL-LOUD no corpo core (verificacao)

Solda o achado 3 do lab anterior (`2026-07-24-1832`): `KeyError` cru quando o corpo core
malformado chega no `_decode_column`/HCC. Rodado contra o `src/tcf` REAL.

## O que foi soldado (`src/tcf/composicional/syntax.py`)

Varredura do caminho achou **5 sitios da mesma classe**, nao 1 — e dois eram piores que o
achado original:

| sitio | antes | gravidade |
|---|---|---|
| `frags[refs[0]]` (referencia pendente) | `KeyError: 9` | crash cru — o achado do 1832 |
| composicao `1~9` / range `0..9` | `KeyError` | crash cru |
| `^N` alto | `IndexError` | crash cru |
| `^N` nao-numerico / contador RLE | `ValueError` cripto | mensagem inutil |
| **`^0`** | **devolvia `nos_decl[-1]` CALADO** | **corrupcao silenciosa** |
| **`*~2`** | **LOOP INFINITO + memoria sem teto** | **hang: 8 B derrubam o processo** |

Os dois em negrito nao apareceram no 1832 (a bateria de la' nao gerava essas formas). O `^0`
caia no indice negativo do Python; o `*~2` travava porque um `~` em inicio de segmento nao era
consumido por ramo nenhum e o `while` externo nunca progredia. O guard do segundo e' de
**PROGRESSO** (nao consumiu 1 char => fail-loud), entao vale para qualquer caractere futuro
que caia no mesmo buraco, nao so' `~`.

Tudo e' **caminho-de-erro** => byte-neutro por construcao.

## Resultado (`result.md`)

- **A. byte-neutro** — RT 5/5; gates byte-canonicos (pinados ANTES do weld) **passam**
- **B. fail-loud** — 501 mutacoes deterministicas, **0 excecao crua** (era a metrica do weld)
- **C. aceite-calado** — 15/15 fail-loud, e a faixa valida `1..len` intacta (controle positivo)
- **D. amplificacao RLE** — **achado NOVO, NAO soldado** (abaixo)

## Amplificacao do contador RLE — FECHADO (weld `max_length`)

`*N|` nao tinha teto — 13 B de wire materializavam 10M elementos
(`saida.extend([no] * count)`); 15 B chegavam a 1e9 (~8 GB). Foi o que travou a rodada 1
deste lab. Owner aprovou fechar seguindo a tradicao:

- nome **`max_length`** e convencao **`0 == sem teto`** roubados do `zlib`/`bz2`/`lzma`
- **unidade = elementos** decodificados, nao bytes: e' o que a bomba aloca
- default **10M**, ~200x de folga sobre o maior caso ja' medido no projeto (~50k)
- ancorado nos **dois** pontos de expansao: o core (`*N|`) e o seq-RLE (`*N+d|`, que expande
  ANTES do core) — este ultimo com pre-checagem do contador **sem materializar**
- no funil unico `_decode_column`, entao single/multi/view/hierarquico ficam protegidos mesmo
  sem expor o override
- custo medido: **+0,5%** no decode de 20k linhas (dentro do ruido)

**Limitacao assumida do default escolhido**: 10M e' generoso de proposito (nao pode barrar
wire legitimo), entao um wire de 13 B ainda produz 10M elementos — ~80 MB de lista. O teto
corta o **catastrofico** (8 GB), nao o **caro**. Quem processa entrada hostil deve baixar o
`max_length` explicitamente. Visivel na tabela D (`teto default` = `passa` na linha de 13 B).

Por que fail-loud e nao warning: quando o warning sairia, a memoria ja' foi alocada. A
mensagem nomeia o parametro a subir — e' o aviso em tempo de servir pra algo.

## Achado de contrato: o default do cabecalho esta INVERTIDO

O owner reportou que as saidas sairam sem `#TCF.8`. Investigado — **o codigo faz o contrario
do contrato declarado pelo owner**:

- para `list[str]`, o default do `encode` e' **SEM header** (docstring: *"single-col flat
  (orfao, sem header)"*); `stamp=True` e' o que **ADICIONA**
- a regra do owner (2026-07-24) e' a inversa: *"o default e' COM cabecalho; se FORCAR pedir
  sem cabecalho e' possivel desde que o meta seja passado nos dois lados"*
- as demais rotas (bool tipado, `[]`, `.8M`, `.8H`) ja' emitem header e **rejeitam** `stamp`

Por que so' apareceu agora: os labs anteriores **nunca** codificaram uma `list[str]` pura —
eram todos `.8H`/`.8M`, que carregam header por construcao. Este foi o primeiro.

Custo da forma com header: **+7 B** (ex.: A-repetidos 28 -> 35 B).

Este lab passou a usar `stamp=True` (helper `_enc`) para que as saidas mostrem a forma que o
owner quer ver. **Decisao de contrato em aberto** — nada em `src/tcf` foi tocado por isso.

Nota lateral: o bool tipado rejeita `stamp` com a mensagem *"nao se aplicam a entrada
hierarquica (.8H)"*, texto que ficou desatualizado com o weld #4a — bool nao vai mais pro
`.8H`, vai pro `#TCF.8b`. So' a mensagem, o comportamento esta' correto.

## Erros DESTE lab (corrigidos, registrados)

1. wire orfao **nao tem cabecalho** — o gerador tratava a 1a linha de dados como header e a
   blindava das mutacoes
2. o filtro anti-bomba so' olhava `*N|`, e a forma seq-RLE `*N+M|` escapava
3. `REPO = parents[4]` apontava pra `experiments/` — os gates rodavam "no tests ran" e eu
   quase reportei isso como quebra
4. parte C usava valores `v0`/`v1`: o digito vira **referencia de fragmento**, entao o proprio
   corpo-base era invalido e todo o controle positivo falhava
5. as saidas sairam **sem cabecalho** (rodadas 1-2) — eu segui o default do codigo em vez do
   contrato do owner; corrigido com `stamp=True`, e a divergencia virou achado (secao acima)

## Rodar / layout

```
python run.py     # A (RT+gates) + B (501 mutacoes) + C (^N) + D (amplificacao)
```
`inputs/*-fonte.json` · `intermediates/*-dataset-consumido.json` ·
`outputs/*-wire.tcf` + `*.roundtrip.json` · `result.md`.

Regressao durable na suite: `tests/test_decode_corpo_failloud.py` (17+ testes).

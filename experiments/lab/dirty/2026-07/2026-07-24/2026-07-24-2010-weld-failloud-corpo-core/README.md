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

## Achado em aberto: amplificacao do contador RLE

`*N|` nao tem teto — 13 B de wire materializam 10M elementos (`saida.extend([no] * count)`);
15 B chegam a 1e9 (~8 GB). **Deliberadamente sem weld**: o teto e' decisao de POLITICA do
owner (wire legitimo tambem tem count alto), nao correcao obvia, e esta' fora do escopo deste
weld — que e' so' fail-loud. Foi o que travou a rodada 1 deste lab.

## Erros DESTE lab (corrigidos, registrados)

1. wire orfao **nao tem cabecalho** — o gerador tratava a 1a linha de dados como header e a
   blindava das mutacoes
2. o filtro anti-bomba so' olhava `*N|`, e a forma seq-RLE `*N+M|` escapava
3. `REPO = parents[4]` apontava pra `experiments/` — os gates rodavam "no tests ran" e eu
   quase reportei isso como quebra
4. parte C usava valores `v0`/`v1`: o digito vira **referencia de fragmento**, entao o proprio
   corpo-base era invalido e todo o controle positivo falhava

## Rodar / layout

```
python run.py     # A (RT+gates) + B (501 mutacoes) + C (^N) + D (amplificacao)
```
`inputs/*-fonte.json` · `intermediates/*-dataset-consumido.json` ·
`outputs/*-wire.tcf` + `*.roundtrip.json` · `result.md`.

Regressao durable na suite: `tests/test_decode_corpo_failloud.py` (17+ testes).

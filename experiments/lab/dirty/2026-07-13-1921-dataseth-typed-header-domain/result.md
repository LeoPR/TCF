# Resultado - dominio tipado no header

**[probatorio]** `run.py` validou round-trip semantico antes da medicao.
Entradas e vies: [datasets-provenance.md](datasets-provenance.md).

## Contra-prova

`null=<indice>` e lossy se o dominio ja contem apenas strings. Em
[`01-naive-counterexample.txt`](artifacts/01-naive-counterexample.txt), `null`
e a string `"null"` viram ambos o indice `0`; o header nao consegue recuperar
qual ocorrencia era o primitivo. A tipagem precisa existir antes da indexacao,
ou cada ocorrencia precisa carregar um kind separado.

## Formas que passam

`HDOM` guarda no header o dominio inteiro de atomos tipados e usa indices
`bN`. E a forma direta de `tipo -> index_ref`, mas so se aplica quando o
dominio inteiro cabe em `k <= 16`.

`HK` guarda no header apenas os kinds ativos. O corpo tem indices de kind mais
o payload de `tcf.encode(list[str])` para string, integer e number. `null`,
NaN e infinitos nao carregam payload; a string `"null"` usa kind string e nao
colide com kind null.

O payload TCF real esta em
[`05-hk-string-payload.tcf.txt`](artifacts/05-hk-string-payload.tcf.txt). O
trace OBAT/HCC esta em
[`06-hk-string-payload-obat-hcc-trace.txt`](artifacts/06-hk-string-payload-obat-hcc-trace.txt).

## Bytes medidos

| perfil | HDOM | HK | V por ocorrencia |
|---|---:|---:|---:|
| collision-matrix | 157 | 93 | 90 |
| specials-dense-100 | 63 | 62 | 309 |
| low-card-mixed-100 | 114 | 246 | 489 |
| sparse-special-high-card | N/A (`k>16`) | 120 | 1242 |
| numbers-and-strings | 135 | 310 | 477 |

Fonte: [`04-bytes-comparison.txt`](artifacts/04-bytes-comparison.txt), com RT
em [`07-roundtrip.txt`](artifacts/07-roundtrip.txt).

## Veredito

O desenho e viavel se `index_ref` referencia uma entrada tipada ou se existe
kind por ocorrencia. Um dicionario apenas de strings nao separa `null` de
`"null"`. Esta e a primeira prova sintetica de B em coluna regular; ainda
faltam presence/definition/repetition levels, dados reais e a gramatica final
de `#TCF.8H`.

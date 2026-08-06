# T-LAZYTYPE-BOOL — cabeça congelada + extras declarados (2026-08-01-0229)

**Achado de rota**: hoje a união bool+str NÃO cai no `.8H` — o `.8H` RECUSA escalares mistos (`HierarchicalError`, fail-loud). A única rota atual é a (d) flat-string, que **perde o tipo**. O lazy `bB` seria a primeira rota a EMITIR lista mista `[True, None, "other", …]` por construção.

## A — bytes × rota × coluna (n=200)

| coluna | n | extras | (a) lazy bB | (b) bB completo | (c) hoje | (d) flat-str | RT lazy | RT compl |
|---|---:|---:|---:|---:|---|---:|:--|:--|
| `extras-raro` | 200 | 1 | 86 | 100 | FAIL-LOUD (HierarchicalError) | 97 | OK | OK |
| `extras-frequentes` | 200 | 1 | 86 | 100 | FAIL-LOUD (HierarchicalError) | 97 | OK | OK |
| `k-extras-01` | 200 | 1 | 84 | 98 | FAIL-LOUD (HierarchicalError) | 95 | OK | OK |
| `k-extras-05` | 200 | 5 | 133 | 147 | FAIL-LOUD (HierarchicalError) | 144 | OK | OK |
| `k-extras-20` | 200 | 20 | 201 | 215 | FAIL-LOUD (HierarchicalError) | 212 | OK | OK |
| `armadilha-tipos` | 200 | 3 | 126 | 135 | FAIL-LOUD (HierarchicalError) | 132 | OK | **perde tipo** |

## B — controles

| coluna | n | extras | (a) lazy bB | (b) bB completo | (c) hoje | (d) flat-str | RT lazy | RT compl |
|---|---:|---:|---:|---:|---|---:|:--|:--|
| `controle-0-extras` | 200 | 0 | — (recusa) | 94 | 79 | 91 | — | — |

**0 extras**: o lazy RECUSA (`proto_encode` devolve `None`) — o ternário puro é do denso b2 soldado (79 B, modo `2`).

| `controle-300-extras` | 400 | 300 | — (recusa w>8) | — | FAIL-LOUD (HierarchicalError) | 517 | — | — |

**300 extras**: recusa — `w` passaria de 8 (tabela > 256 slots). Cairia no flat-string.

## C — coluna real-ish (Adult)

Adult `sex` convertido a bool (conversão dos labs 0829/2350/0037), null injetado a cada 11º e a exceção `" ?"` a cada 23º — **injetados pelo lab**, proveniência em `datasets-provenance.md`.

| coluna | n | extras | (a) lazy bB | (b) bB completo | (c) hoje | (d) flat-str | RT lazy | RT compl |
|---|---:|---:|---:|---:|---|---:|:--|:--|
| `real-adult-sex-lazy` | 100 | 1 | 50 | 64 | FAIL-LOUD (HierarchicalError) | 61 | OK | OK |

## D — fail-loud

```
[OK] índice fora da tabela (7 numa tabela de 5) → ValueError: indice 7 fora da tabela lazy de 5 valores — corpo nao-canonico
[OK] header não-canônico (zero à esquerda) → ValueError: contagem bN nao-canonica: '0c8' (canonico: c8)
[OK] domínio mal-formado (vazio) → ValueError: dominio lazy vazio — a cabeça congelada não se declara
```

Determinismo: mesmo input → mesmo wire, byte a byte (**OK**).

## E — vereditos (pra decisão do owner)

### 1. ganho da cabeça congelada

- × domínio completo: **9..14 B** por coluna ({'extras-raro': 14, 'extras-frequentes': 14, 'k-extras-01': 14, 'k-extras-05': 14, 'k-extras-20': 14, 'armadilha-tipos': 9, 'real-adult-sex-lazy': 14}).
- × flat-string (única rota atual que codifica): **6..11 B** por coluna, E preserva o tipo (a flat perde).
- × rota atual: N/A — a rota atual é **fail-loud** na união (não produz byte).

### 2. semântica do marcador `bB`

**Recomendação: `bB` = SEMPRE cabeça congelada pra tag `b`.** O domínio bool é fechado e conhecido a priori — declará-lo é redundante (mesma lógica do ADR-0037). O `bB` completo do lab 0829 viraria não-canônico para a tag `b` (o decode pode seguir aceitando como decodável-não-emitido, contrato do modo `C`).

### 3. contrato união

Primeira rota que EMITE lista mista `[True, None, "other", …]` por construção (hoje união = fail-loud no `.8H`). Contrato medido: coluna = união de {bool, None, str} com ≥1 extra str; extras por primeira aparição a partir do slot 3; tabela = `TABELA_B2 + extras`; RT tipo-estrito. **Documentado, sem decidir weld.**

### 4. adversário de tipo (`"true"`/`"0"`/`"1"` como strings-extra)

Lazy: cada armadilha vira **slot próprio** (≥3), RT tipo-estrito OK — `"true"` str NUNCA colide com `True` (ele é o slot 2 congelado). **Na rota (b) completo o RT tipo FALHA** (RT compl = perde tipo): o domínio declara por string e `"true"` extra funde com o `True` — perda silenciosa de tipo. Mais um argumento pra cabeça congelada.

### 5. limites

- **Onde deixa de compensar**: extras dominantes (`k-extras-20`, 20 distintos a cada 4º) — o lazy continua ≤ flat, mas a margem encolhe; a 300 extras recusa (w>8, tabela > 256).
- Frequência do extra quase não move o tamanho (índices são bits); o que pesa é o **número de extras distintos** (domínio + largura).
- O lazy nunca piora o 0-extras porque **recusa** — o b2/core cobrem.

### Recomendação minimalista de forma (SE soldar um dia — PROPOSTA)

`bB` sempre lazy pra tag `b`: candidato quando a coluna é união de {bool, None, str} com 1..253 extras distintos; entra no FLOOR (`min()`) dos candidatos; decode misto (tabela = `TABELA_B2` + domínio declarado). **T-TIPOS-CONFORTO-MAP ficou FORA** — o mapa congelado/versionado/custom é decisão separada do owner; isto aqui é domínio DECLARADO no arquivo, não tipo de conforto.


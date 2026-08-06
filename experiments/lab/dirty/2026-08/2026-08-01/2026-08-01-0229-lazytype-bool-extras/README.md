# 2026-08-01-0229 — T-LAZYTYPE-BOOL: cabeça congelada + extras declarados (`#TCF.8bB`)

Coluna concentrada em null/true/false **com exceções string** ("other"). **Achado de
rota**: hoje a união bool+str NÃO "cai no `.8H`" — o `.8H` **recusa** escalares mistos
(`HierarchicalError`, fail-loud); a única rota atual é converter tudo pra string, perdendo
o tipo. A proposta medida: slots congelados da `TABELA_B2` (null=0, false=1, true=2) +
extras declarados a partir do slot 3, mecânica do `dominio_bn` (ADR-0036), só modo `B`.

## Tabela principal (bytes × rota × coluna, n=200)

| coluna | extras | (a) lazy `bB` | (b) `bB` completo | (c) hoje | (d) flat-str |
|---|---:|---:|---:|---|---:|
| `extras-raro` | 1 | **86** | 100 | FAIL-LOUD | 97 |
| `extras-frequentes` (20%) | 1 | **86** | 100 | FAIL-LOUD | 97 |
| `k-extras-01` | 1 | **84** | 98 | FAIL-LOUD | 95 |
| `k-extras-05` | 5 | **133** | 147 | FAIL-LOUD | 144 |
| `k-extras-20` | 20 | **201** | 215 | FAIL-LOUD | 212 |
| `armadilha-tipos` (`"true"/"0"/"1"`) | 3 | **126** | 135 | FAIL-LOUD | 132 |
| `real-adult-sex-lazy` (n=100) | 1 | **50** | 64 | FAIL-LOUD | 61 |

Controles: **0 extras** → lazy recusa (o b2 soldado cobre, 79 B); **300 extras** → recusa
(w>8). RT lazy tipo-estrito OK em todas; roundtrip arquivo byte-idêntico; fail-loud 3/3;
determinístico.

## Os 5 vereditos

1. **Ganho da cabeça congelada**: 9–14 B × domínio completo; 6–11 B × flat-string — e a
   flat **perde o tipo**, o lazy preserva. × rota atual: N/A (fail-loud).
2. **Semântica do `bB`**: recomendação — `bB` = SEMPRE cabeça congelada pra tag `b`
   (domínio bool é fechado; declará-lo é redundante). O completo do 0829 vira
   decodável-não-emitido.
3. **Contrato união**: primeira rota a EMITIR `[True, None, "other", …]` — união
   {bool, None, str} com ≥1 extra; extras por 1ª aparição do slot 3; tabela =
   `TABELA_B2 + extras`. Documentado, sem decidir weld.
4. **Adversário de tipo**: `"true"` str vira slot próprio (≥3), nunca colide com `True`
   (slot 2 congelado). Na rota (b) completo, `"true"` extra **funde com True — perda
   silenciosa de tipo**. Argumento decisivo pra cabeça congelada.
5. **Limites**: o que pesa é o NÚMERO de extras distintos (domínio + largura), não a
   frequência; margem × flat encolhe com extras dominantes; w>8 recusa.

**Forma minimalista (se soldar)**: `bB` sempre lazy p/ tag `b`, candidato pra união
{bool, None, str} com 1..253 extras, FLOOR decide, decode misto. `T-TIPOS-CONFORTO-MAP`
ficou fora — isto é domínio DECLARADO no arquivo, não tipo de conforto.

## Limites do lab

- Nada soldado; `src/tcf` intocado. Os `-lazy.tcf` são proposta.
- Sintéticos com viés declarado (construídos pra testar esta hipótese); real = Adult com
  null e `" ?"` **injetados pelo lab**.
- gzip e CPU não medidos.

## Rodar

```
python run.py
```

Sai `0` só se RT lazy tipo-estrito passar em todas as colunas aplicáveis, os 3 fail-louds
rejeitarem, e o fio for determinístico.

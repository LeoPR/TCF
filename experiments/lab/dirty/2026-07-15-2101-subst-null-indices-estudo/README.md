# Lab 2026-07-15-2101 — estudo: índices de substituição (null via dicionário pré-semeado)

**Status**: protótipo/medido, mecanismo. NADA weldado. **Plano**:
[substituicao-indices-especiais-plano.md](../notas/substituicao-indices-especiais-plano.md)
(H-SUBST-INDEX-01) · **Ticket**: [T-CODE-TCF8H-JSON-PARITY](../../../../tickets/T-CODE-TCF8H-JSON-PARITY.md) (P3).

Protótipa a ideia do owner (2026-07-15): tratar null **na camada de referência/dicionário** — o
dict por-coluna **nasce pré-semeado** com os especiais nos índices baixos (byte combinatório), null
= índice 0 (sentinela NÃO-STRING → a string sai do arquivo, vive na VERSÃO). Modela as **duas formas
de header** pra medir lado a lado, com o hook do bN (`.9`) em mente (o corpo é um stream de índices).

## O que roda (`proto.py` + `study.py`)

Codec de dicionário com especiais pré-semeados (o núcleo de "dict = descoberta"). Mede:

| # | mede | resultado |
|---|---|---|
| (1) | **4 vias** `null`/`"null"`/`""`/(ausente-fora) | RT exato; `None` NÃO entra no dict (vive na versão); `"null"`/`""` são strings descobertas — **sem colisão** |
| (5) | **null em ELEMENTO** de array | RT no **mesmo codec**, sem gramática nova → **unifica P3a+P3b** (o ganho vs máscara) |
| (2) | **Form A inline vs Form B bloco** (16 col × 200 lin) | **crossover**: A vence com poucas col-null (0→A por −2B); B vence com muitas (16→B por −14B); vira em ~2-3 col |
| (3) | **custo DECIMAL do shift +1** | barato longe das fronteiras; +1 dígito perto de 9/99/999 (Δ +4→+7B). Confirma o owner: medir, não assumir |
| (4) | **byte-compat** | fração 0 de col-null → nenhum byte de especial pago (idêntico ao sem-mecanismo) |
| base | **máscara-`0` (P1) vs índice** | índice **vence no null RARO** (p=0.1: −149B); máscara edge só no null frequente (p=0.5: +13B) — **com ressalva** (máscara-baseline crua, sem RLE) |

Exemplos vistoriáveis: [inputs/01-coluna-nullable.json](inputs/01-coluna-nullable.json) →
[outputs/01-roundtrip.json](outputs/01-roundtrip.json) (as 4 vias). Números:
[outputs/00-medicoes.txt](outputs/00-medicoes.txt).

## Leitura (o que decide)

1. **O mecanismo funciona e é lossless** — 4 vias distintas, a colisão que refutou "null=index" (2026-07-13-1921)
   some porque o especial é sentinela não-string.
2. **Unifica P3a (campo) + P3b (elemento)** no mesmo codec — o argumento mais forte vs a máscara.
3. **Header: não há vencedor único** — é crossover por nº de colunas-com-especial. Sugere ou escolher
   por `ncols`/densidade, ou um default + knob (como o L3). A decisão fica pro owner após esta medição.
4. **Shift decimal**: quase-grátis no comum; a borda 9/99/999 é real mas pequena.
5. Byte exato do índice-vs-máscara é APROXIMADO (dict puro ≠ L1 afixo/HCC real; máscara-baseline sem
   RLE). O robusto é a **unificação** + índice ganhar no null raro (o caso comum).

Zero mudança em `src/tcf` (engenhoca de estudo; o weld integraria na numeração real do L1).
Ver [result.md](result.md).

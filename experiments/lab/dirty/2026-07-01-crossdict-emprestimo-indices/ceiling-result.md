# Cross-column sharing — teste-TETO [probatório]

**Data**: 2026-07-01. Responde "vale insistir no HCC ref-share?" (owner pediu apostar mais um pouco
antes do descapar). Barra corrigida pelo [DICT-HIGHCARD](../2026-07-01-dict-highcard/result.md): o
per-coluna já é `min(tcf,raw,dict)`. Teste: `encode(A ++ B)` numa passada (o **teto** de qualquer
share — ignora fronteira de coluna) vs `min(A)+min(B)`. Script: [crosscol_ceiling.py](crosscol_ceiling.py).

## Resultado (TETO<0 = share PODE ganhar)
```
par same-domain        per-col (modo)     teto-concat   TETO      modo-concat
SNAP from~to           47004 (tcf+dict)   51626         +9.8%     dict
cit-HepTh from~to      43436 (tcf+dict)   53154        +22.4%     dict
email-Enron from~to    29582 (tcf+dict)   43817        +48.1%     tcf
OpenFlights src~dst    35607 (tcf+dict)   37621         +5.7%     dict
football home~away     35260 (dict+dict)  33722         -4.4%     dict   <- único <0
CONTROLE (disjunto)    26469 (dict+dict)  34552        +30.5%     dict
```

## Achado: o share é BECO SEM SAÍDA (a adaptividade per-coluna vence)
**Mesmo o TETO** (upper-bound: concat sem custo de fronteira) **perde em 4/5**. E qualquer share REAL
(HCC ref-share, header-dict) tem de **preservar a fronteira de coluna** (pra decode/lazy) → seria
**estritamente pior que este teto** → não bate o per-col-min.

**A causa é clara nos modos**: quase todo par é `tcf+dict` — a coluna **estruturada** (`from`,
agrupada → tcf/seq-RLE) e a **espalhada** (`to` → dict) escolhem ferramentas DIFERENTES. O per-col-min
dá a cada uma o seu melhor encoder (**adaptividade**). O share força **um** modo pro conjunto → perde a
melhor das duas. O dedup da tabela compartilhada **não compensa** a adaptividade perdida.

O único TETO<0 (football, −4.4%) é o nicho **small-K + ambas-dict** (K≈250 times, sem bucket, tabela
dedup relevante no blob pequeno) — o mesmo caso SNAP-like que o greedy do B2 já self-gate.

## Conexão com a literatura + o DICT-HIGHCARD
**Abadi 2006**: a força do column-store é a **seleção de encoding POR COLUNA** — cada coluna seu
esquema. O share (dicionário global) sacrifica isso. Nossa medição confirma no espaço textual do TCF.
E é a **ironia do DICT-HIGHCARD**: o `min()` per-coluna é forte JUSTAMENTE porque é adaptativo — e é
isso que o share não consegue igualar.

## Veredito: FECHAR o cross-dict / HCC-ref-share
`closed-insufficient-generalization` (estende o [gate B2](../2026-06-27-gdict-b2-prototype/gate-result.md)):
não é só o bucket-crossing — no TETO, o share perde por **perda de adaptividade**. O nicho small-K
(SNAP-like) fica como opt-in greedy-gated (seguro, estreito), não feature geral.

**Pivô → (a) descapar o V2-B**: a direção certa não é compartilhar entre colunas — é **fortalecer o
`min()` per-coluna** (dar-lhe o dict high-card como candidato). É o oposto do share, e é o que os dados
apontam. Voltar ao DICT-HIGHCARD (descapar), agora sem a dúvida do cross-dict.

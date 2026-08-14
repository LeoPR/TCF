# Loss mode e lossless-alterado em float — pesquisa (interna + literatura)

**2026-08-14** · pedido do owner:

> *"tinha o caso desses floats serem colocados em loss mode, ou lossless alterando a
> distribuição numérica... 0.2, 0.4... e aparece um 0.333333333 no meio, daria pra
> arredondar pra caber com o resto. ainda no lossless alterado... 0.333333333333 →
> `1/3...12` pra indicar fração com casas... técnicas de arredondamento financeiro que
> numa possível soma ele não muda... veja estudos nesse sentido, se não tiver, criamos."*

**Tipo**: [probatório] pesquisa. Nenhum código, nenhum weld.

---

## 1. As DUAS ideias, separadas

| ideia | contrato | o que muda | risco |
|---|---|---|---|
| **loss mode** | dentro-de-tolerância ou exato-no-agregado | o VALOR (`0.333333333` → `0.33`) | número não volta idêntico |
| **lossless alterado** | **exato** | só a GRAFIA no corpo (`0.333333333333` → `1/3…12`) | zero — RT byte-a-byte |

A distinção importa porque os gates são diferentes: **lossy está gateado**
(decisão de escopo do owner 2026-06-15: 0.7/0.8 lossless-puro, lossy = v2.0,
Pacote 10); **lossless-alterado NÃO está** — é um candidato de grafia como
qualquer outro do `min()`, na mesma família da escala ×10^k já avaliada.

## 2. O estudo INTERNO já existe (o que o owner não lembrava)

- **[`loss-taxonomia.md`](../2026-06/loss-taxonomia.md)** (2026-06-14) — a revisão
  completa, 9 vertentes + crítico. A ideia-chave registrada É a do owner:
  **"loss por-linha, LOSSLESS NO AGREGADO"** (o exemplo do parcelamento).
- **PoC empírico** (`2026-06-14-v2c-lossy-round-caracterizacao/poc_soma_preservada.py`):
  maior-resto (Hamilton) preserva a soma EXATA de `wine.density` enquanto o round
  ingênuo drifta +1.99; bytes caem 37% (d=3) / 65,5% (d=2), erro por-linha ≤ 1 step.
- **Registry**: `roadmap-hipoteses.md` Pacote 10, H-LOSS-00..11. A do owner é a
  **H-LOSS-01** (resíduo-redistribuído). Sequenciamento e gate já decididos.

**Conclusão da parte interna**: o "arredondamento financeiro que numa soma não muda"
está estudado, com PoC validado, e esperando a decisão de abrir o lossy (v2.0).

## 3. A literatura EXTERNA (o que a busca de hoje trouxe)

### 3a. Lossless-alterado — a família que a academia consolidou em 2023-2024

- **ALP** (Afroozeh/Kuffó/Boncz, SIGMOD 2024, CWI/DuckDB): a maioria dos doubles
  reais **nasceu decimal**; ALP os re-codifica **sem perda** como inteiros ×10^k
  (PseudoDecimals reforçado) e trata os que não fecham como **EXCEÇÕES por vetor**
  (patching), com fallback de front-bits (ALPrd) para os genuinamente binários.
  Bate Gorilla/Chimp/Patas/Elf/Zstd em razão E velocidade. É o estado da arte do
  lossless float em bancos colunar (adotado no DuckDB).
- **Elf** (VLDB 2023): apaga bits baixos que a grafia decimal não precisa, XOR
  encoding — lossless porque o decimal de saída é o mesmo.
- **PseudoDecimals** (BtrBlocks, SIGMOD 2023): o ancestral direto da ideia.

**A lição transferível** (só a ideia — os codecs são binários, não importam,
taxonomia §5): **decimal-como-inteiro não é tudo-ou-nada**. A avaliação de float
de hoje cedo descartou o spec de escala quando a precisão suja aparecia
(`10.0333333333333` derruba a coluna INTEIRA). ALP resolve exatamente isso com
**exceções por-valor**: escala o vetor e guarda os poucos que não fecham em grafia
plena. Isso reabilita parte das colunas onde a escala "não servia".

### 3b. A grafia fracional (`1/3…12`) especificamente

Não há codec mainstream de "fração + nº de casas"; o que existe de próximo:

- **notação de dízima periódica** (`0.(3)`) — matemática padrão, não compressão;
- **melhor aproximação racional** por frações contínuas (convergentes) — é como
  achar o `1/3` dado `0.333333333333`; algoritmo clássico, custo baixo;
- na compressão, o parente é **modelo+resíduo** (H-LOSS-08), com resíduo=0 quando
  a dízima é genuína.

**Avaliação honesta**: dízima genuína em corpus tabular nasce de DIVISÃO
(rateio, 1/3 de parcela, média de 3) — é exatamente o cenário do parcelamento do
owner. Como grafia lossless é legítima e barata de testar (`Fraction.limit_denominator`
+ verificar que `str(float(fração))` reproduz byte-a-byte). Provável nicho; a
escala-com-exceções (3a) deve dominar na frequência. **Testar juntas.**

### 3c. Loss mode — literatura de referência

- **Error-bounded lossy** (científico): **SZ/SZ3** (predição+quantização) e **ZFP**
  (transformada por bloco); survey ACM 2025 cobre 47 compressores. Contrato =
  `|erro| ≤ eps` declarado — o mesmo "dentro-de-tolerância" da taxonomia §1b.
- **Sum-preserving/controlled rounding** (estatística oficial): maior-resto /
  greatest-mantissa; "controlled rounding" força aditividade em tabelas (Sande,
  FCSM 2005). Confirma que o método do PoC é o canônico da área.

## 4. O que muda com a pesquisa de hoje

1. **T-FLOAT-SPEC ganha um adendo**: a razão "precisão suja inviabiliza a escala"
   está enfraquecida — o desenho ALP (escala + exceções por-valor) contorna. O spec
   de escala continua adiado (8% agregado), mas quando for reaberto, o desenho de
   referência é escala-com-exceções, não escala-tudo-ou-nada.
2. **Hipótese nova (lossless, SEM gate)**: grafia fracional para dízimas —
   registrada como **H-FLOAT-GRAFIA-01** no registry (junto do estudo da escala,
   não no Pacote 10, porque é lossless).
3. **Pacote 10 inalterado**: o loss mode segue gateado; a pesquisa só acrescenta
   as referências externas (SZ/ZFP/survey) à taxonomia já escrita.

## Fontes externas

- ALP: dl.acm.org/doi/10.1145/3626717 · ir.cwi.nl/pub/33334 · duckdb.org/library/alp
- Elf: vldb.org/pvldb/vol16/p1763-li.pdf
- Survey lossy científico: dl.acm.org/doi/10.1145/3733104 (SZ3: arxiv 2111.02925; ZFP idem)
- Controlled rounding: nces.ed.gov/FCSM/pdf/2005FCSM_Sande_IXA.pdf

## Conexões

- [`loss-taxonomia.md`](../2026-06/loss-taxonomia.md) · Pacote 10 (`roadmap-hipoteses.md`)
- `2026-06-14-v2c-lossy-round-caracterizacao/` (PoC maior-resto)
- [`2026-08-14-0400-avaliacao-float.md`](2026-08-14-0400-avaliacao-float.md) (a avaliação
  que o adendo corrige) · T-FLOAT-SPEC (STATUS.md)
- [[project-teoria-comparacao-modular]] (pré-tx aproximado ortogonal ao CORE)

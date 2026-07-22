# Resultado — escalares especiais: A (folha tipada) vs C (string escapada)

> Medido por `run.py` (contra-prova em `artifacts/02-rt-counterproof.txt`). 21 casos × 2
> variantes RT True sob o oráculo semântico; 10 pares de distinctness sem colisão nas DUAS
> representações; 2 origens (árvore Python e JSON-like declarado) produzem o MESMO DatasetH.

## Bytes por perfil (100 folhas)

| perfil | A | C | Δ C−A |
|---|---:|---:|---:|
| specials-heavy (100 × NaN) | 513 | 613 | **+100** |
| lookalike-strings (100 × string `"NaN"`) | 613 | 713 | **+100** |
| backslash-strings (100 × string `\x`) | 513 | 613 | **+100** |
| neutral (100 × string `"abc"`) | 613 | 613 | 0 |

## Leitura

1. **A não perde em bytes em nenhum dos 4 perfis medidos**; C paga o escape em TRÊS
   (delta idêntico +100 em cada): nos especiais (léxico `Infinity` = 8 chars vs tag
   `Vinf` = 4), nas strings colidentes (`"NaN"` literal vira `\NaN`) e em **qualquer
   string começando com `\`** — este último mesmo em documento SEM especiais. O imposto
   de escape de C é **global** ao canal de string; o custo de A é local (1 tag nova no wire).
2. **A é inspecionável**: `Vnan` declara o kind no wire. Em C, `S3·NaN` (especial) e
   `S4·\NaN` (string literal) só se distinguem conhecendo a regra de escape — semântica
   escondida, exatamente o risco que o plano registrou para C.
3. **O oráculo é obrigatório** (comprovado executável): o `==` ingênuo colapsa
   `-0.0`/`0.0` (True) e o NaN-como-float não seria reflexivo; com kinds tipados +
   `semantic_key` (repr para number), ambos falsificadores passam.
4. **Equivalência declarada** (não é colisão): `1e3` ≡ `1000.0` — o DatasetH preserva
   **valor**, não léxico (política herdada do lab-ponte, agora asserted).

## Veredito (probatório, confiança Média — sintético, N=1 lab)

**H-HIER-SCALAR-01: confirmada nesta bancada para a alternativa A** — folha tipada
sobrevive a todos os falsificadores (presença, não-finitos, números, containers), custa
menos bytes e mantém o wire inspecionável. **C fica refutada-parcial**: funciona (RT ok),
mas o imposto de escape é global e a semântica fica escondida no canal de string.

B (`bN` como portador de domínio tipado) permanece **ortogonal-depois**: só reavaliar com
domínio pequeno + perfil terminal, sem apagar o kind (o domínio precisa carregar tipo).
D (dicionário interno) segue **bloqueada por decisão de formato**.

**Nota de representação** (registro pro weld): a escolha A é sobre **semântica de folha**;
ela é ortogonal à forma do wire (por-instância do stage 1 **ou** a forma regular
multirow-com-header do EXP-015/ADR-0031, onde a multiplicidade é implícita no header). O
kind tipado tem de sobreviver às duas formas — no header regular, `V`-leaf vira candidato
a coluna tipada/def-level; decisão fica para P5 (gramática) com ADR.

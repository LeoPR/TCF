# EXP-015 — report (protótipo TCF hierárquico CSV↔JSON) [probatório]

Números gerados: `outputs/` (`python run.py`). Protótipo v0 — consolida o estudo dirty (peças 1-9), clean.

## Resultado

| via | amostra | bytes | RT |
|---|---|---|---|
| **JSON → TCF.8H → JSON** | S4 (pessoa⊃telefones) | 67B | **exato OK** |
| **JSON → TCF.8H → JSON** | S6 (pessoa⊃endereco{geo}+telefones) | 154B | **exato OK** |
| **CSV → TCF → CSV** | C1 (pessoa,telefone 1:N, 4 linhas) | 107B | **exato OK** |

## A hipótese do owner — CONFIRMADA (v0)

> "no JSON precisamos preservar mais; no CSV já não precisa tanto."

- **JSON**: a **árvore É o RT-alvo** → a hierarquia tem de ser **explícita** (preservada). O formato TCF.8H
  carrega a árvore no colchete (`{}` objeto, `[]` array); tudo mais (M/N/cardinalidade) é deduzido.
- **CSV**: o **RT-alvo é a tabela plana** → a hierarquia é **dispensável**. Deduzir a 1:N (`03-csv-deducao.txt`):
  (i) precisa de **link posicional** (array-em-array / N raízes — o limite da peça 10, o v0 não faz), e
  (ii) **não compensa bytes** — o pai sozinho já vira RLE (23B), e RLE↔fk são duais (peças 1/8). Logo, no
  CSV, o plano basta e a hierarquia é opt-in inútil (para bytes).

## Consistência + escala

Amostras **minúsculas** (S4/S6/C1) consistentes → o próximo é **escalar** com `datasets/synthetic/` (D1-D17)
e checar se o padrão se mantém (dedução de FD em dados reais tem near-FD, g3>0 — peça 7/8).

## Limites conhecidos (v0)

- **Array-em-array / N raízes**: precisa de link posicional (peça 10). É o que trava a hierarquização de CSV
  multi-pai e arrays aninhados dentro de arrays.
- **Tipos**: tudo string (num/bool/null = extensão). **Nomes**: sempre presentes (sem `drop_names` ainda).
- **Não toca `src/tcf`**: é protótipo de codec externo. Welding = decisão de formato futura (gate real-world).

## Próximo

Escalar (sintéticos) · tipos · link posicional (peça 10) · cross-convert JSON↔CSV · comparar com/sem
implícito em N maior.

# EXP-015 — report (protótipo TCF hierárquico CSV↔JSON) [probatório]

Números gerados: `outputs/` (`python run.py`). Protótipo v0 — consolida o estudo dirty (peças 1-9), clean.

## Resultado

| via | amostra | bytes | RT |
|---|---|---|---|
| **JSON → TCF.8H → JSON** | S4 (pessoa⊃telefones) | 66B | **exato OK** |
| **JSON → TCF.8H → JSON** | S6 (pessoa⊃endereco{geo}+telefones) | 153B | **exato OK** |
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

## Micro-opt do cabeçalho (insight do owner) — `04-header-otimizado.txt`

O `\n` do fim do cabeçalho **já fecha** todos os grupos abertos → os `}`/`]` finais são redundantes. O
decoder auto-fecha no EOF (o parser já fazia). **`omit-closes` = ganho limpo (-1B, RT-EXATO)** — adotar no
TCF.8H (byte grátis, sem downside).

### Condições do reorder + hex (`05-header-condicoes.txt`) — não é "quem vence", é a SITUAÇÃO

As duas otimizações de fim-de-linha atuam na **última folha** (em DFS). Escolher qual folha fica por último
(reorder de irmãos, order-free) economiza:
```
SAVING(L) = digits(size(L)) + depth(L)      [última-sem-size dá digits; omit-closes dá depth]
```
- **omit-closes**: SEMPRE bom (RT-exato).
- **reorder**: vale **SSE** `argmax_L(digits(size L)+depth L) ≠ natural-última`. **Não é só profundidade** —
  é **digits+depth**: uma folha rasa mas de size grande pode ganhar de uma profunda de size pequeno. Em
  **S6 empata** (natural-última `tel` = depth1+2dig=3, já é o argmax — situação particular, não "perde").
  Num caso construído (folha profunda **e** grande enterrada) o reorder ganha **+4B**.
- **hex nos sizes** (ideia do owner): `digits_hex(s)=len(hex(s)) < len(str(s))` para `s∈[10,15]∪[100,255]∪
  [256,4095]…` (fronteiras 16ᵏ vs 10ᵏ). Economiza por-size no header TODO **e** pode mudar o argmax do
  reorder. (16-99 empata; <10 empata.) Medido: caso com sizes 201/13 → hex economiza 2B.
→ **Nenhuma otimização vence sempre; o ganho é uma CONTA config-dependente.** Adotar omit-closes (sempre);
reorder + base do size (dec/hex) = escolher para minimizar `Σ digits + (digits+depth) da última folha`.

## Próximo

Escalar (sintéticos) · tipos · link posicional (peça 10) · cross-convert JSON↔CSV · comparar com/sem
implícito em N maior · **welding**: `omit-closes` é o 1º candidato (RT-exato, byte grátis).

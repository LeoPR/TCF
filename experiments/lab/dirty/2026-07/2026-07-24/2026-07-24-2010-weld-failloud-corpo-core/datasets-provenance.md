# Proveniência — weld fail-loud no corpo core (2026-07-24-2010)

**Fonte**: 100% sintético/determinístico. Nenhum dado real, nenhum download, nenhum CPF/CNPJ.

**Datasets (5)** — sintéticos mas realistas (feedback validação-e-dados: dados realistas, não
caos artificial). Cada um exercita um mecanismo distinto do corpo core, e é isso que os
justifica — não a quantidade:

| id | dados | mecanismo exercitado |
|---|---|---|
| `A-repetidos` | 6 status de pedido, repetidos | referência de linha `^N` |
| `B-run` | 40× `ok` + 3× `falha` | RLE `*N\|` |
| `C-prefixo` | 30 ids `pedido-2026-NNNN` | fragmento/composição `~` + seq-RLE `*N+M\|` |
| `D-bool` | 24 bools (1 em 3) | ramo TIPADO `#TCF.8b` sobre o mesmo core |
| `E-bordas` | strings vazias e unitárias | bordas de literal |

**Mutações (parte B)**: 501, **determinísticas** (não aleatórias) — troca de 1 char por
`9`/`^`/`*`/`0` em cada posição do corpo, truncamento (−1/−2/−3) e 10 formas fixas
adversariais. **Todas as saídas mutadas são descartáveis por construção** — nenhuma
reintroduzida como dado.

**Desvio declarado**: 2 mutações são desviadas da parte B para a classe AMPLIFICAÇÃO (parte D)
por um teto **do lab** (`TETO_RLE = 1000`), que **não é limite do formato**. Os counts
legítimos destes datasets são ≤ 43, então o teto é folgado. Isso está contado e visível no
`result.md` (`desviadas p/ classe AMPLIFICACAO`) — não é truncamento silencioso.

**Gates byte-canônicos**: `run.py` invoca os testes de baseline reais por subprocess. Eles
foram pinados **antes** deste weld, então passar é evidência de byte-neutralidade — não
auto-afirmação.

**Reprodutibilidade**: `python run.py` regenera byte-a-byte (sem `random`, sem relógio, sem
rede). Zero escrita em `src/tcf` pelo lab — o weld foi feito à parte e está versionado.

# Proveniência — escada bN (2026-07-27-1608)

## Sintéticas — determinísticas, sem RNG

As colunas de varredura são `f"v{i % k}"` e `f"{i % k:0Ld}"` — **aritmética pura sobre o
índice**, sem `random`, sem relógio, sem rede. Escolhidas assim de propósito: para varrer
`k`, `n` e `len(valor)` como eixos independentes, o dado precisa ser o mais neutro possível.

Não há documento (CPF/CNPJ/cartão) sintetizado neste lab.

| eixo | valores varridos |
|---|---|
| `k` (cardinalidade) | 1, 2, 3, 4, 5, 8, 9, 16, 17, 32, 64, 100, 150 |
| `n` (linhas) | 2, 5, 10, 20, 50, 100, 500, 2000 |
| `len(valor)` | 1, 2, 5, 10, 20, 40 |
| `null` | ausente / presente, em bool e em string |

O grupo `casos_null` existe para expor a assimetria de hoje (`bool` sem null usa o denso,
`bool` com null cai no core) e para exercer a colisão `"0"` dado × slot nulo — que **falhou
na primeira rodada** e está documentada no README.

## Reais — fixtures já committadas

**Nenhum download.** Todas de `datasets/samples/`, versionada no repo. Escolhidas por serem
**categóricas** — o regime que a proposta ataca:

| coluna | arquivo | campo | k |
|---|---|---|---:|
| `adult-sex` · `adult-class` | `adult-census/adult-sample.csv` | `sex`, `class` | 2 |
| `adult-race` · `adult-relationship` | idem | `race`, `relationship` | 5 |
| `adult-workclass` | idem | `workclass` | 6 |
| `cnpj-uf` | `receita-cnpj/cnpj-2k.csv` | `uf` | 28 |
| `cnpj-situacao` · `cnpj-matriz` | idem | `situacao`, `matriz_filial` | 2 |
| `pm25-cbwd` | `beijing-pm25/beijing-pm25-sample.csv` | `cbwd` | 4 |
| `ibge-uf` | `ibge-municipios/ibge-municipios-sample.csv` | `uf_sigla` | 3 |

Valores vazios são pulados; o `n` da tabela é o número real de valores usados. Leitura é
fail-loud em nome de coluna inexistente.

`ibge-uf` está aqui **porque a proposta perde nela** (+28 B) — é o contraexemplo, não um
descuido.

## Validação — e por que não é circular

O `hoje` vem do `encode` **REAL** do `src/tcf`. O `bN` é lido por **`le_bn`, um leitor
independente**: ele reimplementa a semântica (lê o cabeçalho posicionalmente, fatia o
domínio, desempacota os bits) em vez de ser a inversa de `para_bn`. O alvo da comparação são
os **dados originais**.

Foi essa independência que pegou o bug do domínio: `de_X(para_X(v)) == v` teria passado, e o
leitor falhou em 2 de 5 casos com null.

Lição aplicada do lab `2026-07-26-0038`, que foi retratado justamente por validação circular.

## Limites declarados

- **Nada soldado**; `src/tcf` intocado. O `.tcfp` é **proposta** — o `decode` público não o lê.
- **gzip não medido.** O estudo de `bN-dense` multi-col registrou no `STATUS.md` que o gzip
  encolhe muito o ganho; aqui a métrica é byte cru.
- **CPU não medido.** O `pack_w` vem do próprio repo (`tcf.bitpack`), mas o custo relativo ao
  core não foi cronometrado.
- A fórmula de custo (`custo_bn`) foi conferida contra a medição em 4 pontos, não em todos.
- Escopo **single-col**. A decisão pendente de `bN-dense` no `STATUS.md` é **multi-col `.8M`** —
  são irmãs, não a mesma.

## Reprodutibilidade

`python run.py` regenera byte a byte — sem RNG, sem relógio, sem rede. Sai `0` só se todos os
RT do leitor independente passarem.

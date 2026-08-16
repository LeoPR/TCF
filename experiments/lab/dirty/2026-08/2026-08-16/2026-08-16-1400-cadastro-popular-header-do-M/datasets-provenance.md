# Procedência — sintético, determinístico, e a política de CPF

## O cadastro

`run.py::cadastro()`, `random.Random(20260815)`, n=500, sem `Z:`. Sete colunas, todas string
(a condição do `.8M`):

| coluna | forma | mecanismo que exercita |
|---|---|---|
| `id` | `000001..000500` (largura 6 uniforme) | seq-RLE do core; e o `int_pad_para` → `None` |
| `nome` | 20 primeiros × 10 sobrenomes | bN no flat, OBAT no `.8M` |
| `cpf` | **gerador da suíte soldada** | `SPEC_CPF` (aplica e vence) |
| `email` | `nome.sobrenomeNN@{3 provedores}` | nenhum (o gap declarado) |
| `telefone` | `+55 11 9NNNN-NNNN` template uniforme | split `%` |
| `nascimento` | ISO espalhado 1950–2005 | `SPEC_DATA_ISO` (aplica e PERDE pro split) |
| `ativo` | `"ativo"/"inativo"` | dict `@` no `.8M`, bN no flat |

## A política de CPF, resolvida por precedente

Regra do projeto: CPF DV-válido de aparência real **nunca publicado**. O precedente que
governa está na suíte soldada: `tests/test_nature_compete.py:21-48` gera CPFs
**algoritmicamente** (base `randint(0, 999999999)` com seed fixa + DV mod-11 calculado).
Este lab replica o gerador byte a byte. São CPFs-contador com seed pública — não amostrados
de nenhuma distribuição real, não associados a pessoa nenhuma.

Nomes/emails idem: combinação de listas sintéticas de 20×10; qualquer coincidência com pessoa
real é colisão de gerador, não dado.

## Vieses declarados

- **Uma seed, um n.** Os vencedores por coluna dependem de cardinalidade×n (o `ativo` com 2
  únicos favorece bN/dict; o `telefone` com template 100% uniforme favorece split — quebra de
  template em 1 linha mata o split, gate em `multi/split.py:40-41`).
- **Telefone irrealisticamente uniforme**: todos `+55 11 9…`. DDDs variados mudariam o
  template e o split ainda pegaria (o DDD viraria campo), mas não foi medido aqui.
- **Datas de nascimento espalhadas** (regime `esparsa-desordenada` do lab do date) — é o
  regime em que o ordinal do `:dt` menos rende, e por isso o split ganha. Coluna de datas
  ORDENADA daria outro vencedor.

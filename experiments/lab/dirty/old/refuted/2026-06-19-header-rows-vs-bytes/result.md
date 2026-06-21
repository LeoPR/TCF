# Header por LINHAS vs BYTES — teste de hipótese (proporção) [resultado]

**Data**: 2026-06-19 · resultado (lab read-only, **modelo paramétrico, SEM tocar core**). Origem:
owner — "trocar byte-size por nº de linhas no header não seria mais econômico (tabelas pequenas) e a
simetria deixa 1 número só?". Script: [`modelo_proporcao.py`](modelo_proporcao.py) ·
saída: [`result.txt`](result.txt).

## Método

Modelo paramétrico (não precisa do encoder): varre **C colunas × N linhas × b bytes/valor
comprimido** e mede a economia de header como **% do blob** (blob ≈ C·N·b; o header é fração mínima).
3 opções:
- **A** byte-size **decimal** (atual): acesso O(1) à coluna (somo os tamanhos → pulo) + decode paralelo.
- **B** byte-size **base-94** (o "hexa" do owner, melhor): **mantém** O(1) + paralelo; só encurta o número.
- **C** **row-count** (linhas), 1 número compartilhado + restaurar `\n` separador/coluna (modo
  "solid block"): **perde** O(1) (vira scan), decode paralelo e group por slice.

## Resultado (60 formas testadas)

| opção | economia ≥1% do blob | ≥5% | perde desempenho? |
|---|---|---|---|
| **C (row-count)** | **11/60** (só tiny-wide; abs. 2-90 B) | **0/60** | **sim** (O(1), paralelo, groups) |
| **B (base-94 size)** | **14/60** | 0/60 | **não** (mantém tudo) |

- **C só passa de 1% em tabela minúscula (N≤100) + muitas colunas (C≥20)** — e lá a economia
  **absoluta** é de dezenas de bytes. Em **2 colunas é NEGATIVO** (row-count + 2 separadores > 1
  byte-size). Em **volume real** (N≥1000): <0,2%; em N=100k: **0,00%**. (Bate com o medido antes:
  adult/tpch ~0,01-0,02%.)
- **B domina C**: proporção igual/melhor, **sem** perder O(1)/paralelo/groups.

## Veredito

- **C (header por linhas) = `REFUTED-INSUFFICIENT`** (solid-block). A economia é **estatisticamente
  desprezível** (sub-1% fora do canto tiny-wide; dezenas de bytes no melhor caso) e custa **todo** o
  resto: o lazy perde acesso O(1) por coluna (vira scan → toca o prefixo até a coluna, mata a
  "venda"), perde **decode paralelo** (bytes permitem fatiar e paralelizar; linhas forçam scan
  sequencial) e perde **group por slice**. Analogia do owner (solid block) confirmada: ganha um pouco
  de ratio, perde acesso aleatório. **Não vale.**
- **B (byte-size base-94) = candidato de header micro-opt** (se o alvo for transmissão minúscula):
  encurta o número ~2× **mantendo** O(1) + paralelo + groups. É a forma certa de atacar "header menor".
  Format change mínimo (só o encoding do número no meta), seguro.

## Impacto no mecanismo (a outra pergunta do owner)

- **C**: **alto** — parser de **header com 2 semânticas** (a desambiguação que o owner esboçou:
  1-col nada, 2-col marcador, 3+ deduz) + o lazy teria que **reconstruir os offsets ao carregar**
  (scan) + perda de paralelismo. Muita mudança pra <0,2% em tabela real.
- **B**: **baixo** — trocar decimal↔base-94 no parse/emit do byte-size do meta. Mantém toda a
  semântica (continua byte-size, continua O(1)). É só a representação do número.

## Encaminhamento

- **Header por linhas**: **não fazer** (refutado; registrado pra não reabrir). Se algum dia houver um
  modo "pacote único / decode-all sem query", reconsiderar — mas o ganho seguiria ínfimo.
- **Byte-size base-94**: registrar como **O-FMT header micro-opt** (transmissão), candidato futuro
  (#TCF.8, opt-in, default off). Não é prioridade (header é fração mínima do blob).
- `src/tcf` intocado.

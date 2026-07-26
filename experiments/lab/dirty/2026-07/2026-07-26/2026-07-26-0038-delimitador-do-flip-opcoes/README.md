# 2026-07-26-0038 — O delimitador do flip: opções para escolher

O flip de polaridade ([lab `2026-07-25-2337`](../../2026-07-25/2026-07-25-2337-polaridade-escape-vs-referencia/))
esbarra numa adjacência inexpressável: em FLIP, `\1` colado num literal-dígito `2` colapsa em
`\12`. Este lab **não decide** — levanta o espaço com número em cada eixo.

Escopo: **uma coluna, single-col**, como você delimitou.

## Eixo 1 — qual char

**Tomados no corpo** (levantados do `src/tcf`, não de memória): `\` `*` `|` `~` `^` `,` `.`
`+` `-` e LF.

**Candidatos com zero ocorrência** na amostra (10 formas × 500 valores, 70.185 chars):

```
!   #   %   &   '   ;   <   >   [   ]   _   `
```

E os que **já aparecem** no dado — se escolhidos, passariam a precisar de escape em FLIP,
cobrando de volta parte do ganho:

| char | ocorrências | onde |
|---|---:|---|
| `/` | 4500 | data-BR, URL, path |
| `"` | 2000 | JSON |
| `:` | 1500 | URL, JSON |
| `(` `)` | 500 cada | telefone |
| `$` `=` `?` `@` `{` `}` | 500 cada | moeda, URL, email, JSON |

> **Ressalva**: *zero nesta amostra* não é *zero no mundo*. `%`, `&`, `=`, `?` aparecem em
> query string; `:` em hora; `;` em CSV europeu. Nenhum char é impossível — o esquema tem que
> saber escapá-lo de qualquer jeito. A escolha é sobre **frequência**, não impossibilidade.
>
> Nota sobre `#`: está livre no **corpo**, mas é o primeiro char do **cabeçalho** (`#TCF.8`).
> Reusá-lo não é ambíguo (namespaces diferentes), mas custa legibilidade.

## Eixo 2 — onde aplicar

| | como | custo |
|---|---|---|
| **(a)** | delimitador só na posição ambígua | 1 B por adjacência |
| **(b)** | terminar **toda** referência | 1 B por referência |

| forma | corpo | ganho bruto | (a) líquido | (b) líquido |
|---|---:|---:|---:|---:|
| hex | 5711 | +1211 | **+1211** | **+1211** |
| moeda | 6226 | +900 | **+796** | **+764** |
| int-ruido | 3922 | +500 | **+500** | **+500** |
| telefone | 8244 | +764 | **+354** | **+256** |
| versão | 4929 | +114 | −119 | −526 |
| data-BR | 4905 | +77 | −243 | −572 |
| URL | 6563 | −137 | −618 | −963 |
| path | 6319 | −831 | −1117 | −2129 |
| email | 5743 | −812 | −962 | −1991 |
| JSON-ish | 5348 | −1333 | −1450 | −2846 |

**Somando só onde cada um ganha: (a) 2861 B · (b) 2731 B.**

O achado que simplifica a decisão: **a diferença entre (a) e (b) é de 130 B na matriz
inteira** — 4,5%. O motivo é estrutural: as colunas onde o flip ganha são justamente as que
têm **poucas ou nenhuma referência** (hex e int-ruído têm zero). Onde há muita referência, o
flip já perde por outros motivos e o `min()` descarta antes de o delimitador importar.

Ou seja: **(b), que é o parser mais simples, custa quase nada a mais.** Não é preciso pagar
complexidade de contexto por 4,5%.

## Eixo 3 — alternativas que não gastam char

| alternativa | custo | observação |
|---|---|---|
| escape duplo na posição ambígua | **2 B** por adjacência | não gasta char novo, mas `\\` já é o escape de `\` — precisaria de outra grafia |
| referência de largura fixa | (largura − dígitos reais) por referência | só compensa com tabela pequena; some o ganho em coluna com muitas refs |
| flip só onde não há adjacência | **0 B** | cobre 20 das 33 colunas; deixa telefone e moeda na mesa |

A terceira é a mais barata de implementar (o detector já existe) e a que menos entrega.

## O que este lab não fez

- **Não implementou** nenhuma das opções — os números do eixo 2 são contagem × 1 B, não
  corpos materializados. O lab anterior mostrou que contagem erra (previu −38 B onde o real
  era +221); aqui o risco é menor porque o delimitador é literalmente 1 B por posição, mas
  **ainda é estimativa**.
- **Não testou multi-col nem `.8H`** — escopo é single-col.
- **Não olhou o registry de chars do header** (`tcf8-header-char-registry.md`) para conflito
  de reserva futura.

## Rodar

```
python run.py
```
`inputs/` · `intermediates/` · `outputs/<forma>-corpo.tcfp` (corpos reais) · `result.md`.
**Não toca `src/tcf`.**

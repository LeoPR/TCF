# Resultado — hierarquia fortificada + cardinalidade

**[probatório]** `run.py` valida RT antes dos bytes. Contra-prova:
[`outputs/10-contraprova.txt`](outputs/10-contraprova.txt); roundtrips `.json` byte-idênticos
aos canônicos de `intermediates/` (diffáveis). Sintético, viés declarado
([datasets-provenance.md](datasets-provenance.md)).

## RT + bytes (LF-only)

| entrada | header | tabelão | JSON | #TCF.8H | RT |
|---|---|---:|---:|---:|---|
| 01-endereco (`{}` 1:1 + `[]` 1:N) | `nome,plano,endereco{rua,cidade,geo{lat,lon}},telefones[` | 6×7 | 735 B | **392 B** | ✅ |
| 02-pedidos (`[]` 1:N aninhado) | `cliente,pedidos[data,itens[produto,qtd` | 5×4 | 469 B | **175 B** | ✅ |

## O que ficou FIRME (testado)

1. **Gramática do header recursiva**: `{}` (1:1) + `[]` (1:N) aninhados a qualquer
   profundidade, última-folha-sem-size + omit-closes, chaveada por CAMINHO. Casos:
   objeto-com-objeto (endereco⊃geo), array-com-array (pedidos⊃itens), duplicatas em
   array folha (preservadas), N:N (fail-loud). RT-exato em todos.
2. **A hierarquia É a multi-col + RLE**: o pai repete no tabelão e colapsa no `*N|pai`
   (o run = a multiplicidade); nada foi adicionado ao codec — é `tcf.encode` normal.
3. **O mapa de cardinalidade fecha**: 1:1→`{}`, 1:N→`[]` (os dois que ANINHAM);
   N:1→coluna @dict (não é ramo); N:N→ponte (não aninha, fail-loud).

## N:1 na prática (`outputs/08`)

No tabelão, o motor distingue-se pela contagem de distintos vs nº de registros (=3):
- `plano` (2<3) e `endereco.cidade` (2<3) = **N:1 compartilhado** → `*3|Premium`,
  `*3|Sao Paulo` (dict/RLE encolhe a largura do valor).
- `nome`, `endereco.rua`, `geo.lat/lon` (3==3) = **pai do 1:N** → RLE é a multiplicidade.

A mesma primitiva de bytes (RLE/dict) serve as duas; a **cardinalidade explica a origem**.

## N:N na prática (`outputs/09`)

`{aluno, cursos[], clubes[]}` → **NNError fail-loud**: 2 arrays irmãos = produto
cartesiano que inventa pares. Caminho: ponte/junction ou dois 1:N separados (peça 9,
link posicional — fora do escopo).

## Segurança: fail-loud, nunca corromper calado

O `encode_h` **se auto-verifica** (`decode_h(blob) == records`) e recusa (`AmbiguityError`)
qualquer documento que a re-nestação por chave contígua NÃO reverteria — instâncias irmãs
de mesma chave abrigando array aninhado (ex.: 2 pedidos de mesma `data`, cada um com
`itens[]`). Achado da verificação adversarial: sem isso, os itens se fundiriam num pedido
só (`outputs/09`). Chaves distintas revertem normal; o caso geral pede repetition-level (peça 9).
Invariante garantido: **encode sucede ⟹ decode é exato**.

## Para FIRMAR (welding), o que falta

1. Fronteira pai/filho carregada (repetition-level) para resolver o caso hoje fail-loud.
2. N:N / link posicional (peça 9) — se entrar no escopo do `.8`.
3. Gate real-world em JSON aninhado de produção (anti-incidente antes de `confirmada-empirica`).
4. Reconciliar com a gramática ADR-0031 no weld (sem-espaço `#TCF.8H<meta>`; sizes hex).

Tipos/nulos/especiais: **ortogonais**, camada posterior (não bloqueiam a hierarquia).

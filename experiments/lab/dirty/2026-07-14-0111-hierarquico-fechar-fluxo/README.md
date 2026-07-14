# Lab 2026-07-14-0111 — fechar FUNCIONALIDADE + FLUXO do hierárquico (clássicos de transmissão)

**Status**: pesquisa/medido, sintético. **Ticket**:
[T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md).
**Base**: inventário [hierarquia-inventario-hipoteses](../notas/hierarquia-inventario-hipoteses.md)
+ envelope/blocos (peça 2/3) + counts (Modelo B, lab 2356).

Foco do owner (2026-07-14): **sem payload de API real** (isso é gate de performance = `.9`);
performance dá pra **simular** (encode/decode ou encode+compress+decompress+decode). Agora
**fechar a funcionalidade + o fluxo encode/decode do hierárquico** com os **clássicos de
transmissão** (cadastro, pedido, telemetria) — a maioria em JSON.

## O que fecha (e por que precisava de um codec novo)

Um cadastro real tem **múltiplas listas irmãs** — `telefones[]` E `emails[]` — que o tabelão
integrado (labs 2325) **fail-loudava** (2 arrays no mesmo nível = produto cartesiano). O codec
aqui (`shred.py`) fecha isso: **SHREDDING em blocos + counts** — cada array vira um bloco ligado
ao pai por um `#count` explícito (a multiplicidade 1×, o "sincronismo" do Modelo B, generalizado).

Isso resolve as três coisas que o tabelão não fechava:
1. **múltiplas listas irmãs** (cadastro: tel[] E email[]) — cada uma seu bloco, sem cruzar;
2. **arrays aninhados** (pedido⊃itens) — bloco filho de bloco;
3. **ambiguidade de chave** (2 pedidos de mesma data) — o count é ESCRITO, não deduzido do run RLE.
   Também: **arrays vazios** (pessoa sem emails) e schema robusto a array-vazio-no-1º-registro.

Colunas-pai ficam na granularidade da pessoa (SEM `*N|` por coluna); a multiplicidade vive nos
`#count`. É o nível-aware (peça 9 / lab 2356) generalizado recursivamente.

## Gramática do header (fechada aqui)

```
#TCF.8H <meta>\n<colunas DFS, tcf.encode cada, fatiadas por size>
  name:size            escalar
  name{ ...itens... }  objeto 1:1 (INLINE, mesmo bloco)
  name#:csize[ ... ]   array de OBJETOS (bloco filho; #csize = coluna de counts)
  name#:csize[]:asize  array de ESCALARES (coluna name = elementos; #csize = counts)
  última folha DFS omite size; omit-closes dropa o `]`/`}` final.
```

## Os dois fluxos (ambos RT-exato)

- **A · FUNCIONAL**: `JSON -> encode_h -> #TCF.8H -> decode_h -> JSON` (roundtrip.json byte-idêntico
  ao canônico).
- **B · TRANSMISSÃO simulada**: `JSON -> encode_h -> gzip/brotli -> gunzip/unbrotli -> decode_h -> JSON`
  (performance por proxy; a API real fica pro `.9`).

## Clássicos exercitados (RT-exato A e B)

| entrada | forma | JSON | TCF.H | +gzip | +brotli | JSON+br |
|---|---|---:|---:|---:|---:|---:|
| `01-cadastro-clientes` | endereco{geo} 1:1 + **telefones[] + emails[]** (2 listas) | 842 | 520 | 379 | 362 | 330 |
| `02-pedidos-itens` | **pedidos[itens[]]** aninhado + `pedidos:[]` vazio | 635 | 328 | 270 | 246 | 255 |
| `03-telemetria-dispositivos` | sensores{temp,umid} 1:1 + leituras[] série | 698 | 314 | 231 | 204 | 196 |

TCF.H cru é ~40–55% menor que o JSON. Sob brotli fica competitivo (empata/perde por poucos bytes
em payload minúsculo — coerente: a vantagem do TCF aparece com volume; isso é medida de FORMA, o
gate de performance é `.9`). **O ponto aqui é a FUNCIONALIDADE + o FLUXO fecharem, não os bytes.**

## Rodar

```powershell
python experiments/lab/dirty/2026-07-14-0111-hierarquico-fechar-fluxo/run.py
```

Zero `src/tcf` (read-only `tcf.encode`/`decode`). Sem tipos/nulos (ortogonal). Ver [result.md](result.md).

## Limites (registrados)

- **Chaves uniformes por nível** (todos os objetos de um bloco têm o mesmo conjunto de campos).
  Objetos ragged (chaves faltando) = a máscara de presença/def-level (peça 11) — camada seguinte.
- **Uma raiz** (lista de registros homogêneos). N raízes independentes = raiz sintética/peça 11.
- **Tipos como string** (ortogonal; camada posterior).
- Sintético; medida de FORMA. Gate real-world + performance = `.9`.

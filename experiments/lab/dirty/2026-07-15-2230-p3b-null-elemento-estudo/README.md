# Lab 2026-07-15-2230 — ESTUDO P3b: null em elemento de array (element-mask)

**Status**: estudo/protótipo PARA REVISÃO — nada weldado. **Ticket**:
[T-CODE-TCF8H-JSON-PARITY](../../../../tickets/T-CODE-TCF8H-JSON-PARITY.md) (P3b).

**P3b** = `null` como ELEMENTO de array (`["a", null, "b"]`, `[{...}, null, {...}]`) — hoje fail-loud.
Gramática NOVA (por isso estudo-primeiro, ≠ P3a que reusou a máscara). Protótipo **extrai a ideia**
(codec recursivo mínimo, não copia o core).

## O que muda vs P3a

A máscara do P1/P3a alinha às **instâncias do campo**; um elemento é **outra cardinalidade** (um por
elemento, somando os counts). P3b usa uma **element-mask** alinhada ao stream de elementos:
- **2-estados** `.`=valor · `0`=null — **sem `-`** (a posição existe via count; elemento é valor ou null).
- ordem das colunas de um array element-nullable: **count → emask → elementos densos** (só `.`).
- gramática: `nome#?[...]` — o `?` após `#count` = elementos mascarados (posicionalmente distinto do
  `?` de campo, que vem antes do `#`).

## Resultado (rodar: `python study.py`) — [outputs/00-resultado.txt](outputs/00-resultado.txt)

RT byte-exato em **8/8** formas didáticas ([inputs/](inputs/01-didatico-null-elemento.json) →
[outputs/*-rt.json](outputs/) diffável):

| forma | meta | RT |
|---|---|:--:|
| null no meio (escalar) | `tags#?[]` | ✅ |
| null início e fim | `xs#?[]` | ✅ |
| array todo-null | `xs#?[]` | ✅ |
| vazio vs `[null]` vs `[v]` (≠) | `xs#?[]` | ✅ |
| elemento OBJETO null | `itens#?[p,q]` | ✅ |
| 4-vias no elemento (null/`""`/`"null"`/v) | `xs#?[]` | ✅ |
| duas listas, só uma com null | `tel#?[],email#[]` | ✅ |
| aninhado (array em obj em array) | `pedidos#[itens#?[]]` | ✅ |

**Ponto-chave**: o `?` aparece **só onde há null** (`tel#?[]` mas `email#[]`; o `pedidos` externo sem
`?`, o `itens` interno com) — deduzido do dado, como todo o header. Alinhamento count×emask×dense
consistente inclusive no elemento-objeto e no aninhamento.

## Fronteira / próximo

- É prova de CONCEITO (sem L1/escaping/omit-closes — o weld integra no core como o P3a).
- **Duas rotas** pro weld: (a) esta element-mask (L2, consistente com P3a); (b) o **índice-de-
  substituição** (unifica P3a+P3b, toca L1 — [[H-PROFILE-01]]). O estudo valida (a); (b) fica a medir.
- Pós-aprovação: weld no core com didático→realista→massa + gate (padrão P3a) + probes adversariais
  (a lição do P1: gramática nova esconde corrupção — testar borda, não só o caminho feliz).

Ver [result.md](result.md).

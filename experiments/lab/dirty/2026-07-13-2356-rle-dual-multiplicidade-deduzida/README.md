# Lab 2026-07-13-2356 — dual do RLE: multiplicidade repetida (tabelão) vs deduzida (nível-aware)

**Status**: pesquisa/medido, sintético. **Ticket**:
[T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md).
**Recupera**: peça 9 ([2328](../2026-07-05-2328-tcf8-schema-cardinalidade-explicito-implicito/result.md))
+ H-CARD-06 + [teoria-cardinalidade](../notas/teoria-cardinalidade.md) §1-4.

Revisão a pedido do owner (2026-07-13): *"como o header já diz que telefones está
aninhado em pessoa (1:N), o pai não expande de fato... o RLE poderia ser deduzido, as
colunas ficariam com algum sincronismo pra serem vinculadas."* Isso já foi concluído —
este lab **recupera e MEDE**.

## A questão (as duas situações do owner)

Nome com 2 telefones. Na hierarquia, a multiplicidade `[2,1,3]` mora onde?

- **Modelo A — tabelão** (protótipo 2301/2325): toda coluna-pai vai à granularidade FINA
  (telefone); o pai repete e o RLE `*N|pai` colapsa. **A multiplicidade aparece no RLE de
  CADA coluna-pai** (nome, rua, cidade, geo… todas `*2|…*3|`) — redundante entre irmãs.
- **Modelo B — nível-aware** (peça 9): cada coluna fica na SUA granularidade (pessoa-nível
  1× por pessoa; telefone achatado); a multiplicidade é **UM canal `counts` [2,1,3]** — o
  "sincronismo" que liga os níveis. Colunas-pai não carregam `*N|`.

## O que já concluímos (recuperado)

- **Peça 9 (2328)**: cardinalidade/rows é **DEDUZÍVEL do nº de linhas dos filhos**; "custo
  transmitido ZERO"; o header carrega só as **arestas de hierarquia** (o irredutível).
- **teoria §3-4**: RLE `*N|pai`, `counts` e `fk` são **DUAIS**; a ×N é **conservada** (~log N);
  o schema compra **reconstrução**, não bytes de multiplicidade. Cardinalidade ⊥ compressibilidade.
- **H-CARD-06**: o RLE do pai exige o pai AGRUPADO (Order Dependency); ordem livre → O(d)
  runs; ordem semântica → side-channel de permutação (= **rep/def levels do Dremel**).

## Medido (RT-exato nos dois modelos)

| entrada | registros | campos-pai | A (tabelão) | B (nível-aware) | vence |
|---|---:|---:|---:|---:|---|
| `01-estreito` (nome + telefones) | 3 | 1 | **135 B** | 140 B | A (+5 B) |
| `02-largo` (cadastro completo) | 3 | 11 | 466 B | **423 B** | B (−43 B) |

**É um CROSSOVER, não absoluto**: com POUCOS campos-pai, o `*N|` por coluna é barato e o
`counts` não paga (tabelão A vence); com MUITOS campos-pai (registro largo), a multiplicidade
repetida em cada coluna domina e carregá-la UMA vez vence (nível-aware B). Coerente com a
teoria: os dois conservam a mesma ×N; a diferença é **onde** ela mora e **quantas vezes**.

## Conclusão

1. A intuição do owner está certa e já estava concluída (peça 9): a multiplicidade **não
   precisa repetir** por coluna — pode ser deduzida (doc único) ou carregada 1× (multi-registro).
2. Meu protótipo (2301/2325) usa o **Modelo A** (dual explícito, mais simples, RT-exato). É
   correto, mas paga a redundância em registros largos.
3. **A e B são candidatos de `min()`** (como o FLOOR das natures): encodar os dois e ficar
   com o menor por documento é a resposta natural do TCF — A para estreito, B para largo.
4. Para FIRMAR o mínimo, migrar/oferecer B (counts 1×) — **decisão do owner**.

## Rodar

```powershell
python experiments/lab/dirty/2026-07-13-2356-rle-dual-multiplicidade-deduzida/run.py
```

Zero `src/tcf`. Ambos RT-exatos (`outputs/*.modelo-*.tcf`, `10-conclusao.txt`). Sem tipos/nulos.

## Limites

- Spine (um array 1:N + objetos 1:1). Multi-array/aninhado profundo = extensão.
- `counts` do B é carregado (não deduzido) porque multi-registro precisa das fronteiras —
  o "deduzido custo ZERO" da peça 9 é p/ doc ÚNICO; multi-registro paga o counts 1×.
- Sintético; medida de FORMA (crossover), não gate real-world.

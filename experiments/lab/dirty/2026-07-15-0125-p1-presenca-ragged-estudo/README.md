# Lab 2026-07-15-0125 — ESTUDO P1: presença/ragged (def-level) no #TCF.8H

**Status**: estudo PARA REVISÃO DO OWNER — nada weldado. **Tickets**:
[T-CODE-TCF8H-JSON-PARITY](../../../../tickets/T-CODE-TCF8H-JSON-PARITY.md) (P1 é o 1º incremento) ·
[T-CODE-TCF8H-WELD](../../../../tickets/T-CODE-TCF8H-WELD.md).

**O que é P1**: chave OPCIONAL (objeto ragged) — o construto JSON de API mais comum que o `.8H`
ainda rejeita (`test_ragged_fail_loud`). Base provada: máscara de presença do lab
[2026-07-06-2246](../2026-07-06-2246-tcf8h-fronteira-link-posicional/) (B1/B2). Este estudo a
INTEGRA à gramática weldada (ADR-0033), com exemplos vistoriáveis e medições.

## A proposta em 1 olhada (exemplo real do lab — `03-pedido-aninhado-ragged`)

Entrada ([inputs/](inputs/03-pedido-aninhado-ragged.json)): pedidos onde `cupom` é opcional,
`itens` é opcional (Daniel NÃO tem a chave; Carla tem `[]` vazio — coisas DIFERENTES), e `obs`
é opcional DENTRO de cada item.

Wire ([outputs/03-pedido-aninhado-ragged.tcf](outputs/03-pedido-aninhado-ragged.tcf)):

```
#TCF.8Hcliente:29,cupom?:13:21,itens?:10#:11[produto:47,qtd:20,obs?:16
Ana                  ← colunas de dado (L1 intacto)
...
.                    ← máscara do cupom: [. - - . -] com RLE: '.', '*2|-', '^1', '^2'
*2|-                   (dá pra LER "2 ausentes" sem decodificar — pilar explicabilidade)
...
*3-1|\2              ← counts dos itens PRESENTES [2,1,0,3] colapsados por seq-RLE
```

- **Gramática**: `nome?:msize` = campo opcional (o `?` cola no nome; `msize` = bytes da
  coluna-máscara). Combina com TODO tipo: `cupom?:13:21` (escalar) · `itens?:10#:11[...]`
  (array) · `cfg?:m{...}` (objeto). `?` vira char estrutural → entra no escape (`\?`).
- **Máscara**: coluna de CONTROLE (como o `#count`), 1 entrada por INSTÂNCIA do nível
  (opcional dentro de array = 1 por elemento). Alfabeto 3-estados com wire já reservado:
  `.`=presente · `-`=ausente · `0`=RESERVADO para null (P3) — não solda duas vezes.
- **Corpo denso**: colunas de dado só carregam instâncias PRESENTES (sem buracos).

## Resultados (rodar: `python study.py`)

| medição | resultado |
|---|---|
| RT dos 3 clássicos ragged | 3/3 byte-exato ([outputs/*-rt.json](outputs/) diffáveis vs [intermediates/](intermediates/)) |
| M1 custo da máscara | regime raro (1/20 ausente): **~0,5 B/registro** (RLE colapsa); alternado (pior caso): ~3 B/registro |
| M2 sentinela `""` (a alternativa) | **LOSSY** — `""`-vazio e ausente COLIDEM; máscara preserva (por isso canal próprio) |
| M3 compat | dado uniforme → wire **BYTE-IDÊNTICO** ao weld atual (`?` só aparece onde há raggedness; deduzido do dado) |
| M4 escala API-like (n=1000, opcionais 90%/50%/5%) | RT=True; 10329 B vs 81130 B JSON-compacto |
| M5 bordas | objeto-opcional-com-filho-opcional · presente-em-1-só · ordem heterogênea · ausente≠vazio≠cheio · opcional-em-elemento-de-array — **RT 5/5** |
| M5b fail-loud | null → P1Error claro (P3 não engolido); nome com `?` escapado faz RT |

## Decisões pro owner revisar (antes de qualquer weld)

1. **Gramática `nome?:msize`** — ok o `?` colado no nome? (alternativas consideradas no result).
2. **Alfabeto 3-estados com `0` reservado** — P1 usa só `.`/`-`, mas o wire já nasce com o slot
   do null (P3) pra não mudar duas vezes. Ok?
3. **`?` entra no escape** — nome contendo `?` passa a ser `\?` (wire muda pra esses nomes raros).
4. **Semântica**: chave ausente ≠ `""` ≠ `[]` ≠ null (M2/M5 provam) — é o contrato desejado?
5. **Ordem de chave** normalizada pra ordem do schema (união por 1ª aparição) — RFC 8259 diz que
   ordem não é significativa; dict `==` passa. Aceitável?

## Plano de weld (só após aprovação) — ver [result.md](result.md) §Plano

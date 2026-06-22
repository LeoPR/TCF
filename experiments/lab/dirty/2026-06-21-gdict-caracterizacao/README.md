# B1 — cross-dict / dicionário global (H-GDICT): plano de hipóteses [plano]

**Data**: 2026-06-21 · lab read-only (`src/tcf` intocado). Owner liberou o B1 pedindo
**planejar com exemplos sintéticos mínimos antes de construir** — possibilidades, perdas/ganhos,
e avaliar um **modo híbrido**. Ticket: [T-EXP-H-GDICT-01](../../../../tickets/T-EXP-H-GDICT-01.md).
Evidência medida: [result.md](result.md). Prior art: [`dict-referencia-hipoteses.md`](../notas/dict-referencia-hipoteses.md)
(família H-REF), [roadmap-hipoteses Pacote 11-ter/quater](../notas/roadmap-hipoteses.md).

## O quê

Hoje cada coluna categórica vira um `@dict` V2-B **independente** (tabela de únicos + stream de
índices). Colunas que **compartilham valores** (flags SIM/NÃO, UFs, status, códigos) guardam a
tabela N vezes. H-GDICT promove a **um dicionário compartilhado no header** + colunas viram só
streams de índices. É format change `#TCF.8`, opt-in (default off = `#TCF.7` byte-idêntico).

## As 3 tensões do owner — formalizadas e respondidas pela medição

> Anchored em [result.md](result.md). Decomposição do net do cross-dict:
> `net = (Σ tabelas_per_col − tabela_global) − Σ_c N_c·(w(K_global) − w(K_c))`.

### T1 — Paralelismo ↔ sincronismo
*"se eu não mover os índices pra reaproveitar, as outras colunas perdem o paralelismo... vira um
paralelo com sincronismos entre colunas."*

**Confirmado.** Compartilhar dict **inline cross-coluna** (coluna B referencia um valor definido na
coluna A) cria **dependência serial**: B não decoda sem A. Hoje o decode é embaraçosamente paralelo
(cada coluna é fatiada por size e decodada sozinha). A única forma de compartilhar **sem** acoplar é
**hoistar a tabela pro header**: prelúdio serial único (decodar a tabela 1×) → todas as colunas
paralelizam depois. **→ decisão: dict compartilhado vive no HEADER, nunca inline cross-coluna.**

### T2 — Custo do dict no header
*"carregar os índices num dict no cabeçalho sobrecarregaria um pouco, perderíamos uns bytes... a
coluna que fazia auto-referência cederia sua referência pro índice."*

**Medido, e mais matizado que a intuição.** A TABELA no header é **barata** (E3: 55 B p/ 15 valores
compartilhados por 6 colunas). O custo real **não é a tabela** — é a **largura do índice**: quando o
namespace global incha e cruza o limite base-94 (94, 8836, ...), cada índice ganha +1 char, pago em
**toda linha de toda coluna**. Em E2 isso custou +600 B e afundou o ganho. **→ o "sobrecarregar" só
morde quando o pooling cruza um bucket de largura; senão é ganho quase puro (dedup da tabela).**

### T3 — Namespace de índice cross-coluna
*"um índice 1 de uma coluna usado em outra... a outra não poderia usar esse índice 1; quebra a
lógica de índice por posição se eu quiser cada coluna começar do 0."*

**É exatamente o gatilho do custo de T2.** Um namespace **global flat** (0..K_global−1) força a
largura do maior K. **→ decisão: namespaces por GRUPO** — cada grupo de colunas que compartilham tem
seu próprio dict 0-based, pequeno. "Índices de cada coluna do 0" vira "índices de cada GRUPO do 0".
Isso bound a largura e é o coração do modo híbrido (V2 abaixo).

## Espaço de design (variantes)

| id | descrição | paralelismo | streaming | quando ganha |
|---|---|---|---|---|
| **V0** | per-column `@dict` (HOJE) | máximo (colunas independentes) | por coluna | baseline |
| ~~Vx~~ | dict inline cross-coluna | **perde** (serial entre colunas) | pausas espalhadas | **rejeitada** (T1) |
| **V1** | 1 dict global flat no header (todas as colunas) | prelúdio serial + paralelo | 1 pausa frontal | overlap alto **e** K_global no mesmo bucket de largura |
| **V2** | **híbrido**: dicts por GRUPO no header (colunas particionadas) | prelúdio(s) + paralelo | pausa(s) por grupo | caso geral — pega o ganho de V1 sem o custo de largura |

V1 é caso particular de V2 (1 grupo só). V0 é V2 com grupos unitários.

## Modo híbrido (V2) — a proposta

Particionar as colunas dict-elegíveis em **grupos**; cada grupo recebe um dict compartilhado no
header **sse o net do grupo > 0**. Coluna fora de qualquer grupo fica V0 (`@dict` per-column) ou
tcf/raw (fallback atual).

**Regra de decisão (barata, derivável no pré-pass):** dois eixos —
1. **Overlap real**: agrupar colunas com interseção de value-set alta (Jaccard ≥ limiar). Sem
   overlap não há economia de tabela (E2).
2. **Bucket de largura**: só juntar enquanto `w(K_grupo)` **não cruza** o limite acima do
   `max w(K_c)` do grupo. Se juntar uma coluna estoura a largura, ela vira grupo à parte.

Greedy: ordena candidatos por overlap, vai agregando ao grupo enquanto `net_estimado > 0` (fórmula
acima, computável só com os value-sets + N — sem encodar). Decisão **order-free** e barata.

Isto encaixa nas 3 tensões: paralelismo preservado (header, por grupo), custo de largura controlado
(grupos pequenos), namespace por grupo (cada um 0-based).

## Perdas e ganhos (síntese)

| | ganha | perde |
|---|---|---|
| **bytes** | dedup de tabelas compartilhadas (E1 −20, E3 −58) | índice global mais largo se cruzar bucket (E2 +594) |
| **paralelismo** | preservado (prelúdio + paralelo) | prelúdio serial de 1 (V1) ou poucos (V2) dicts |
| **streaming** | pausa frontal previsível por grupo | não-zero (V0 não tem pausa) |
| **lazy/latência** | dict no header = **leitura única** (sinergia H-QUERY) — payoff ESTRUTURAL, não só bytes | índice global a resolver |
| **complexidade** | — | particionamento + namespace por grupo + format change #TCF.8 |

**O argumento mais forte do H-GDICT não é bytes** (que pode empatar sob brotli, lição V2-RLE) — é
**estrutural**: dict no header resolvido 1× serve o lazy (`tcf.view`) sem re-decodar por coluna.
Por isso o gate inclui a porta estrutural (latência), não só os 15% de bytes.

## Gate (do plano 0.8) e formato

- **Critério de weld**: ≥15% weighted em 2+ reais **OU** justificativa estrutural (latência/leitura
  única no lazy). Medir **textual E sob brotli E** latência. Checklist anti-incidente 2026-05-21.
- **Formato**: `#TCF.8` **opt-in**; default off = `#TCF.7` byte-idêntico (D1-D9=1523B, D17a=303B).
- Se o net real (≥5 datasets) não pagar nem por bytes nem por estrutura → cross-dict **sai do 0.8**,
  vira 0.9/estudo (precedente honesto: V2-RLE-STREAM).

## Próximos passos (B1 completo)

1. **Medir overlap real intra-blob** em ≥5 reais (adult, tpch, receita, br-identidades, ibge):
   quais pares de colunas de fato compartilham value-set, e qual o Jaccard. **Risco já sondado**: o
   sharing forte (UF, município) costuma ser **cross-TABELA**, não intra-tabela; `encode()` opera
   sobre 1 blob → o caso feliz pode exigir multi-tabela (fora do uso padrão). Confirmar/refutar.
2. **Rodar o modelo** (este script, generalizado) sobre os blobs reais: net V0 vs V1 vs V2-híbrido,
   textual e sob brotli.
3. **Latência no lazy**: medir leitura-única do dict de header vs re-decode per-column.
4. **Decidir** (B2): se paga (bytes ou estrutura) → design #TCF.8 + ADR; senão → 0.9.

## Conexões

- Pré-requisito conceitual: família **H-REF** ([`dict-referencia-hipoteses.md`](../notas/dict-referencia-hipoteses.md))
  — H-REF-02 (índices globais) = T3; H-REF-03 (alfabeto livre-de-conflito) ataca o escape inline.
- Plano 0.8: [`v08-plano-etapas.md`](../notas/v08-plano-etapas.md) (workstream B).
- Lazy (sinergia estrutural): [`docs/reference/lazy-view.md`](../../../../docs/reference/lazy-view.md).
- V2-B atual: [ADR-0025](../../../../docs/adr/0025-v2b-dictionary-categorical-weld.md).
- Precedente "só bytes não basta": [V2-RLE-STREAM](../old/refuted/2026-06-19-v2rle-stream-caracterizacao/result.md).

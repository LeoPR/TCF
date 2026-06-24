# B1.0 — cross-dict (H-GDICT): evidência sintética mínima [probatório]

**Data**: 2026-06-21 · lab read-only (`src/tcf` intocado). Script: [`synth_minimal.py`](synth_minimal.py).
Modela com os internos REAIS do V2-B (`_v2b_encode`, `_encode_column`, `_v2b_width`).

## O que foi medido

Duas representações do MESMO conteúdo categórico, só o corpo do dict (tabela + stream;
meta do header estimada à parte):

- **@dict per-column (HOJE, V2-B)**: cada coluna = `<len(tab)>\n` + tabela própria + stream `N·w(K_c)`.
- **cross-dict GLOBAL (H-GDICT)**: 1 tabela compartilhada (união dos únicos) + cada coluna = stream `N·w(K_global)`.

`w(K)` = largura base-94 do índice (1 char até K=94; 2 até 8836; ...).

## Resultados (textual | brotli q11)

| caso | descrição | per-col | cross-dict | net textual | net brotli |
|---|---|---|---|---|---|
| **E1** | 3 flags SIM/NÃO, alto overlap, K_global=2 (w=1) | 102 B | **82 B** | **−20 (ganha)** | 49→**40** (ganha) |
| **E2** | 3 cols 40-distintos disjuntos, N=200, K_global=120 (w 1→2) | 642 B | 1236 B | **+594 (perde)** | 74→173 (perde) |
| **E3** | misto: flags+UFs compartilham, porte disjunto, K_global=15 (w=1) | 257 B | **199 B** | **−58 (ganha)** | 118→**96** (ganha) |

Decomposição do net (só colunas que seriam dict):
- **E1**: economia_tabela **+20**, custo_índice **0** → +20.
- **E2**: economia_tabela +6, custo_índice **−600** (3 cols × 200 linhas × +1 char) → −594.
- **E3**: economia_tabela **+58**, custo_índice **0** → +58.

## Leitura — a dobradiça é o LIMITE DE LARGURA

O net do cross-dict decompõe em exatamente dois termos:

```
net = (Σ tabelas_per_col − tabela_global)   [economia: tabelas duplicadas colapsam]
    − Σ_c N_c · (w(K_global) − w(K_c))       [custo: índice global mais largo, pago em TODA linha]
```

- **Economia** = só dos valores que **de fato se repetem entre colunas** (a tabela deles deixa
  de ser guardada N vezes). Vale pouco por valor (cada entrada de tabela é curta), mas escala com
  o nº de colunas que compartilham.
- **Custo** = `w(K_global) − w(K_c)` pago em **cada linha de cada coluna**. É **zero** enquanto a
  união fica no mesmo bucket de largura base-94 da coluna; vira **+1 char/linha** (e mais) assim que
  `K_global` cruza 94 / 8836 / ...

**Conclusão central**: cross-dict ganha **sse e só se** o pooling **não cruza um limite de largura**
(E1, E3: K_global ≤ 94 → custo 0 → ganho = dedup puro). Se cruza (E2), o custo por-linha-por-coluna
domina e o cross-dict **perde feio, inclusive sob brotli** (os bytes de padding do índice são
baixa-entropia, brotli recupera parte, mas o per-column continua melhor).

## Implicação direta pro design (as 3 tensões do owner)

1. **Paralelismo ↔ sincronismo**: confirmado que compartilhar dict **inline cross-coluna** (coluna B
   referencia valor definido na coluna A) cria dependência serial. A única forma de compartilhar SEM
   acoplar é **hoistar a tabela pro header** → prelúdio serial único (decodar a tabela 1×) e depois
   as colunas paralelizam. Streaming = **uma pausa frontal** (carregar o dict), não pausas espalhadas.
2. **Custo do dict no header**: medido — a TABELA compartilhada no header é barata (E3: 55 B p/ 15
   valores). O custo real **não é a tabela**, é a **largura do índice** quando o namespace global
   incha (E2). A intuição "perderia uns bytes ao ceder a auto-referência" é verdadeira só quando o
   pooling cruza o bucket de largura.
3. **Namespace de índice cross-coluna**: é exatamente o que causa o estouro de largura. Um namespace
   **global flat** (0..K_global−1) força a largura do maior K. **Manter namespaces por GRUPO**
   (cada grupo 0-based, pequeno) bound a largura → resolve a tensão. "Índices de cada coluna do 0"
   vira "índices de cada GRUPO do 0".

## Caveats

- **Sintético mínimo** (viés declarado: construído pra isolar o mecanismo). NÃO generaliza —
  o gate exige ≥5 reais (anti-incidente 2026-05-21). Aqui só estabelece o MODELO e a dobradiça.
- Meta de header (`@<size>=<name>` per-col vs declaração do dict global + marcador por coluna)
  não incluída — é secundária vs os efeitos de corpo medidos; entra no design #TCF.8.
- Brotli em blob minúsculo tem overhead alto; os sinais batem com o textual mas o número real
  precisa de volume.

---

# B1 (completo) — caracterização em dados reais [probatório]

**Data**: 2026-06-21 · lab read-only, dados em `Z:/tcf-data/` (no projeto só apontamentos).
Scripts: [`etapa1_overlap.py`](etapa1_overlap.py) (+ medição V0/V1 inline). 5 datasets canônicos.

## Etapa 1 — overlap intra-blob (o filtro decisivo)

Jaccard entre value-sets de colunas categóricas (card ≤ 1024) **dentro de cada tabela** (o que
`encode()` vê). Resultado:

| dataset / tabela | colunas dict-elegíveis | maior Jaccard intra-blob |
|---|---|---|
| adult / adult | sex, class, race, relationship, marital-status, workclass, occupation, education, native-country | **0** (todos disjuntos) |
| tpch / (todas) | r_name, n_name, flags lineitem, p_brand, ... | **0** |
| receita / estabelecimentos | matriz_filial, situacao, uf | **0** |
| br-identidades / pessoas, empresas | uf_sigla (1 por tabela) | — (1 col, sem par) |
| ibge / municipios | regiao_*, uf_*, meso/microrregião | **0.032** (trivial, 1 string coincidente) |

**NENHUM par intra-blob com Jaccard ≥ 0.30.** As colunas categóricas reais são **domínios
disjuntos** — até as de cardinalidade 2 não compartilham (adult: sex=Male/Female vs
class=>50K/≤50K).

**O sharing forte existe, mas é CROSS-TABELA** (confirmado, como o owner previu):
`pessoas.uf_sigla` = `empresas.uf_sigla` = `receita.uf` (mesmo conjunto de 27/28 UFs);
`pessoas.municipio_id` = `empresas.municipio_id` (5571). `encode()` opera sobre **1 blob/tabela**
→ não expõe esse compartilhamento.

## Etapa 2 — confirmação em bytes reais (V0 per-col vs V1 global)

Como o overlap intra-blob é ~0, toda tabela real é o caso E2 (disjunto). Medido:

| tabela | K_global | net V1−V0 textual | brotli |
|---|---|---|---|
| adult (9 cat) | 102 (**cruza 94** → w 1→2) | **+99.8%** (880183 vs 440614 B) | pior (118617 vs 102952) |
| lineitem (4 flags) | 16 (w1) | −5 B (~0%) | **pior** (54388 vs 51984) |
| receita (3 cols) | 35 (w1) | −4 B (~0%) | **pior** (140329 vs 138747) |

Dois regimes, ambos ruins: união cruza 94 → índice dobra (+100%); união ≤94 → dedup ~0 →
empate textual **e pior sob brotli** (o dict global quebra a localidade que o brotli explorava).

## Veredito B1 — `CLOSED-INSUFFICIENT-OVERLAP` para o 0.8 (recomendação)

- **Cross-dict intra-blob NÃO paga em dado tabular real** (entidades de domínio disjunto):
  melhor caso empate textual / leve perda sob brotli; pior caso +100%. Zero datasets ≥15% → falha
  o gate de bytes.
- **A porta estrutural (lazy) também não abre**: com colunas disjuntas, um dict global força ler
  TODAS as entradas pra consultar 1 coluna — pior que a seletividade per-column do `tcf.view`.
- **O ganho real (E1/E3) exige a forma "muitas colunas compartilhando um vocabulário pequeno"**
  (matrizes de flag/survey, 0/1, SIM/NÃO) — **ausente** nos canônicos; nicho específico.
- **O sharing forte é cross-TABELA** → seria outra feature (modo multi-tabela com dict
  compartilhado), escopo maior e API diferente → candidato a **0.9+**, não 0.8.
- Anti-incidente 2026-05-21: sintético (construído com sharing) mostrou que CAN ganhar; real
  (single-table) mostra ~0 overlap → não generaliza, **diferença explicada** (domínios disjuntos;
  sharing é cross-tabela). Passa o checklist como refutação honesta.

## Etapa 3 — o NICHO flag/survey (testado a pedido do owner)

O único caso onde cross-dict intra-blob ganha é "muitas colunas compartilhando vocabulário
pequeno" (matriz de flags/survey). Ausente nos canônicos; sintetizado modelando uma forma REAL
(questionário/voting-records/feature-flags). Sweep C×N, vocab {SIM,NÃO} e {y,n,?}. Script:
[`etapa3_niche.py`](etapa3_niche.py).

| vocab | C×N | net% textual | **net% brotli** | veredito |
|---|---|---|---|---|
| SIM/NÃO (2) | 8×200 | −4.2% | **−34.7%** | ganha (escala pequena) |
| SIM/NÃO (2) | 16×2000 | −0.5% | **+3.6%** | **perde** |
| SIM/NÃO (2) | 32×2000 | −0.5% | **+22.9%** | **perde feio** |
| y/n/? (3) | 16×200 | −3.6% | −6.1% | ganha (sub-gate) |
| y/n/? (3) | 32×2000 | −0.4% | −5.1% | ganha (sub-gate) |

**Leitura**: a economia é só a TABELA deduplicada (poucos bytes/coluna); o STREAM (o grosso) é
idêntico em V0 e V1. Logo o ganho textual é sempre pequeno (≤4.6%) e **encolhe com N**. Sob brotli:
- **2 valores**: instável — ganha em escala pequena, **regride em escala** (+22.9% em 32×2000),
  porque o brotli já modela bem o per-column e o índice global concatenado perde localidade.
- **3 valores** (voting-records-like): ganha consistente mas **≤6%, sub-gate**. Um exemplar real
  (UCI Congressional Voting Records, 435×16, y/n/?) cairia neste regime (~−5% brotli) → não muda o veredito.

**Mesmo no nicho que foi construído pra ganhar, nenhum regime atinge o gate de 15%**; o 2-valores
chega a regredir sob brotli em escala. A porta estrutural (lazy) também é marginal aqui (dicts
per-column já são triviais, 2-3 entradas).

## CORREÇÃO METODOLÓGICA (owner, 2026-06-21) — brotli NÃO é critério de exclusão

O veredito anterior gateava em brotli. **Errado** (owner): (1) brotli nem sempre é aplicado no
processo real; (2) **brotli é incompatível com lazy** — não dá pra `count`/`group`/`where` seletivo
sobre um blob comprimido sem descomprimir tudo. Avaliar uma feature lazy/paralela sob brotli é medir
na quadra do compressor. Alinha com a memória `gzip não é TCF — sinal qualitativo, não critério de
descarte` e com a filosofia (TCF ocupa a área explicável/lazy, não compete com brotli). **Os números
brotli acima ficam como sinal qualitativo, NÃO como gate.** A coluna que vale é a **textual** + as
**capacidades TCF-nativas (paralelismo, lazy counts/groups/filtros)**.

### O que se sustenta SEM brotli (textual + estrutura)

- **Dado real disjunto (adult)**: cross-dict GLOBAL FLAT (V1) = **+100% textual** (união 102 cruza 94
  → width 1→2). Isso é real independente de brotli. **MAS** o modo **híbrido V2** (dicts por grupo)
  NÃO pool colunas disjuntas → degrada pra V0 (sem perda). Então a conclusão correta é: **V1 naive é
  ruim em entidade; V2 não piora**. Falta ver se V2 AJUDA.
- **Nicho flag/survey**: ganho textual pequeno (≤4.6%, encolhe com N) — porém é a TABELA dedup; o
  stream é igual. Falta a dimensão que importa: **lazy/paralelismo**.

## Etapa 4 — teste TCF-nativo (textual + paralelismo + lazy, SEM brotli)

Script: [`etapa4_lazy_parallel.py`](etapa4_lazy_parallel.py). N=2000. Métricas: textual, prelúdio
serial (paralelismo), lazy bytes-tocados + dict-decodes (single-col e cross-col).

| cenário | C, K_global | textual | prelúdio V1 | lazy single-col | lazy cross-col |
|---|---|---|---|---|---|
| (a) flags full-share K=2 | 16, 2 (w1) | −0.5% | 10 B | igual | bytes ~igual; **decodes 16→1** |
| **(b) same-domain refs K=300** | 3, 300 (w2) | **−19.2%** | 1580 B | ~igual (5580 vs 5575) | **−19%** + **decodes 3→1** |
| (c) partial-share | 4, 100 (w2) | +78.3% | 524 B | **V1 pior** (4524 vs 2325) | pior |
| (d) disjunto/entidade | 6, 240 (w2) | +91.2% | 1383 B | **V1 pior** (5383 vs 2207) | pior |

**Leitura**:
- **(b) é o caso-uso real e GANHA**: colunas que referenciam o MESMO domínio (origem/conexão/destino;
  de/para; source/target; FK repetida) compartilham um vocab grande intra-blob → cross-dict dedup a
  tabela (−19.2% textual, limpo) e o lazy cross-col lê o dict **1× em vez de C×**. Cruza o gate de 15%
  **em textual puro** — sem depender de brotli.
- **(a) flags**: marginal (vocab trivial; o único ganho é dict-decodes 16→1, mas cada decode é de 2
  entradas). Não justifica sozinho.
- **(c)/(d) perdem**: união cruza 94 e/ou pouco overlap → V1 infla textual E **piora a selectividade
  lazy single-col** (precisa ler a tabela global inteira pra 1 coluna). São exatamente os casos que o
  **híbrido V2** evita: não pool colunas sem overlap forte → degrada pra V0 (per-column), sem perda.

## Veredito B1 (corrigido) — cross-dict PAGA no regime same-domain-refs; seguir pro híbrido V2

1. **Existe caso-uso real e gate-clearing**: same-domain reference columns (−19.2% textual + lazy
   cross-col). É uma forma de tabela comum (voos origem/destino, transações de/para, grafos
   source/target, qualquer tabela com 2+ colunas FK pro mesmo domínio).
2. **O híbrido V2 é essencial**: pool só grupos com overlap forte (Jaccard alto, vocab compartilhado);
   colunas disjuntas/parciais ficam per-column (V0) → captura o ganho de (b) sem a perda de (c)/(d).
3. **Brotli não é gate** (correção owner): é incompatível com lazy e nem sempre aplicado; o ganho
   textual + lazy é o que vale.
4. **Lacuna pro gate empírico**: os canônicos (adult/tpch/receita = tabelas de entidade) **não têm**
   colunas same-domain-ref. Pra fechar ≥2 reais, precisaria de dataset com essa forma (rotas de voo
   origem/destino, edge-list de grafo, transações de/para). O mecanismo está provado (sintético em
   escala); falta a magnitude em vocab real.

→ **Recomendação**: NÃO fechar. Cross-dict (modo híbrido V2, opt-in `#TCF.8`) tem mérito no regime
same-domain-refs. Próximo: (i) achar/adicionar ≥2 datasets reais com same-domain refs; (ii) medir V2
neles (textual + lazy); (iii) se confirmar, B2 design. Decisão de escopo (0.8 vs 0.9): owner.

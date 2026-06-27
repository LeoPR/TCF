# Re-segmentação — 5 workstreams (separação de concerns) [decisão de organização]

**Data**: 2026-06-27. **Tipo**: decisão de organização (owner confirmou). Origem: brainstorm do
owner conectando o B2 (cross-dict) a temas maiores (paralelismo, binarização, linguagem de spec,
posicionamento). Aterrissado no que o repo JÁ mediu (3 explorações read-only). Separa cinco frentes
que estavam emaranhadas.

## Os 5 workstreams

| # | workstream | o que é | estado | onde vive |
|---|---|---|---|---|
| **W1** | **Cross-dict same-domain** | dict de grupo no header p/ colunas que referenciam o mesmo domínio (email1/2, telefone1/2, grafo source/target, FK repetida) | B2 design (em revisão) | #TCF.8, 0.8/0.9 |
| **W2** | **Binarização por nature** | coluna bool/categórica → bits (8 bools/byte = 8×); a spec é o **dict implícito** ({false,true} não armazenado) | NOVO (era colado em W1) | V2-L (ADR-0018) + nature `bool` |
| **W3** | **Decode paralelo + lazy multi-col** | header-share → colunas independentes; filtro multi-col especulativo + intersect + count/sum | design (hquery01) | 0.9 / V2-J |
| **W4** | **TCFL — linguagem de spec + auto-tune** | DSL compila spec + (futuro) expressa check-digit/segment/compose; harness de pré-teste decide pipeline | compilador FEITO (F1); expressivo+auto-tune NOVO | gadget `scripts/natures_compiler/`, não-core |
| **W5** | **Posicionamento / value-prop** | re-pesar "legível" ↔ "estrutural (O(1)/lazy/assíncrono/paralelo)" | discussão | README/CLAUDE.md filosofia |

## A chave da re-segmentação: W1 ≠ W2

Estavam colados ("s/n são candidatos a cross-dict"). **Medido (B1 etapa3,
[result.md](../2026-06-21-gdict-caracterizacao/result.md))**: cross-dict de s/n dá ≤4.6% textual e
REGRIDE sob brotli (a tabela é minúscula; o stream domina). **Cross-dict de s/n NÃO paga.** O ganho
de s/n está em **W2 (binarização, 8×)** — mecanismo distinto. Separar libera os dois: W1 fica só
same-domain (ganho real medido), W2 ataca bool/categórico por bits.

## Intuições do owner que bateram com o que já temos (grounding)
- **"email1/2, telefone1/2 = característica próxima"** = same-domain-refs do B1 (Jaccard alto = paga,
  SNAP −19.3%). São mais exemplos pro gate N≥5 do W1.
- **"encode serializado descobre dict e vê se o próximo reaproveita"** = o particionamento greedy
  custo-modelado do B2 (W1), formalizado.
- **"dicts no header facilitam decode paralelo"** = correto; o **prelúdio-de-header do B2 é o
  pré-requisito** (lê 1×, colunas independentes). Decode paralelo em si é W3 (substrato é futuro:
  view.py tem lazy L1-L5 implementado, mas paralelismo-por-coluna é plano 0.9 / V2-J defer-v2.0).
- **"TCFL que avalia e compila spec"** = JÁ EXISTE em embrião: `scripts/natures_compiler/` (F1 feito
  2026-06-16, compila `.dsl`→spec com round-trip de 64 amostras). O expressivo (check-digit no DSL) +
  auto-tune (testar pipeline numa base modelo) são extensões — ver ressalva no
  [filtros-dsl-plano.md](filtros-dsl-plano.md) §F5.
- **"fácil de ler vs O(1)/lazy/paralelo"** (W5): NÃO são rivais. A forma textual-estruturada é **o que
  habilita** o lazy/O(1)/paralelo (fatiar/escanear o texto sem descomprimir). "Inspecionável" e
  "consultável sem descomprimir" são a mesma propriedade por dois ângulos. Reposicionar = "a estrutura
  legível É o que dá as propriedades estruturais", não largar o pilar.

## Impacto imediato no B2 (W1)
- **Estreita o B2 a same-domain puro**; s/n sai do B2 → W2.
- **Gate N≥5** (owner confirmou): rotas/grafo/de-para/FK/email1-2/telefone1-2.
- **brotli/gzip = CONTROLE padronizado** (owner): sempre reportar como referência, nunca gate
  pass/fail. Definir o protocolo (vale pro projeto).

## Próximo
- (a) Registrar (este doc) + aplicar correções A-D da [revisão](../2026-06-21-gdict-caracterizacao/design-b2-revisao.md)
  no B2 já estreitado a same-domain.
- (b) Mapear a literatura JÁ baixada por workstream (W1 cross-column dict/Parquet-Abadi; W2
  bitpacking/roaring; W3 late-materialization/predicate-pushdown; W4 schema-on-read/DSL de tipos) —
  o que temos vs o que falta — antes de puxar mais.

## Cross-links
[fila-estudos-tcf8.md](fila-estudos-tcf8.md), [tcf8-estrutura-plano.md](tcf8-estrutura-plano.md),
[design-b2.md](../2026-06-21-gdict-caracterizacao/design-b2.md) + [revisão](../2026-06-21-gdict-caracterizacao/design-b2-revisao.md),
[filtros-dsl-plano.md](filtros-dsl-plano.md) (W4), ADR-0018 (W2/W3 V2-L/V2-J).

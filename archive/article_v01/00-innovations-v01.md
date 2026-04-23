# Inovacoes Teoricas do TCF

Este arquivo registra as inovacoes teoricas **comprovadas por experimentos**.
Atualizado conforme resultados sao confirmados.
Separacao clara: inovacao (o que funciona) vs tentativa (registrada em TESTS.md/TICKETS.md).

---

## I1: Formato Columnar para LLMs (comprovado E1+E2)

**Inovacao:** Primeiro formato columnar textual proposto para consumo por LLMs.
Toda a literatura usa formatos row-oriented (CSV, JSON, Markdown, HTML, NL).

**Evidencia:** TCF e 3-6x menor que JSONL em todos os cenarios testados (C1).
Encode/decode e reversivel para todas as variantes (7/7, Phase 0).

**Base teorica:** Orientacao columnar elimina repeticao de nomes de campo
(O(K) vs O(N×K) em JSONL). Compressao proporcional ao numero de colunas.

---

## I2: RLE como Compressao Natural para LLMs (comprovado E2)

**Inovacao:** Run-Length Encoding (RLE) aplicado a colunas sorted como
compressao textualmente interpretavel. `7:1 3:2` e legivel por humanos e LLMs.

**Evidencia:** RLE 10-40x eficiente com FK repetitiva (C3).
1000 vendas com 30 clientes → 33x compressao na coluna pessoa.

**Base teorica:** RLE e a compressao textual mais simples que preserva
legibilidade. Alternativas possiveis a investigar:

| Tecnica | Descricao | Legivel? | Compressao | Status |
|---------|-----------|----------|------------|--------|
| **RLE** | `N*val` | Sim | Alta com repeticao | **Implementado** |
| Delta encoding | `base + deltas` | Media | Boa para sequencias | A investigar |
| Dictionary refs | `@1=Ana, @2=Bruno; @1 @2` | Sim | Boa para strings | Parcial (DICT mode) |
| Frequency prefix | `val(N)` ao inves de `N*val` | Sim | Igual ao RLE | Alternativa notacional |
| Bitmap | `1100110` para presenca/ausencia | Nao | Alta para booleanos | Nao para LLMs |
| Elias gamma | Codificacao de inteiros | Nao | Otima para inteiros | Nao para LLMs |

**Criterio para compressao LLM-friendly:** deve ser **textual**, **legivel**,
e **explicavel em 1 linha** no header. RLE atende perfeitamente.
Delta encoding e dictionary refs sao candidatos para investigacao futura.

---

## I3: Diagnostico 3-Layer (comprovado E3, F6)

**Inovacao:** Separar capacidade aritmetica (math_control), compreensao
de formato (decode_only) e capacidade computacional (compute) em 3 camadas.

**Evidencia:** math_control separa modelos em 2 classes binarias:
100% (gpt-oss, qwen3) vs 0% (todos os outros). Isso prova que accuracy
< 50% nos modelos fracos NAO e culpa do formato — e falta de capacidade
aritmetica basica.

**Base teorica:** Metodologia inspirada em ablation studies de ML.
Isolar variaveis para atribuir causalidade corretamente.

---

## I4: FK Mode Ablation (comprovado E4, F8)

**Inovacao:** Primeira ablacao sistematica de representacao de FK
dentro de um formato de serialization.

**Evidencia:** dict mode (67%) SUPERA JSONL (63%).
qwen3 com raw_float/dict/True atinge 100%.
FK mode e o 2o fator mais impactante (+6pp), atras de numeric (+24pp).

**Base teorica:** O bloco DICT fornece contexto semantico que permite
ao modelo resolver IDs para nomes sem cross-reference entre tabelas.

---

## I5: Stats como Hints Pre-computados (comprovado E5, F12-F14)

**Inovacao:** Incluir estatisticas pre-computadas (sum, avg, min, max)
no header TCF como hints gratuitos para a LLM.

**Evidencia:** Stats melhoram accuracy global em +12pp.
Para questoes de aggregate direto (sum, avg): +33 a +67pp.
MAS para questoes FK-dependentes: -11 a -22pp (PIORA).

**Base teorica:** Stats funcionam como "cola" — o modelo le a resposta
ao inves de calcular. Util para aggregates globais, CONTRAPRODUCENTE
quando o modelo precisa raciocinar sobre subgrupos.
Stats globais confundem o raciocinio per-group.

**Implicacao:** Stats devem ser seletivos — emitir apenas para metricas
que o usuario quer confirmar, nao para tudo indiscriminadamente.

---

## Inovacoes Pendentes (a comprovar)

| ID | Inovacao | Status | Grupo |
|----|----------|--------|-------|
| I6 | Supertable (JOIN desnormalizado) | A implementar | G03b |
| I7 | Agrupamento pre-encoding (GROUP BY) | A testar | G10 |
| I8 | PoT+Verify (LLM gera script de verificacao) | A testar | G11 |
| I9 | Text-to-Insight (narrativa analitica) | A testar | G11 |
| I10 | Arredondamento inteligente (smart precision) | A investigar | G13 |
| I11 | Compressao alternativa ao RLE (delta, dict refs) | A investigar | Pesquisa |
| I12 | Perguntas progressivas | A testar | G06 |

---

## Tecnicas Alternativas de Compressao Textual (I11)

Alem do RLE, outras tecnicas podem ser LLM-friendly:

### Delta Encoding
```
Original: vl: 2.5 2.7 2.9 3.1 3.5
Delta:    vl: 2.5 +0.2 +0.2 +0.2 +0.4
```
Vantagem: comprime sequencias monotônicas. A LLM ve tendencia diretamente.
Desvantagem: erro acumulativo se LLM errar um delta.

### Dictionary References
```
## DICT @A=Ana @B=Bruno @C=Caneta @D=Caderno
pessoa: @A @B @A @C
produto: @C @D @C @D
```
Vantagem: comprime strings longas. Ja implementado parcialmente (fk_mode=dict).
Extensao: aplicar a TODAS as colunas de texto, nao so FKs.

### Run-Length + Value Encoding
```
Original: status: OK OK OK WARN OK OK ERROR OK OK OK
Atual RLE: status[sorted]: 7:OK 1:ERROR 2:WARN  (perde ordem)
Proposta:  status: 3:OK WARN 2:OK ERROR 3:OK    (preserva ordem!)
```
Extensao do RLE atual: aplicar RLE na coluna RAW (nao sorted).
Preserva ordem posicional E comprime.

### Conclusao sobre alternativas

RLE e a melhor primeira opcao porque:
1. Simples de explicar em 1 linha (`N*val = val repeated N times`)
2. LLMs ja entendem (confirmado por Phase 1+2)
3. Eficiente com dados categoricos (FK, status, etc)

Delta encoding e RLE-na-ordem sao candidatos para Phase 3+ (escala).
Dictionary refs global ja esta parcialmente implementado (DICT mode).

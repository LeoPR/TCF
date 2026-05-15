# Perspectiva tríplice + estratégias de pré-tx

**Data**: 2026-05-17
**Tipo**: nota teórica (analise critica + direcoes)
**Origem**: revisao critica do user em 2026-05-17 do estado atual
(OBAT + HCC consolidados em src/tcf) com 3 estrategias de evolucao.

## A perspectiva tríplice do algoritmo

Qualquer algoritmo de compressao tem 3 vetores ortogonais que
precisam ser avaliados em conjunto, nao isoladamente:

1. **Compressao** — quantidade de bytes economizados
2. **Memória** — pico de uso durante encode/decode
3. **Latência** — tempo entre input e output (especialmente
   importante em modos streaming/batch híbrido)

### Estado v0.6 atual

| Vetor | Status | Gap |
|---|---|---|
| Compressao | bem caracterizado (54.2% ratio D1-D9) | — |
| Memoria | apenas algebrico (O(N) Counter, listas) | `tracemalloc` nao rodado em escala |
| Latencia | apenas estrutural (HCC batch, OBAT online em principio) | sem detector online; freeze-and-emit ausente |

**Critica**: o desenvolvimento dirty (M0-M14) focou compressao.
Memoria e latencia sao especulativas. Quando v0.6 evoluir para
multi-coluna + escala, esses vetores tornam-se críticos.

## Estratégia 1 — Pré-filtro: schema + tipos notáveis

### 1.A) Encoder/decoder de tipos estruturados

Tipos com **estrutura conhecida e fixa** podem ser detectados e
codificados de forma especializada antes do OBAT:

- **CPF**: `XXX.XXX.XXX-XX` — 11 digitos + 3 separadores. Bytes
  bruto: 14. Representacao compacta: 11 digitos = 44 bits = 6 bytes.
- **UUID**: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` — 32 hex + 4 hifens
  = 36 bytes. Bytes bruto compacto: 16 bytes (binario) ou 32 base32.
- **IP v4**: `X.X.X.X` — variavel mas 4 numeros. Compacto: 4 bytes
  binario.
- **Datas ISO**: `YYYY-MM-DD` — 10 bytes textual. Compacto: 4 bytes
  ou delta vs base.

Cada tipo vira par `encoder/decoder` (note o **r** final em ambos
— sao funcoes bidirecionais que preservam roundtrip).

### 1.B) Schema-based segmentation

Le DB schema (`metadata.json`), particiona dados em colunas,
**dispatch para instancias TCF independentes** por coluna. Pode
usar tipos da estrategia 1.A por coluna.

### Maturidade

- Estrategia 1.A: bem caracterizada na literatura
  (representacao binaria de tipos estruturados). Implementacao =
  engenharia direta. Risco baixo.
- Estrategia 1.B: ja' no roadmap (item 1 "migracao + multi-coluna").
  Engenharia. Risco baixo-medio.

### Relacao com TCF-CORE atual

Estrategia 1 e' **ortogonal** ao OBAT/HCC. OBAT recebe strings ja'
pre-filtradas. HCC ja' funciona naturalmente.

## Estratégia 2 — Manager com memória shared + sincronização

### Problema

Multi-coluna ingenuo: cada coluna instancia seu proprio OBAT+HCC.
Memoria cresce linear com numero de colunas, sem aproveitar
overlaps potenciais entre colunas (ex: coluna "data_cadastro" e
coluna "data_atualizacao" tem strings similares "2026-...").

### Proposta

**Manager** acima das instancias TCF coordena:

1. **Memoria shared**: nos detectados em uma coluna sao **visiveis** a
   outras. Se coluna A detecta "2026-05" como reusavel, coluna B
   pode usar diretamente.
2. **Sync via "freeze + continue"**:
   - Online: trees crescem com dados chegando
   - Quando batch entrega exigida: trigger composicao, freeze tree
     ao estado atual, emit, continuar online
   - Latencia previsivel: budget de tempo dispara freeze
3. **Coordenacao de memoria**: budget global; manager decide quais
   trees podam (descartam nos antigos) quando memoria estoura

### Análogos na literatura

- **Apache Arrow** — shared memory cross-language para data exchange
- **Kafka streams + watermarks** — sync de delivery em stream
  processing
- **DB shared scans** — multiplas queries reaproveitam mesmo scan
- **Spark RDD caching** — memoria compartilhada entre transformacoes

### Concerns

1. **Concorrencia**: locks vs lock-free. Single-thread serializado
   pode bastar pra v0.6 inicial.
2. **Watermark semantics**: gatilhos de freeze — tempo? bytes?
   linhas? Hibrido?
3. **Cross-column node sharing**: precisa indexar nos por conteudo
   (hash de subseq?). Custo de lookup vs ganho de share.

### Maturidade

100% teorica. Implementacao requer design nao-trivial. **Risco alto.**
Talvez justifique experimento separado (EXP-008 ou M15 dedicado).

### Relacao com TCF-CORE atual

Estrategia 2 e' **camada acima** do OBAT/HCC. Cada instancia continua
single-column. Manager coordena. Nao requer modificar OBAT/HCC
no nucleo.

## Estratégia 3 — Detecção de slot pattern online

### Problema

D9 (`@@@KEY=value-xN@@@`) tem 7 linhas com pattern `17,X,5` onde
X varia. HCC atual emite linha completa cada vez:
```
17,9,5
17,10,5
17,11,5
...
```

Custo: 7 linhas × ~6 chars = ~42 bytes para esse bloco.

### Proposta — duas posicoes

#### 3.A) OBAT-level: anti-unificacao

Durante tokenizacao, OBAT reconheceria que `s_i` matches `s_{i-1}`
EXCETO em uma posicao. Trataria como template + slot:
```
[atom-prefix] [SLOT] [atom-suffix]
```
onde SLOT e' o trecho variavel.

**Conexao com literatura**: este e' o problema de
**anti-unificacao** em programacao logica (Plotkin 1970, Reynolds
1970). Encontrar termo mais especifico que generaliza dois termos
dados (lggu — least general generalization).

**Custo**: re-arquitetar OBAT. Hoje OBAT compara so' LCP+LCS de
extremidades; anti-unificacao exige busca por **diferenca interna**.

#### 3.B) HCC-level: detector online com janela de pattern

HCC atual e' batch (analisa body completo antes de decidir).
Versao online manteria janela deslizante de N linhas recentes e
detectaria padroes `(estavel, X, estavel)` incrementalmente.

**Custo**: menor que 3.A. HCC ja' opera em tokens; estender pra
detectar template-com-slot e' algoritmico mas tratavel.

### Conexao com nota `no-funcional-marca-e-troca.md`

A nota
[`no-funcional-marca-e-troca.md`](no-funcional-marca-e-troca.md)
ja' discute sintaxe (`no19=17,?=9,5` etc.) e custo algebrico para
slot pattern. Esta nota agora SUBSUMES aquela em escopo — slot
detection deveria ser **online** (durante encode), nao apenas
sintatico.

### Maturidade

- 3.A (OBAT-level): teorica + ambiciosa. Talvez M16+ ou prototipo
  dedicado. **Risco alto.**
- 3.B (HCC-level): teorica mas tratavel. Caminho mais direto.
  **Risco medio.**

## Interacao entre as 3 estratégias

```
[Dados brutos tabulares]
         ↓
[Estrategia 1.B: schema parser] → particiona em colunas
         ↓
[Estrategia 1.A: type-aware pre-tx] → CPF/UUID/etc. → bytes compactos
         ↓
[Estrategia 2: manager] ←→ memoria shared, freeze+continue
         ↓
[OBAT + HCC + Estrategia 3 (slot detection)] por coluna
         ↓
[Texto TCF final]
```

Cada estrategia e' **ortogonal** as outras — podem ser implementadas
isoladamente. Mas o ganho combinado e' multiplicativo:
- Estrategia 1 reduz **bytes** em colunas estruturadas (CPF/UUID)
- Estrategia 2 reduz **memoria** em multi-coluna e melhora **latencia**
  via freeze
- Estrategia 3 reduz **bytes** em colunas com padroes slot

## Roadmap implicito (atualizado)

Em ordem de impacto vs custo:

1. ✓ DONE: OBAT + HCC welded em src/tcf
2. ✅ **CURTO**: Estrategia 1.A (type encoders simples — CPF, UUID,
   data ISO). Engenharia direta. Pode mostrar -30%+ em datasets
   com IDs estruturados.
3. ✅ **CURTO**: Estrategia 1.B (multi-coluna ingenuo: instancias
   independentes). Sem otimizacao cross-column. ~1 semana.
4. ⚠ **MEDIO**: Estrategia 3.B (HCC online com slot detection).
   Resolve D9-tipo padroes. Algoritmico.
5. ⚠ **LONGO**: Estrategia 2 (manager + shared memory + sync).
   Sistema. Talvez EXP-008 dedicado.
6. ⚠ **LONGO**: Estrategia 3.A (OBAT-level anti-unificacao).
   Re-arquitetar tokenizer.

## Triple perspective ao longo das estratégias

| Estrategia | Compressao | Memoria | Latencia |
|---|---|---|---|
| 1.A type encoders | ↑↑ (em colunas estruturadas) | neutro | neutro |
| 1.B multi-col ingenuo | ↑ (multiplica por colunas) | ↓↓ (cada inst. cresce) | neutro |
| 2 manager shared | neutro | ↑↑ (compartilha nos) | ↑↑ (freeze previsivel) |
| 3.B slot online | ↑ (datasets slot-pattern) | ↓ (janela deslizante) | neutro |
| 3.A anti-unification | ↑↑ (mais agressivo) | ↓ | ↓ (mais busca) |

**Conclusao critica**: as 3 estrategias **complementam** os 3 vetores
da perspectiva triplice de formas diferentes. Estrategia 2 sozinha
nao reduz bytes — mas e' essencial pra memoria/latencia escalavel.
Estrategias 1 e 3 reduzem bytes mas sem cuidado com memoria
podem inflacionar.

## Conexoes

- [`roadmap-hipoteses.md`](roadmap-hipoteses.md) — lista geral de hipoteses
- [`comparacao-modular-camadas.md`](comparacao-modular-camadas.md) — pre-tx layers (extends Estrategia 1)
- [`no-funcional-marca-e-troca.md`](no-funcional-marca-e-troca.md) — slot pattern (subsumido por Estrategia 3)
- [`2026-05-11-tipos-com-estrutura.md`](2026-05-11-tipos-com-estrutura.md) — tipos estruturados (precursor Estrategia 1.A)
- [`vetores-de-comparacao-alem-de-bytes.md`](vetores-de-comparacao-alem-de-bytes.md) — vetores alem de bytes (precursor perspectiva triplice)
- `../algorithms/OBAT.md` — camada 1 atual
- `../algorithms/HCC.md` — camada 2 atual
- `../algorithms/TCF-format.md` — formato + posicionamento

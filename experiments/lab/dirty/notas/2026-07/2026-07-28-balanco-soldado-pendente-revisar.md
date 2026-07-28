# Balanço 2026-07-28 — o que foi soldado, o que falta soldar, o que falta revisar

Fechamento do ciclo que começou em 2026-07-24 (fail-loud) e terminou em 2026-07-27 (bN de
domínio). Estado: **suíte 1042 passed, 3 skipped**; gates **D1-D9 1545 · D17a 300 ·
real-world 89430**.

O próximo tema é **float**, mas há coisas antes dele. Este documento separa as três pilhas.

---

## 1. SOLDADO — está no `src/tcf`, com teste e gate

| # | o quê | onde | efeito medido |
|---|---|---|---|
| 1 | **Fail-loud no corpo do core** — 5 sítios + guard de progresso | `syntax.py` | achou loop infinito real (`*~2`); `^0` corrompia calado |
| 2 | **`max_length`** — teto de descompressão | `syntax.py`, `decoder.py` | `MAX_LENGTH_PADRAO = 10M`, override no `decode` |
| 3 | **Header default 100%** (ADR-0034) | `encoder.py` | +7 B/artefato; o arquivo passa a se auto-explicar |
| 4 | **`null` no slot 0 pré-alocado** | `syntax.py` | `0` cru = null; wire de coluna sem null **byte-idêntico** |
| 5 | **Rota tipada generalizada** — tags `b`/`n` | `encoder.py`, `decoder.py` | int/float saíram do `.8H`; tipo preservado |
| 6 | **FLOOR do seq-RLE** | `hcc_seqrle.py` | o marcador `*N±d\|` só entra se encolher |
| 7 | **Delimitador de POLARIDADE** (ADR-0035) | `composicional/polaridade.py` | 1 B por **transição**, não por literal. D1-D9 −41, real-world −207 |
| 8 | **bN de DOMÍNIO** (ADR-0036) | `composicional/dominio_bn.py` | densidade por **cardinalidade**: `['0','1']*100` **609 → 54 B**. Nenhum gate moveu |

**Suíte foi de 861 → 1042.** Dois ADRs novos (0035, 0036), dois arquivos novos de teste
(`test_polaridade.py` 32, `test_dominio_bn.py` 32).

### Invariante que emergiu (custou 4 bugs)

> **Toda estrutura que grafa valores ao lado do slot nulo tem de usar a grafia do core e
> desfazer exatamente o que fez, nem mais.**

Apareceu no weld do slot 0, no lab `2126` (a string `"0"` virando `None`), no `1608` (domínio)
e no `2231` (`\temp` virando `temp`). Hoje tem teste em `test_dominio_bn.py`.

---

## 2. FALTA SOLDAR — ganho medido, esperando encaixe

Ordenado por **custo de entrada**, não por ganho. Os quatro primeiros são **byte-neutros** —
não re-pinam gate nenhum, então são os candidatos naturais para abrir o `.9`.

### 2a. Byte-neutros (só CPU) — não mexem em nenhum baseline

| ticket | o quê | onde encaixa |
|---|---|---|
| `T-POLARIDADE-FUSE` | fundir a varredura da polaridade no laço que `_escape_lit` **já roda** | `syntax.py:173-193` |
| `T-GATES-ANTES` | avaliar os gates C1-C7 **antes** de materializar candidatos do FLOOR | `multi/core.py:420-434` |
| `T-SEQRLE-INCREMENTAL` | janela de 2 em vez de re-varredura completa do texto emitido | `hcc_seqrle.py:310` |
| `T-OBAT-TRIGRAMA` | bucket por `min_len` em vez de `3` fixo | `core/online.py:115,141,219` |

### 2b. Mudam byte — precisam de re-pin e ADR

| ticket | ganho medido | por que ainda não |
|---|---|---|
| `T-BN-TIPADO` | **`bool + null`: 546 B → 92 B** | o wire `B` devolve **string**; a rota tipada tem de preservar o tipo. Exige tag no cabeçalho (`#TCF.8bB…`) — grafia nova |
| `T-BN-LOTE` | ~1 B/coluna | falta só o opt-in; o modo `C` **já é decodável** |
| `T-BN-LARGURA-VARIAVEL` | slots desperdiçados em `k` = 3, 5, 6, 7 | largura fixa arredonda pra cima; `k` = 2ⁿ é o caso justo |
| `T-BN-MULTICOL` | ver a decisão pendente do `STATUS.md` | escopo `.8M`, irmão mas diferente |
| `T-SPEC-L0L1` | detecção automática de spec (hoje **não existe**) | camadas L0 forma / L1 validade / L2 momento; **CPF é o piloto** |
| `T-FLOAT-SLOTS` | destrava NaN/±Inf | **é decisão de formato, não de código** — ver §3 |

### 2c. Registrados sem ticket ainda

- **`min_len` dinâmico** — medido: 5× CPU, e o OBAT é **online** (o vocabulário é semeado
  pelo 1º valor). Obstáculo estrutural, não falta de vontade.
- **Delimitador de polaridade como grafia canônica interna** — exigiria o seq-RLE localizar o
  dígito incrementável **pela polaridade** em vez de pelo escape. Aberto desde o lab `1913`.
- **`parallel=` aceito em silêncio na rota flat** — inconsistência de fail-loud, barata.

---

## 3. FALTA REVISAR — antes do float, e no float

### 3a. Precisa de DECISÃO sua (não de código)

| # | pergunta | por que bloqueia |
|---|---|---|
| **1** | **Qual a ordem canônica dos slots reservados?** `null` = 0, e depois? | Bloqueia NaN/±Inf, que hoje é **fail-loud**. É a única lacuna funcional real do float. Coluna float de dado real tem NaN (`beijing-pm25` usa `"NA"`) |
| **2** | O `repr` de float é **contrato de formato**? | O `str(float)` do Python é *shortest round-trip*. No port pra Rust do 1.0 isso vira contrato (Ryū/Grisu). **Não está escrito em lugar nenhum** |

### 3b. Não medido — merece 1 lab antes de mexer no float

| # | o quê | por quê |
|---|---|---|
| **3** | **polaridade × notação científica** | `1e20` vira `\1*e+\20` — o `e+` **parte a corrida de dígito**. É o único regime de float não medido |
| **4** | **gzip** sobre polaridade e bN | o estudo multi-col já registrou que o gzip **encolhe muito** o ganho do bN. Nossa métrica é byte cru |
| **5** | **CPU** dos dois welds | nenhum foi cronometrado. O `bench_perf` existe e está com a rodada probatória pendente |

### 3c. Escopo declarado que continua fora

- **`.8M` (multi-col)** e **`.8H` (hierárquico)** — nem polaridade nem bN entraram. O `D17a`
  inalterado é a evidência de que a solda ficou onde foi dita.
- **spec/nature** e **órfão (`stamp=False`)** — idem.
- **Modo denso e hierárquico por dentro** — são recusados por teste de 1 linha, nunca
  exercitados internamente pelos welds novos.

---

## 4. O que o float realmente precisa

Probe direto (RT pelo `decode` público comparando **valor, tipo e sinal**) mostrou que a tag
`n` **já cobre**: simples, integral, científica (`1e20`/`1e-7`), precisão máxima, `-0.0` com
sinal preservado, mistura int/float, e float+null. **Só `NaN` e `±Inf` caem em fail-loud.**

Então o float **não precisa de rota nova**. Precisa, nesta ordem:

1. **decisão §3a.1** (ordem dos slots reservados) → destrava NaN/±Inf
2. **lab §3b.3** (polaridade × científica) → o único regime não medido
3. **doc §3a.2** (contrato do `repr`) → dívida de port pro 1.0

Talvez um **spec/tipo próprio para float** dependendo do que a decisão 1 abrir — mas isso só
faz sentido depois de saber como NaN/Inf vão morar no formato.

---

## Onde cada coisa está registrada

- **tickets** com ganho medido: bloco no topo do [`STATUS.md`](../../../../../STATUS.md)
- **onde encaixar cada otimização**: [guia do `.9`](2026-07-27-guia-de-encaixe-para-o-dot9.md)
- **o pipeline que existe**: [mapa](2026-07-27-mapa-do-pipeline-e-o-que-falta-pro-float.md)
- **decisões de formato**: `docs/adr/0034`, `0035`, `0036`
- **evidência**: `experiments/lab/dirty/2026-07/2026-07-{24,25,26,27}/`

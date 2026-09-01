---
title: T-PERF-BORDAS-E-MODOS-09, as bordas do TCF e os modos de compressão (rápido × maior); o alvo do .9
status: open
priority: P1
created: 2026-08-23
updated: 2026-09-01
gate: ".9 (desempenho e limpeza) (triagem 2026-09-01)"
target: ".9 (otimização), este é o ticket-mestre do ciclo"
blocked-by: []
related:
  - experiments/lab/dirty/2026-08/2026-08-23/2026-08-23-0300-tempo-ate-o-dado-chegar/
  - experiments/lab/dirty/2026-08/2026-08-23/2026-08-23-0100-janela-massa-pos-release/
  - tickets/T-STUDY-USE-PROFILES.md
  - tickets/T-API-SCHEMA-PRESCRITIVO.md
  - scripts/bench_perf/README.md
  - docs/adr/0002-vertice-triplice-restricao.md
---

# T-PERF-BORDAS-E-MODOS-09

**[dispositivo → registro. Baseline medido; nada em `src/tcf` sem aprovação.]**

Abre o ciclo `.9` com **base medida** em vez de intuição. Direção do owner (2026-08-23), ao ver
os primeiros números de tempo-até-o-dado-chegar.

## O enquadramento do owner: as quatro delimitações

Ditas ao ver o primeiro resultado, e elas **mudam o que os números significam**:

1. **"o TCF tende a substituir volumes pequenos, mas quero estabelecer bordas para saber até
   onde vai"**, o alvo declarado é payload pequeno. Medir 500 mil linhas não é achar o regime
   de uso: é achar a **borda superior**. O objetivo do bench é o *até onde*, não o *quão bom*.
2. **"não otimizamos ainda no .9"**: todo número atual é de código deliberadamente
   não-otimizado. Serve de **ponto de partida**, não de conclusão sobre o formato.
3. **"o TCF é para multiclient, onde o servidor centralizado fará as descompressões com mais
   frequência, mas também pensar que o servidor dará respostas TCF"**, a topologia real é
   **1 encode : N decodes**, com o servidor nos dois papéis. Bench 1:1 **não representa** isso.
4. **"o TCF ainda nem foi testado com modos de compressão rápida, onde utiliza praticamente a
   busca e repetição"**, hoje só existe **um** modo, o mais caro. O eixo que mais mexe no
   break-even nunca foi exercitado.

## A base medida (2026-08-23, pré-otimização)

**O penhasco de encode não é volume, é característica do dado.** População completa, RT
validado em 6/6:

| caso | linhas | encode | decode | razão | ratio vs CSV |
|---|---:|---:|---:|---:|---:|
| adult | 48.842 | **3,3 s** | 0,33 s | 10× | 19,5% |
| lineitem | 60.175 | **475,3 s** | 0,58 s | **~800×** | 47,5% |
| orders | 15.000 | 25,7 s | 0,22 s | 117× | 61,9% |
| br empresas | 100.000 | **375,7 s** | 0,81 s | 464× | 32,2% |
| ibge | 5.571 | 5,8 s | 0,05 s | 116× | 30,9% |
| customer | 1.500 | 0,78 s | 0,06 s | 13× | 74,6% |

`lineitem` (60k) leva **143× mais** que `adult` (49k), mesma ordem de linhas. Consistente com a
probatória de 2026-08-20: **o eixo quente é CARDINALIDADE**, não linhas×colunas.

**Borda superior achada**: `br-identidades/pessoas` (500 mil linhas) consumiu **53 min de CPU e
1,2 GB** sem terminar, interrompido. Fica registrado como **limite prático do encode atual**.

**Bytes: o argumento se sustenta.** `tcf+brotli` é o menor no fio em todos os casos:
`adult` **2,3%** do JSON contra 4,5% do `json+brotli` (metade); ibge 4,6% vs 6,6%;
customer 18,0% vs 22,9%.

**Relógio: hoje não colhe.** Break-even do TCF contra JSON cru: **1,2 a 36 Mbps**, abaixo de
rede comum. O break-even é **linear no custo de CPU**: encode 10× mais rápido → ~360 Mbps
(vence em 4G e banda larga).

## O que o `.9` precisa produzir

### 1. Modos de compressão (o eixo nunca testado)

O owner: *"vamos testar versões de compressão rápida e maior"*. Hoje há **um** modo. Propostas
a caracterizar, cada uma com byte E tempo, sobre os mesmos casos:

| modo | ideia | hipótese |
|---|---|---|
| **rápido** | "praticamente só busca e repetição", sem a busca composicional cara do HCC | o grosso do ganho a uma fração do custo |
| **normal** | o de hoje | referência |
| **máximo** | busca exaustiva, sem os cortes atuais (`budget` de 99, top-K) | teto do formato |

O `T-BUDGET-DE-BUSCA` já registra que o único freio é um contador **fixo de 99, já saturado**:
é o parâmetro natural do modo rápido. O `T-PERFIS-MACRO` (`fast=true`) é a superfície de API, e o
`T-API-SCHEMA-PRESCRITIVO` é onde ela deve morar.

### 2. Bench com a topologia REAL (1 encode : N decodes)

O bench atual é 1:1 e **subestima** o TCF na topologia do owner. Refazer com N ∈ {1, 10, 100,
1000} leituras por escrita, que é o servidor central servindo clientes. A assimetria medida
(10× a 800× a favor do decode) só aparece assim.

### 3. As bordas, explicitamente

Onde o encode deixa de ser viável, por eixo: **cardinalidade** (o quente), linhas, colunas,
largura de valor. Entregar uma tabela de *"até aqui vai"*, que é o pedido literal.

### 4. Fechar o que a janela de massa não cobriu

Interrompida em `pessoas`: faltam **paralelismo byte-idêntico** fora do D17a e os combos
(`parallel × sort_by × drop_names`), buraco F3-3 declarado no T-QA-8, , **specs em volume**,
**curva de dimensionamento** e **`.8H`/tipado em massa**. Rodar com teto de linhas (~100k) pra
caber em tempo praticável.

## Critério de aceite

- [ ] Modo rápido caracterizado: byte e tempo vs o modo atual, nos mesmos casos
- [ ] Bench multi-cliente (1:N) com N ∈ {1, 10, 100, 1000}
- [ ] Tabela de bordas por eixo, com o eixo cardinalidade separado
- [ ] Break-even recalculado pós-otimização (o número que decide se o formato paga no fio)
- [ ] F3-3 (paralelismo + combos) fechado
- [ ] Nada de `src/tcf` sem aprovação; gates byte-canônicos verdes em toda mudança

## Não fazer agora

Otimizar. Este ticket **registra a base e o plano**; o `.9` executa.

---

## Pista aberta em 2026-09-01: o `.8H` pode ter andado para trás, e o controle é que diz

Ao estabelecer a base da `0.8.4` (`perf-nucleo-2026-09-01`), a comparação contra a rodada de
20/08 separou as famílias em direções opostas. Os caminhos de **referência** são `csv`/`json`
da stdlib, código idêntico entre as duas rodadas, então servem de controle: eles andaram
**−17,1%** em conjunto, o que mede o viés da normalização pelo calibrador, não ganho de
código. Contra esse controle, o `tcf-flat` fica em torno de **+16%** e o `tcf-8h` em torno de
**+47%**.

**Não é medição.** O `compare` recusou o par fail-closed (matriz e plano re-pinados em
`e46ef37a`), as duas rodadas estão termicamente suspeitas, e o desconto do controle é
aritmética sobre medianas. O que justifica registrar é o padrão: duas famílias em direções
opostas, separadas muito além do piso de ruído de 6,8%.

O que fazer quando este ciclo abrir, nesta ordem:

1. **Medir os dois lados no mesmo pino**, mesma máquina e mesma sessão térmica: `nucleo` sobre
   a tag `v0.8.4` e sobre o candidato. Só aí o `compare` aceita e o veredito vale. Sem isso,
   qualquer número daqui é conversa.
2. **Se confirmar**, o suspeito de primeira parada é o caminho `.8H`, que foi o que mais mexeu
   na janela (`R` soldado, FLOOR do spec corrigido cobrando `:<size>:<id>`), e não o
   `tcf-flat`.
3. **Se não confirmar**, o resultado ainda vale: fecha a dúvida e valida o método do controle
   por caminho de referência, que hoje só tem uma aplicação.

Detalhe e tabela por família em
[`perf-baseline/README.md`](../experiments/results/evidencia-0.8/perf-baseline/README.md).

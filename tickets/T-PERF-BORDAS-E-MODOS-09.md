---
title: T-PERF-BORDAS-E-MODOS-09, otimização multicamada, bordas e perfis; o alvo do .9
status: open
priority: P1
created: 2026-08-23
updated: 2026-09-14
gate: ".9 (desempenho e limpeza) (triagem 2026-09-01)"
target: ".9 (otimização), este é o ticket-mestre do ciclo"
blocked-by: []
related:
  - experiments/lab/dirty/2026-08/2026-08-23/2026-08-23-0300-tempo-ate-o-dado-chegar/
  - experiments/lab/dirty/2026-08/2026-08-23/2026-08-23-0100-janela-massa-pos-release/
  - tickets/T-STUDY-USE-PROFILES.md
  - tickets/T-API-SCHEMA-PRESCRITIVO.md
  - scripts/bench_perf/README.md
  - experiments/lab/dirty/2026-09/2026-09-01/2026-09-01-1937-perf-8h-dois-lados-mesmo-pino/
  - experiments/lab/dirty/2026-09/2026-09-07/2026-09-07-0208-perf-diagnostico/
  - docs/adr/0002-vertice-triplice-restricao.md
---

# T-PERF-BORDAS-E-MODOS-09

**[dispositivo → registro. Baseline medido; nada em `src/tcf` sem aprovação.]**

Orienta o eixo de desempenho da `.9` com base medida. Otimizar inclui rever o trabalho
realizado e seus caminhos, não somente acelerar a implementação atual.

## Direção: arquitetura primeiro, otimização em todas as camadas

**Direção do owner.** Investigar nesta ordem: **arquitetura e fluxo de dados → algoritmos
e estruturas de dados → implementação na linguagem → compiladores/runtime → linguagens
e bibliotecas auxiliares**. Em cada camada cabem reorganizar e melhorar o que existe,
revisar alternativas para a mesma tarefa e substituir a estratégia por outro caminho que
cumpra melhor o objetivo. A ordem vale por frente e admite retorno guiado pela medição;
não exige encerrar toda a arquitetura do projeto antes de experimentar um algoritmo.

Comparar **memória, velocidade, CPU, latência e compressão**, além dos custos pertinentes
à carga. Medir encode, decode e consultas conforme a topologia; uma diferença de tempo
entre encode e decode não exclui o mais barato da investigação. Preferir o caminho que
melhore algum eixo sem piorar os demais no regime medido. Quando houver trocas, manter
alternativas não dominadas e permitir seleção explícita por prioridade ou limite.
Roteamento por características dos dados é candidato, com custo e fallback medidos.

### Objetivo de uso e compromissos

O alvo da `.9` é melhorar ao máximo os caminhos que já funcionam, tanto na eficiência
algorítmica (crescimento do trabalho, estruturas e decisões) quanto na eficiência da
implementação, incluindo execução compilada. Nenhuma dessas dimensões substitui a outra.
Otimizar roteamentos inclui o custo de decidir: experimentar todos os caminhos para
escolher o menor arquivo pode contrariar o perfil de baixa latência.

A intenção de uso admite representações diferentes conforme a prioridade: filtros e
agregações rápidos sobre a estrutura comprimida, maior compressão, menor latência ou
menor memória. Uma representação mais compacta pode perder acesso seletivo; liberar
resultados cedo pode exigir mais trabalho total; economizar memória pode exigir
recomputação. Essas trocas são admissíveis quando explícitas e medidas no regime alvo.
Não se presume que toda melhoria tenha uma perda, nem que um caminho ganhe em tudo.

Streaming e estrutura naturalmente aproveitável como índice são objetivos de investigação,
ligados a O-FMT-08 e H-QUERY-04, não capacidades prometidas para toda representação.
Avaliar filtros e agregações por operação, seletividade, preparação e materialização,
incluindo o custo de produzir e manter qualquer estrutura auxiliar.
`O(1)` só pode descrever uma operação delimitada, com tamanho de entrada e preparação
declarados: decode que materializa uma saída de tamanho S exige ao menos trabalho
proporcional a S. Acesso a metadados ou agregado já disponível tem outro contrato.
Buscar caminhos melhores por perfil não constitui prova de ótimo global.

**Recorte da `.9`:** começar pela arquitetura e pelos caminhos existentes, comparar
trabalho algorítmico e explorar melhorias de compilação de baixo custo e esforço.
Entender plataforma, representação dos dados e backend antes de atribuir significado
a tempos ou ciclos. A medição final continua necessária, mas não substitui essa análise.
Mudanças caras de contrato, formato ou infraestrutura não entram automaticamente neste
ciclo por serem objetivos desejáveis: encaminhar à avaliação para 2.0, sem implementá-las
nem ampliar a rodada atual. Otimizações simples pertinentes à `.9` permanecem elegíveis.

Diagnóstico exploratório do instrumento: [controle de chamadas aninhadas](../experiments/lab/dirty/2026-09/2026-09-07/2026-09-07-0208-perf-diagnostico/01-instrumento/README.md)
(registro local). A cópia testada dos wrappers de `bench_perf.layers` não separou
profundidades no controle. Não usar seus buckets para atribuir custo principal versus
candidatos sem demonstrar mecanismo adicional; isso não invalida toda medição do harness.

Não escolher Rust, Cython ou um port completo antes de justificar a estratégia e seu
gargalo. Resultados de variantes encerradas continuam delimitados aos casos estudados;
não vetam outras arquiteturas ou algoritmos. H-PERF-01 a 06 e H-TH-02 são os registros
de investigação; H-PROFILE-01 rege os perfis. O-FMT-08 e O-FMT-20 conservam as frentes
de streaming e armazenamento. O plano operacional local é `tcf9-performance-plano.md`,
em `experiments/lab/dirty/notas/2026-09/`; este ticket conserva a direção e o aceite.

### Investigação antes da arquitetura

Literatura orientada por perguntas e diagnóstico experimental precedem a escolha do
desenho. Controles de backend podem entrar cedo para distinguir trabalho algorítmico,
custo de implementação e política de busca; isso não seleciona uma linguagem para o produto.

Propostas preliminares, tentativas, erros, descarte e reformulação ficam no
[caderno dirty de diagnóstico](../experiments/lab/dirty/2026-09/2026-09-07/2026-09-07-0208-perf-diagnostico/README.md)
(reservado no disco, fora do git). Sua sonda estrutural não é benchmark nem ganho validado.
Clean recebe apenas um candidato promissor sustentado por hipótese forte, contra-provas
e testes representativos, adaptado às conclusões e sujeito à regressão rigorosa.
Não se promove o conjunto de tentativas nem se incorpora automaticamente ao core.

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

- [ ] Arquitetura e algoritmos avaliados por frente, com hipótese, alternativas e teste que possa refutá-las; justificar manter ou substituir o caminho
- [ ] Implementação, compiladores/runtime e backends avaliados onde o custo justificar, sem linguagem escolhida por antecipação
- [ ] Comparação reproduzível de memória, velocidade, CPU, latência e compressão; ganhos, perdas, ruído e limites declarados por regime
- [ ] Caminho dominante identificado ou perfis não dominados caracterizados, com seleção explícita e custo do eventual roteamento
- [ ] Modo rápido caracterizado: byte e tempo vs o modo atual, nos mesmos casos
- [ ] Bench multi-cliente (1:N) com N ∈ {1, 10, 100, 1000}
- [ ] Tabela de bordas por eixo, com o eixo cardinalidade separado
- [ ] Break-even recalculado pós-otimização (o número que decide se o formato paga no fio)
- [ ] F3-3 (paralelismo + combos) fechado
- [ ] Nada de `src/tcf` sem aprovação; gates byte-canônicos verdes em toda mudança

## Limite de execução

Este ticket registra direção e critérios, não autoriza alteração do core. Aceleração
transparente preserva os bytes; estratégia que melhore compressão emitindo bytes diferentes
precisa de contrato e evidência próprios. Mudar default, pins, API ou gramática exige decisão
explícita, sem dispensar os gates. Round-trip é obrigatório antes de reportar resultados.

## Concordância da superfície `.8`

**Probatório: diagnóstico inicial, não aceite da etapa 1 nem baseline de desempenho.**
Antes de propor outra arquitetura, a execução e sua descrição precisam concordar.
No recorte conferido, os testes passam, mas a superfície ainda contém divergências.

### Referência examinada

- Checkout `85ee26e17e045123d5f702108a5468f38622fe59`; `git diff --name-only v0.8.4 -- src/tcf pyproject.toml hatch_build.py`
   sem diferenças. As alterações locais são documentais, não um candidato de implementação.
- Interpretador selecionado no editor: `.venv/Scripts/python.exe`, Python `3.13.13`.
   Import de `tcf` a partir de `src/tcf/__init__.py`, com `tcf.__version__ == "0.8.4"`.
- Detector Cython ativo, módulo `tcf._core.detect`; equivalência com o fallback exercitada
   pelos testes abaixo. Isso identifica o backend local, não a proveniência de um wheel do PyPI.
- **Metadados instalados divergentes**: `importlib.metadata.version("tcf-format")` informa
   `0.8.3`. O código importado corresponde à `.8.4`, mas este ambiente não certifica uma
   instalação limpa do pacote `.8.4`. Nenhuma reinstalação foi feita nesta conferência.
- Biblioteca sem `console_scripts` e sem `tcf.__main__`; o tooling de `scripts/` não é
   um CLI público do pacote. A configuração de distribuição está em [pyproject.toml](../pyproject.toml).

### Fluxo observado

| porta | decisões do caminho vigente | fonte executável |
|---|---|---|
| `encode` | resolve schema e valida opções; trata single-col, vazio e tipos; reconhece registros retangulares e tabelas; delega o restante representável ao hierárquico, que também rejeita entradas fora do contrato | [encoder.py](../src/tcf/encoder.py): `encode`, `_tipo_single_col`, `_registros_flat`, `_tabela_flat` |
| compressão por coluna | pré-pass/features, OBAT e HCC; a rota multi avalia seus candidatos por coluna; registros usam o mesmo caminho e registram a forma de origem com `R` | [encoder.py](../src/tcf/encoder.py): `_encode_column`; [multi/core.py](../src/tcf/multi/core.py): `_encode_multi` |
| `decode` | valida a versão, trata polaridade e despacha pelo discriminador; `R` usa o decoder multi e remonta registros; tipos e naturezas são restaurados segundo a rota/header | [decoder.py](../src/tcf/decoder.py): `decode`, `_decode_typed`, `_decode_column` |
| `view` | interpreta o envelope; consultas aproveitam estrutura quando suficiente e recorrem à materialização da coluna quando precisam de valores; hierárquico não-tabular é recusado | [view.py](../src/tcf/view.py): `LazyTCF._parse`, `_parse_hier`, `_col` |

Este mapa descreve responsabilidades e decisões existentes. Não atribui custo às etapas
nem recomenda mudanças de arquitetura.

### Matriz de concordância

| superfície | confronto com a execução | verificação e destino |
|---|---|---|
| exports, versão e assinaturas de `encode`/`decode` | conformes ao pin dos testes; isso não verifica a correção das anotações de retorno | [test_regression_v1_baseline.py](../tests/test_regression_v1_baseline.py), `TestPublicAPISurface` |
| rotas descritas na referência de API | **divergência documental**: a tabela principal inclui `[]` na rota `.8H`; também restringe o multi a strings e envia tabelas tipadas/com nulo ao hierárquico. A execução emite single-col para `[]` e `.8M` para tabelas retangulares tipadas/com nulo | [api.md](../docs/reference/api.md), seções de dispatch e slot 0; reprodução abaixo. Corrigir a referência a partir dos contratos/testes vigentes |
| ajuda do módulo e retorno de `decode` | **divergência na descrição do código**: a docstring do módulo ainda envia registros/tipados ao hierárquico; a anotação e o `Returns` de `decode` restringem o resultado a listas/tabelas de strings, embora haja números, registros e estruturas aninhadas | [__init__.py](../src/tcf/__init__.py) e [decoder.py](../src/tcf/decoder.py). Correção exige aprovação por estar em `src/tcf`, mesmo sem alterar execução |
| `max_length` por rota | **inconsistência de contrato público**: o override é aplicado no single-col e não é encaminhado nas rotas multi, registros e hierárquica | [T-FMT-META-STRICT](T-FMT-META-STRICT.md), seção sobre alcance do override, com contra-prova. Não resolver apenas estreitando a promessa documental |
| exemplos GitHub/PyPI, tutoriais e referências | os blocos executados passam, com avisos dos exemplos de tipos mistos/coerção; prosa, tabelas e resultados escritos como comentário não são todos verificados pelo runner | [test_docs_snippets.py](../tests/test_docs_snippets.py); conformidade dos exemplos não equivale a concordância documental completa |
| registros, tipos JSON e consultas exercitadas | round-trips, fronteiras de registros e consultas cobertas pelos exemplos/testes passam | [test_registros_8r.py](../tests/test_registros_8r.py), [test_json_flow_parity.py](../tests/test_json_flow_parity.py). Não é cobertura de todos os kwargs cruzados com todas as rotas |

Reprodução pequena das rotas em questão, sem benchmark nem medição de bytes:

```python
from tcf import decode, encode

cases = [
      ([], "#TCF.8\n"),
      ({"v": ["abc", None]}, "#TCF.8M"),
      ({"v": [1, 2]}, "#TCF.8M"),
      ([{"v": 1}, {"v": 2}], "#TCF.8R"),
      ({"item": {"v": "abc"}}, "#TCF.8H"),
]
for data, prefix in cases:
      wire = encode(data)
      assert decode(wire) == data
      assert wire.startswith(prefix)
```

### Verificações e saída pendente

Comandos executados no interpretador acima:

```powershell
& '.\.venv\Scripts\python.exe' -m pytest -q tests/test_regression_v1_baseline.py tests/test_docs_snippets.py
& '.\.venv\Scripts\python.exe' -m pytest -q tests/test_registros_8r.py tests/test_json_flow_parity.py tests/test_decode_max_length.py tests/test_real_world_snapshots.py tests/test_pyx_byte_equivalence.py
```

Resultados: **78 passed, 4 warnings** e **173 passed, 1 skipped**, respectivamente.
O caso skipped não é contado como cobertura. Os gates são do checkout; não foi executada
campanha de desempenho, validação de wheel publicado ou matriz exaustiva de parâmetros.

Para aceitar a referência antes da etapa 2: alinhar as descrições de rotas, encaminhar a
correção da ajuda/anotações do core com aprovação, decidir o contrato do override no ticket
existente e separar a verificação de código-fonte da verificação de instalação. Lacunas de
opções por rota permanecem explícitas. Nenhuma hipótese de otimização foi escolhida.

---

## O `.8H` não regrediu: a suspeita de 2026-09-01 está resolvida

O lab [`2026-09-01-1937-perf-8h-dois-lados-mesmo-pino`](../experiments/lab/dirty/2026-09/2026-09-01/2026-09-01-1937-perf-8h-dois-lados-mesmo-pino/result.md)
mediu os dois lados no mesmo pino, mesma máquina e mesma sessão térmica. A suspeita ampla
não se confirma.

O `+16%` e o `+47%` nunca foram leitura crua do comparador: eles já saíam **líquidos do
controle de referência**, num par que o `compare` recusou fail-closed, entre árvores e
sessões térmicas distintas. Naquela rodada o fator do calibrador era 1,2951 e sobre-corrigiu,
puxando as referências da stdlib, de código idêntico nas duas árvores, para −17,1%.

Medidos os dois lados no mesmo pino, a razão `tcf ÷ referência` dentro da rodada, em que a
máquina cancela por construção, dá `+3,2%` no flat com n=33 e `+4,0%` no `.8H` com n=8, e o
decode anda para o outro lado. Tudo dentro do MDE de 7%.

A explicação é tripla, e nenhuma parte dela responde sozinha: viés do calibrador, deriva
térmica na cauda da rodada B, onde as células a partir da ordem 96 ficam indecidíveis, e a
mudança intencional de rota do ADR-0049.

**O achado real é uma célula, e ela é o ADR-0049 funcionando.** `tcf-8h|synth|flat-mixed|base`
trocou de rota `#TCF.8H` para `#TCF.8R`: 212.177 bytes contra 308.417, decode de 111,6 ms
contra 221,1 ms, encode de 667,1 ms contra 504,9 ms. Mais trabalho no encode, wire 31% menor,
decode duas vezes mais rápido. **Essa célula hoje mede `.8R`**, e toda comparação futura
precisa saber disso.

O método que resolveu a dúvida fica valendo: normalizar pelos caminhos de referência dentro
da rodada, em vez do fator do calibrador. É a higiene já proposta no
[README do `bench_perf`](../scripts/bench_perf/README.md), e é pré-requisito de qualquer
veredito deste ciclo enquanto o `compare.py` não a incorporar.

Detalhe e tabela por família em
[`perf-baseline/README.md`](../experiments/results/evidencia-0.8/perf-baseline/README.md).

---

## Recebido do T-QA-8 (2026-09-14): o que o `.8` deixou para este ciclo

O `T-QA-8` era o dossiê da `0.8.0`. Na verificação de fechamento, o que não foi feito e não é
correção veio para cá, com o estado de hoje. Nenhum destes itens bloqueia o `.8`.

- **F5-1, triagem de otimização com o dado das fases F2 a F4.** Os quatro candidatos registrados
  na época: a porção serial depois do pool, `parallel=1` com saldo negativo, o custo incondicional
  de `obat_log` e `hcc_trace`, e o V2-B com largura de 2 ou mais. Cada um vira sub-experimento ou
  ticket próprio, com o gate de regressão real-world, e nenhum weld acontece dentro da triagem.
- **F3-4, natures em volume.** A rodada com `br-identidades` (600k, seed 20260601) não foi
  registrada; existem os controles pequenos em `evidencia-0.8/f2/e5` a `e7`.
- **F4-2, os três hubs públicos.** `online-retail` está no gate real-world e no EXP-019;
  `wine-quality` só no EXP-019, que compara `.8H` com `.8R`; `beijing-pm25` em nenhum. Falta a
  matriz no formato do F4-3 para os três.
- **F4-4, a tabela-mestra cross-fase**, com a nota Wohlin. Os `RESULT.md` por fase existem.

O paralelismo (F3-3) foi para o [T-CODE-PARALLEL-BUDGET](T-CODE-PARALLEL-BUDGET.md), que já espera
esses números para decidir o design.

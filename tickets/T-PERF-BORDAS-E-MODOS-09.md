---
title: T-PERF-BORDAS-E-MODOS-09, otimização multicamada, bordas e perfis; o alvo do .9
status: open
priority: P1
created: 2026-08-23
updated: 2026-09-20
gate: ".9 (desempenho e limpeza) (triagem 2026-09-01)"
target: ".9 (otimização), este é o ticket-mestre do ciclo"
blocked-by: []
related:
  - experiments/lab/dirty/2026-08/2026-08-23/2026-08-23-0300-tempo-ate-o-dado-chegar/
  - experiments/lab/dirty/2026-08/2026-08-23/2026-08-23-0100-janela-massa-pos-release/
  - tickets/T-STUDY-USE-PROFILES.md
  - tickets/T-REL-08-CLOSEOUT.md
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
profundidades no controle. O [`07-aninhamento`](../experiments/lab/dirty/2026-09/2026-09-07/2026-09-07-0208-perf-diagnostico/07-aninhamento/result.md)
(registro local, 2026-09-16) mostrou que isso não faz a soma contar tempo em dobro: no encode
serial da `0.8.4`, nenhum dos sete pontos cronometrados roda dentro de outro, em 49 execuções de
caso de 20 estruturas de chamada distintas, e a leitura estática dos imports não acha caminho para
isso. O instrumento serve ao passo 0 para dizer quanto do encode serial está em cada camada. Ele
não separa pipeline de candidato: cada bucket soma o que foi emitido e o que só foi avaliado, e
comparar regimes exige registrar quais candidatos rodaram, porque o V2-B só roda com repetição e
até 8.192 valores distintos. O docstring do `layers.py` passou a dizer isso.

**O passo 0 respondeu onde o tempo está na `0.8.4`**, no
[`08-perfil-0.8.4`](../experiments/lab/dirty/2026-09/2026-09-07/2026-09-07-0208-perf-diagnostico/08-perfil-0.8.4/result.md)
(registro local, 2026-09-18). Nas amostras de 1.000 e 5.000 linhas de `lineitem` e `empresas`,
o HCC fica com 52% a 77% das camadas e o OBAT com o resto; o pré-pass não passa de 1,5%. Dentro
das duas camadas o custo é busca: o detector de composições é o maior item do HCC, com 48% a 63%
do `tottime` no fallback, e `_melhor_pref`, em Python puro, é a maior função atribuível do
acelerado. De 74% a 78% das chamadas do HCC acontecem dentro da avaliação de candidatos, contadas
em chamadas e não em tempo. O acelerador economiza de 31% a 38% do encode. Wire byte-idêntico
entre todas as rodadas e os dois backends, e round-trip em arquivo, nos 23 casos.

Duas consequências valem para o ciclo. A fila começa pela busca. E as células `flat-mixed` do
`bench_perf` não representam essas amostras: nelas o detector quase não trabalha e o custo é
emissão, então uma otimização da busca precisa de gate em amostra real, não só nelas.

**O tempo gasto em candidatos está medido, e ele não escolhe entre as duas primeiras frentes da
fila**, no [`09-tempo-dos-candidatos`](../experiments/lab/dirty/2026-09/2026-09-07/2026-09-07-0208-perf-diagnostico/09-tempo-dos-candidatos/result.md) (registro local, 2026-09-19). Cronometrando as
camadas com o caminho de candidato como rótulo, em 16 casos e 44 subprocessos, com wire
byte-idêntico ao do 08 e contagens cruzadas exatas com o rastreador dele: de 64% a 98% do encode
acontece em candidatos que perdem o `min()` por coluna, e o maior bloco, de 40% a 93%, é a busca
feita dentro desses perdedores, que tanto um orçamento de busca quanto evitar o candidato
alcançam. Os territórios exclusivos de cada frente somam de 0,06 a 0,53 do encode, e as duas
tabelas apontam frentes opostas com margem: `lineitem` aponta evitar candidatos, `empresas`
aponta limitar a busca do vencedor, e a divergência desaparece quando o detector roda em Python
puro. O maior desperdício isolado medido é uma coluna de texto livre que gasta 52,6 s dos 81,0 s
do encode montando um corpo `tcf` que sai descartado, porque a coluna é emitida como `raw`.

A escolha que resta não é de frente, é de técnica, e o critério é o contrato.

**A técnica mais barata que preservaria o wire está refutada**, no
[`10-limite-exato`](../experiments/lab/dirty/2026-09/2026-09-07/2026-09-07-0208-perf-diagnostico/10-limite-exato/result.md) (registro local, 2026-09-19). Simulando a decisão do `min()`
sobre o encode real, com o vencedor reconstruído igual ao emitido em toda coluna: o limite
inferior estrutural do slot do dicionário, calculado de `N` e `K`, dispensa de 0% a 0,03% do
encode e custa de 0,4% a 12,9%. A refutação não depende do custo, e vale para a família
`N × largura(K) + c` inteira: a força do limite é 0,96 mediana nas chamadas em que o dicionário
vence e 0,27 nas em que perde, porque o fluxo de índices só domina o slot quando a cardinalidade
é baixa, que é quando o candidato ganha.

**A peça que faltava não existe em forma barata, e o caminho que preserva o wire por construção
está fechado.** O [estudo de 2026-09-19](../experiments/lab/dirty/notas/2026-09/2026-09-19-limite-do-corpo-tcf/README.md) (registro local) testou as duas famílias
possíveis de limite inferior do corpo `tcf`. A das estatísticas que ignoram a ordem cai por
construção: duas colunas com o mesmo `n`, o mesmo `k` e o mesmo conjunto de valores dão corpos de
18 e de 59.998 bytes conforme a ordem, então qualquer limite dessas estatísticas fica preso ao
menor deles. A que olha o arranjo, contando segmentos numa passada, tem força mediana de 0,141 e
dispensaria o candidato `tcf` em 0 de 104 colunas.

O motivo é geral: candidato perde por pouco, de 0,78 a 1,0 no dicionário e de 0,68 a 1,0 no
`tcf`, então provar que ele perde sem calculá-lo exige um limite que capture quase todo o tamanho
dele, e um limite assim custa quase o que custa a própria conta. Se algum dia ele aparecer, o
alcance seria de 12,8% a 47,8% no dicionário e de 17% a 85% no `tcf`, e ainda seria preciso provar
o desempate do `_best_of`, que hoje decide empate pela ordem.

As alternativas continuam mudando bytes: um orçamento de busca alcança o bloco partilhado inteiro
e é classe 2, com gate por I4; prever o vencedor muda o wire quando erra.

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
1,2 GB** sem terminar, interrompido. Fica registrado como **limite prático do encode atual**. Os
dois números são anotação do README do lab `0100`; a saída bruta (`g1-parcial.log`) termina em `empresas`.

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

O único teto da busca composicional do HCC é um contador **fixo de 99 iterações**
(`src/tcf/composicional/syntax.py:524`, repetido no acelerador `src/tcf/_core/detect.pyx:151`),
que o registro de 2026-08-13 deu como já saturado em texto livre: é o parâmetro natural do modo
rápido. O teto está anotado no H-PERF-05f do
[registry de hipóteses](../experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md). A
superfície de API (`fast=true`, perfis macro) é a hipótese H-PROFILE-01 do mesmo registry, e o
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
(`parallel × sort_by × drop_names`), buraco F3-3 declarado no T-QA-8 e hoje com o
[T-CODE-PARALLEL-BUDGET](T-CODE-PARALLEL-BUDGET.md), **specs em volume**,
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
- [ ] Baseline de desempenho repetida depois das otimizações, condição do owner registrada em [`perf-baseline/README.md`](../experiments/results/evidencia-0.8/perf-baseline/README.md): a `0.8.4` e o candidato medidos na mesma máquina e na mesma sessão térmica, com a decisão do instrumento, registrada na seção do `.8H`, tomada antes da rodada
- [ ] F3-3 (paralelismo + combos) fechado no [T-CODE-PARALLEL-BUDGET](T-CODE-PARALLEL-BUDGET.md), que recebeu o item do T-QA-8
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
| rotas descritas na referência de API | **divergência documental corrigida em 2026-09-16**: a tabela principal punha `[]`, a lista tipada e a chave não-`str` na rota `.8H`, restringia o multi a strings e enviava tabelas tipadas/com nulo ao hierárquico. A referência agora segue a execução: single-col para `[]` e para lista tipada, `.8M` para tabela retangular tipada/com nulo, fail-loud para chave não-`str`. A mesma correção entrou no [README.md](../README.md), no [README.pt-BR.md](../README.pt-BR.md) e em [json-equivalence.md](../docs/reference/json-equivalence.md) | [api.md](../docs/reference/api.md), seções de dispatch e slot 0; reprodução abaixo. Pinos em [test_multi_col_rt.py](../tests/test_multi_col_rt.py) (`TestTagDeTipoNoMeta`), [test_null_slot0.py](../tests/test_null_slot0.py) e [test_registros_8r.py](../tests/test_registros_8r.py) |
| ajuda do módulo e retorno de `decode` | **divergência na descrição do código**: as docstrings do módulo e de `encode` ainda enviam registros/tipados ao hierárquico; a anotação e o `Returns` de `decode` restringem o resultado a listas/tabelas de strings, embora haja números, registros e estruturas aninhadas | [__init__.py](../src/tcf/__init__.py), [encoder.py](../src/tcf/encoder.py) e [decoder.py](../src/tcf/decoder.py). Correção exige aprovação por estar em `src/tcf`, mesmo sem alterar execução |
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

Para aceitar a referência antes da etapa 2: encaminhar a
correção da ajuda/anotações do core com aprovação, decidir o contrato do override no ticket
existente e separar a verificação de código-fonte da verificação de instalação. Lacunas de
opções por rota permanecem explícitas. Nenhuma hipótese de otimização foi escolhida.

---

## O regime alvo, e o que ele muda na evidência do ciclo (owner, 2026-09-19)

**Direção do owner.** Massa é instrumento, não alvo: ela serve para ver se nada quebra, entender o
comportamento e testar se a pequena escala representa a grande. O uso regular é transmissão de API,
ou sincronismo de volumes pequenos, ou um arranjo colaborativo em que muitos emissores mandam coisa
em comum de pontos diferentes e o framework integra um dicionário compartilhado. O vértice de massa
existe e é o de armazenamento, tipo Parquet, e fica para experiência futura.

**Vocabulário: isto se chama topologia aqui.** Os eixos de uso já estão tabelados em
[`T-STUDY-USE-PROFILES`](T-STUDY-USE-PROFILES.md), com quatro linhas: A, cliente encoda e servidor
consome; B1, servidor encoda o mesmo payload para N clientes; B2, servidor encoda payload único por
requisição; C, disco e armazenamento. O "vértice" da ADR-0002 é outra coisa, a restrição entre
compressão, memória e latência. E "massa é instrumento, não alvo" já está escrito lá, com estas
palavras: medir em massa serve para ter noção de ordem de grandeza, não para decidir. O protocolo de
verificação em massa também já existe, em `T-REL-08-CLOSEOUT`: gate de reentrada, integridade,
custo e população. Nada disso é novo, e o `.9` não citou nenhum deles.

**O vértice colaborativo já está registrado, e o que mudou hoje é a categoria dele.** Ele está na
nota de hipóteses, escrito pelo owner em 2026-08-31 e com a magnitude corrigida por ele em
2026-09-01: não é acúmulo dentro de uma sessão, é buffer entre sessões, com containers por assunto
ou contrato, e o dicionário pertence ao assunto, não à conexão. A nota o posiciona como tier
intermediário, distinto do `H-CODEBOOK-01`, que é tabela externa pré-acordada e não aprende, e do
`H-GDICT-01`, que é dicionário entre colunas de um mesmo artefato. O status lá é "sem lab e sem
medição, registrado para avaliar, não para fazer", e alvo 2.0.

O que a fala de hoje muda: ele deixou de ser ideia para avaliar e passou a ser um dos regimes de
uso declarados, ao lado da transmissão de API e do sincronismo pequeno. Regime de uso é critério de
aceite. Ele não aparece neste ticket, nem no plano do `.9`, nem no ROADMAP, que só registra o primo
intra-blob; o único lugar onde ele vive é a nota de hipóteses, que é dirty. O que o bloqueia
continua sendo contrato, não byte: quem nomeia o container, como as duas pontas concordam no nome,
o que acontece quando um lado o tem e o outro não, e invalidação e versão. Um blob que depende de
estado externo deixa de ser auto-contido, que é invariante da família `.8`.

**E o teto dele foi medido agora, pela primeira vez, no regime alvo.** Modelo: K transmissões
pequenas do mesmo assunto, com R linhas cada; soma dos encodes independentes contra o encode do
concatenado, que é limite inferior de qualquer esquema com dicionário partilhado, porque um esquema
real ainda paga moldura por blob. Duas fontes reais, 4.000 linhas cada:

| fonte | R=20 | R=50 | R=200 |
|---|---:|---:|---:|
| `adult-census`, 7 colunas categóricas | −76,1% | −61,2% | −31,5% |
| `online-retail`, `StockCode`, `Description` e `Country` | −55,2% | −51,0% | −45,9% |

O ganho **cresce quando o payload encolhe**, que é a direção do regime alvo, e o teto do
intra-blob, medido em 2026-07-01, ia no sentido oposto, de +5,7% a +48,1%. O motivo é que o
concorrente é outro: entre blobs cada transmissão paga a própria tabela de únicos do zero, e o
`min()` por coluna continua livre dos dois lados da conta. Um controle isola que não é só
amortização de cabeçalho: com R=200, `Country`, de 7 distintos, dá −78,9%; `Description`, de 1.475,
dá −51,1%; e `InvoiceNo`, cujos valores são contíguos e quase não se repetem entre transmissões, dá
−6,6%. O ganho acompanha a repetição de vocabulário entre as transmissões.

Quatro ressalvas: é teto, não ganho; o concatenado é de linhas, no plano do dado, e concatenar
wires corrompe, o que já foi reprovado em lab; o fechamento do `T-EXP-H-GDICT-01` continua correto
no escopo dele, que é entre colunas do mesmo blob, e não se transfere para cá; e, a quarta, escrita
depois de medir: **essa conta compara o TCF com o TCF**. O concorrente de fora nunca entrou nela, e
quando ele entrou, no lab `02-piso-de-payload`, virou outra história, abaixo.

**O que a evidência do `.9` sustenta sob esse enquadramento.** As medições que decidiram algo foram
as de 1.000 e 5.000 linhas, com wires de 43 KB a 317 KB e encodes de 3,5 s a 23,0 s. Isso é arquivo,
não payload de API. Sobrevive o que não depende de escala: os fatos estruturais do encoder, a
refutação da família de limites (que se apoia em onde o limite é forte, não no tamanho), a queda das
estatísticas que ignoram a ordem, e os achados de instrumento. Não sobrevivem como critério de
escolha as frações por camada e os territórios `P`, `Sp` e `Sv`: nas amostras medidas o que cai fora
do pipeline por coluna vale de 0,3% a 1,9% do tempo, e na única célula com wire de tamanho de API,
195 bytes, esse mesmo resto vale 61,7%.

**Três números que o ciclo não tinha, e que mudam a decisão.** Todos calculados da baseline
publicada da `0.8.4` ou por sonda direta, com round-trip conferido:

| medida | valor | fonte |
|---|---|---|
| decode do TCF contra `json.loads`, forma aninhada, que é a de payload de API | 15,8× a 20,5× | `perf-nucleo-2026-09-01.jsonl`, mesma rodada |
| (o JSON aqui é régua comparativa, não produto: no núcleo do TCF não existe JSON, e o que existe de fato são os datasets) | | owner, 2026-09-20 |
| assimetria interna do TCF nessa forma | 1,97× a 2,14× | idem |
| conta 1 encode : N decodes, forma aninhada, de N=1 a N=1000 | 23,0× cai só para 20,5× | idem |
| piso de payload contra a régua comprimida, seis projeções de dado real | de 1 a 500 registros conforme forma e compressor, e inexistente até mil em 7 de 42 combinações (a sonda anterior dizia 5 registros, de uma forma só) | lab `02-piso-de-payload`, execução 3 |
| custo de `import tcf`, acima do interpretador vazio | 290,3 ms, com ruído de 2% e dois instrumentos concordando em 2,3% (a sonda anterior dizia 232 a 286 ms) | lab `03-custo-de-partida`, execução 2 |
| piso por chamada do decode, um registro, quente | 0,16 ms a 0,33 ms (a sonda anterior dizia 0,50 ms a 0,52 ms, e era do encode) | lab `01-decode`, execução 2 |
| primeira chamada de decode contra regime quente | **refutado**: razão de 0,65 a 1,48, mediana perto de 1, em dois instrumentos independentes. A sonda anterior dizia de 4,9 a 5,2 | lab `01-decode` e revisão independente |

A leitura dura, **corrigida pela medição no regime alvo** ([`01-decode`](../experiments/lab/dirty/2026-09/2026-09-20/2026-09-20-0100-regime-alvo/01-decode/result.md), registro local,
2026-09-20, execução 2 com o instrumento emendado): a conta 1:N converge mesmo para a razão de
decode, mas a **velocidade** dessa convergência é o que decide, e ela é lenta. O encode manda no
total até N passar da assimetria interna, que na forma de registro com dado real vale 3 em um
registro, de 14 a 19 em vinte, de 24 a 32 em cem e de 84 a 147 em mil. Em N realista de uma API,
de uma a poucas dezenas de leituras por payload, **o encode é a maior parte da conta**, e ele custa
de 34× a 1.409× o `json.dumps`. O decode custa de 9× a 21× o `json.loads`, e é o limite para onde
a conta tende.

Duas coisas que essa medição fecha. A primeira: a conta **não cruza a régua em CPU para nenhum N**,
porque o limite dela é maior que 1; o que o formato compra é byte, com o wire indo de 92% do JSON
em um registro a 17% em mil. A segunda: a assimetria de 1,97× a 2,14× da baseline não vale aqui, e
a diferença não é de tamanho, é de **dado**, dezesseis e seis colunas reais contra quatro colunas
sintéticas com 10% de distintos, e de rota.

**O instrumento não alcança o alvo.** A menor escala de toda a matriz do `bench_perf` é R=100, e só
três células medem TCF nessa escala. O plano `smoke` se declara sem valor probatório. Nos labs, as
amostras de 200 linhas rodaram como smoke, com voto desligado antes da medição. O recorte do
`bench_perf` vai de entrada materializada a saída wire, com aquecimento descartado, o que apaga por
contrato os três custos que mandam no alvo: import, primeira chamada e piso por chamada.

**O piso de payload, medido no regime alvo** ([`02-piso-de-payload`](../experiments/lab/dirty/2026-09/2026-09-20/2026-09-20-0100-regime-alvo/02-piso-de-payload/result.md),
registro local, 2026-09-20, execução 3 de 3). Seis projeções de duas fontes reais, dez tamanhos de
1 a 1.000 registros, sete compressores, contra o concorrente **comprimido**, que é o que trafega
de fato num fio HTTP. A execução 3 reproduziu a 2 byte a byte, em 1.320 células, com round-trip
conferido dos dois lados em todo caso. Quatro coisas saem dali, e três delas apertam o ciclo:

1. **O piso é superfície, não número.** Ele vai de 1 a 500 registros conforme forma e compressor, e
   em 7 das 42 combinações não existe até mil, todas projeções de coluna única. A aproximação não é
   monótona: a razão sobe em algum passo em 35 das 42 combinações, e em 13 o wire ganha num tamanho
   e devolve o ganho num maior. Um tamanho isolado abaixo de 1 não prova piso, que é o vício da
   sonda que esta medida substitui.
2. **No tamanho alvo a economia é de dezenas de bytes.** Em vinte registros com `brotli-5`, que é o
   nível de HTTP dinâmico, o wire economiza 124 B numa fonte e 25 B na outra, e com `brotli-11`
   **custa 17 B a mais**. Com `gzip-6` a economia chega a 235 B. É a ordem de grandeza de um
   cabeçalho HTTP, e é menor que o framing que o lab não mediu. Junto com o `01-decode`, a troca no
   alvo fica explícita: 25 ms de encode por até algumas centenas de bytes.
3. **A régua escolhida decide metade da conta.** O JSON na forma de registro repete as chaves em
   toda linha, e uma API pode mandar colunar ou em linhas com cabeçalho separado. Contra essas, em
   vinte registros, o TCF **empata ou fica atrás em todos os casos medidos**. Boa parte do ganho
   contra a forma de registro é a repetição de chave dela, não redundância do dado. Toda citação de
   razão contra JSON neste ticket herda essa ressalva.
4. **O dicionário partilhado não é exclusividade do formato.** Medido como concorrente, com
   `zstd-19` e cada lado treinando o seu dicionário de 16 KB em até 100 transmissões anteriores do
   mesmo assunto: em vinte registros de `lineitem` o TCF faz 720 B contra 894 B da régua de
   registro e 773 B da colunar; em `empresas` ele **perde** para a colunar, 522 B contra 512 B, e
   em cem registros perde para as duas. Isso não derruba o vértice colaborativo, mas derruba a
   premissa de que ele é uma saída que só o TCF tem: qualquer payload ganha dicionário treinado, e
   o que decide é quanto vocabulário se repete entre transmissões, não o formato.

**O custo de partida, medido** ([`03-custo-de-partida`](../experiments/lab/dirty/2026-09/2026-09-20/2026-09-20-0100-regime-alvo/03-custo-de-partida/result.md),
registro local, 2026-09-20, execução 2 de 3). Oito células, quinze processos frios cada, com o
round-trip (I4) rodando dentro de cada processo. Ruído de 1,1% a 2,8%, e os dois instrumentos,
relógio de processo e `-X importtime`, concordando em 2,3%.

1. **Ligar o pacote custa 290,3 ms**, que é 6,2 vezes o `import json`. Num processo que nasce,
   atende uma requisição de vinte registros e morre, o total do TCF é 2,84 vezes o do JSON, e
   **68% desse total é o import**, contra 6% de encode.
2. **Três quartos do import não são código do pacote.** Os 133 módulos que o `import tcf` traz
   se dividem em 31 do pacote, com 69,6 ms, e 102 de fora, com 211,3 ms. As famílias mais caras
   são a máquina de paralelismo e a de introspecção. O lab somou a primeira por nome e chegou a
   "cerca de 38 ms", que era **piso, não valor**: o `04-import-adiavel`, abaixo, mediu por
   conjunto exclusivo e achou 107 ms. A de introspecção, com `inspect`, `ast`, `dis` e
   `tokenize`, entra pelo `dataclasses` e soma 31 ms. Um payload de vinte registros não usa
   nenhuma das duas.
3. **A partida amortiza em onze encodes** de vinte registros. Worker de vida longa passa disso
   na primeira fração de segundo; função sem servidor que atende uma invocação por processo
   nunca chega lá, e para ela otimizar encode não muda o que o usuário sente.
4. **Conferência cruzada de graça:** o encode frio deu 26,12 ms contra os 25,43 ms que o
   `01-decode` mediu quente, com outro instrumento. Menos de 3% entre dois labs que não se
   coordenaram.

Ressalva de plataforma, que o resultado omitiu e a revisão achou: tudo é **Windows 10, máquina
única**, onde import custa várias vezes o que custa em Linux. Os milissegundos absolutos não
transferem; as razões (6,2 vezes o `json`, um quarto contra três quartos, onze encodes) tendem a
transferir, e não foram conferidas em outra plataforma.

O lab mede e para: ele **não** diz que esses 211 ms são cortáveis. Módulo arrastado não é módulo
inútil, e descobrir quanto disso é carregável sob demanda mexe em `src/tcf`, o que depende de
aprovação (I5).

**Quanto da partida é adiável, medido sem tocar no pacote** ([`04-import-adiavel`](../experiments/lab/dirty/2026-09/2026-09-20/2026-09-20-0100-regime-alvo/04-import-adiavel/result.md),
registro local, 2026-09-20, execução 2 de 3). Três instrumentos: um leitor de AST que classifica
o uso de cada import externo do pacote, na carga ou só na chamada; o conjunto exclusivo de cada
import direto, que é o que sairia da partida se só ele fosse adiado; e um contrafactual que
planta um módulo falso em `sys.modules` antes do `import tcf`, mede pelo relógio de processo e
roda o round-trip sob o stub, com gate de wire idêntico ao controle.

1. **Metade do que o pacote arrasta entra por uma linha.** `src/tcf/multi/parallel.py:12` importa
   `ProcessPoolExecutor` no topo do arquivo, os nomes só são usados dentro de
   `_encode_columns_parallel`, e `parallel` tem padrão `False`. Essa linha traz **51 módulos que
   nada mais no pacote pede**, entre eles `multiprocessing`, `socket`, `logging`, `threading`,
   `subprocess` e `tempfile`: **107 ms** pelo conjunto exclusivo, **116 ms** pelo relógio de
   processo, com os dois instrumentos a 8,6% um do outro. É 52% do arrastado e cerca de 40% do
   import líquido.
2. **Sob o stub nada muda no fio.** O pacote importa, o round-trip passa em dois payloads, o wire
   sai com o mesmo SHA-256 do controle, e o stub nunca é chamado nem acessado no caminho.
3. **O `json` é o contra-exemplo.** Com payload só de strings ele sai intocado; com as colunas
   numéricas tipadas, o pacote chama `json.loads` e o stub dispara. Adiá-lo deslocaria 9 ms em
   vez de tirar. Foi uma contra-prova acrescentada por emenda que achou isso: sem ela, o `json`
   teria entrado na soma do adiável.
4. **O resto não sai sem redesenho:** 33 ms estão presos a uso na carga, quase tudo pelo
   `dataclasses`, decorador em dez arquivos, e 55 ms são base partilhada entre vários imports.
5. **Há precedente no código:** o pacote já tem 9 imports externos dentro de função.

O lab **não mede a primeira chamada com `parallel` ligado**, que é para onde os 107 ms iriam, e
não prova nada sobre `pickle` dos workers nem sobre a suíte. Ele não propõe a mudança: mexer em
`src/tcf` é I5, e a decisão é do owner.

**O envelope HTTP, medido** ([`05-framing-http`](../experiments/lab/dirty/2026-09/2026-09-20/2026-09-20-0100-regime-alvo/05-framing-http/result.md),
registro local, 2026-09-20, execução 1 de 3). Servidor da biblioteca padrão e cliente de socket
cru dos dois lados, contando o que trafega na camada de aplicação. 24 células, round-trip (I4)
verde em todas, tamanho determinístico em todas.

1. **O envelope é constante entre os dois formatos.** A diferença entre os dois cabeçalhos é
   exatamente o media type mais os dígitos do `Content-Length`, com resíduo zero nas dezesseis
   comparações. O framing **não muda o sinal** da economia medida no lab 02.
2. **Mas ele dilui.** Uma resposta custa 147 a 174 B de cabeçalho no perfil mínimo e 315 a 342 B
   no realista, mais 164 a 171 B de requisição. Contra a régua de registro, em vinte registros,
   isso é **1,46 vez** a economia com `gzip`, **1,54** com `zstd` e **2,74** com `brotli`.
   Contra a régua colunar, ou não há economia, ou o envelope vale **11,8 vezes** ela.
3. **Contra a régua colunar a resposta inteira do TCF é maior**, com `gzip` e com `brotli`.
4. **O repositório não declara media type**, só a extensão `.tcf` (ADR-0001, ADR-0029). O lab
   escolheu `application/vnd.tcf` para poder medir, e declara que é escolha dele. São 3 B a mais
   que `application/json`, e é a única parte do envelope onde a escolha do projeto muda a conta.

Limite que desfavorece esta leitura, e por isso precisa vir junto: é **HTTP/1.1 sem HPACK**. Com
cabeçalho comprimido o envelope encolhe e a economia do corpo pesa relativamente mais. O que foi
medido é o caso mais favorável à tese de que o framing domina.

**A conta do regime alvo, agora fechada nos três labs.** Num processo frio que atende uma
requisição de vinte registros: 290 ms de partida, 26 ms de encode, menos de 2 ms de decode, e um
ganho no fio de 25 a 235 bytes contra JSON comprimido, ou nada contra uma régua que não repete
as chaves, e um envelope HTTP de 315 a 342 bytes carregando esse ganho. **A fila de otimização
deste ciclo mira o encode, que são 6% dessa conta.** Isso não fecha o formato contra o regime
alvo, fecha contra este recorte: um processo por requisição, um payload por processo, e uma
régua escolhida pelo concorrente.

**Consequência para o aceite.** Nenhum dos onze critérios exige medição no regime alvo, e nenhum
nomeia piso de payload, custo fixo por chamada, latência ponta a ponta ou decode contra o
concorrente. A tabela da base medida, de 1.500 a 100.000 linhas, é fotografia de borda. Os itens de
massa do ciclo passam a ser rotulados como verificação, pelo protocolo que já existe, e não como
entrega de objetivo.

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
decode anda para o outro lado. Tudo abaixo do limiar de ruído que o comparador aplica a esse par
(10,15%, o piso da rodada B).

A explicação é tripla, e nenhuma parte dela responde sozinha: viés do calibrador, deriva
térmica na cauda da rodada B, onde as células a partir da ordem 96 ficam indecidíveis, e a
mudança intencional de rota do ADR-0049.

**O achado real é uma célula, e ela é o ADR-0049 funcionando.** `tcf-8h|synth|flat-mixed|base`
trocou de rota `#TCF.8H` para `#TCF.8R`: 212.177 bytes contra 308.417, decode de 111,6 ms
contra 221,1 ms, encode de 667,1 ms contra 504,9 ms. Mais trabalho no encode, wire 31% menor,
decode duas vezes mais rápido. **Essa célula hoje mede `.8R`**, e toda comparação futura
precisa saber disso.

O método que resolveu a dúvida fica valendo: normalizar pelos caminhos de referência dentro
da rodada, em vez do fator do calibrador. O `compare.py` a incorporou em 2026-09-14
([README do `bench_perf`](../scripts/bench_perf/README.md)), e o veredito do comparador já sai
dessa razão. O comparador também imprime a `nota_adjudicacao` da rodada, o que encerra a
higiene que estava registrada.

Fica **uma decisão do instrumento**, para quando houver baseline nova: 31 das 106 células do
`nucleo` não têm referência de mesma cauda e saem `sem-referencia`. Dar veredito a elas exige
incluir referências na matriz, o que muda o `cases.json` e pede re-pin dos três planos. É o
momento de trocar o pin para o hash do conteúdo canonizado, que hoje é dos bytes do arquivo.

Relidos com o comparador novo, os dois JSONL deste lab dão 5 células acima dos pisos de ruído das
duas rodadas. Uma é a `flat-mixed` que passou a medir o `.8R`. As outras quatro são do `tcf-flat`
em `flat-mixed`, nos pontos baixos dos eixos (`K0001`, `K001`, `R1e2` e `L8`), com `+11%` a
`+20%`, e rodaram no início da rodada B, nas ordens 9 a 20, longe da cauda com deriva térmica.
Não é veredito: são duas rodadas, a B termicamente suspeita, com a referência pareada 17 posições
depois. Seguem candidatas a remedição: o passo 0 mediu onde o tempo está e não as remediu,
porque a pergunta delas é outra, regressão entre árvores.

A tabela por família saiu do README do snapshot em 2026-09-14 (`32861ecf`); o detalhe fica em
`outputs/razao-resumo.txt` do lab `1937`, e o fator 1,2951 se reproduz com `compare --dev` sobre
os JSONL de 20/08 e 01/09 do snapshot, em
[`perf-baseline/README.md`](../experiments/results/evidencia-0.8/perf-baseline/README.md).

---

## Recebido do T-QA-8 (2026-09-14): o que o `.8` deixou para este ciclo

O `T-QA-8` era o dossiê da `0.8.0`. Na verificação de fechamento, o que não foi feito e não é
correção veio para cá, com o estado de hoje. Nenhum destes itens bloqueia o `.8`.

- **F5-1, triagem de otimização com o dado das fases F2 a F4.** Os quatro candidatos registrados
  na época: a porção serial depois do pool, `parallel=1` com saldo negativo, o custo incondicional
  de `obat_log` e `hcc_trace`, e o V2-B com largura de 2 ou mais. Na `0.8.4`, `parallel=1` já roda serial sem spawn (BUG-10c,
  2026-07-10) e o `hcc_trace` é opt-in (`8575f98b`, 2026-08-13); o `obat_log` segue incondicional.
  Cada candidato restante vira sub-experimento ou
  ticket próprio, com o gate de regressão real-world, e nenhum weld acontece dentro da triagem.
- **F3-4, natures em volume.** A rodada com `br-identidades` (600k, seed 20260601) não foi
  registrada; existem os controles pequenos em `evidencia-0.8/f2/e5` a `e7`.
- **F4-2, os três hubs públicos.** `online-retail` está no gate real-world e no EXP-019;
  `wine-quality` só no EXP-019, que compara `.8H` com `.8R`; `beijing-pm25` em nenhum. Falta a
  matriz no formato do F4-3 para os três.
- **F4-4, a tabela-mestra cross-fase**, com a nota Wohlin. Os `RESULT.md` por fase existem.

O paralelismo (F3-3) foi para o [T-CODE-PARALLEL-BUDGET](T-CODE-PARALLEL-BUDGET.md), que já espera
esses números para decidir o design.

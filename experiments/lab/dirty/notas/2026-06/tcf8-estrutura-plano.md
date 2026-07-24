---
title: TCF.8 - plano de revisão integral do formato
type: plan
status: aberta
created: 2026-06-25
updated: 2026-07-23
related:
  - experiments/lab/dirty/notas/2026-07/2026-07-23-0259-implicitude-singlecol-logica.md
  - experiments/lab/dirty/notas/2026-07/2026-07-23-0345-modo-denso-marcador-binarizacao.md
  - experiments/lab/dirty/notas/2026-07/tcf8-header-char-registry.md
  - experiments/lab/dirty/notas/2026-07/dataset-json-dois-contratos.md
  - experiments/lab/dirty/2026-07/2026-07-23/2026-07-23-0204-api-8-catalogo-de-casos/
  - docs/reference/json-equivalence.md
---

# TCF.8 - plano de revisão integral do formato

**[probatório]** Este é o ponto de entrada único da revisão integral do `#TCF.8`. Organiza perguntas,
ordem e provas; não escolhe antecipadamente uma gramática, não autoriza weld e não é um plano de
release. Decisões de formato continuam exigindo artefato inspecionável, contraditório, gate e ato
dispositivo próprio.

## 1. Escopo e ordem

A revisão percorre as formas do menor contexto para o maior:

1. **single-column** - assinatura/cabeçalho, tipo lógico e representação do body;
2. **multi-column** - composição de colunas, meta, modos, nomes, sizes, view e paralelismo;
3. **hierárquico** - topologia, presença, repetição, folhas tipadas e reconstrução do dataset.

Dentro de single-column, a ordem de foco é:

1. **cabeçalho mínimo e autocontido**;
2. **bool como tipo lógico**;
3. **binário/denso como representação física**;
4. demais tipos e variações, um por vez;
5. combinações entre tipos, exceções e representações.

Essa ordem é de **inspeção**, não de exclusão. Ao focar uma célula, o runner continua gerando a matriz
transversal já declarada. O foco muda quais arquivos são lidos em profundidade; não apaga combinações,
contraprovas nem sentinelas das outras rotas.

O `.8` só pode ser discutido como conjunto depois dos três estágios. Resultado positivo em single-column
não conclui multi-column; resultado positivo em ambos não conclui hierarquia.

## 2. Modelo de análise

Cada caso deve separar três perguntas que se confundem facilmente:

| camada | pergunta | exemplo |
|---|---|---|
| **semântica** | qual dataset precisa voltar? | `True` bool e não `"true"` string |
| **moldura** | qual informação irredutível precisa viajar? | tipo `b`, width, domínio, presença |
| **representação** | como o body carrega os valores? | TCF textual, RLE, dict, base64 denso |

Consequências:

- bool não é sinônimo de bitmap;
- bN não define sozinho a semântica de enum, null ou exceção;
- base64 é um transporte textual de bytes, não um tipo lógico;
- JSON é uma fonte/saída; o TCF recebe e devolve o **dataset materializado** pela linguagem;
- CSV e JSON podem conter superfícies parecidas e ainda produzir datasets e rotas diferentes;
- header menor só é ganho se continuar canônico, autocontido e fail-loud.

## 3. Regra experimental obrigatória

### 3.1 Ciclo focal e matriz transversal

Todo lab declara em arquivo uma matriz de casos antes de medir. O runner gera o produto cartesiano dos
eixos declarados para o ciclo. Uma célula incompatível não é omitida: aparece como `N/A`, acompanhada da
regra que a torna inaplicável.

Há dois níveis de cobertura em toda rodada:

1. **exaustivo no estágio ativo** - todas as combinações declaradas para a pergunta focal;
2. **sentinelas cross-route** - catálogo estável de single, multi e H, regenerado para detectar efeitos
   laterais fora do foco.

Adicionar uma capacidade ao estudo adiciona uma dimensão ou células ao manifesto; não autoriza escolher
manualmente apenas exemplos favoráveis. O relatório interpreta a matriz gerada, mas não é a fonte dela.

### 3.2 Fluxo visível de fonte para TCF

Para JSON, o fluxo mínimo materializado é:

```text
inputs/NN-fonte.json
  -> json.loads
intermediates/NN-dataset-consumido.json
  -> tcf.encode(dataset)
outputs/NN-wire.tcf
  -> tcf.decode
outputs/NN-dataset.roundtrip.json
  -> serialização JSON canônica
outputs/NN-fonte.roundtrip.json
```

O lab prova separadamente:

1. `dataset_decodificado == dataset_consumido`, sob igualdade adequada ao tipo;
2. o arquivo roundtrip é byte-idêntico ao canônico declarado em `intermediates/`;
3. o wire real é inspecionável e seu header/body são decompostos em artefato;
4. falhas esperadas são arquivos de resultado, não exceções escondidas no console.

Cada família focal inclui também uma fonte tabular semelhante quando houver equivalência útil:

```text
inputs/NN-fonte.csv
  -> dataset_reader/csv.reader
intermediates/NN-tabela-consumida.json
  -> tcf.encode(table)
outputs/NN-tabela.tcf
  -> tcf.decode
outputs/NN-tabela.roundtrip.csv
```

O par JSON/CSV não pressupõe que os objetos Python sejam iguais. Um manifesto declara o que é comparável:
valores de folha, ordem, tipos, cardinalidade e relação entre linhas. A diferença de rota também é dado:
JSON aninhado pode gerar `.8H`; tabela retangular pode gerar `.8M`.

Tipos fora de JSON padrão usam a extensão real da fonte (`.bin`, `.csv`, etc.) e um manifesto semântico
em JSON. Não se deve transformar bytes em string base64 na entrada e depois alegar que o tipo bytes foi
testado; nesse caso foi testada uma string.

### 3.3 Artefatos mínimos por lab

Todo novo lab segue `dirty-lab-convencoes.md` e contém:

```text
README.md
result.md
run.py
datasets-provenance.md
inputs/
intermediates/
outputs/
```

Além dos arquivos de fonte, wire e roundtrip, o runner produz:

- `intermediates/00-matrix.csv` - todas as células, com `run`, `pass`, `fail-expected` ou `N/A`;
- `intermediates/01-cases.json` - parâmetros completos, seed e versão do protocolo;
- `intermediates/NN-header.txt` - header separado e explicado byte a byte;
- `intermediates/NN-wire-breakdown.json` - bytes de assinatura, meta, domínio, body, padding e exceções;
- `intermediates/NN-obat-hcc-trace.txt` - SideOutputs e decisões do pipeline quando aplicáveis;
- `outputs/NN-wire.tcf` - wire real, sem reconstrução manual para o relatório;
- `outputs/NN-*.roundtrip.{json,csv,bin}` - extensão da fonte e diff executável;
- `outputs/00-measurements.csv` - bytes, tempo, memória e status de RT por célula;
- `outputs/01-malformed-results.json` - aceitação/rejeição de truncamentos e formas não canônicas.

O `run.py` regenera tudo de forma determinística e falha se:

- um artefato declarado não for produzido;
- uma célula desaparecer do manifesto;
- bytes forem agregados sem RT aprovado;
- serial e paralelo divergirem onde ambos se aplicam;
- o roundtrip não coincidir com o canônico declarado.

Probe de terminal orienta uma hipótese, mas não entra como evidência do plano até ser reproduzido no lab.

## 4. Matriz transversal

Cada ciclo escolhe valores concretos para os eixos abaixo. O manifesto registra inclusive os eixos que não
se aplicam ao foco.

| eixo | variações de referência |
|---|---|
| **fonte** | JSON, CSV/dataset tabular, dataset Python tipado, binário quando aplicável |
| **forma** | single, multi, H; sentinelas das três em toda rodada |
| **escala** | `N=0`, `1`, pequeno inspecionável, médio, realista `>1k`, extrapolação quando viável |
| **distribuição** | constante, alternada, runs, aleatória, skew, alta cardinalidade, cadência |
| **ordem** | fonte, seed embaralhada, agrupada/ordenada quando a ordem puder mudar |
| **presença** | sem null, all-null, null esparso/denso, ausente, vazio, exceção rara |
| **tipo aparente** | valor tipado, string homógrafa, número-código, valor fora do domínio |
| **body** | TCF/HCC, raw, dict, split, RLE/seq-RLE, denso/base64 e híbridos em estudo |
| **moldura** | baseline vigente e cada gramática candidata completa |
| **knobs** | fallback, stamp, min_header, drop_names, sort_by, nature, serial/paralelo quando válidos |
| **consumo** | decode completo, view/materialização seletiva, inspeção direta do wire |
| **transporte** | terminal, gzip, Brotli e zstd como lentes separadas, nunca como substitutos do RT |
| **integridade** | canônico, truncado, padding alterado, tag desconhecida, count/size/domínio inválido |

A rodada focal pode ampliar um eixo. Ela não reduz silenciosamente os anteriores. Quando o custo do produto
cartesiano exigir amostragem, o plano de amostragem, a seed e as células preservadas ficam no manifesto;
o relatório não escolhe a amostra depois de ver o resultado.

## 5. Estágio S - single-column

### S0. Baseline permanente

O catálogo executável `2026-07-23-0204-api-8-catalogo-de-casos` é a sentinela visual inicial. Cada ciclo
single acrescenta sua matriz própria e regenera, no mínimo:

- string órfã, com e sem stamp;
- nature single;
- lista tipada que hoje segue para `.8H`;
- single constante, alternada, em runs e alta cardinalidade;
- uma tabela `.8M` e um dataset `.8H` equivalentes como sentinelas externas;
- falhas de union, tipo não suportado e wire malformado.

O baseline serve para comparação. Não é uma decisão de manter o envelope atual.

### S1. Cabeçalho mínimo e autocontido

Pergunta focal: **qual é a menor moldura canônica que declara apenas o que o body não permite deduzir?**

As formas abaixo são candidatas de laboratório, não decisões:

```text
#TCF.8 :b
<body>

#TCF.8:b
<body>

#TCF.8b
<body>
```

O espaço vigente é uma dica de single-column. `:` pode ser testado como discriminador direto e substituir
essa dica se simplificar o parse sem perder namespace ou autocontenção. A contraprova sem assinatura,
como `:b\n<body>`, mede bytes, mas deve ser marcada como não identificável externamente.

#### Informação a classificar

Para cada candidato, o lab marca cada campo como **deduzido**, **default da versão** ou **escrito**:

- assinatura e versão;
- forma single-column;
- tipo lógico;
- modo físico do body;
- domínio, quando não for intrínseco ao tipo;
- largura em bits, bit order e alfabeto de transporte;
- número de elementos, tamanho do payload e padding;
- presença/nullability;
- canal de literais/exceções;
- nome opcional e nature/spec;
- fronteira header/body.

O header não deve declarar por hábito o que o body prova, nem omitir o que uma exceção torna ambíguo.

#### Critérios de revisão

1. **autocontenção** - um decoder recebe apenas o wire;
2. **canonicidade** - um dataset e uma configuração produzem uma única grafia;
3. **dispatch local** - a rota é identificada sem varrer o body;
4. **prefixo sem ambiguidade** - formas curtas não são prefixos perigosos de outras;
5. **fail-loud** - tipo/modo desconhecido, truncamento e grafia não canônica são rejeitados;
6. **extensibilidade** - tipos, natures e modos físicos possuem namespaces distinguíveis;
7. **inspeção** - o primeiro trecho do wire informa formato, forma, tipo e modo necessários;
8. **custo total** - assinatura + meta + body + padding + exceções, não só o token de tipo;
9. **streaming** - declarar count/size antecipadamente só quando a semântica exigir;
10. **paridade** - a mesma regra de tipo pode ser reutilizada em S, M e H.

#### Contraprovas obrigatórias

- `#TCF.8`, `#TCF.8 `, `#TCF.8:`, tags vazias e desconhecidas;
- colisão entre tipo primitivo e nature com o mesmo texto;
- nome opcional contendo `:`, espaço, `M`, `H`, prefixos de modo e backslash;
- body vazio: lista vazia, um valor vazio, um null e truncamento devem permanecer distintos;
- count ausente/presente divergente do body;
- payload com lixo após o último elemento;
- duas grafias semanticamente equivalentes: o decoder aceita só a canônica;
- arquivo aberto por ferramenta externa: assinatura continua detectável.

O resultado de S1 é uma tabela de propriedades e wires reais lado a lado. Escolher um byte a menos sem
fechar as contraprovas não conclui o cabeçalho.

### S2. Bool lógico

Bool deve ser revisto primeiro como domínio semântico `{false, true}`. O lab precisa manter distintos:

| entrada | tipo esperado |
|---|---|
| `true`, `false` em JSON | bool |
| `"true"`, `"false"`, `"True"`, `"False"` | string |
| `1`, `0` | number |
| `"1"`, `"0"`, `"Y"`, `"N"`, `"sim"`, `"não"` | string/enum, salvo spec explícita |
| `null` | null, não terceiro bool implícito |

#### Perfis mínimos

- `N=0` e `N=1` para cada valor;
- all-false, all-true e alternado;
- proporções `1/99`, `10/90`, `50/50`, `90/10`, `99/1` com seed fixa;
- runs curtos, médios e longos, alinhados e desalinhados;
- null esparso, null em runs, all-null e nullable alternado;
- um literal fora do domínio no início, meio e fim;
- typed bool JSON versus coluna CSV de strings visualmente iguais;
- pequeno inspecionável, `>1k` e escala realista.

#### Representações a comparar

1. envelope `.8H` vigente;
2. single tipado mínimo com body textual atual;
3. domínio bool implícito + referências textuais;
4. RLE/seq-RLE vigente;
5. dict explícito e dicionário interno da versão;
6. bitmap denso transportado em base64;
7. denso + RLE/segmentação, sempre competindo pelo wire total;
8. bitmap de presença separado versus domínio ternário;
9. canal de exceção/literal para perfis que o declararem.

O runner força cada representação para diagnóstico e também materializa o FLOOR completo. Uma forma não
é descartada só porque perde no agregado: o arquivo mostra em qual regime ganha ou perde. A decisão não
confunde economia de domínio, economia de header e economia do stream.

#### Medidas específicas

- bytes de assinatura, tipo, domínio, presença, body e exceções;
- bits úteis, padding e expansão base64;
- tempo e memória de análise, encode e decode;
- número de passadas e materializações intermediárias;
- legibilidade do wire e informação consultável sem decode completo;
- resultado terminal e sob compressores externos;
- custo no payload pequeno, onde o header não amortiza;
- RT tipado e distinção contra todas as strings homógrafas.

### S3. Binário/denso como representação física

Só depois da semântica bool, o modo denso é estudado como mecanismo geral. Há duas perguntas separadas:

1. **body binário/denso** para um tipo lógico conhecido, como bool ou enum;
2. **tipo lógico bytes**, que JSON padrão não possui.

#### Espaço físico

- widths exatas `1..8` e escadas propostas, sem reservar largura para semântica antes da medição;
- ordem dos bits e dos bytes;
- padding final e regra de validação dos bits não usados;
- count explícito versus dedutível;
- domínio implícito, domínio embutido e domínio externo;
- base64, hex e bytes crus como alternativas de transporte, respeitando o perfil textual;
- stream único versus blocos/segmentos;
- denso, RLE e composição adaptativa como candidatos concorrentes;
- acesso ao elemento, contagem e filtro sem materialização total;
- comportamento serial/paralelo e custo de cópias.

#### Integridade e forma canônica

O decoder de laboratório deve rejeitar:

- caractere fora do alfabeto;
- base64 com padding ou grafia alternativa não canônica;
- payload curto ou longo para `N` e `w`;
- índice fora do domínio;
- bits de padding não zero;
- width impossível;
- domínio duplicado ou vazio onde não permitido;
- exceção apontando para posição fora do stream;
- concatenação silenciosa de dois payloads.

#### Tipo bytes

O tipo bytes usa fonte `.bin` e roundtrip `.bin`. Também se mede uma fonte JSON que contém **string**
base64, mas ela é contraprova: sem uma declaração de tipo, continua string. Devem permanecer distintos:

- `b""`, bytes zero, bytes UTF-8 válidos e bytes UTF-8 inválidos;
- string vazia, string base64 e string hexadecimal;
- `bytes`, `bytearray` e `memoryview`, caso sejam admitidos pelo Dataset; caso contrário, falha tipada;
- um blob por elemento versus uma única coluna de octetos.

### S4. Fila de tipos e variações

Depois de cabeçalho, bool e binário, a mesma disciplina percorre os tipos abaixo. A ordem pode mudar por
achado do lab, mas nenhum item é dado como resolvido por analogia.

| ordem sugerida | família | distinções mínimas |
|---:|---|---|
| 1 | **null, ausência e vazio** | `None`, ausente, `""`, `"null"`, lista vazia, all-null, nullable |
| 2 | **number** | int, float, int+float sob `number`, `0`, `-0.0`, grandes, finitos, notação de origem |
| 3 | **string/Unicode** | homógrafas de tipos, LF/CR/backslash/NUL, NFC/NFD, emoji, vazia, alta entropia |
| 4 | **enum/categórico** | domínio fechado/observado, skew, runs, ordem, outlier, domínio em crescimento |
| 5 | **decimal e monetário exatos** | escala, zeros finais, sinal, moeda, `Decimal` versus float/string |
| 6 | **temporal** | date, time, datetime, timezone, duração, ISO string versus tipo declarado, cadência |
| 7 | **IDs e natures** | CPF/CNPJ/IP, UUID, códigos com zeros, máscara, checksum, exceção literal |
| 8 | **bytes/buffers** | blob, octetos, base64-string, buffer mutável/imutável |
| 9 | **especiais numéricos** | NaN, ±Infinity, sinal de zero; fronteira JSON e igualdade semântica |
| 10 | **union e tipos não suportados** | mistura por posição, tuple, set, chave não-string, tipos customizados |

Para cada família, o lab responde sempre:

1. qual identidade semântica precisa voltar;
2. como a fonte materializa o dataset realmente entregue ao TCF;
3. qual tag/default é necessário;
4. como null, ausência e exceção compõem;
5. quais representações físicas são aplicáveis;
6. quais superfícies visualmente iguais precisam permanecer distintas;
7. qual é o comportamento em S, M e H;
8. qual malformed deve falhar alto;
9. como bytes, tempo e memória variam por regime;
10. se o resultado é contrato `.8`, fronteira explícita ou pesquisa posterior.

## 6. Estágio M - multi-column

O estágio M reexecuta a matriz de tipos já exercitada em S e adiciona relacionamento entre colunas. Não
presume que a melhor forma single é automaticamente a melhor forma por-coluna.

### Eixos específicos

- 1, 2 e muitas colunas;
- todas do mesmo tipo, tipos heterogêneos e tipos homógrafos;
- cardinalidades e distribuições iguais/diferentes;
- domínio compartilhado, parcialmente compartilhado e disjunto;
- nullable em uma, algumas ou todas as colunas;
- ordem de colunas e posição da última coluna;
- nomes ausentes e nomes com todos os caracteres estruturais;
- sizes presentes/omitidos, hexadecimal e fronteiras de largura;
- modos `tcf`, `!raw`, `@dict`, `%split` e candidatos novos combinados no mesmo blob;
- type/nature + modo físico na mesma coluna;
- fallback, min_header, drop_names e sort_by isolados e compostos;
- serial/paralelo byte-idênticos;
- decode completo versus view, `select`, `where`, `group_count` e contagem estrutural;
- truncamento em cada coluna, bytes excedentes e divergência de `n_rows`;
- JSON objeto-de-arrays, CSV e dataset tabular equivalente.

### Cabeçalho M

A revisão separa:

1. **L1 por coluna** - semântica/tipo/body definidos no estágio S;
2. **meta M** - fronteiras, nome, tipo, modo e relação posicional;
3. **otimizações cross-column** - só depois de L1 e meta serem auditáveis.

O header é avaliado pelo blob completo. Remover nome, size ou domínio só é válido quando o restante do
wire ou um contrato explicitamente selecionado permite deduzi-lo sem ambiguidade. Otimização de uma coluna
não pode obrigar outra a abandonar seu candidato vencedor sem que o custo apareça no FLOOR total.

## 7. Estágio H - hierárquico

O estágio H reutiliza as conclusões de S para folhas e de M para composição de colunas. Não cria uma
segunda semântica de bool, number, null ou bytes apenas porque a folha está aninhada.

### Fontes e consumo

Cada família usa, quando possível:

1. arquivo JSON real ou realista;
2. `json.loads` materializado em `intermediates/` - o dataset efetivamente consumido;
3. fonte tabular semelhante produzida por CSV/dataset reader ou shaper;
4. wires `.8H` e `.8M` lado a lado;
5. roundtrip do dataset e roundtrip da fonte canônica;
6. manifesto do que é semanticamente comparável entre as duas formas.

### Matriz estrutural

- raiz escalar, objeto, array e vazios;
- objetos 1:1, arrays 1:N e profundidade recursiva;
- campos obrigatórios, opcionais, ausentes, null e vazios;
- arrays de escalares, arrays de objetos, array-em-array e ragged;
- uma e múltiplas coleções irmãs;
- folhas de cada tipo estudado em S;
- tipo constante, nullable, exceção e union na folha;
- counts, masks, repetition/definition levels e multiplicidade dedutível;
- nomes/chaves com caracteres estruturais e Unicode;
- ordem de chaves/itens e canonicidade do schema;
- escala estreita/larga e rasa/profunda;
- body por folha, meta de topologia e colunas de controle medidos separadamente;
- malformed em cada nível e falha localizada.

O JSON não é o teto conceitual do DatasetH, mas é o primeiro oráculo de consumo do `.8`: tudo que a fonte
JSON padrão materializa no domínio contratado deve fechar RT. Tipos além dessa borda são testados com
fonte e igualdade próprias, sem serem chamados de JSON.

## 8. Sequência de cada ciclo

1. formular uma pergunta falsificável e seu contraditório;
2. declarar e versionar a matriz antes da execução;
3. gerar inputs, datasets consumidos, wires, traces, malformados e roundtrips;
4. inspecionar arquivos representativos antes de agregar números;
5. executar adversarial sobre parser, canonicidade e colisões de tipo;
6. registrar resultado por célula, incluindo perdas e `N/A`;
7. regenerar sentinelas S/M/H e comparar manifests;
8. classificar o achado: semântico, moldura, representação, performance ou fronteira;
9. decidir com o owner o próximo foco;
10. só então abrir um novo ciclo ou pedir autorização para weld.

Um ciclo pode refutar uma forma sem encerrar o tipo. Pode confirmar semântica sem confirmar bytes. Pode
confirmar um body sem confirmar seu header. Essas conclusões permanecem separadas no `result.md`.

## 9. Próximos ciclos sugeridos

### Ciclo A - gramática single tipada

- materializar as formas com espaço, `:` direto e tag colada;
- decompor informação dedutível versus irredutível;
- exercer primitivos, nature, nome opcional, vazio e malformed;
- usar bool como âncora, sem escolher ainda seu body;
- regenerar o catálogo S/M/H.

### Ciclo B - bool completo

- manter as gramáticas de A lado a lado;
- executar todos os perfis semânticos, distribuições, nullable e exceções;
- forçar corpos textual/RLE/dict/denso e materializar o FLOOR;
- comparar JSON bool com CSV/string homógrafa;
- registrar tempo, memória, passadas e inspeção, além de bytes.

### Ciclo C - binário físico

- generalizar o body denso para widths e domínios diferentes;
- fixar ou refutar count, padding, bit order e base64 canônico;
- separar low-card indexado do tipo bytes;
- testar malformed e operações de view;
- reaplicar ao bool sem apagar as alternativas textuais.

### Ciclo D em diante - tipos

Começar por null/presença, seguir para number e string, depois enum, decimal, temporal, IDs/natures,
bytes e fronteiras. Cada ciclo usa o mesmo protocolo e volta às sentinelas das três formas.

## 10. Gates antes de estabilização

Nenhuma proposta sai do research-track apenas por reduzir bytes. Antes de estabilizar uma parte do `.8`:

- semântica e igualdade de RT estão declaradas;
- JSON/dataset e fonte tabular foram materializados quando aplicáveis;
- wires e roundtrips estão versionados e reproduzíveis;
- matriz não contém células desaparecidas ou falhas não adjudicadas;
- gramática é canônica, autocontida e fail-loud;
- tipo, presença, exceção e body compõem sem colisão;
- S, M e H reutilizam a mesma regra ou documentam por que não podem;
- serial, paralelo, decode e view concordam nas superfícies aplicáveis;
- claims de compressão passam os gates real-world do projeto e incluem bytes absolutos;
- snapshots byte-canônicos obrigatórios passam quando o código elegível for tocado;
- custo de encode/decode e memória é conhecido no regime em que o candidato vence;
- documentação distingue fato medido, hipótese e decisão do owner;
- qualquer alteração em `src/tcf/` recebeu aprovação explícita.

Fechar single, M ou H isoladamente não fecha o formato. A estabilização só entra em pauta após a revisão
integral e uma inspeção final dos artefatos, não pela quantidade de tickets marcados como concluídos.

## 11. Pontos de inspeção

- [catálogo executável da API `.8`](../../2026-07/2026-07-23/2026-07-23-0204-api-8-catalogo-de-casos/)
- [regra de implicitude single-column](../2026-07/2026-07-23-0259-implicitude-singlecol-logica.md)
- [modo denso e marcador de binarização](../2026-07/2026-07-23-0345-modo-denso-marcador-binarizacao.md)
- [registry de chars do header](../2026-07/tcf8-header-char-registry.md)
- [TCF e JSON: dois contratos](../2026-07/dataset-json-dois-contratos.md)
- [equivalência JSON](../../../../../docs/reference/json-equivalence.md)
- [plano DatasetH e escalares especiais](../2026-07/dataseth-hierarquia-completa-plano.md)
- [convenções do dirty lab](../2026-07/dirty-lab-convencoes.md)
- [ADR-0029: discriminador](../../../../../docs/adr/0029-version-format-identification-semi-implicit.md)
- [ADR-0030: single-column pré-1.0](../../../../../docs/adr/0030-freeze-single-col-body-at-1.0.md)
- [ADR-0033: codec hierárquico](../../../../../docs/adr/0033-hierarchical-codec-weld.md)
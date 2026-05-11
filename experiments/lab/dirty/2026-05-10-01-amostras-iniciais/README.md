# 01 — amostras iniciais

## Princípio / motivação

Nasceu sob o reset v0.6 (2026-05-10). Para testar qualquer algoritmo
de compressão depois, precisamos de **um catálogo de tipos de dados
com suas variedades**, não de um dataset pronto. A ferramenta aqui é
o próprio catálogo: descreve as ideias dos tipos, suas variações e a
regra de geração — qualquer outro experimento usa o catálogo para
fabricar dados sob medida ao que está testando.

A ferramenta é atemporal. Pode ser usada para experimentos do v0.6 ou
para reanalisar comportamentos descritos em `dirty/old/`. O foco é a
variedade, não um conjunto canônico de valores.

## Propósito

Responde a **viabilidade**: catalogar todos os tipos de dado que
aparecem em datasets relacionais comuns e em experimentos anteriores,
junto com seus eixos de variação e padrões de repetição. Sem este
catálogo, qualquer experimento posterior gera dados ad-hoc e perde
comparabilidade.

## Comparação

- Compara com: nenhum.
- É comparável? Não. É experimento **paralelo de fundação**: produz
  insumo (catálogo + amostras) para todos os experimentos seguintes.
- Não há baseline a vencer; há cobertura de variedade a documentar.

## Cenários e valores possíveis

Tipos cobertos (cada um com suas variações próprias):

- **Temporais**: datas (ISO, BR, US, por extenso, com hora, timestamp,
  com timezone, granularidade variável).
- **Identidade pessoal**: nomes (simples, composto, apelido, título,
  inicial, acento, não-latino), CPF, CNPJ.
- **Contato**: telefones (BR celular/fixo, internacional, formato
  TPC-H, com erros de cadastro), emails (1 domínio, multi-domínio,
  com tag/ponto/subdomínio).
- **Endereçamento**: URLs (curtas, longas, com query, hierárquicas),
  endereços (CEP, rua, complemento), IDs (sequencial, com prefixo,
  UUID).
- **Comerciais**: produtos (nome, SKU, hierárquico, com marca),
  valores monetários (BR, US, ISO, sem moeda).
- **Categóricos**: enums baixa/média/alta cardinalidade, booleans,
  status com vazios.
- **Numéricos**: inteiros pequenos/grandes, decimais, percentuais,
  notação científica.
- **Espécies**: frutas/animais com nome comum vs científico, com
  variedades regionais.
- **Texto livre**: curto, longo, com pontuação variada.
- **Ausência**: NULL em diferentes representações (`""`, `NULL`,
  `N/A`, `?`, `não informado`).

Sem afirmar que cobre o real. Cobre o que **observamos em**:
- 26 experimentos do `dirty/old/` (mapeados em ideias.md).
- Datasets canônicos `datasets/samples/adult-census/` e
  `datasets/samples/tpch-sf001/` (espreitados — anotações em
  observacoes-reais.md).

## Resultado observado

Saídas:

- [ideias.md](ideias.md) — catálogo principal por tipo, com eixos de
  variedade, falhas de cadastro, padrões realistas e regra de geração.
- [observacoes-reais.md](observacoes-reais.md) — o que vimos no Adult
  Census e TPC-H que orienta a geração sintética.
- [amostras/pequenas/](amostras/pequenas/) — 1 CSV por família de
  tipo, ~30 linhas, ilustrativos. **Não são canônicos**; são exemplos
  da regra documentada em ideias.md.
- [amostras/grandes/](amostras/grandes/) — gerados sob demanda por
  futuro experimento, seguindo as regras do catálogo.

Não há métrica de bytes/tempo/RT neste experimento. Nenhuma comparação
"melhor/pior" se aplica.

## Limitações

- O catálogo NÃO cobre todos os tipos do mundo — cobre os tipos
  observados em 26 labs antigos + 2 datasets canônicos.
- As regras de geração são deterministas com seed; **não são
  estatisticamente representativas** do real. São representativas das
  IDEIAS de variação. Para realismo estatístico (distribuição de
  cardinalidade, frequências), usar dados reais via DatasetReader.
- "Falhas de cadastro" listadas são as mais comuns observadas; outros
  modos de falha existem e não estão cobertos.
- O catálogo será expandido conforme experimentos posteriores
  encontrem tipos não cobertos. **Não é congelado** após este
  experimento.

# Proveniência dos dados

**Oito fontes reais, todas pelo Shaper, todas com estratificação proporcional.** Nada de
sintético e nada de `LIMIT N`: a regra do projeto é que teste de massa usa o Shaper, que
responde representatividade, dimensionamento e distribuição, e grava as métricas.

## As fontes

| amostra | dataset canônico | tabela | população | estrato | o que ela traz de próprio |
|---|---|---|---:|---|---|
| adult-census | `adult-census` | `adult` | 48.842 | `education` | 15 colunas, mistura de int e categórico de baixa cardinalidade |
| online-retail | `online-retail` | `online_retail` | 541.909 | `Country` | texto livre em `Description`, float de preço, cauda de 38 países |
| ibge-municipios | `ibge-municipios` | `municipios` | 5.571 | `uf_sigla` | nomes próprios com acento, hierarquia geográfica redundante |
| br-identidades | `br-identidades` | `pessoas` | 500.000 | `uf_sigla` | CPF formatado, email, data ISO: o território das natures |
| tpch-orders | `tpch-sf001` | `orders` | 15.000 | `o_orderstatus` | chave de alta cardinalidade ao lado de status de 3 valores |
| tpch-lineitem | `tpch-sf001` | `lineitem` | 60.175 | `l_returnflag` | 16 colunas, a mais larga do conjunto, muitos decimais |
| receita-cnpj | `receita-cnpj` | `estabelecimentos` | 200.000 | `situacao` | dado público real, nome fantasia com ruído de digitação |
| wine-quality | `wine-quality` | `wine` | 6.497 | `quality` | 13 colunas todas numéricas, float denso |

Volume: **800 linhas** por amostra, `seed=42`. O dimensionamento é para *consistência*, não
para escala: o que se verifica é se as regras valem em formas de coluna diferentes.

A escolha das oito não é por conveniência. Cada uma traz uma forma que as outras não têm, e
duas delas existem no conjunto justamente para serem desfavoráveis: o `ibge-municipios` é quase
todo valor distinto (onde o dicionário não paga) e o `wine-quality` é float denso (onde o
dicionário é o pior caso). Medir só nas favoráveis responderia a pergunta errada.

## A estratificação

Proporcional, sobre a coluna de estrato, com as métricas gravadas pelo próprio Shaper em
`intermediates/<amostra>.shaper-trace.txt`: TVD, JSD, Hellinger e qui-quadrado, mais a
contagem de cada estrato na amostra e na população.

O TVD ficou entre **0,0003 e 0,0206**. O maior é o do online-retail, e é esperado: 38 países
com cauda muito longa, onde estratos de uma dúzia de linhas na população não sobrevivem
inteiros a uma amostra de 800. Os traces registram o aviso de N baixo onde ele aparece.

## Dados pessoais

O `br-identidades` é **sintético gerado**, não é cadastro real: os CPFs são placeholders
mod-11 válidos que a Receita nunca emitiu, então não correspondem a pessoa alguma. O
`receita-cnpj` é dado **público** de pessoa jurídica. Nenhum CPF de pessoa real, e nenhum
valor de qualquer amostra é publicado neste repositório: `inputs/amostras.entrada.json` guarda
**três linhas** por amostra, o suficiente para conferir a forma.

Os SQLite ficam fora do repositório (`Z:\tcf-data\interim\`), por convenção de infraestrutura.

**Nada em `src/tcf` foi tocado.** O lab importa `encode`, `decode`, `view` e o encoder
hierárquico interno (para reconstruir o baseline do que a mesma entrada emitia antes), e só lê.

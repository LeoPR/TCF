**Português** · [English](README.md)

# `docs/divulgacao/`: material para apresentar o TCF

Peças para mostrar o projeto publicamente. É material de apoio, não é a documentação da
biblioteca, que fica nas pastas irmãs desta. Não publica medição nova: todo número vem de um
documento datado do repositório, e cada um nomeia onde é reproduzido.

## Como está organizado

A **raiz** guarda a **fonte de notícia** datada: um arquivo por anúncio, com o estado, as
manchetes e os limites ditos por inteiro. As **subpastas** são os **canais**, e cada uma dá
àquela fonte o formato que o meio aceita.

A regra que mantém os dois alinhados: nenhum texto de canal muda sem a fonte datada mudar antes.

| Caminho | O que é |
|---|---|
| [`2026-09-04-lancamento.md`](2026-09-04-lancamento.md) / [`2026-09-04-release.en.md`](2026-09-04-release.en.md) | a fonte de notícia atual (PT / EN) |
| [`linkedin/post.*`](linkedin/) | a peça curta do feed, uma por língua |
| [`linkedin/artigo.*`](linkedin/) | o artigo, uma por língua, **já pronto para colar** |
| [`linkedin/figuras/<língua>/`](linkedin/figuras/) | as cinco figuras, uma pasta por língua |

São dois textos por língua e nada além disso. O LinkedIn tem duas áreas, o post do feed, com
limite duro de caracteres, e o artigo, que aceita texto longo mas numa coluna estreita. Cada
arquivo atende uma delas.

Fica sob `docs/` porque **documento de divulgação é documento**. Uma segunda hierarquia na raiz
faria o leitor escolher entre dois lugares para procurar a mesma coisa.

**O artigo já sai pronto para colar.** O editor do LinkedIn não renderiza tabela e a coluna é
estreita, então o artigo não tem tabela: onde ela caberia, ele chama a figura `4-tabela`, que sai
dos mesmos números para texto e imagem não divergirem. Os blocos de código também são estreitos
por isso. Cole o texto e suba as figuras onde ele as chama.

As figuras ficam em `linkedin/figuras/<língua>/`, uma subpasta por língua para o diretório do
canal não misturar texto com binário. O `scripts/make_divulgacao_figuras.py` gera todas, e
rodá-lo regenera tudo. Elas obedecem à mesma regra dos números do texto: existe um comando que
as reproduz.

Elas saem em **SVG**, que é texto e dá para editar. O PNG que o LinkedIn pede sai junto só se
`cairosvg` estiver instalado, e o script avisa em vez de falhar quando não está.

Nenhuma é ilustração. As barras são bytes medidos com o roundtrip validado antes, o wire
desenhado é o que o `encode` devolve de fato, e as colunas materializadas da figura 3 saem do
`view.report()`.

São cinco por língua, numeradas na ordem de leitura: `0-capa` é o quadro 1.91:1 do topo,
`1-formatos` compara os quatro formatos, `2-wire` anota a saída real, `3-view` mostra o que uma
consulta materializa, e `4-tabela` é a tabela de compressão que o editor não renderiza.

Aqui o português é a língua canônica, ao contrário do resto do projeto, porque o público a que
estes textos se dirigem lê português primeiro. O inglês é a tradução.

## Limites de cada canal

- **Post do LinkedIn** (`linkedin/post.*`): cerca de 3.000 caracteres, e só as duas ou três
  primeiras linhas aparecem antes do "ver mais". Essas linhas não podem conter jargão: o público
  é largo, e uma primeira frase que só fala com quem já conhece compressão filtra em vez de
  convidar. Contexto antes de jargão, densidade sem tom professoral, e um fecho que fecha em vez
  de parar. Hashtags no fim e sem acento, porque hashtag acentuada quebra a busca do LinkedIn.
- **Artigo do LinkedIn** (`linkedin/artigo.*`): formato longo, com títulos renderizando, bom
  para a versão que carrega os números. **Tabela não renderiza e a coluna é estreita**, então
  nada de tabela e nada de linha larga: o que seria tabela vira figura. Termina com o link do
  repositório.

## Antes de publicar

**Nenhum número destes textos tem instrumento próprio, e isso é deliberado.** Cada um continua
pertencendo a quem já era dono dele: os tamanhos canônicos ao `tests/test_regression_v1_baseline.py`,
que pina byte a byte e roda o roundtrip da §RT; os ganhos em dado real ao relatório datado do
EXP-019; os tempos ao baseline pinado do `scripts/bench_perf`. Um script de divulgação medindo o
mesmo criaria uma segunda verdade para divergir da primeira.

O que a divulgação acrescenta é que **os exemplos rodam**. A fonte vigente e os artigos estão no
`PAGINAS_DIDATICAS` do `tests/test_docs_snippets.py`, junto com o README e a referência, e a
fonte carrega as próprias asserções de tamanho. Um número que ficar velho quebra a suíte.

**O que estes textos evitam de propósito:**

- superlativo. O gancho é o problema do leitor, não a vantagem do projeto;
- dizer "menor" sem dizer contra o quê, medido de que jeito, e em que dado;
- histórico de desenvolvimento. Estes textos dizem o que a biblioteca faz hoje. O caminho até
  aqui fica no `CHANGELOG.md`, nas ADR e nos labs datados, que é onde alguém procura de
  propósito. A razão é do leitor: quem chega agora nunca viu a versão antiga.

**Não suavize a seção de limites.** Ela é curta, é verdadeira, e é a parte que dá credibilidade
ao resto. Aqui ela inclui o que não favorece o projeto: sob `gzip` os formatos empatam dentro de
1 B, o CSV passa o TCF depois de comprimido no tamanho minúsculo, a otimização de algoritmo é o
ciclo seguinte e ainda não aconteceu, e a comparação com Parquet não foi feita.

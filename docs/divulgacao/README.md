# `docs/divulgacao/`: material para apresentar o TCF

Peças para mostrar o projeto publicamente. É material de apoio, não é a documentação da
biblioteca, que fica nas pastas irmãs desta. Não publica medição nova: todo número vem de um
documento datado do repositório, e cada um nomeia o comando que o reproduz.

## Por que aqui dentro, e não numa pasta própria na raiz

O molde desta pasta veio do `outreach/` do PatchCraft, que fica na raiz do repositório. Aqui a
decisão foi outra, e ela é deliberada: **documento de divulgação é documento**, então mora na
`docs/` junto com o resto. Uma segunda hierarquia de documentação na raiz faria o leitor
escolher entre dois lugares para procurar a mesma coisa, e pasta demais atrapalha mais do que
organiza.

Pela mesma razão, o canal é **prefixo de nome de arquivo** e não subpasta. Se amanhã entrar um
segundo canal, ele entra como `<canal>-post.md` ao lado, sem nível novo. A única subpasta
prevista é `figuras/`, e ela existe só para não misturar binário com texto.

## Como está organizado

A separação que segura tudo é entre **fonte** e **canal**.

A **fonte de notícia** é datada e canônica: um arquivo por anúncio, com o estado do projeto,
as manchetes na ordem que interessa a quem nunca ouviu falar do TCF, e os limites ditos por
inteiro. Os **textos de canal** são a mesma fonte no formato que cada meio aceita.

A regra que mantém os dois alinhados: **nenhum texto de canal muda sem a fonte datada mudar
antes.** E a fonte anterior não se reescreve, fica como registro do que foi dito naquele dia.

| Padrão de nome | O que é |
|---|---|
| `<data>-<assunto>.md` | registro datado: fonte de notícia, ou um texto como foi publicado |
| `<canal>-<peça>.md` | texto de canal, sempre o vigente |
| `pitch-curto.md` | o resumo de um parágrafo, sem canal, para colar em qualquer lugar |
| `figuras/` | só imagem, PNG para subir e SVG ao lado para editar |

O que já existe:

| Arquivo | O que é |
|---|---|
| [`pitch-curto.md`](pitch-curto.md) | o pitch de um parágrafo, com o `JSON → CSV → TCF` em bytes reais |
| [`2026-08-25-linkedin-0.8.2.md`](2026-08-25-linkedin-0.8.2.md) | o post da `0.8.2`, versão longa e curta. Registro datado, **não se reescreve** |

## Limites de cada canal

**Post do LinkedIn**: cerca de 3.000 caracteres, e só as duas ou três primeiras linhas
aparecem antes do "ver mais". Essas linhas não podem ter jargão. O público é largo, e uma
primeira frase que só fala com quem já conhece compressão filtra em vez de convidar. Contexto
antes de jargão, densidade sem tom professoral, e um fecho que fecha em vez de parar. Hashtag
no fim e sem acento, porque acento quebra a busca do LinkedIn.

**Artigo do LinkedIn**: formato longo, com título e tabela renderizando, que é onde os números
cabem. Termina com o link do repositório.

Um detalhe do editor do LinkedIn que vale saber antes de escrever: ele não faz tabela e não faz
código no meio da frase. Em vez de piorar o artigo para caber nele, o certo é manter o artigo
bom e gerar dele uma versão para colar, com a tabela virando imagem.

## As regras que fazem o texto valer

**Todo número tem comando que reproduz.** Nada é estimativa, e nada é arredondado para soar
melhor. Vale aqui a mesma regra §RT do resto do projeto: **não se reporta byte sem roundtrip
validado**, nem em texto de divulgação.

**Nada é ilustração.** Uma vantagem que o TCF tem sobre um projeto de imagem: o wire é texto
legível, então a "figura" pode ser a saída real do `encode`, colada. Onde entrar imagem de
verdade, ela sai de script que se roda de novo, não de desenho.

**A superfície carrega só o presente.** Estes textos dizem o que a biblioteca faz hoje. O
caminho até aqui fica no `CHANGELOG.md`, nas ADR e nos labs datados, que é onde alguém procura
de propósito. A razão é do leitor, não de coragem: quem chega agora nunca viu a versão antiga,
e contar a correção só transmite que o projeto errou, antes de a pessoa saber para que ele
serve.

**Sem superlativo.** O gancho é o problema do leitor, não a vantagem do projeto.

**Não suavize a seção de limites.** Ela é curta, é verdadeira, e é a parte que dá credibilidade
ao resto. No TCF ela inclui coisas que não favorecem o projeto e ficam mesmo assim: sob `gzip`
os formatos empatam dentro de 1 B, o CSV passa o TCF depois de comprimido no tamanho minúsculo,
e as otimizações de algoritmo são o ciclo seguinte e ainda não aconteceram.

**O português é a língua canônica aqui**, ao contrário do resto do projeto. O público a que
estes textos se dirigem lê português primeiro, e a tradução entra quando for publicar em
inglês, não antes.

## Antes de publicar

Uma pendência **aberta** e que vale fechar antes de aumentar o número de pessoas olhando o
repositório: o levantamento de 2026-09-02 encontrou 265 CPFs com dígito verificador válido em
arquivos versionados, um deles em `src/tcf/natures/__init__.py`, que embarca na wheel. São
números sintéticos e não vazamento, mas o critério do projeto fala de DV válido e não de
origem. O verificador é `scripts/scan_cpf_dv.py`, e o registro está em
[`T-QA-8`](../../tickets/T-QA-8-material-comprobatorio.md).

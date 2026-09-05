**Português** · [English](post.en.md)

# Resumo curto (reels / feed), apontando para o artigo e o repositório

> **Nota de publicação, fora do corpo do post.** Chamada para feed ou legenda de reels,
> com orçamento de até 3.000 caracteres. O conteúdo completo está em
> [artigo.pt-BR.md](artigo.pt-BR.md); os números vêm do
> [documento de lançamento](../2026-09-04-lancamento.md).
> Substitua o marcador do link após publicar o artigo. O corpo está em texto simples,
> sem depender de formatação Markdown. Figuras em [figuras/pt-BR/](figuras/pt-BR/).

---

Um cadastro pode repetir a mesma cidade centenas de vezes.
E se fosse possível ocupar menos espaço sem esconder essa estrutura?

Essa é a proposta do TCF, Tabular Compact Format: representar dados repetitivos de forma
compacta, sem perdas, mantendo um texto que pode ser aberto em um editor.

Por exemplo, três ocorrências consecutivas de uma cidade podem ser escritas como
*3|Sao Paulo. O marcador diz "repita este valor três vezes". A informação permanece;
muda a maneira de representá-la.

Num cadastro de quatro pessoas apresentado no artigo, os mesmos dados ocupam 451 bytes
em JSON compacto, 277 em CSV e 242 em TCF, com a reconstrução exata verificada.
Esses tamanhos são sem compressor externo e valem para esse exemplo, não para toda tabela.

O interesse vai além do tamanho. Como o marcador também informa uma contagem, algumas
consultas podem aproveitar a estrutura sem reconstruir todos os registros. Com a função
view(), uma soma filtrada por cidade pode acessar apenas cidade e valor, sem decodificar
as outras colunas.

Isso não torna o TCF um substituto do gzip: os dois podem ser combinados. No exemplo,
sob gzip, JSON e TCF empatam em tamanho, e o CSV comprimido é menor. Codificar também tem
um custo que precisa ser medido, especialmente quando os dados mudam a cada requisição.

O projeto é aberto, ainda pré-1.0, e requer Python 3.10 ou mais novo, sem dependências de
execução. A licença é MIT.

No artigo, explico o funcionamento, mostro as medições e discuto os limites:
[link do artigo, preencher depois de publicar]

Código, documentação e exemplos:
https://github.com/LeoPR/TCF

#Python #Compressao #DataEngineering #OpenSource #FormatosDeDados

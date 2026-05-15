# Quebra de linha como marcador — teoria geral

**Data**: 2026-05-13
**Tipo**: nota teorica transversal (vale para qualquer macro do dirty)
**Contexto de origem**: discussao no macro M4 (desfragmentacao da
arvore), durante analise de buffer/refragmentacao. User levantou
visao mais profunda sobre a natureza do arquivo de entrada.
**Conecta com**: [`../2026-05-13-M4-desfragmentacao-arvore/notas/buffer-e-refragmentacao.md`](../2026-05-13-M4-desfragmentacao-arvore/notas/buffer-e-refragmentacao.md)
(buffer e chunking), [`../README.md`](../README.md) (camadas de custo).
**Status**: registrada para revisita futura — nao ha' acao imediata.

## Tese central

> Arquivos texto colunares sao, em ultima analise, uma sequencia
> sem fim binaria com uma formatacao **muito conveniente**.

Essa formatacao tem 3 conveniencias que tiram a "cara totalmente
binaria":

### Conveniencia 1 — escopo ASCII limitado

Texto tabular tipico usa um SUBCONJUNTO pequeno do espaco de
bytes (256 possiveis):
- letras maiusculas/minusculas (~52)
- digitos (10)
- alguns separadores (`,`, `;`, `\t`, `.`, `@`, `-`, `_`)
- escapes/aspas (`\\`, `'`, `"`)

Concentracao real: tipicamente 40-80 chars unicos por dataset.
**Consequencia**: alfabeto efetivo pequeno → margem grande para
recodificacao binaria (Huffman, ANS, etc).

### Conveniencia 2 — quebra de linha = chunk semantico

Cada linha **e' como se dissesse**: "esse grupo de caracteres tem
uma caracteristica diferente da proxima". Funcionalmente equivale
a fazer **chunking automatico** do stream.

**Consequencia**: o container "linha" facilita:
- Processar uma "unidade logica" por vez
- Detectar padroes dentro do container (M1)
- Detectar padroes entre containers (M2, M3)
- Aplicar RLE adjacente (containers identicos consecutivos)

### Conveniencia 3 — quebras de linha sao MARCADORES

Para a versao comprimida (TCF), as quebras de linha **tambem podem
ser vistas como marcadores**, nao como estrutura imutavel.

> A gente pode "sumir" ou "reaparecer" as quebras de forma
> inteligente. Nao temos compromisso de manter as quebras de linha.
> Podemos olhar elas tambem como caracteres comuns que podem ser
> "deduzidos".

**Consequencia**: oportunidade adicional de compressao se as
quebras forem tratadas como chars comuns deduziveis.

## Trade-off (risco vs oportunidade)

| Aspecto | Manter quebras | Tratar como char comum |
|---|---|---|
| Container natural pra trabalhar | sim — facilita | perde |
| Compressao potencial | limitada por container | maior espaco |
| Complexidade do decoder | menor | maior |
| Streaming/parcial | natural (linha = unidade) | requer outro mecanismo |
| Risco de perder estrutura semantica | baixo | maior |

**E' arriscado** porque as quebras servem de container que facilita
trabalhar "um pedaco por vez". Mas **da' margem** para tecnicas
que tratam o stream inteiro como sequencia.

## Implicacoes possiveis (para revisita futura)

1. **Pos-RLE de quebras**: se varias quebras consecutivas viram
   marcador unico no formato (raro em texto tabular mas vale
   considerar).
2. **Compressao de quebras em runs adjacentes**: quando RLE
   coalesce N linhas em `*N|<linha>`, as N-1 quebras desaparecem.
   Ja fazemos isso parcialmente.
3. **Deducao de quebras**: se cada linha tem padrao previsivel
   (ex: ~30 chars), decoder pode inferir onde estao sem marcar.
   Risco: linhas de tamanho variavel quebram a inferencia.
4. **Container alternativo**: em vez de quebra-de-linha, usar
   marcador binario ou nenhum (delimitar por tamanho). Muda
   completamente a "cara" do TCF.

## Conexao com camadas de custo

Na convencao das 4 camadas de custo do dirty v0.6
([../README.md](../README.md)):

- Camada 1 (dados efetivos): chars das strings — afetados se
  quebras virarem chars comuns
- Camada 2 (marcadores de referencia): `,`, `..`, `\`, etc — nao
  afetados diretamente
- **Camada 3 (marcadores macro)**: quebras de linha, delimitadores
  `[`/`]`. Tradicionalmente "escala pequena, nao contamos bytes"
  — mas se quebras virarem deduziveis, podem reduzir bytes
- Camada 4 (comentarios): nao se aplica

A teoria sugere que **camada 3 pode ter mais oportunidade do que
considerado ate' agora** se tratarmos quebras como sinal
deduzivel.

## O que NAO fazer agora

- NAO implementar nada baseado nesta teoria no estado atual do
  dirty
- M4 atual e' sobre desfragmentacao da arvore — outra dimensao
- Quebras de linha viram tema relevante no prototipo ou em macro
  futuro

## Quando revisitar

- Apos M4 fechar: avaliar se faz sentido como M5
- Em discussao do formato canonico do prototipo (decidir se quebras
  sao parte do contrato ou opcionais)
- Se algum dataset real (futuro) revelar que quebras consomem %
  significativo dos bytes totais

## Resumido em 1 linha

"Quebras de linha sao marcadores opcionais, nao estrutura
inviolavel — futuro: deduzir/comprimir quebras como char comum."

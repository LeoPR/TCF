# Proveniência — delimitador do flip, variantes materializadas (2026-07-26-0038)

**Fonte**: 100% sintético/determinístico (LCG de seed fixa). Nenhum download, nenhum dado real.

## As 12 formas

Escolhidas para **cobrir chars e regimes**, não para amostrar frequência de uso real:

| forma | tag | por que existe |
|---|---|---|
| `int-ruido` | `n` | número puro sem cadência — o caso que o owner apontou |
| `int-seq` | `n` | cadência limpa: corpo minúsculo, o flip é irrelevante |
| `hex` | `s` | dígitos sem separador — o melhor caso do flip |
| `data-br` | `s` | traz `/` e a **adjacência ambígua** |
| `telefone` | `s` | traz `(` `)`; ganha **apesar** de ter adjacência |
| `moeda` | `s` | traz `$`; ganho grande com poucas adjacências |
| `versao` | `s` | pontuação densa entre números |
| `email` | `s` | mais referência que escape — controle negativo |
| `url` | `s` | traz `:` `?` `=`; texto com números |
| `path` | `s` | traz `/`; texto com números |
| `json-ish` | `s` | traz `"` `{` `}` `:` — o pior caso medido |
| `com-delim` | `s` | **o delimitador `;` aparece no dado** — testa o escape do próprio delimitador |

`n = 500` em todas, para os bytes serem comparáveis entre formas.

## O que é medição e o que não é

**Tudo nesta rodada é medição.** As três formas são materializadas e gravadas; os bytes são
`len(wire.encode())` do arquivo real, cabeçalho incluído.

Isso corrige a 1ª rodada, que estimava (`ganho − contagem × 1 B`) e só gravava o corpo normal.
A estimativa acabou batendo em 1–2 B com o medido — o desvio é exatamente o cabeçalho, que
ela não contabilizava. Mas **sem os arquivos não havia como conferir**, que era a objeção.

## Validação — e o que ela NÃO provava

**Correção após verificação adversarial.** O protocolo original era:
`de_flip(para_flip(corpo)) == corpo`, seguido de `decode` do corpo **des-flipado**. Isso é
**circular**: testa a consistência do par de funções deste lab, não a decodabilidade da forma
flipada. Nenhum `.tcfp` era passado ao `decode`.

Um verificador independente escreveu um leitor do corpo FLIP e achou 2 de 12 colunas com
RT=OK e wire corrompido. Um **detector estrutural** foi então escrito aqui (sem usar o
round-trip) e chega às mesmas 2 — confirmação cruzada de implementações independentes.

**Um fuzz de round-trip, por maior que fosse, não acharia os bloqueadores 2 e 3** — neles o
round-trip passa. Só decodar a forma proposta acha.

## Validação (o que continua valendo)

- **Inversas**: `polaridade.py` define `para_flip_*` e `de_flip`; o lab exige
  `de_X(para_X(corpo)) == corpo` byte a byte. Sem isso, qualquer medida de tamanho seria
  medida de uma transformação com perda.
- **RT ponta a ponta**: cada wire flipado é des-flipado, remontado com o cabeçalho normal e
  passado pelo `decode` **REAL** do `src/tcf`. 36/36.
- A forma `com-delim` é o teste de que o esquema aguenta o **próprio delimitador** dentro do
  dado.

## Limites declarados

- **`;` é placeholder.** A escolha do char é decisão do owner; trocá-lo altera só a linha
  `com-delim`.
- **Protótipo**: os `.tcfp` não são decodáveis pelo `src/tcf` — daí a extensão. Nada soldado.
- **Single-col apenas.** Multi-col e `.8H` fora do escopo.
- **Métrica única: bytes.** Sem gzip, sem latência, sem custo de CPU do parser (que é
  justamente onde `flipA` e `flipB` diferem — e isso **não** foi medido).

## Reprodutibilidade

`python run.py` regenera byte a byte — LCG de seed fixa, sem `random` global, sem relógio,
sem rede. **Zero escrita em `src/tcf`.**

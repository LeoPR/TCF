# ADR-0035 — Delimitador de polaridade no single-col (camada de borda)

- **Status**: aceito (weld 2026-07-26)
- **Escopo**: single-col `#TCF.8` (version-stamp) e `#TCF.8<tag>` (tipado). **Fora**: `.8M`,
  `.8H`, `#TCF.8 :spec`, órfão (`stamp=False`).
- **Supersede**: nada. **Interage com**: ADR-0024 (git-as-compat / baselines re-pináveis),
  ADR-0029/0034 (header), ADR-0032 (discriminador).

## Contexto

O corpo canônico escapa corrida de dígito **literal** com `\`; dígito **nu** é referência a
fragmento. Isso custa **1 byte por literal**. Em coluna formatada (documento, cartão, CEP,
timestamp) quase todo dígito é literal e o escape carrega informação quase nula — no CPF, a
sequência de decisões literal/referência é constante ao longo da coluna inteira.

Três propostas anteriores tentaram remover o escape e falharam pelo mesmo motivo, medido nos
labs `2026-07-26-0038`, `-0200` e `-0330`:

> O escape carrega **duas** informações: o **tipo** (literal × referência) e a **fronteira**
> entre corridas de dígito. Apagá-lo funde `56\033` em `56033`.

## Decisão

Marcar a **troca de estado**, não cada literal. Um char delimitador inverte o estado
literal↔referência; por estar *entre* as duas corridas, ele carrega a fronteira junto.

```
canônico     56\033-\0910-\4383      1 escape por LITERAL
polarizado   56!033-0910-4383        1 byte por TRANSIÇÃO
```

### Camada de borda, não grafia canônica interna

```
encode:  ... -> corpo canônico (JÁ com seq-RLE) -> polariza   -> wire
decode:  wire -> despolariza -> corpo canônico -> parser de sempre
```

O `seq-RLE` (`hcc_seqrle.find_escape_digit_runs`) localiza o dígito incrementável **pelo
escape**. Como a polarização é a última etapa do encode e a primeira do decode, ele só vê
corpo canônico dos dois lados. Tornar o delimitador grafia canônica **interna** exigiria o
seq-RLE achar o dígito pela polaridade — **questão aberta, fora deste ADR**.

### O char é eleito, não fixo

Não se pergunta "qual char usar", se pergunta **onde existe conflito**: o alfabeto que a
coluna realmente usa. O complemento tem conflito zero por construção — sem lista de
candidatos e sem escapar o próprio delimitador.

A `FAIXA` é **só pontuação ASCII fora da gramática** — nem dígito, nem letra. Exclusão por
**classe**, não por lista, por dois defeitos que a auditoria adversarial do lab
`2026-07-26-2126` reproduziu:

| classe | defeito |
|---|---|
| **dígito** | o delimitador **funde** com a corrida que deveria delimitar: com `0` eleito, `1\22.\33` vira `1022.33` e a volta deixa de ser exata |
| **letra** | o sufixo pousa no índice 6 — o slot do **discriminador**. Uma coluna de STRING elegia `b` e emitia `#TCF.8b`, byte-idêntico ao cabeçalho de uma coluna bool |

Excluir por classe fecha os dois e **continua fechado quando surgir tag nova**.

### Gramática do cabeçalho

```
#TCF.8<tag><sufixo>        tag = alfanumérico (ou vazio)   sufixo = 1-2 chars de pontuação
```

`#TCF.8!` = polaridade inicial `R`; `#TCF.8!!` = `L` (char dobrado). A separação é inequívoca
**por construção**: a FAIXA exclui dígito e letra, e nenhum discriminador de hoje (`M`, `H`,
`b`, `n`, `s`, espaço, vazio) é pontuação. `#TCF.8 nome:id` não casa o padrão e segue intocado.

### A decisão é uma conta, não um experimento

Uma varredura acumula três coisas; a decisão lê os acumuladores sem tocar no dado de novo:

```
presentes   alfabeto da coluna   -> elege o char
trocas_R    contador             -> polaridade inicial R
trocas_L    contador             -> polaridade inicial L
```

**FLOOR incluindo o custo do próprio sufixo** — mesmo padrão do `hcc_seqrle` e do
`min(tcf, raw, dict, split)` do multi-col. Empate fica com a grafia de hoje. Nunca-pior por
construção: nenhuma coluna sai maior.

## Consequências

### Baselines re-pinados (ADR-0024)

| gate | antes | depois | Δ |
|---|---:|---:|---:|
| D1-D9 | 1586 | **1545** | −41 (só D5 e D6 mexeram) |
| D17a (multi) | 300 | **300** | 0 — `.8M` fora do escopo |
| real-world | 89637 | **89430** | −207 (só `stockcode`; as 2 colunas de texto livre não mexeram) |

Suíte: **1010 passed, 3 skipped**.

### Compatibilidade

Wire novo não é legível por decoder anterior a este commit. Pré-1.0 isso é git-as-compat
(ADR-0024) — **não** houve bump de `#TCF.8`, coerente com a política de minors como
marcadores de dev.

### Um bug do próprio weld, corrigido

O FLOOR da `nature` comparava o candidato contra um baseline **não polarizado**, o que daria
vitória à nature em disputa que ela perde de fato. O baseline agora compete na mesma grafia
que será emitida.

## Alternativas descartadas

| alternativa | por que não |
|---|---|
| apagar o escape quando a coluna não usa referência | 1 de 12 colunas formatadas (lab `-0200`); e quebra o seq-RLE em silêncio |
| inverter a polaridade sem delimitador (flip) | retratado — 3 bloqueadores, incluindo colisão com a grafia do slot nulo (lab `-0038`) |
| máscara: o fluxo L/R num canal separado com RLE | cobria 3 de 8 colunas; perde a **fronteira**, e o `cartao` corrompia (lab `-0330`) |
| char fixo (`/`) declarado no cabeçalho | char precisa ser eleito por coluna; e `/` aparece em dado real (data BR, CNPJ) — lab `-1913` |
| deduzir o char pelo menor da faixa presente no corpo | 18 de 29 colunas (lab `-1954`): falha quando o dado usa o menor char **e** quando o delimitador nunca é emitido |

## Aberto

- Delimitador como grafia canônica interna (exige o seq-RLE localizar pela polaridade).
- `.8M`, `.8H` e a rota de spec — não medidos, não soldados.
- Fusão da varredura no laço que `syntax._escape_lit` já roda (otimização de `.9`,
  `T-POLARIDADE-FUSE`) — não muda byte nenhum.
- Coluna que usa a FAIXA inteira: a regra recusa. A saída alternativa (escapar o próprio
  delimitador) não foi medida.

## Evidência

`experiments/lab/dirty/2026-07/2026-07-26/`: `1853` (a proposta, do owner), `1913` (marcador
virtual + alfabeto da coluna), `1954` (35 variações + auto-declaração pelo caractere
inicial), `2126` (cruzamento com bool/binário/null + auditoria adversarial em 6 lentes).
Testes: `tests/test_polaridade.py` (32).

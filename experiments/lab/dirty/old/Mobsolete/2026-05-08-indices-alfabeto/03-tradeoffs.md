# Tradeoffs — legibilidade, gzip, complexidade

A escolha de alfabeto não é só de bytes. Tem 3 outras dimensões críticas.

---

## Dimensão 1 — Legibilidade humana e LLM

O TCF tem como objetivo declarado ser **legível**. Cada nível de alfabeto
preserva legibilidade em grau diferente:

| Alfabeto | Legibilidade humana | Legibilidade LLM |
|---|---|---|
| Decimal | ★★★★★ | ★★★★★ |
| Hex | ★★★★ | ★★★★★ (LLM treina em hex regularmente) |
| Letras | ★★★★ | ★★★★★ |
| Base64 | ★★ | ★★★★ (familiar, mas mistura confusa) |
| Base94 (printable ASCII) | ★ | ★★★ (caracteres exóticos) |
| Binário | ✗ | ✗ |
| Bit-packed | ✗ | ✗ |

→ **Cutoff prático**: até base64. Acima, perde o objetivo do TCF.

### Argumento adicional

LLMs lidam bem com:
- Decimal (familiar)
- Hex (visto em código)
- Letters (visto em variáveis)

LLMs lidam menos bem com:
- Base64 (estatisticamente "compacto" mas ruído visual)
- Base94 (caracteres como `~`, `^`, `\``)
- Binário (impossível em texto)

---

## Dimensão 2 — Compatibilidade com gzip/zstd downstream

TCF é texto. Em pipelines reais, vai passar por compressor binário (gzip,
zstd, brotli) antes de viajar pela rede ou ser armazenado. Cada alfabeto
afeta o que sobra para o gzip:

### Decimal

Caracteres `0-9` se repetem MUITO (especialmente `1`, `2`, `3` em refs
de baixa cardinalidade). Gzip extrai bem essa redundância.

→ TCF decimal + gzip = boa compressão final.

### Hex / Letras / Base64

Mais variedade de chars → menos repetição local → gzip extrai menos.

→ TCF base64 + gzip = boa, mas ganho menor que decimal+gzip
proporcionalmente. Em valor absoluto, o tamanho final é parecido (porque
TCF base64 já entregou parte do ganho que gzip teria feito).

### Binário pré-empacotado

Entropia próxima de máxima → gzip não comprime nada extra.

→ TCF binário + gzip = TCF binário (gzip não ajuda).

### Conclusão da dimensão

**Em pipelines com gzip downstream, o ganho de mudar de decimal para
base64/letras é MENOR do que o cálculo bruto sugere.** Parte do ganho
já vinha do gzip. Esse "duplo gain" não acontece — é zero-soma parcial.

Para pipelines SEM compressor downstream (uso direto no contexto do LLM,
chamadas REST sem gzip), o ganho do alfabeto denso é integral.

---

## Dimensão 3 — Complexidade do encoder/decoder

| Alfabeto | Complexidade encoder | Complexidade decoder |
|---|---|---|
| Decimal | trivial | trivial |
| Hex | trivial | trivial |
| Letras | simples (mapa idx ↔ letra) | simples |
| Base64 | médio (mapa de 64 chars) | médio |
| Base94 | médio (mapa cuidadoso para evitar reservados) | médio |
| Bit-packed | alto (escrita bit-a-bit) | alto |
| Binário | alto + perda de robustez (escape de caracteres especiais) | alto |

Para um TCF que se quer simples e portável, decimal/hex/letras são as
opções mais saudáveis.

---

## Decisão da mesa

### Alfabetos sobreviventes (pelo critério de domínio)

1. **Decimal** — domina quando coluna alfabética e cardinalidade ≤ 9
   (1 char, sem complexidade extra). É o default.
2. **Letras** — domina quando coluna **numérica** (elimina marcador `:`).
   Pode ser ativado por flag/auto-detect.
3. **Hex** — fica intermediário; só vence em casos onde cardinalidade
   13-16 e a coluna é alfabética. Cobertura pequena. Provavelmente
   redundante com letras.

### Alfabetos descartados

- **Base64** — ganho marginal, custo de legibilidade não compensa para
  TCF v0.5. Reservar para extensão futura se cardinalidades muito altas
  forem comuns.
- **Base94** — ilegível, cabe pouco mais que base64.
- **Binário e bit-packing** — saem do objetivo do TCF (legibilidade).
  Reservar para um modo "TCF-binary" separado, que seria outro formato.

### Modos efetivos

| Modo | Quando |
|---|---|
| `A=decimal` | default; coluna alfabética |
| `A=letters` | coluna numérica (elimina `:`) |
| (nenhum) | cardinalidade trivial (≤ 9 com 0 colisão) — irrelevante |

---

## Regra de seleção do encoder (atualizada)

Junta a regra de discriminação da mesa anterior com a escolha de
alfabeto:

```
Para cada coluna após sort:
  card = cardinalidade da coluna
  domínio = analisar valores
  
  Se domínio é "estritamente numérico":
    se card ≤ 26:  alfabeto = letras a-z (1 char/ref, sem marcador)
    senão card ≤ 52: alfabeto = letras a-z A-Z
    senão: alfabeto = letras+marcador ou base64 (decisão futura)
  
  Se domínio é "estritamente alfabético":
    alfabeto = decimal (sem marcador, denso o suficiente)
  
  Se domínio é "misto":
    use marcador (`:`) com decimal — mais robusto
```

Resultado: encoder pode declarar no header `# alpha: nome=dec, qty=letters`
ou deixar implícito (decoder infere).

---

## Comentário sobre a hipótese H-A5 (gzip)

A hipótese era: ganho líquido depende de gzip. Confirma-se:

- Sem gzip: alfabeto otimizado economiza bytes integralmente
- Com gzip: economia parcial (gzip recuperava parte sem isso)

→ A escolha de alfabeto deveria ser **sensível ao contexto de uso**:
- Pipeline para LLM context (sem gzip): alfabeto otimizado vale a pena
- Pipeline para storage (com gzip): pode usar decimal e deixar o gzip
  trabalhar

Mas como TCF não conhece o pipeline, default razoável: **letras para
colunas numéricas, decimal para resto**. Complexidade marginal, ganho
médio bom.

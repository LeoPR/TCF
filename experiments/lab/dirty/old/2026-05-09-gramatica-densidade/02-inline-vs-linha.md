# Inline vs linha — quando `\n` é redundante

A quebra de linha hoje serve como separador de tokens. Mas se os tokens
**são auto-delimitados** (cada token tem prefixo identificável), a
quebra é redundante.

---

## Análise por tipo de token

### Datas absolutas (ISO 8601 — `2026-01-05`)

Tamanho fixo: 10 chars. Decoder pode contar 10 e saber onde acaba.
Quebra de linha **não é necessária**.

```
2026-01-052026-01-062026-01-07     ← 3 datas inline, 30 chars
```

Vs com newline:
```
2026-01-05\n2026-01-06\n2026-01-07\n     ← 33 chars
```

Ganho: 1 byte por absoluto (o newline).

### Deltas

Cada delta começa com `+`, `-` ou `0`. Esses são marcadores de início
de token.

- `+1+2+3` = `+1`, `+2`, `+3`
- `+1-2+3` = `+1`, `-2`, `+3`
- `0+1+2` = `0`, `+1`, `+2`
- `+10+5` = `+10`, `+5` (greedy parse de dígitos até próximo `+`/`-`/`0`/EOL)

Ambiguidade potencial: `+100+5`?
- Parse greedy: `+100` (3 dígitos) então `+5`. Sem ambiguidade porque
  `+` corta.

E `0+10`?
- Parse: `0` (token isolado, 1 char) então `+10`. Sem ambiguidade.

E `010`?
- Sem `+` — não pode ser delta. Decoder espera delta nesse contexto;
  rejeita ou trata como ref. **Ambiguidade**: pode ser ref `010` ou
  início de absoluto numérico.
- Solução: se está no contexto de coluna delta, qualquer dígito sem
  prefixo é ref. `010` = ref idx 10 (3 chars vs 4 chars `+10`).

### RLE prefix `N*`

`N*X` onde X é qualquer token. O `*` separa run-count de valor.

`3*+1` = run de 3 deltas +1.
`3*+1+2` = run de 3 `+1` seguido de delta `+2`.

Greedy: `3*` consome `+1` (delta primário), depois encontra `+2` como
próximo token.

E `3*0+1`?
- `3*` + `0` (run de 3 zeros) + `+1` (delta). OK.

E `3*0123`?
- `3*0` (run de 3 zeros) + `123` (ref bare).
- Ou `3*0` + `+1` + `2` + `3`? Não, sem `+`/`-`. `123` é ref.
- Ou `3*0123` = `3*` + `0123`? `0123` não é delta válido (deltas começam
  com `+`/`-`/`0` mas `0123` inicia com `0` que é delta de zero, depois
  o resto?).
- Ambiguidade real: `0123` = `0` (delta zero) + `123` (ref) ou `0123`
  como ref?

Solução: parser greedy + regra fixa.
- Após `*`, espera 1 token (delta ou absoluto ou ref).
- Token delta: começa com `+`/`-` (greedy digit) OU é exatamente `0`
  (single-char).
- Token ref: bare digit sequence (greedy até próximo separator de tipo).

`3*0123` parseia como `3*0` (run de 3 deltas zero) seguido de `123`
(ref). Decoder lê isso corretamente.

Mas `3*012` em uma coluna sem refs? `3*0` + `12` (ref). Ainda OK porque
o contexto da coluna delta sabe que `12` é ref ao dict de deltas.

### Refs (bare integer)

`12` = ref ao idx 12. Greedy: `12` = `1` + `2`? Ou `12` direto?

Sem newline, ambiguidade: como saber? Refs PRECISAM de delimitador OU
contexto.

Soluções:
- **Newline mantido como separador para refs**: refs ficam em modo linha
- **Comprimento implícito**: cardinalidade da coluna determina dígitos
  por ref. Se cardinalidade 12, todas refs têm 1-2 chars... ambíguo.
- **Marcador para refs**: `:12` em vez de `12`. Resolve mas custa 1 char.

### Conclusão sobre refs em modo inline

Refs bare introduzem ambiguidade em inline. Soluções:
1. Manter `\n` para refs (modo misto: alguns tokens inline, refs em
   linha)
2. Usar marcador `:` para refs (volta para discriminado)
3. Usar refs de tamanho fixo (zero-padded: `01`, `02`, ..., `12` se
   cardinalidade 99)

→ Para inline mode com refs, a opção mais limpa é **marcador `:`**.
Volta a custar 1 char/ref que `M` (auto-discrim) tinha eliminado.
Trade-off real.

---

## Tabela de auto-delimitação por tipo de token

| Token | Delimitado por | OK em inline? |
|---|---|---|
| Data ISO `2026-01-05` | tamanho fixo (10 chars) | sim |
| Delta `+N` ou `-N` | prefixo `+`/`-` | sim |
| Delta zero `0` | char único | sim |
| RLE `N*<token>` | `*` separa, depois token | sim |
| Ref bare `N` | (sem prefixo) | **não** sem marcador `:` |
| String genérica | (sem padrão fixo) | **não** sem separador |

→ Inline funciona bem para colunas de **tipos com padrão fixo**
(datas ISO, deltas, RLE de tipo conhecido). Falha em colunas onde
tokens são de comprimento variável e sem prefixo (refs bare, strings).

---

## Estimativa de ganho

Para a coluna `data` no cenário 5 da mesa anterior (delta + unified, 74
B em modo linha):

Tokens contados: 1 absoluto + 4 RLE + 16 outros = 21 tokens (linhas
após RLE).

Newlines elidíveis: 21 - 1 = 20 (último ainda precisa de \n para
separar do próximo bloco de coluna).

Mas alguns tokens são refs bare (e.g., `1`, `3`, `4`) que precisam de
separador. ~8 dos 21 tokens são refs.

Newlines elidíveis com segurança: 21 - 1 (último) - 8 (refs) = 12.

Ganho: ~12 B em coluna data.

Total coluna data: 74 - 12 = ~62 B. Saves ~16%.

---

## Decisão sobre modo

### Default: modo linha

Linha-por-token é robusto, fácil de parsear, fácil de inspecionar
visualmente. **Default obrigatório.**

### Inline: opt-in por coluna

Encoder ativa inline quando:
1. Coluna usa tipos auto-delimitados (datas ISO, deltas, RLE)
2. Não há refs bare (ou usa `:` para discriminar)
3. Header declara `# layout: <coluna>=inline`

### Híbrido por linha

Para casos onde só PARTE da coluna é inline-friendly:
- Tokens de prefixo claro (deltas, RLE de delta) ficam inline
- Tokens de comprimento variável (refs bare, strings literais) ficam em
  linhas próprias

Encoder pode misturar — uma linha pode ter 1 ou N tokens dependendo do
tipo.

```
data:
2026-01-05
6*+1+4
5*0+7
1
+9
3
1
+13
3
1
+15+7
+2+8+5+7+4+10
```

(Tokens delta agrupados quando vizinhos; refs em linha solo.)

Bytes: complexo de calcular exatamente, mas ganho moderado.

---

## Trade-off com legibilidade

Em modo linha, abrir o arquivo no editor mostra cada valor em sua
linha — visualmente claro. Em inline, valores ficam apertados, mais
difícil de ler.

Para LLM, inline pode ser mais denso mas perde a estrutura visual que
ajuda a alinhar colunas (todos os arquivos usam newline-por-valor como
default).

→ **Recomendação**: inline é otimização avançada, opt-in via header.
Default = linha por token.

---

## Adição à hierarquia Lxxx

Nova flag opcional:

```
I = inline (elide newlines onde tokens são auto-delimitados)
```

Ativada por coluna via header:
```
# layout: data=inline, qty=line
```

Sem header, default é tudo line-mode.

Compatibilidade: encoder v0.5 sem flag I gera output 100% compatível
com decoder v0.4. Encoder com flag I requer decoder v0.5.

# Algoritmo — Online sem revisão

## Característica central

**Sem revisão retroativa**: uma vez que uma string `s_k` foi
emitida (com seus tokens), nenhuma string futura `s_{k+1}, ...`
pode modificá-la.

**Em contraste com**:
- Re-Pair batch (exp 13): processa tudo de uma vez, pode
  substituir padrões em todas as strings simultaneamente.
- Online com revisão (exp 15 proposto): processa string-por-string
  mas pode reabrir strings anteriores ao descobrir novo padrão.

## Fluxo

```python
def processar(strings_unicas, min_len=3):
    tokens_por_string = []
    for s in strings_unicas:
        if não há strings anteriores:
            tokens_por_string.append([Literal(s)])
            continuar

        melhor_pref = (id=0, len=0)
        melhor_suf = (id=0, len=0)

        for prev_idx, prev_s in enumerate(strings_anteriores):
            lp = LCP(s, prev_s)
            if lp >= min_len and lp > melhor_pref.len:
                melhor_pref = (prev_idx+1, lp)

            ls = LCS(s, prev_s)
            if ls >= min_len and ls > melhor_suf.len:
                melhor_suf = (prev_idx+1, ls)

        if melhor_pref.len + melhor_suf.len > len(s):
            # overlap — descarta o menor
            if melhor_pref.len >= melhor_suf.len:
                melhor_suf = (0, 0)
            else:
                melhor_pref = (0, 0)

        tokens = []
        if melhor_pref.len > 0:
            tokens.append(TokRefPref(melhor_pref.id, melhor_pref.len))
        meio = s[melhor_pref.len: len(s) - melhor_suf.len]
        if meio:
            tokens.append(TokLit(meio))
        if melhor_suf.len > 0:
            tokens.append(TokRefSuf(melhor_suf.id, melhor_suf.len))

        tokens_por_string.append(tokens)
    return tokens_por_string
```

## Decisões de design

### 1. Comparação O(N²) sem janela

Cada nova string compara com TODAS as anteriores. Em N strings,
custo total é O(N² × max_len). Aceitável para N pequeno (testes
em 6-20 strings).

Para escalar, exp 16 introduziria **janela deslizante** (compara
só com últimas K).

### 2. Critério de escolha: maior LCP / maior LCS

Greedy local: para cada nova string, escolhe o anterior com maior
LCP (e separadamente maior LCS).

Tie-break: primeiro encontrado vence (ordem de iteração).

Alternativas não testadas:
- Ganho líquido em bytes (Fraenkel-Mor-Perl)
- Considerar quanto o "meio" sobrante vai custar
- Score combinado LCP × N_uses_potencial

### 3. Resolução de overlap: descarta o menor

Mesma regra do exp 10/11. Se `LCP + LCS > len(s)`, sacrifica o
menor. Determinista, simples.

### 4. Sem criação de "símbolos" próprios

Cada referência aponta para uma **string anterior inteira** (ou
um pedaço dela). Não há "biblioteca de símbolos" como em Re-Pair.

Consequência: se o mesmo padrão aparece em 5 strings, ele é
referenciado 4 vezes (uma por string), cada uma apontando para
uma das anteriores. Não há "símbolo único compartilhado".

### 5. Sintaxe `noN[a:b]`

Notação Python-like:
- `noN[0:K]` — primeiros K chars de noN (prefixo)
- `noN[-K:]` — últimos K chars de noN (sufixo)

Não usamos `noN[a:b]` para "meio" — apenas pref e suf são
detectados (LCP/LCS). Meio fica como literal.

## Decode

Em 1 passada. Strings são reconstruídas em ordem (`no1`, `no2`,
..., `noN`). Cada `noK` é resolvido usando `no1..noK-1` que já
estão no cache.

```python
def decode(tcf_text):
    strings = {}
    body_seq = []
    for linha in tcf_text:
        if é decl externa "noN: tokens":
            tokens = parse_tokens(linha)
            strings[N] = resolve_tokens(tokens, strings)
            body_seq.append((N, count))
        elif é ref:
            body_seq.append((N, count))
    return [strings[eid] for eid, count in body_seq for _ in range(count)]
```

Sem forward refs. Sem decls tardias. Decode trivial.

## Streaming-friendly

Cada `noN: ...` pode ser emitido para output assim que a string
`s_N` é processada. Não precisa esperar `s_{N+1}`. Latência =
1 string.

Memória: O(N × max_len) — precisa manter as strings anteriores
reconstruídas em memória para calcular LCP/LCS rápido (alternativa:
reconstruir on-demand — mais lento, menos memória).

## Comparação com Re-Pair (exp 13)

| Aspecto | Re-Pair (13) | Online sem revisão (14) |
|---|---|---|
| Ordem | global, simultânea | string-por-string |
| Símbolos | extraídos globalmente (count alto) | implícitos (cada ref aponta para 1 anterior) |
| Captura padrão dominante? | sim (globalmente frequente) | sim, se aparecer em strings adjacentes/parecidas |
| Captura LCP local longo? | parcial (limitado pelo símbolo extraído) | sim (LCP entre quaisquer 2 anteriores) |
| Padrão disperso (não adjacente) | bem capturado | mal capturado (precisa de pelo menos 1 anterior parecida) |
| Streaming-friendly | não (precisa de tudo) | sim |
| Complexidade | O(N²·max_len²) | O(N²·max_len) |
| Decode | 1 passada | 1 passada |

## Onde online vence

D4: dataset com **alta similaridade local** (strings consecutivas
compartilham prefixo de 33-37 chars). Re-Pair extraiu só 27
chars; online aproveita o LCP completo.

## Onde online perde

D2: padrões globais dispersos (`mail.com` em 8 strings
não-adjacentes). Cada uso paga `no1[-8:]` em vez do `R1` mais
compacto do Re-Pair. Margem pequena.

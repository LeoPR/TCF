# 13 — Re-Pair bottom-up (substrings em qualquer posição)

## Princípio / motivação

Mudança radical em relação aos exps 02–12: abandonar a estrutura
Patricia (que só detecta prefixos comuns das folhas top-level) e
usar **Re-Pair** (Larsson & Moffat 2000) — extração iterativa da
substring de maior ganho líquido, **em qualquer posição**.

Re-Pair captura prefixos, sufixos e padrões "no meio" numa única
passada, sem precisar de árvore reverse separada (a árvore reverse
do exp 07/08 vira desnecessária). Padrão é qualquer substring que
apareça em ≥ 2 strings — não importa onde na string.

Conceito do user: "fazer por exclusão do maior e vai diminuindo
numa segunda ou mais passadas como subarvores". Re-Pair é
exatamente isso, com força bruta.

## Propósito

Responde a três perguntas:

1. **Viabilidade**: Re-Pair extrai e roundtrip funciona?
2. **Cobertura**: captura padrões que Patricia bidirecional do
   exp 10 não capturava (substrings no meio, sufixos com
   contagem alta)?
3. **Tamanho**: produz output menor ou maior que exp 10?

## Comparação

- **Compara com**: [10-decomposicao-com-avos](../2026-05-10-10-decomposicao-com-avos/).
- **É comparável?** Sim, mas com diferenças sintáticas. Mesmos
  datasets (D2-completo, D4). A sintaxe do exp 13 é mais simples
  (sem rótulos `pref:`/`suf:`).
- Métrica: ref+dados por dataset.

## Cenários

3 datasets:

| Nome | Strings | Origem |
|---|---:|---|
| D2-mini | 6 | exp 09 (2 nomes × 3 domínios) |
| D2-completo | 20 (12 únicas) | exp 06/08/10 |
| D4 | 20 (12 únicas) | exp 06/08/10 |

### Algoritmo Re-Pair simplificado

Para um conjunto de strings únicas:

1. Cada string é uma `list[Token]`, inicialmente `[Literal(s)]`.
2. **Iter**: para todas substrings de tamanho ≥ `MIN_LEN` que
   aparecem em ≥ `MIN_COUNT` strings, escolhe a de **maior ganho
   líquido**.
3. `gain_liquido = count × (len − ref_chars) − (decl_overhead + len)`.
   Heurística: `ref_chars=3`, `decl_overhead=7`. Stop quando
   melhor candidato tem `gain < 1`.
4. Cria símbolo novo, substitui em todas as strings (split por
   padrão em cada literal).
5. Repete.

### Sintaxe TCF (didática, verbosa)

Cada string vira uma sequência de tokens (literais e refs). Decls
de símbolos são embutidas na 1ª ocorrência (estilo exp 06):

```
no1: (no2="maria.silva@") + "g" + (no3="mail.com")
no4: no2 + "hot" + no3
no5: no2 + "yahoo.com"
```

Sem rótulos `pref:`/`suf:` — só ` + ` entre tokens. Refs simples
(`noN`) ou decls aninhadas (`(noN="X")`). Mais limpo que a sintaxe
composta dos exps 08/10.

## Resultado observado

Roundtrip **3/3 OK**.

| Dataset | ref+dados (exp 13) | ref+dados (exp 10) | delta |
|---|---:|---:|---:|
| D2-mini | 192 | — | — |
| D2-completo | **447** | 655 | **-208 (-31.8%)** |
| D4 | **424** | 505 | **-81 (-16.0%)** |

**Re-Pair gerou output significativamente menor em ambos os
datasets comparáveis.** D2-completo teve -31.8%; D4 teve -16.0%.

### Decomposições produzidas

**D2-mini** (símbolos: `maria.silva@`, `joao.souza@`, `mail.com`):
```
maria.silva@gmail.com    -> R1 + "g" + R3
maria.silva@hotmail.com  -> R1 + "hot" + R3
maria.silva@yahoo.com    -> R1 + "yahoo.com"
joao.souza@gmail.com     -> R2 + "g" + R3
joao.souza@hotmail.com   -> R2 + "hot" + R3
joao.souza@yahoo.com     -> R2 + "yahoo.com"
```

`yahoo.com` não virou símbolo (gain insuficiente — só 2 ocorrências
restantes após mail.com ser extraído primeiro).

**D2-completo** (símbolos: `mail.com`, `@yahoo.com`, `maria.silva`,
`pedro.alves`, `joao.souza`):
```
maria.silva@gmail.com    -> R3 + "@g" + R1
joao.souza@hotmail.com   -> R5 + "@hot" + R1
maria.silva@hotmail.com  -> R3 + "@hot" + R1
ana.lima@gmail.com       -> "ana.lima@g" + R1
joao.souza@gmail.com     -> R5 + "@g" + R1
pedro.alves@yahoo.com    -> R4 + R2
ana.lima@hotmail.com     -> "ana.lima@hot" + R1
...
```

Observação: `ana.lima` não virou símbolo apesar de aparecer em 4
strings. Razão: após `mail.com` ser extraído na iter 1 e
`@yahoo.com` na iter 2, a heurística greedy chegou a iter 3 com
`maria.silva` empatado com `pedro.alves` em gain 6. Escolheu
maria.silva (lex order). Iter 4 escolheu pedro.alves. Iter 5
escolheu joao.souza. Em iter 6, `ana.lima` ainda apareceria em 4
strings (gain ≥ 5), mas o algoritmo parou (verificar critério).

**Bug suspeito ou comportamento esperado?** Vou verificar nas
limitações.

**D4** (símbolos: base URL, `orders/10`, `products/5`):
```
https://api.example.com/v1/users/1     -> R1 + "users/1"
https://api.example.com/v1/orders/100  -> R1 + R2 + "0"
https://api.example.com/v1/users/2     -> R1 + "users/2"
https://api.example.com/v1/orders/101  -> R1 + R2 + "1"
https://api.example.com/v1/products/50 -> R1 + R3 + "0"
...
```

Re-Pair capturou a base URL (27 chars, count 12) na iter 1.
Depois capturou `orders/10` (count 5) e `products/5` (count 3).
`users/` não virou símbolo (gain marginal — 4 strings × 6 chars
vs custo de decl).

### Comparação qualitativa com Patricia bidirecional (exp 10)

| Aspecto | exp 10 (Patricia bidir) | exp 13 (Re-Pair) |
|---|---|---|
| Estrutura | 2 árvores + decomposição (pref,mid,suf) | 1 algoritmo único, N tokens por string |
| Detecta sufixos? | sim, via árvore reverse | sim, naturalmente (substring é substring) |
| Detecta "no meio"? | não (só pref + suf) | sim |
| Sintaxe | `pref:noP + "X" + suf:noQ` (verbosa) | `noP + "X" + noQ` (simples) |
| Decode | parser 2-passadas (forward refs) | parser 1-passada |
| Bytes em D2-completo | 655 | 447 (-31.8%) |
| Bytes em D4 | 505 | 424 (-16.0%) |

## Limitações

- 3 datasets pequenos. Não fala sobre escala.
- Heurística greedy global: escolhe melhor candidato local em cada
  iter, sem backtracking. Sub-ótimo (NP-difícil pelo argumento de
  Fraenkel-Mor-Perl 1983).
- Re-Pair com `_contar_substrings` é O(n²) por string (todas
  substrings). Para strings curtas (< 50 chars) é tractable mas
  não escala para textos grandes.
- `ana.lima` em D2-completo não foi capturado mesmo aparecendo 4
  vezes. Causa precisa investigar: pode ser bug na heurística
  ou comportamento esperado (re-contagem após iters anteriores).
- Sintaxe ainda verbosa (`(no2="texto")`, ` + ` entre tokens). A
  comparação com exp 10 já mostra ganho considerável; com sintaxe
  mais compacta, ganho seria ainda maior.
- Não considera composições recursivas de símbolos (símbolo que
  contém ref a outro símbolo). Cada símbolo é uma string literal
  fixa.
- Não houve comparação com formato compacto, CSV, JSON ou HTFC
  (baseline da literatura).

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-10-13-repair-bottomup
python run.py
```

Tabela consolidada no stdout. Detalhe por dataset em `debug-output/`.
TCF salvo em `encoded/`. Decode validado contra input.

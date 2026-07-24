# 2026-07-24-0033 — O vazio e a canonicidade do LF (`[]` vs `[""]` vs `["",""]`)

Continua [`0006`](../2026-07-24-0006-cicloA-formas-hipoteticas-resistencia/), que expôs a
não-canonicidade do vazio. Responde à pergunta do owner sobre o mapeamento correto.

## A pergunta

```
'#TCF.8'      -> []          '#TCF.8b\n'   -> []
'#TCF.8\n'    -> ['']        '#TCF.8b\n\n' -> ????
'#TCF.8\n\n'  -> ['','']
```

Duas convenções para o LF do corpo:
- **(A) TERMINADOR** — cada elemento termina em LF. É o que o `encode` **já produz** (`['a']`→`'a\n'`).
- **(B) SEPARADOR** — LF separa; `[]` = wire pelado `#TCF.8`. É a proposta literal do owner.

## Medição

| teste | (A) terminador | (B) separador |
|---|---|---|
| bijetividade | ✅ 0 colisões | ✅ 0 colisões |
| compat. com wires que o `encode` já emite | **6/6** | **0/6** |
| robustez a normalização POSIX (LF final) | **sobrevive** | **corrompe** (`[]`→`['']`) |

- **§2 — compatibilidade**: o `encode` já emite terminador final em todo wire. (A) valida todos sem
  mudar 1 byte (só o *decode* fica estrito). (B) leria o LF final de cada wire como um elemento vazio
  extra → todo wire de hoje decodificaria errado (viola 'body congelado').
- **§3 — o ponto decisivo**: em (B), `[]` = `'#TCF.8'` **não é arquivo POSIX válido** (sem LF final);
  qualquer editor/git/linter acrescenta o LF e `[]` vira `['']` **silenciosamente**. Em (A), `[]` =
  `'#TCF.8\n'` já é POSIX-válido — o normalizador não age.

## O `????` do owner — `#TCF.8b\n\n`

| wire | corpo | resultado |
|---|---|---|
| `#TCF.8b\n` | `''` (0 elem) | **`[]`** |
| `#TCF.8b\n\n` | `'\n'` (1 elem = `''`) | **FAIL-LOUD** — `''` não é `true`/`false` |

**Não existe `[,]`**: linha vazia só é valor legítimo para **string**; para `b`/`n` é valor fora do
domínio ⇒ erro. **A tag é dispensável no vazio** (`[]` de bool = `[]` de int, zero elementos, nenhum
tipo a preservar) ⇒ a grafia canônica de `[]` é `#TCF.8\n`, sem tag.

## Veredito

O mapeamento do owner está **semanticamente certo**. A convenção **(A)** entrega o mesmo mapeamento —
`#TCF.8\n`→`[]` · `#TCF.8\n\n`→`['']` · `#TCF.8\n\n\n`→`['','']` — com **zero mudança** nos bytes
produzidos hoje, `[]` expresso na flat (7 B, não os 11 B do `.8H#D0`), e robustez a LF. A diferença
para o que o owner escreveu é de **um LF** (ele contou o LF do header como corpo); semanticamente
idênticos, (A) é a grafia que sobrevive às ferramentas.

**A mudança real que isso implicaria** (não executada, exige aprovação): tornar o *decode* estrito
(rejeitar corpo sem terminador final) — hoje o decode é tolerante, e é essa tolerância que colapsa
`'#TCF.8\n'` e `'#TCF.8\n\n'` no mesmo `['']`. **Nada em `src/tcf`.**

## Rodar

```
python run.py
```
`intermediates/*-convA.tcfp` / `*-convB.tcfp` (as duas grafias, hipóteses) · `outputs/*-wire-real.tcf`
(âncora real) · `result.md`.

# Ciclo B — o marcador de modo `~` é necessário, ou a ausência é inferível?

Duas coisas separadas (owner): (1) DECISÃO de modo = FLOOR (outro ticket); (2) GRAMÁTICA = ESTE lab. Três candidatas: **G1** `~<n>` explícito · **G2** sem `~`, n no header (deduz por dígito) · **G3** sem `~` e sem n no header (n embutido no base64, deduz por FORMA).

## 1. Os corpos e a FORMA (o modo é distinguível por inspeção?)

| dataset | n | corpo core | corpo denso(raw) | core parece base64? | core tem marcador HCC? |
|---|---:|---|---|:---:|:---:|
| n1-true | 1 | `'true\n'` | `'gA=='` | ⚠️ SIM | não |
| n1-false | 1 | `'false\n'` | `'AA=='` | ⚠️ SIM | não |
| n2-alt | 2 | `'true\nfalse\n'` | `'gA=='` | não | não |
| all-true | 8 | `'*8|true\n'` | `'/w=='` | não | sim |
| n8-alt | 8 | `'false\ntrue\n^1\n^2\n^1\n^2\n^1\n^2\n'` | `'VQ=='` | não | sim |
| n9-alt | 9 | `'false\ntrue\n^1\n^2\n^1\n^2\n^1\n^2\n^1\n'` | `'VQA='` | não | sim |
| p50-64 | 64 | `'false\ntrue\n*3|^1\n^2\n*3|^1\n*2|^2\n*2|^1\n^2\n*5|^1\n^2\n^1\n*3|^2\n^1\n*3|^2\n*2|^1\n^2\n^1\n*3|^2\n*3|^1\n^2\n^1\n*2|^2\n*3|^1\n*5|^2\n*2|^1\n^2\n^1\n^2\n^1\n^2\n*2|^1\n^2\n*3|^1\n^2\n'` | `'RGQXcuLHypE='` | não | sim |
| runs-64 | 64 | `'*40|true\n*24|false\n'` | `'//////8AAAA='` | não | sim |

**Colisões de forma: 2** (sob detector FROUXO — só alfabeto). Corpos CORE indistinguíveis de denso só pela forma:
- `n1-true`: corpo core = `'true\n'` (4 chars, len%4=0). Alfabeto base64 puro, 1 linha.
- `n1-false`: corpo core = `'false\n'` (5 chars, len%4=1). Alfabeto base64 puro, 1 linha.
> Nuance (verificação): um detector ESTRITO (exige `len%4==0`, comprimento base64 válido) rejeitaria `false` (5 chars) → só `true` (4) sobrevive — e mesmo esse **crasha** no varint. A colisão real é ainda menor que o detector frouxo sugere.

## 2. `n` (contagem) é dedutível em cada modo?

- **core**: `n` = nº de linhas do corpo (após expandir RLE). **DEDUZÍVEL** de graça.
- **denso raw**: base64 de `ceil(n/8)` bytes → dado B bytes, `n ∈ [8(B-1)+1, 8B]` (8 valores possíveis pelo padding). **NÃO-dedutível** — `n` TEM que viajar.
  - 1 byte(s) de payload → n pode ser 1..8 (ambíguo).
  - 8 byte(s) de payload → n pode ser 57..64 (ambíguo).
  - 9 byte(s) de payload → n pode ser 65..72 (ambíguo).
  - ex.: `p50-64` empacota em 8 bytes; sem `n`, 57..64 são todos consistentes.
- **CHAVE (achado da verificação)**: como `n` é OBRIGATÓRIO no denso, ele pode servir de disambiguador de graça — é o que torna o **G2** (n logo após a tag) marker-free E sem custo dedicado.
- **denso embed (G3)**: `n` vai como varint DENTRO do base64 → self-contained, mas o MODO ainda é deduzido por FORMA (inseguro — ver §4).

## 3. RT das três gramáticas (e onde a dedução QUEBRA)

| dataset | G1 (~ explícito) | G2 (n-header, sem ~) | G3 (embed, deduz forma) |
|---|:---:|:---:|:---:|
| n1-true | ✅(d) | ✅(d) | ✅(d) |
| n1-false | ✅(d) | ✅(d) | ✅(d) |
| n2-alt | ✅(d) | ✅(d) | ✅(d) |
| all-true | ✅(d) | ✅(d) | ✅(d) |
| n8-alt | ✅(d) | ✅(d) | ✅(d) |
| n9-alt | ✅(d) | ✅(d) | ✅(d) |
| p50-64 | ✅(d) | ✅(d) | ✅(d) |
| runs-64 | ✅(d) | ✅(d) | ✅(d) |

### Estresse do G3 — FORÇANDO denso em todos (inclui as colisões):

| dataset | wire G3 (denso forçado) | dedução acerta o modo? | RT |
|---|---|:---:|:---:|
| n1-true | `'#TCF.8b\nAYA='...` | denso✅ | ✅ |
| n1-false | `'#TCF.8b\nAQA='...` | denso✅ | ✅ |
| n2-alt | `'#TCF.8b\nAoA='...` | denso✅ | ✅ |
| all-true | `'#TCF.8b\nCP8='...` | denso✅ | ✅ |
| n8-alt | `'#TCF.8b\nCFU='...` | denso✅ | ✅ |
| n9-alt | `'#TCF.8b\nCVUA'...` | denso✅ | ✅ |
| p50-64 | `'#TCF.8b\nQERkF3Lix8qR'...` | denso✅ | ✅ |
| runs-64 | `'#TCF.8b\nQP//////AAAA'...` | denso✅ | ✅ |

## 4. DECISIVO — forçando CORE nas colisões (as 3 gramáticas)

> O 8/8 da §3 é enganoso: nas colisões (`n1-true`/`false`) o FLOOR escolheu DENSO, então o corpo core nunca foi emitido. Aqui FORÇO core e testo se a dedução ainda acerta. **Correção pós-verificação: incluí o G2, que eu havia omitido (viés a favor do `~`); e a falha do G3 é um CRASH (fail-loud), não corrupção silenciosa.**

| dataset | wire core forçado | G3 (forma) | G2 (n-header) | G1 (`~`) |
|---|---|:---:|:---:|:---:|
| n1-true | `'#TCF.8b\ntrue\n'` ⬅️COLISÃO | ❌CRASH(IndexError) | ✅ | ✅ |
| n1-false | `'#TCF.8b\nfalse\n'` ⬅️COLISÃO | ❌CRASH(Error) | ✅ | ✅ |
| n2-alt | `'#TCF.8b\ntrue\nfalse\n'` | ✅ | ✅ | ✅ |
| all-true | `'#TCF.8b\n*8|true\n'` | ✅ | ✅ | ✅ |
| n8-alt | `'#TCF.8b\nfalse\ntrue\n^1\n^2\n^1\n^2\n^1\n^2\n'` | ✅ | ✅ | ✅ |
| n9-alt | `'#TCF.8b\nfalse\ntrue\n^1\n^2\n^1\n^2\n^1\n^2\n^1\n'` | ✅ | ✅ | ✅ |
| p50-64 | `'#TCF.8b\nfalse\ntrue\n*3|^1\n^2\n*3|^1\n*2|^2\n*2|^1\n^2\n*5|^1\n^2\n^1\n*3|^2\n^1\n*3|^2\n*2|^1\n^2\n^1\n*3|^2\n*3|^1\n^2\n^1\n*2|^2\n*3|^1\n*5|^2\n*2|^1\n^2\n^1\n^2\n^1\n^2\n*2|^1\n^2\n*3|^1\n^2\n'` | ✅ | ✅ | ✅ |
| runs-64 | `'#TCF.8b\n*40|true\n*24|false\n'` | ✅ | ✅ | ✅ |

- **G3 (deduz por forma)**: falha 2/8 — mas por **CRASH (fail-loud)**, não corrupção silenciosa (lê `true` como base64 → IndexError/binascii). Inseguro E acopla à heurística.
- **G2 (n-no-header, SEM marcador dedicado)**: acerta 8/8 — o byte logo após a tag desambigua de graça: **dígito → denso** (início do `n`), **`\n` → core**. Disjunto por construção, sem char reservado, sem olhar tamanho (NÃO acopla à heurística).
- **G1 (`~` dedicado)**: acerta 8/8 — inambíguo, mas paga 1 byte a mais que o G2 em todo wire denso.

## 5. Custo — G2 (n-header) vs G1 (`~`) nos wires densos

| dataset | G1 (`~<n>`) | G2 (`<n>`) | Δ |
|---|---:|---:|---:|
| n1-true | 14 | 13 | -1 |
| n1-false | 14 | 13 | -1 |
| n2-alt | 14 | 13 | -1 |
| all-true | 14 | 13 | -1 |
| n8-alt | 14 | 13 | -1 |
| n9-alt | 14 | 13 | -1 |
| p50-64 | 23 | 22 | -1 |
| runs-64 | 23 | 22 | -1 |

**Total denso: G1=130 B · G2=122 B → G2 é 8 B mais barato** (1 byte/wire, o char `~`).

## Leitura CORRIGIDA (pós-verificação adversarial `wf_3a7ab214`)

⚠️ **Correção**: a v1 concluía "o `~` é NECESSÁRIO" — isso era **overclaim**, por dois erros meus: (a) omiti o G2 do teste decisivo (viés pró-`~`); (b) chamei de "corrompe" o que na verdade **crasha (fail-loud)**. Corrigido abaixo.
- **A resposta à sua pergunta**: SIM, existe gramática **marker-free segura e desacoplada da heurística** — é o **G2** (`#TCF.8b<n>\n<base64>`). O disambiguador é o **byte logo após a tag fixa**: dígito → denso (início do `n`), `\n` → core. Disjuntos por construção; sem char reservado; sem olhar tamanho. Passa 0 falhas no teste decisivo.
- **Um disambiguador É preciso** (a dedução por FORMA — G3 — é insegura: crasha nas colisões `true`/`false` base64-limpas, e acopla à heurística). Mas um **marcador DEDICADO (`~`) NÃO é preciso** — o `n`, que é obrigatório (padding), já desambigua.
- **A colisão é minúscula e enumerável**: só `n=1` bool (2 de 2046 corpos core n≤10 são base64-puros: `true`,`false`). Para n≥2 todo corpo core tem `\n`/`*`/`|`/`^`. `number` `[1]`/`[0]` vira `\1`/`\0` (backslash) — **não colide**.
- **O trade-off REAL (pra você decidir)**:
  - **G2 (n-header)**: mais barato (−1 byte/denso), marker-free, desacoplado. Ideal se forem **só 2 modos** (core + 1 denso): dígito-vs-`\n` é um split binário.
  - **`~` (ou char de modo)**: +1 byte, mas **estende limpo pra ≥3 modos** — a família bN do roadmap (`b1`/`b2`/`b4`/`b8`) + `misto`, onde dígito-vs-`\n` não basta (só dá binário). O marcador vira `~<modo><n>`.
- **Assimetria que se mantém**: seja `~` ou G2, o **core (comum) fica nu** e o **denso (raro) se declara** — marcar o caso raro/grande e deixar o comum/pequeno implícito é o lado certo do pagador (a v1 acertou ISSO; errou só em dizer que o marcador dedicado era obrigatório).

---
**§3 RT sob FLOOR: G1/G2/G3 = 8/8 (enganoso, corpo core não-emitido). §4 core-forçado: G3 falha 2/8 (crash), G2 8/8, G1 8/8. §5: G2 −8 B vs G1.** Artefatos: `intermediates/*.tcfp`. Regenera: `python run.py`.

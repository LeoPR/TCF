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

**Colisões de forma: 2** — corpos CORE que passam por base64 puro (sem marcador HCC), logo indistinguíveis de um corpo denso SÓ pela forma:
- `n1-true`: corpo core = `'true\n'` — é alfabeto base64 puro, 1 linha. `base64.decode` daria bytes; a dedução por forma erraria.
- `n1-false`: corpo core = `'false\n'` — é alfabeto base64 puro, 1 linha. `base64.decode` daria bytes; a dedução por forma erraria.

## 2. `n` (contagem) é dedutível em cada modo?

- **core**: `n` = nº de linhas do corpo (após expandir RLE). **DEDUZÍVEL** de graça.
- **denso raw**: base64 de `ceil(n/8)` bytes → dado B bytes, `n ∈ [8(B-1)+1, 8B]` (8 valores possíveis pelo padding). **NÃO-dedutível** — `n` TEM que viajar.
  - 1 byte(s) de payload → n pode ser 1..8 (ambíguo). Ex.: p50-64 empacota em 8 bytes; sem `n`, 57..64 são consistentes.
  - 8 byte(s) de payload → n pode ser 57..64 (ambíguo). Ex.: p50-64 empacota em 8 bytes; sem `n`, 57..64 são consistentes.
  - 9 byte(s) de payload → n pode ser 65..72 (ambíguo). Ex.: p50-64 empacota em 8 bytes; sem `n`, 57..64 são consistentes.
- **denso embed (G3)**: `n` vai como varint DENTRO do base64 → self-contained, **dedutível do payload**. Custo: +1..2 bytes de varint (antes do base64).

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

## 4. DECISIVO — forçando CORE nas colisões (G3 sem marcador deve QUEBRAR)

> O 8/8 acima é enganoso: nas colisões (`n1-true`/`false`) o FLOOR escolheu DENSO, então o corpo core nunca foi emitido. Aqui FORÇO core e testo se o G3 (deduz por forma) ainda acerta — é onde a ausência de marcador falha.

| dataset | wire G3 core forçado | G3 deduz | G3 RT | G1 (`~`) RT |
|---|---|:---:|:---:|:---:|
| n1-true | `'#TCF.8b\ntrue\n'` | denso ⬅️ COLISÃO | ❌ CORROMPE | ✅ |
| n1-false | `'#TCF.8b\nfalse\n'` | denso ⬅️ COLISÃO | ❌ CORROMPE | ✅ |
| n2-alt | `'#TCF.8b\ntrue\nfalse\n'` | core | ✅ | ✅ |
| all-true | `'#TCF.8b\n*8|true\n'` | core | ✅ | ✅ |
| n8-alt | `'#TCF.8b\nfalse\ntrue\n^1\n^2\n^1\n^2\n^1\n^2\n'` | core | ✅ | ✅ |
| n9-alt | `'#TCF.8b\nfalse\ntrue\n^1\n^2\n^1\n^2\n^1\n^2\n^1\n'` | core | ✅ | ✅ |
| p50-64 | `'#TCF.8b\nfalse\ntrue\n*3|^1\n^2\n*3|^1\n*2|^2\n*2|^1\n^2\n*5|^1\n^2\n^1\n*3|^2\n^1\n*3|^2\n*2|^1\n^2\n^1\n*3|^2\n*3|^1\n^2\n^1\n*2|^2\n*3|^1\n*5|^2\n*2|^1\n^2\n^1\n^2\n^1\n^2\n*2|^1\n^2\n*3|^1\n^2\n'` | core | ✅ | ✅ |
| runs-64 | `'#TCF.8b\n*40|true\n*24|false\n'` | core | ✅ | ✅ |

**G3 (sem marcador) corrompe 2/8** quando o FLOOR escolhe core num corpo base64-limpo. **G1 (`~`) acerta 8/8** — o marcador remove a ambiguidade por construção.

## Leitura (pra você inspecionar)

- **A resposta à sua pergunta**: a ausência do marcador **NÃO** pode ser sempre entendida como implícita. O modo core-vs-denso NÃO é distinguível pela forma em 2 casos (n1-true, n1-false): o corpo core de bool pequeno (`true`/`false`) é alfabeto base64 puro, indistinguível de um payload denso.
- **Prova (seção 4)**: forçando core nas colisões, o **G3 (sem marcador) corrompe** — a dedução por forma lê `true` como base64 e devolve lixo. O **G1 (`~`) nunca corrompe**.
- **E o `n` do denso não é dedutível** (padding) — algo tem que carregá-lo (o `~<n>` do G1, ou o varint embutido do G3). Então nem o denso 'de graça' escapa de carregar info.
- **Conclusão pra decidir** (não é decisão): o marcador (ou um disambiguador equivalente) é **necessário na gramática completa** — a menos que se aceite ACOPLAR a gramática à heurística (denso só quando vence ⇒ nunca nos N pequenos base64-limpos), o que é frágil e mistura as duas coisas que você pediu pra separar. O caminho limpo: manter o `~` explícito no wire denso; a implicitude fica no CORE (modo A sem marcador, o default).
- **Assimetria elegante**: o modo A (core) É o implícito (sem marcador, deduzido por exclusão como no header); o modo B (denso) é a EXCEÇÃO opt-in que se declara com `~`. Implícito = o comum; explícito = o desvio. Consistente com o resto do formato.

---
**RT: G1=8/8 · G2=8/8 · G3=8/8 (FLOOR) · G3 core-forçado corrompe 2/8 · G1 core-forçado 8/8.** Artefatos: `intermediates/*.tcfp`. Regenera: `python run.py`.

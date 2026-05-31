# M1.C — Sumida (parser stateful elimina escape redundante)

## Tecnica

Decoder mantem `max_idx_visivel` (quantos frags ja' foram declarados).
Em ref-context, ao ler seq de digitos PURA (sem `,` nem `..`):
- Se `int(seq) > max_idx_visivel` E sem leading-zero → trata como
  literal novo (aloca idx).
- Senao → trata como ref.

Encoder espelha: suprime `\` escape quando o frag literal e' inteiro
puro-digits, sem leading-zero, e `int(text) > max_visivel_antes`.

Combina com range (M1.E) e escape escopo (M1.A') para casos em que
ainda e' necessario.

## Custo

**Por caso sumido**:
- Economiza 1 byte (remove `\`).

**Mas requer separador**:
- Se sumido vem APOS uma ref, encoder precisa inserir `*` antes
  (refs terminam em digit; sumido comeca com digit; parser uniria
  os dois).
- Custo do `*`: 1 byte.

**Net por caso sumido apos ref**: 0 bytes (1 economizado, 1 gasto).
**Net por caso sumido apos literal nao-digit-seq**: +1 byte
(economizado, sem separador necessario).
**Net por caso sumido no inicio de linha**: +1 byte (economizado,
sem separador necessario).

## Roundtrip e bytes nos 4 datasets

| Dataset | M1.A | M1.B | M1.A' | M1.E | M1.C |
|---|---:|---:|---:|---:|---:|
| D1-emails-simples | 162 | 162 | 162 | **149** | **149** |
| D2-emails-quote-id | 200 | 198 | 197 | **180** | **180** |
| D3-stress-substring | 242 | 233 | 233 | **206** | **206** |
| D4-caos-mix | 152 | 160 | 152 | **141** | **141** |
| **TOTAL** | 756 | 753 | 744 | **676** | **676** |

**Roundtrip 4/4 OK. Empate total em bytes com M1.E.**

## Insight semantico (o que M1.C revela)

Todos os casos de "literal sumido" nos 4 datasets vem **apos ref**:

| Caso | M1.E | M1.C |
|---|---|---|
| D2 eid=2 `42` apos refs 1..3 | `1..3\42*5..7` (12 chars) | `1..3*42*5..7` (12 chars) |
| D2 eid=10 `42` apos ref 12 | `12\42*14,6,7` (12 chars) | `12*42*14,6,7` (12 chars) |
| D3 eid=2 `103` apos refs 1..3 | `1..3\103*5..7` (13 chars) | `1..3*103*5..7` (13 chars) |
| D3 eid=8 `103` apos refs 1,2,11 | `1,2,11\103*13,6,7` (17 chars) | `1,2,11*103*13,6,7` (17 chars) |

Cada `\` virou `*`. **Mesmo custo, mesma forma estrutural.**

Conclusao: **eliminar marcadores tem custo de separador quando o
contexto original era ambiguo**. Em ref-context (apos ref/range),
o `*` separador precisa entrar para evitar que o parser una o
literal-sumido com a ref anterior. O byte economizado e' compensado
pelo byte do separador.

Isso e' uma **regra de ouro do agrupamento**: 
> Agrupar/sumir so' compensa quando o contexto onde o marcador era
> emitido JA' tinha um separador natural (ex: literal nao-digit-seq
> anterior; inicio de linha; quebra explicita).

## Comparacao com M1.A' (escape escopo)

M1.A' ganhou ao agrupar **K digitos contiguos em 1 escape** —
economia de K-1 bytes. Funcionou porque os digitos vinham EM
SEQUENCIA dentro de um literal nao-digit (ex: `users/00042`), com
contexto natural ja' definido.

M1.C tenta agrupar de outra forma — eliminar o escape inteiro
quando contexto matematicamente resolve. Mas o contexto em
ref-context exige separador, anulando o ganho.

## Quando M1.C ganharia (datasets nao testados)

M1.C ganharia bytes em datasets com:

1. **Literal puro-digit apos literal nao-digit-seq**: ex linha
   `abc42def` onde `abc` (frag), `42` (frag novo). Encoder M1.E:
   `abc*\42*def` (11 chars). Encoder M1.C: `abc42def` (8 chars,
   mas precisa `*` entre `abc` e `42`? não — `b` termina em
   nao-digit, parser sai de lit-mode no `4`, ai `42` sumido).
   GANHO 3 BYTES.
2. **Literal puro-digit no inicio de linha**: linha comeca com
   `42xyz` direto. M1.E: `\42*xyz` (7). M1.C: `42xyz` (5). GANHO 2.

Esses cenarios NAO aparecem em D1-D4 porque os literais novos com
digit puro sempre seguem refs.

## Propriedades

| Eixo | M1.E | M1.C |
|---|---|---|
| Stateful encoder? | nao | **sim** (mantem max_idx_visivel) |
| Stateful decoder? | sim | **sim** (cresce max_idx_visivel) |
| Bytes (D1-D4) | 676 | 676 (empate) |
| Combinavel com outras? | sim | herdou range+escape escopo |
| Ataca dimensao | range refs | escape redundante |

## Limitacoes

- **Empate em todos os 4 datasets** — sem ganho liquido.
- **Encoder agora e' stateful** — diferenca real vs M1.E. Custo
  conceitual (nao bytes).
- **Decoder mais frágil**: ambiguidade entre ref-grande e literal
  numerico-grande resolvida por max_idx atual. Se tabela ficar
  enorme, frags > 1000 nunca sao sumidos.

## Como rodar

```bash
cd 2026-05-12-M1-marcacao-ambiguidade
python run_lote.py
```

## Implicacao para o macro M1

M1.C documenta uma **dimensao semantica que nao compensa** nos
datasets testados. Isso e' resultado valido — a metodologia
[[feedback_exploracao_semantica_antes_de_dataset]] previa que
mapear DIFERENCAS e' o objetivo, nao eleger vencedor.

**Decisao**: M1.C fica registrada como **fracassada em bytes mas
estruturalmente legitima**. Pode reaparecer:
- Em Fase B com dataset enviesado pra literais puro-digit pos-texto.
- Combinada com formato alternativo de declaracao (sem separador
  `*`) — anularia o custo do `*`.

Continua exploracao M1.D (slice arbitrario) — ataca dimensao
diferente (extende algoritmo).

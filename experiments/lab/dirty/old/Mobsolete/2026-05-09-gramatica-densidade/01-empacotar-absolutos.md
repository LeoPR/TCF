# Empacotar valores absolutos por tipo

A representação interna do valor é **independente** de RLE/dict/delta.
Cada um desses opera sobre tokens; o que está dentro do token pode ser
mais ou menos compacto.

---

## Datas

### Variantes de representação

| Formato | Bytes | Legibilidade | Range |
|---|---|---|---|
| `2026-01-05` (ISO 8601) | 10 | ★★★★★ | universal |
| `2026-1-5` (sem zero-pad) | 8 | ★★★★ | ambíguo: `1-5` = mês 1 dia 5 ou mês 1 dia 50? Precisa separador inequívoco |
| `26-01-05` (yy-mm-dd) | 8 | ★★★ | século implícito |
| `260105` (yymmdd compacto) | 6 | ★★ | sem separador, depende de tamanho fixo |
| `2026-W02-1` (ISO semana) | 9 | ★ | edge case |
| `19752` (dia juliano) | 5 | ✗ | inutilizável p/ humano |

### Decisão por contexto

- **Default**: ISO 8601 (`2026-01-05`). Legível, padrão.
- **Modo `D=packed`** (opt-in): `260105` (6 chars). Encoder usa quando
  `# ext: data=packed`.
- **Modo `D=julian`**: dia juliano. Reservado para casos ultra-densos
  (logs, telemetria) — fora do TCF v0.5 prioritário.

### Quando empacotar absoluto vale a pena

Confirma **H-G1**: vale principalmente quando δ está OFF.

| Cenário | Absolutos | Empacotar economiza |
|---|---|---|
| δ ON (1 só absoluto inicial) | 1 | 4 B (10→6) — desprezível |
| δ OFF, sort cronológico, RLE ativo | 22 declarações | 22 × 4 = 88 B |
| δ OFF, sort não-temporal | 22 declarações + refs | 88 B |
| δ ON com chunked TCF (1 absoluto/chunk) | k chunks | 4·k B |

→ Empacotar é mais útil em **chunked TCF** (vários absolutos, um por
chunk) ou quando δ não se aplica.

---

## Números (inteiros e decimais)

### Inteiros

Já são compactos. `1234` = 4 chars. Pouco a empacotar exceto:
- Hex: `0x4D2` = 5 chars (perde legibilidade)
- Base36: `ya` = 2 chars (raro)

→ Não empacotar inteiros por padrão. Só se o domínio fizer sentido (IDs
com base hex, etc.).

### Decimais

`1.50` (4 chars) já está bem. Variantes:
- `1.5` (3 chars) — normalização. Mas perde precisão semântica
  (`1.50` = 2 casas, `1.5` = 1 casa). Decisão de domínio.
- `1.5e0` (5 chars) — científica, raramente útil.

→ Não empacotar decimais. Normalização é decisão pré-encoder.

---

## Strings

### Variantes

- Literal: `Caderno` (7 chars).
- Com prefix-elision: já é a flag P (mesa futura).
- Compactado (lowercase, no diacritics): `caderno` (perde semântica).

→ Não empacotar strings. Outras técnicas (P, dict refs) cobrem.

---

## Identificadores compostos (timestamps, UUIDs)

### Timestamps `2026-01-05 14:30:00` (19 chars)

- ISO compacto `20260105T143000` (15 chars): -4 B/timestamp
- Unix epoch `1767608400` (10 chars): -9 B/timestamp, perde
  legibilidade humana
- Unix epoch + base32: ~7 chars, ilegível

### UUIDs `550e8400-e29b-41d4-a716-446655440000` (36 chars)

- Sem hífens: `550e8400e29b41d4a716446655440000` (32 chars)
- Base64: 22 chars
- Binário: 16 bytes (-20 B/UUID, ilegível)

→ Para timestamps e UUIDs, o ganho de empacotamento é **maior em valor
absoluto** (chars salvos por token) mas trade-off de legibilidade
sobe.

Decisão: oferecer modo `compact` opt-in por coluna. Default permanece
o formato canônico do tipo.

---

## Ortogonalidade com RLE/dict/delta

Empacotamento de absolutos opera **dentro do token**. RLE/dict/delta
operam **sobre tokens**. Composição limpa:

```
Coluna original: 2026-01-05, 2026-01-06, 2026-01-07
   ↓ empacotar absoluto (data=packed)
Tokens compactos: 260105, 260106, 260107
   ↓ delta
Tokens delta: 260105, +1, +1
   ↓ RLE
Final: 260105, 2*+1
```

Encoder pode aplicar empacotamento **antes ou depois** das outras
transformações; o resultado em bytes é equivalente porque os tokens são
manipulados independentemente.

→ A flag `K-pack` (ou similar) na hierarquia Lxxx representa
"empacotamento de absolutos por tipo". Pode ser ativada em conjunto
com δ, R, D etc.

---

## Recomendação

| Tipo | Default | Modo packed (opt-in) |
|---|---|---|
| Data | ISO 8601 (`2026-01-05`) | YYMMDD (`260105`) |
| Timestamp | ISO 8601 estendido | ISO compacto sem hífens/`:` |
| UUID | hífenado canônico | sem hífens |
| Inteiro | decimal | (não há ganho útil) |
| Decimal | natural | (não há ganho útil) |
| String | natural | (cobertto por dict/prefix) |

Adicionar à hierarquia Lxxx:

```
flags = SRDMA + δ + Π     (Π = packed-absolute, opt-in por coluna)
```

Custo: 1 char de header (`Π`) e ~3-5 linhas de regra no decoder.

Ganho: significativo em datasets com muitos absolutos (chunks, dados
sem ordem temporal, dados com sort por outras colunas).

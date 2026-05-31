# M1.D — Slice arbitrario (trecho central de string ancestral)

## Tecnica

Declara literal de cada no INTEIRO (sem fragmentar) e referencia
trechos via slice `e:a-b` (chars [a:b] da string original do eid `e`).

Diferenca chave vs M1.A/B/E/C: **nao fragmenta o no fonte**. Em
M1.A-C, descendentes com quebras propagavam fragmentacao para
ancestrais (ex: D3 eid=1 ficava em 7 frags com 6 `*` overhead).
M1.D mantem ancestral inteiro e usa slice para o que precisa.

## Sintaxe

`e:a-b` onde:
- `e` = eid (string-id, 1-indexed)
- `a` = offset inicial (incluso)
- `b` = offset final (excluso)

Casos:
- `e:0-k`     = prefixo k chars (= TokRefPref)
- `e:(n-k)-n` = sufixo k chars (= TokRefSuf)
- `e:a-b`     = trecho central (NOVO — nao existia nas outras micros)

Combina com escape escopo (M1.A') para chars ambiguos em literais.
NAO usa range (refs sao slices, nao listas de idx — incompativel).

## Algoritmo

Usa tokens RAW de `online.py` (sem propagar quebras). O `processar`
do exp 16 ja' produz tokens limpos (L/P/S). M1.D nao chama
`coletar_quebras_e_frags` — apenas itera tokens raw:

- `TokLit(t)` → declara literal inteiro
- `TokRefPref(e, k)` → emite `e:0-k`
- `TokRefSuf(e, k)` → emite `e:(n-k)-n` onde n = len(string_e)

Decoder mantem `eids_decodados[e-1]` = string completa reconstruida
de cada eid. Slice retorna `string[a:b]`.

## Roundtrip e bytes nos 4 datasets

| Dataset | M1.E | M1.D | diff vs E |
|---|---:|---:|---:|
| D1-emails-simples | 149 | 162 | +13 (+8.7%) |
| D2-emails-quote-id | 180 | 207 | +27 (+15.0%) |
| D3-stress-substring | 206 | 218 | +12 (+5.8%) |
| D4-caos-mix | 141 | 141 | 0 |
| **TOTAL** | 676 | **728** | +52 (+7.7%) |

**Roundtrip 4/4 OK.** Perde em D1/D2/D3, empata em D4.

## Por que perde nos canonicos

Trade-off observado em cada dataset:

### Ganho de M1.D (compactar declaracao do no fonte)

D3 eid=1 (`api/users/00042/profile.json`):
- M1.E: `api*/*users/\00*\042*/profile*.*json` (36 chars)
- M1.D: `api/users/\00042/profile.json` (29 chars, -7)

Sem fragmentacao, sem `*` separadores entre frags do mesmo no.

### Perda de M1.D (descendentes com refs verbosas)

D1 eid=5 (`joao@hotmail.com`) tokens = P(1,5) + L('hot') + S(1,8):
- M1.E: `1..3hot5,6` (10 chars) — usa frags 1,2,3 (`joa,o,@`)
  e frags 5,6 (`mail,.com`) compactados em range
- M1.D: `1:0-5hot1:6-14` (14 chars, +4) — slices verbosos

Cada slice precisa 3 numeros vs M1.E que usa 1-2 chars por ref.
Quando descendente tem multiplas refs cobrindo poucos frags
contiguos, range vence slice.

### Empate em D4

D4 tem nos fonte pequenos (12 chars) com muitas quebras pontuais.
Ganho em fonte e' compensado pela perda em descendentes. Soma da'
141 = M1.E.

## Casos onde slice central E' usado de verdade

Slice nao-trivial (a != 0 e b != n) aparece em D3:

- D3 eid=4 (`web/users/00042/profile.json`):
  `web1:3-28` — slice [3:28] de eid=1 = `/users/00042/profile.json`
- D3 eid=5: `4:0-12*2:12-28` — segundo slice [12:28] de eid=2 =
  `103/profile.json` (trecho central, nao prefix nem suf)
- D4 eid=4: `[b1:2-12` — slice [2:12] = `]*'foo'@42`

Funciona corretamente, mas custo > beneficio nos canonicos.

## Onde slice ganharia (hipotese)

Datasets onde:
1. No fonte com MUITAS quebras (muitos frags = muito `*` overhead).
2. Descendentes que usam UM grande slice central, nao multiplos
   pequenos.
3. Strings longas (mais economia por declaracao).
4. eids de 1 digito (slices ficam menores).

Stress-test rodada 2 vai testar essas condicoes.

## Propriedades

| Eixo | M1.E | M1.D |
|---|---|---|
| Stateful encoder? | nao | nao |
| Stateful decoder? | sim (range) | sim (mantem eids_decodados completos) |
| Mexe no algoritmo? | nao | nao (so' deixa de fragmentar) |
| Sintaxe nova? | range `a..b` | slice `e:a-b` |
| Compativel com range? | sim | nao (refs nao sao lista de idx) |
| Bytes (D1-D4) | 676 | 728 (+7.7%) |

## Limitacoes

- **Slice e' verboso**: 3 numeros + 2 separadores (`:`, `-`).
  Compete mal com refs simples curtas.
- **Incompativel com range** (M1.E): slices nao sao listas
  agregaveis.
- **Nao testado em strings longas**: D1-D4 tem strings de 12-28
  chars. Strings de 50+ chars favoreceriam slice de declaracao.

## Como rodar

```bash
cd 2026-05-12-M1-marcacao-ambiguidade
python run_lote.py
```

## Implicacao para o macro M1

M1.D fecha as 5 dimensoes semanticas planejadas do macro:
- M1.A: escape pontual
- M1.A': escape com escopo
- M1.B: quote em grupo
- M1.E: range de refs
- M1.C: sumida (parser stateful)
- **M1.D: slice arbitrario**

Vencedor em bytes nos canonicos: M1.E/C (empate, 676). M1.D fica
como dimensao mapeada — ataca camada distinta (declaracao do no
fonte) e ganharia em regime nao testado nos D1-D4. Vale stress-test
rodada 2 antes de fechar M1.

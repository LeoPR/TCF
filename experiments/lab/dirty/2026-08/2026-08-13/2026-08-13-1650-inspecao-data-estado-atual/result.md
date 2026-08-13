# Resultado — inspeção do tipo DATA em 2026-08-13

29 casos, **0 falhas de round-trip** (todo `outputs/<c>.roundtrip.json` bate byte-a-byte
com `inputs/<c>.entrada.json`). Números gerados por `run.py`; wires em `outputs/*.tcf`;
cada wire decomposto em `intermediates/<c>.anatomia.txt`.

Isto é dirty: as leituras abaixo são **orientativas**. O que vale como verificação está nos
testes soldados (suíte 1249) e no `EXP-017` clean.

## 1. O mecanismo, visível

O wire de 600 datas diárias, inteiro:

```
'#TCF.8 :dt\n*600+1|\739617\n'      26 bytes   (o núcleo sozinho: 414 B)
```

Lido em partes: `#TCF.8` magic · `:dt` o spec de data (id curto, mudou hoje) · `*600+1|`
seq-RLE aritmético — 600 linhas de passo +1 · `\739617` a âncora, ordinal de `2026-01-01`
(o `\` é escape de dígito do núcleo, não faz parte do número).

| caso | spec | núcleo | o que mostra |
|---|---:|---:|---|
| `a1` diária 600 | **26 B** | 414 B | passo constante `+1` |
| `a2` mensal 600 (+30d) | **27 B** | 6338 B | o passo **não importa** pro seq-RLE: +1 e +30 dão o mesmo trabalho |
| `a3` dias úteis 600 | **34 B** | 2454 B | delta que **cicla** — `*600~1,3,1,1,1\|` (ADR-0040) |
| `a4` quinzenal 400 | **27 B** | 4265 B | outro passo constante, mesma grafia |
| `c6` descendente 300 | **26 B** | 1061 B | o sinal viaja no marcador (`*300-1\|`) |

O contraste `a1` × `a3` é a razão de existir do ADR-0040: dia útil não tem passo constante
(o fim de semana quebra), e sem o marcador periódico ele cairia no corpo cru.

## 2. O limite, e o que ele confirma

`a5` (dia 1 de cada mês, 240 meses) é o caso de passo **irregular**: 31, 28, 31, 30…
O periódico pega, mas **fragmentado** — 9 marcadores, período 12, re-ancorando a cada 48
linhas:

```
*26~31,28,31,30,31,30,31,31,30,31,30,31|\739617
*48~31,30,31,30,31,31,30,31,30,31,31,28|\740407
*48~31,30,31,30,31,31,30,31,30,31,31,28|\741868      ← o mesmo ciclo, 3 vezes
…                                                       323 B (núcleo: 455 B)
```

O ciclo verdadeiro do calendário é **48** (4 anos, por causa do bissexto), e o teto
`MAX_PERIODO=24` o exclui. O detector faz o melhor dentro do teto: acha o período 12 e
re-ancora quando fevereiro quebra. **É a confirmação empírica do ticket
`T-MAX-PERIODO-31`** — ele previa que o teto deixa períodos naturais na mesa; aqui dá para
ver quanto (3 marcadores idênticos que um teto de 48 fundiria em 1).

## 3. O flip do FLOOR — o que mudou hoje

| N | wire | bytes | núcleo |
|---:|---|---:|---:|
| 10 | `#TCF.8` (core) | 42 | 42 |
| 11 | `#TCF.8 :dt` | **43** | 47 |
| 12 | `#TCF.8 :dt` | **43** | 47 |

Em N ≤ 10 o wire é **byte-idêntico** ao do núcleo — a nature compete e perde, e o FLOOR
emite o núcleo. Em N = 11 ela passa a vencer. Com o id antigo (`:data-iso`, 10 B de tag)
esse flip não existia nessa faixa: **o nome longo suprimia a própria nature**.

## 4. Onde o FLOOR recusa (a invariante nunca-pior, visível)

| caso | spec | núcleo | leitura |
|---|---:|---:|---|
| `c1` agrupada (blocos de 20) | 64 B | 64 B | o RLE do núcleo já resolve — **o spec seria pior, e é recusado** |
| `c2` aleatória 300 | 2292 B | 2767 B | sem progressão, mas o ordinal ainda encurta o valor |
| `c3` suja 30% | 1309 B | 1486 B | cada grafia não-canônica vira literal (`_`), RT byte-exato |
| `c4` com nulos | 461 B | 571 B | slot nulo atravessa a nature |
| `c5` N=1 | 19 B | 20 B | sem delta nenhum para observar |

Em `c1` os dois wires têm exatamente os mesmos bytes: é o FLOOR dizendo "não melhoro isto"
e saindo do caminho.

## 5. Dado real — e o achado desta rodada

12 colunas do corpus (10 distintas; ver `datasets-provenance.md`). **O spec venceu em 9**,
com redução agregada de **24,8%** (169.997 B contra 225.937 B) nessas 9.

| coluna | razão spec/núcleo |
|---|---:|
| `football-date` | **48,6%** |
| `br-abertura` | 70,6% |
| `tpch-orderdate` (ordenado) | 72,5% |
| `br-cadastro` | 74,2% |
| `tpch-shipdate` / `receiptdate` | 83,6% |
| `tpch-commitdate` | 84,4% |
| `tpch-orderdate` (natural) | 86,5% |
| `tpch-sf01-orderdate` | 86,9% |

**As 3 em que o núcleo venceu não perderam a competição — o spec nem se aplicou**:
apply-rate **0%**, `length_wrong` em 3000/3000. Elas não são `YYYY-MM-DD`:

| coluna | grafia real | largura |
|---|---|---:|
| `receita-data-inicio` (e a ordenada) | `20260505` | 8 |
| `retail-invoicedate` | `2010-12-01 08:26:00` | 19 |

Ou seja: **a cobertura de `data-iso` no corpus real é 8 de 10 colunas distintas**. As duas
que faltam são grafias irmãs, exatamente o que o ADR-0041 já previu no mapa de ids — `dtm`
está reservado para datetime (cobriria `retail`), mas **`YYYYMMDD` compacta não tem id
reservado**. É informação para o mapa, não decisão deste lab.

Vale registrar o que isso **não** diz: 5 das 12 colunas são TPC-H (mesmo gerador), e duas
são a mesma coluna natural/ordenada. A comparação `f1` × `f2` isola o efeito da ordem na
mesma coluna: 86,5% → 72,5%.

## 6. Estrutura e migração

- **`d1` multi-coluna**: `#TCF.8M…=quando:dt,…` — o `:dt` viaja no meta por coluna. O
  `view` lazy responde `where('quando','2026-01-01') = 8` (verdade: 8) e `group_count`
  devolve **datas**, não ordinais: é o fix de 2026-08-12 em pé.
- **`d2` dataset `.8H`**: `#TCF.8Hquando:…:dt,n:…` — data como folha, 76 B para 300 dias
  úteis.
- **`e1` migração**: um wire gravado com `:data-iso` **falha alto** hoje
  (`nature-id desconhecido…`) e é lido com
  `decode(w, nature=dataclasses.replace(SPEC_DATA_ISO, wire_id="data-iso"))`. Os 14 wires
  históricos do repositório são todos single-col, logo todos alcançáveis por essa válvula.

## O que fica para depois

- `T-MAX-PERIODO-31`: `a5` mostra o custo do teto 24 num caso concreto (calendário).
- Mapa de ids: `YYYYMMDD` compacta apareceu em dado real e não tem id reservado.
- `T-SPEC-SEM-CARIMBO`: tirar o `:dt` do fio quando o contrato vive nas pontas — em `a1`
  isso levaria os 26 B para ~15.

# Resultado — o spec de datetime segue a receita, e ganha em 7 de 8 regimes

3 blocos, **0 falhas** de RT. Orienta, não fecha.

## 1. O spec funciona — e nunca perde

Separador fixo no do corpus; o FLOOR decide:

| regime | k | núcleo | ordinal | epoch | par | melhor | ganho |
|---|---:|---:|---:|---:|---:|---|---:|
| comercial | 80 | 1229 | **994** | 1059 | 1039 | ordinal | 19,1% |
| log alta card | 2000 | 18185 | 12363 | 15230 | **10851** | **par** | 40,3% |
| batimento 5 min | 2000 | 19786 | 104 | **34** | 669 | epoch | **99,8%** |
| batimento 1 s | 2000 | 590 | 89 | **70** | 91 | epoch | 88,1% |
| esparso multi-ano | 2000 | 43957 | 22686 | **21686** | 29162 | epoch | 50,7% |
| um dia só | 1763 | 23981 | 20636 | **19708** | 20073 | epoch | 17,8% |
| constante | 1 | 35 | 31 | **30** | epoch | 14,3% | |
| **embaralhado** | 80 | 3207 | 3207 | 3207 | 3207 | — | **0,0%** |

**Ganha em 7 de 8, de 14,3% a 99,8%.** No embaralhado o FLOOR recusa e devolve o núcleo — o
nunca-pior funcionando.

`epoch` vence em 5, `ordinal` em 1 (o regime do corpus), `par` em 1 (log). **Nenhum domina.**

## 2. O achado que decide o payload — e não é "menos dígitos"

`epoch` bate `ordinal` por **3×** no batimento (34 contra 104 B). Os wires explicam:

```
epoch    → *2000+300|\1772439960        ← um seq-RLE, a coluna inteira
ordinal  → \639081*\2*\3*\160 …          ← o OBAT fatorou o número
```

**O OBAT extraiu o prefixo invariante como afixo e quebrou a corrida de dígitos que o seq-RLE
precisaria ver.** Isolado, o efeito não é da magnitude:

| dígitos | passo | bytes | quem agiu |
|---:|---:|---:|---|
| 11 | 300 | 79 | OBAT (`!639081*8*2760`) |
| 11 | **30000** | **32** | **seq-RLE** (`*2000+30000\|\63908182760`) |
| 10 | 300 | 29 | seq-RLE |
| 9 | 300 | 28 | seq-RLE |

**O que decide é quantos dígitos ficam invariantes**, não quantos existem. Com passo pequeno
sobre número grande, o prefixo comum é longo, o OBAT o fatora, e o seq-RLE perde a corrida.

É a mesma classe do achado da hora (*binarizar destrói a estrutura*), agora entre **dois
mecanismos do próprio núcleo**: um pode inutilizar o outro. Consequência prática para o spec:
**o payload deve ser o menor inteiro que ainda represente o instante**, porque menos dígitos
invariantes = mais chance de o seq-RLE sobreviver. É por isso que `epoch` (desde 1970) bate
`ordinal` (desde o ano 1).

## 3. O separador: escolher errado custa **zero**, e o argumento de norma NÃO transfere

| coluna emitida com | spec espaço | spec `T` | apply |
|---|---:|---:|---|
| espaço (SQL) | **994** | 1229 | 1,0 / 0,0 |
| `T` (ISO/JSON) | 1229 | **994** | 0,0 / 1,0 |

**Errar é simétrico e não regride**: o wire com o spec errado é **byte-idêntico** ao wire sem
spec nenhum — o FLOOR descarta a rota. É ganho não realizado, nunca custo.

E duas correções ao que eu ia argumentar:

- **Nenhuma das duas grafias de 19 chars é RFC 3339.** A produção é
  `date-time = full-date "T" full-time` **e** `full-time = partial-time time-offset` — o
  offset é **obrigatório**. `2026-03-02T08:26:00` é ISO 8601 *local date-time*, não RFC 3339.
  **O argumento "gramática fechada da RFC 3339" que elegeu o `YYYY-MM-DD` do `data_iso` não
  transfere para o datetime.**
- **O corpus não vota.** O espaço do `InvoiceDate` foi **fabricado** pelo
  `setup_online_retail.py` via pandas (`str()` de `datetime64`); a origem do dataset é
  `M/D/YYYY HH:MM`. Contá-lo como evidência de mundo é contar o default do Python duas vezes.

O que sobra, honestamente: o `T` tem a norma (ISO 8601 removeu a omissão em 2019; TOML só
admite `T` em local-date-time); o espaço tem os **bancos** (SQLite, PostgreSQL, MySQL, SQL
Server style 121 — e o PostgreSQL documenta que escolheu espaço *"for readability"*). E o
Python **se divide**: `str(dt)` dá espaço, `dt.isoformat()` dá `T` — para `date` os dois
coincidem, para datetime não.

**Como o custo é simétrico e sem regressão, isto não é decisão sob risco.** O caminho barato é
o separador virar campo do spec, com **duas instâncias congeladas e dois `wire_id`** — o
precedente de "um objeto por grafia" que o próprio `data_iso` declara. Errar passa a custar
**1 byte de id**, não 19.920.

## 4. A receita protege — os três gates pegam coisas diferentes

Todas as 13 bordas com **RT ok**:

| borda | status | quem pegou |
|---|---|---|
| canônica | `compressible` | — |
| **com `T`** | **`format_noncanonical`** | **a re-emissão** — tem 19 chars, passa a largura |
| sem segundo, fração, timezone, compacta, epoch, espaço à direita | `length_wrong` | o gate barato |
| pt-BR (`02/03/2026 08:26:00`) | `format_mismatch` | **o parse** — tem 19 chars, passa a largura |
| mês 13, `24:00:00` | `format_mismatch` | o parse |
| nulo | `null_slot` | interceptado antes do spec |
| **mista** (corrupção) | `compressible` 1 + `format_mismatch` 1 | **apply 0,5, RT ok** |

**A peculiaridade que o datetime tem e a data não**: suas duas grafias canônicas concorrentes
(`T` e espaço) têm **o mesmo comprimento**. O gate barato não as separa — **só a re-emissão**.
No `data_iso` o guard pega a week-date `YYYY-Www-D`; aqui ele pega a irmã direta.

## 5. Um buraco de teste, achado de lado

No `data_iso`, a **única** classe que depende do guard de re-emissão é a week-date
`YYYY-Www-D` (10 chars, invisível ao gate de largura — 735 formas válidas só em 2021+2026). O
teste existente pina `20191204`, que tem 8 chars e o **gate de largura já recusaria**.

**A classe que só o guard pega não está pinada em teste nenhum.** Um `dtm` que replique a
receita deve nascer com ela — e o `data_iso` deveria ganhá-la.

## O que isto orienta

1. **O datetime cabe na receita**, sem inventar nada: mesmos 4 membros do contrato, mesma
   ordem de gates, mesmo `MARKER_LITERAL`, mesmo fallback por valor. `dtm` já reservado.
2. **O payload deve ser o menor inteiro possível** — não por bytes brutos, mas para **não dar
   prefixo longo ao OBAT** e deixar o seq-RLE agir.
3. **O separador vira campo com duas instâncias congeladas**, porque a norma e o mundo
   discordam e o custo de errar é zero.
4. **A interação OBAT × seq-RLE merece ticket próprio** — é do núcleo, não do datetime, e vale
   para qualquer spec que emita inteiro grande (o `data_iso` está a salvo por sorte: 6 dígitos).

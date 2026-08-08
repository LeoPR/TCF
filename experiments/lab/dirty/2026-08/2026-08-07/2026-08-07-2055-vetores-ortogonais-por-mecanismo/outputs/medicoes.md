# Vetores ortogonais por mecanismo — encode × decode

`n=2000`, 12 repetições por medição, mediana + CV. First-order, uma máquina.
Número publicável vem do `bench_perf`, não daqui.

`prefixo%` = de quanto do fio o valor `j` depende, em % do fio. Dois métodos **construtivos**, cada um no seu domínio (ver `dependencia.py`):
`truncamento` — menor `decode(wire[:p])` que já dá o valor `j` certo (core/pol);
`extração` — valor `j` tirado só de cabeçalho + domínio + 1 quarteto b64, conferido contra o decode (bN modo `B`);
`estrutural` — modo `C`: o domínio vem depois do payload, 100% por construção.

É propriedade do **formato**. O `src/tcf` de hoje lê o fio inteiro em todas as rotas — a propriedade está no fio, não no código.


## bool-2  (k=2)

| variante | bytes | Δ bytes | CPU dec (µs) | CV | Δ CPU por rodada | sinal | pico dec (KiB) |
|---|---:|---:|---:|---:|---|---|---:|
| `core` | 6005 | +0 | 3035.2 | ±20.4% | — | — | 243.2 |
| `+bN(B)` | 351 | -5654 | 1346.0 | ±20.3% | -51%, -59%, -53%, -59% | mais rápido | 33.6 |
| `+bN(C)` | 350 | -5655 | 1381.0 | ±20.6% | -55%, -62%, -46%, -51% | mais rápido | 33.2 |

**Online-ness** — de quanto do fio o valor `j` depende:

| variante | j=0 | j=1 | j=n/2 | j=n-1 |
|---|---|---|---|---|
| `core` | 0.1% | 0.2% | 50.1% | 100.0% |
| `+bN(B)` | 6.0% | 6.0% | 6.0% | 5.4% |
| `+bN(C)` | 100.0% | 100.0% | 100.0% | 100.0% |

## cat-4  (k=4)

| variante | bytes | Δ bytes | CPU dec (µs) | CV | Δ CPU por rodada | sinal | pico dec (KiB) |
|---|---:|---:|---:|---:|---|---|---:|
| `core` | 6016 | +0 | 2956.2 | ±23.6% | — | — | 243.6 |
| `+bN(B)` | 701 | -5315 | 1678.9 | ±21.8% | -51%, -43%, -53%, -53% | mais rápido | 35.8 |
| `+bN(C)` | 700 | -5316 | 1439.0 | ±19.5% | -49%, -49%, -63%, -43% | mais rápido | 34.9 |

**Online-ness** — de quanto do fio o valor `j` depende:

| variante | j=0 | j=1 | j=n/2 | j=n-1 |
|---|---|---|---|---|
| `core` | 0.2% | 0.3% | 50.2% | 100.0% |
| `+bN(B)` | 5.4% | 5.4% | 5.4% | 5.3% |
| `+bN(C)` | 100.0% | 100.0% | 100.0% | 100.0% |

## cat-16  (k=16)

| variante | bytes | Δ bytes | CPU dec (µs) | CV | Δ CPU por rodada | sinal | pico dec (KiB) |
|---|---:|---:|---:|---:|---|---|---:|
| `core` | 6898 | +0 | 3020.9 | ±23.3% | — | — | 248.1 |
| `+bN(B)` | 1418 | -5480 | 1981.5 | ±15.8% | -33%, -17%, -33%, -46% | mais rápido | 71.9 |
| `+bN(C)` | 1417 | -5481 | 1688.6 | ±18.2% | -43%, -41%, -12%, -64% | mais rápido | 69.7 |

**Online-ness** — de quanto do fio o valor `j` depende:

| variante | j=0 | j=1 | j=n/2 | j=n-1 |
|---|---|---|---|---|
| `core` | 0.2% | 0.3% | 50.2% | 100.0% |
| `+bN(B)` | 6.2% | 6.2% | 6.2% | 6.1% |
| `+bN(C)` | 100.0% | 100.0% | 100.0% | 100.0% |

## cat-100  (k=100)

| variante | bytes | Δ bytes | CPU dec (µs) | CV | Δ CPU por rodada | sinal | pico dec (KiB) |
|---|---:|---:|---:|---:|---|---|---:|
| `core` | 7489 | +0 | 3727.7 | ±19.1% | — | — | 264.7 |
| `+pol` | 7488 | -1 | 5110.9 | ±17.6% | +34%, +42%, +25%, +38% | mais lento | 279.4 |
| `+bN(B)` | 2381 | -5108 | 3251.2 | ±14.0% | -1%, -10%, -20%, -15% | mais rápido | 126.6 |
| `+bN(C)` | 2380 | -5109 | 3128.2 | ±14.4% | +1%, -16%, -16%, -25% | INDEFINIDO (sinal troca entre rodadas) | 124.1 |

**Online-ness** — de quanto do fio o valor `j` depende:

| variante | j=0 | j=1 | j=n/2 | j=n-1 |
|---|---|---|---|---|
| `core` | 0.3% | 0.4% | 47.7% | 100.0% |
| `+pol` | 0.2% | 0.4% | 47.7% | 100.0% |
| `+bN(B)` | 2.1% | 2.1% | 2.1% | 2.1% |
| `+bN(C)` | 100.0% | 100.0% | 100.0% | 100.0% |

## uf-27  (k=27)

| variante | bytes | Δ bytes | CPU dec (µs) | CV | Δ CPU por rodada | sinal | pico dec (KiB) |
|---|---:|---:|---:|---:|---|---|---:|
| `core` | 7321 | +0 | 3219.7 | ±20.7% | — | — | 250.8 |
| `+bN(B)` | 1761 | -5560 | 2024.0 | ±16.8% | -39%, -40%, -36%, -40% | mais rápido | 90.5 |
| `+bN(C)` | 1760 | -5561 | 2137.2 | ±14.0% | -38%, -33%, -33%, -37% | mais rápido | 87.5 |

**Online-ness** — de quanto do fio o valor `j` depende:

| variante | j=0 | j=1 | j=n/2 | j=n-1 |
|---|---|---|---|---|
| `core` | 0.1% | 0.2% | 50.0% | 100.0% |
| `+bN(B)` | 5.6% | 5.6% | 5.6% | 5.5% |
| `+bN(C)` | 100.0% | 100.0% | 100.0% | 100.0% |

## digito  (k=2)

| variante | bytes | Δ bytes | CPU dec (µs) | CV | Δ CPU por rodada | sinal | pico dec (KiB) |
|---|---:|---:|---:|---:|---|---|---:|
| `core` | 6007 | +0 | 2983.2 | ±23.4% | — | — | 243.4 |
| `+bN(B)` | 355 | -5652 | 1533.7 | ±19.3% | -32%, -56%, -55%, -56% | mais rápido | 33.7 |
| `+bN(C)` | 354 | -5653 | 1495.7 | ±21.5% | -35%, -56%, -61%, -50% | mais rápido | 33.2 |

**Online-ness** — de quanto do fio o valor `j` depende:

| variante | j=0 | j=1 | j=n/2 | j=n-1 |
|---|---|---|---|---|
| `core` | 0.2% | 0.2% | 50.1% | 100.0% |
| `+bN(B)` | 7.0% | 7.0% | 7.0% | 6.5% |
| `+bN(C)` | 100.0% | 100.0% | 100.0% | 100.0% |

---

**falhas: 0**

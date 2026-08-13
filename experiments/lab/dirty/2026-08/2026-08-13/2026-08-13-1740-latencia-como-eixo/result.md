# Resultado — a latência é o eixo; o período é acessório

> Correção do owner (2026-08-13): *"a questão do período é acessório para relacionar com a
> latência… a rigor o que existe é tentar responder por slices de tempo, ou menor latência.
> e isso vale pra virtualmente qualquer tipo… não é só pegar a data e picotar, é sobre como
> transmitir em pequenos slices de tempo… ela tem que derivar da latência."*

4 perguntas, 0 falhas de round-trip. **Duas medições contrariam registros meus anteriores.**

## 1. "Um modo de baixa latência não pode cortar em qualquer lugar" — **falso**

Foi a frase que fechou a nota de 2026-08-10. Testado agora: dias úteis (período 5), cortados
em **todos** os tamanhos de fatia de 1 a 40 — **40 de 40 legais**, round-trip em todos.

| fatia | em fase? | nº de fatias | bytes | grafia da 1ª fatia |
|---:|---|---:|---:|---|
| 1 | fora | 600 | 11400 | `\739617` |
| 3 | fora | 200 | 5859 | `!2026-01-0*1` |
| **7** | **fora** | 86 | 3672 | `!2026-01-0*1` |
| 13 | fora | 47 | 2476 | `\7396*\1*\7` |
| 37 | fora | 17 | 1052 | `\7396*\1*\7` |

O que eu tinha medido continua verdade — o marcador `*N~…|` **daquela grafia** exige 2p+1
valores e pad rotacionado. O erro foi de **conclusão**: tratei a restrição de *uma grafia*
como restrição *do modo de latência*. Quando o corte não cabe no marcador periódico, o FLOOR
simplesmente escolhe **outra grafia** — dá pra ver na tabela, a grafia muda conforme a fatia
encolhe. A fatia manda; o marcador é um candidato, não um portão.

## 2. O custo de fatiar não é propriedade da data

600 valores, cortados em 8 fatias independentes (cada uma um wire completo):

| tipo | 1 fatia | 8 fatias | multiplicador |
|---|---:|---:|---:|
| texto aleatório | 7807 B | 7854 B | **1,01×** |
| categoria (k=5, dicionário) | 347 B | 676 B | 1,95× |
| **data diária SEM spec** | 414 B | 1115 B | **2,69×** |
| CPF (spec por valor) | 603 B | 2024 B | 3,36× |
| e-mail (afixo comum) | 73 B | 615 B | 8,42× |
| **inteiro sequencial** (sem spec, sem período) | 20 B | 288 B | **14,40×** |
| **data diária COM spec** | 26 B | 428 B | **16,46×** |
| data dias úteis COM spec (período 5) | 34 B | 607 B | 17,85× |

Duas leituras que fecham a questão:

- **A mesma coluna de datas** aparece em 2,69× (sem spec) e 16,46× (com spec). Se o custo
  fosse propriedade "da data", os dois seriam iguais. Não são — quem manda é o **mecanismo
  de ganho**, não o tipo.
- **`inteiro sequencial` (14,40×) não é data e não tem período nenhum**, e está na mesma
  faixa da data com spec. O período não explica a coluna.

## 3. O que governa, então: **de onde vem a compressão**

- Ganho **global** (progressão/sequência: `*N+1|`) — cada corte o destrói e cada fatia
  recomeça do zero. Caro: 14–18×.
- Ganho **local** (afixo, dicionário, por-valor) — cada fatia o reconstrói sozinha. Barato:
  1,9–8,4×.
- **Sem ganho** — fatiar é de graça: 1,01×.

Isso responde ao "vale pra virtualmente qualquer tipo": a régua é **quanto do ganho era
global**. Data com spec só é o caso extremo porque é onde o ganho global é maior do projeto
(26 B para 600 valores).

## 4. O penhasco: **100 valores por fatia**, e ele não é de calendário

Data diária com spec, uma fatia por vez:

| valores na fatia | bytes | B/valor | grafia |
|---:|---:|---:|---|
| 600 | 26 | 0,043 | `*600+1\|\739617` |
| 300 | 26 | 0,087 | `*300+1\|\739617` |
| 150 | 26 | 0,173 | `*150+1\|\739617` |
| **100** | **26** | **0,260** | `*100+1\|\739617` |
| 90 | 58 | 0,644 | `\739*\6*\1*\7` ← o marcador **desligou** |
| 75 | 44 | 0,587 | `\7396*\1*\7` |
| 20 | 44 | 2,200 | `\7396*\1*\7` |
| 1 | 19 | 19,000 | `\739617` |

**De 100 a 600 valores o wire custa 26 bytes — constante.** Abaixo de 100 o marcador
seq-RLE perde para o corpo OBAT (em fatia curta os ordinais compartilham o prefixo `7396…`,
e o OBAT ganha), e o custo por valor salta 2,5×.

Para um modo de latência isso é a informação operacional: **a fatia mais barata que ainda
entrega rápido é a menor que mantém o mecanismo ligado.** Aqui, 100. Fatiar em 150 é pagar
latência sem economizar byte; fatiar em 90 é pagar byte sem ganhar latência proporcional.
E esse número sai do FLOOR — não do período (5), não do calendário (12/24/31/48).

*(Ruído honesto: 90 valores custam 58 B e 80 custam 44 B — não-monotônico. É o OBAT: em 90
valores os ordinais cruzam `739700` e o afixo comum encurta. Não muda a leitura.)*

## 5. Convertendo "200 ms" em número de valores

Tempo para encodar **uma** fatia de 100 valores (mediana de 7; ordem de grandeza, máquina
não-quiescente — número probatório é `bench_perf`):

| tipo | ms / fatia de 100 | valores que cabem em 200 ms |
|---|---:|---:|
| categoria (k=5) | 1,489 | ~13.428 |
| inteiro sequencial | 4,382 | ~4.563 |
| CPF (spec) | 5,135 | ~3.894 |
| texto aleatório | 6,645 | ~3.009 |
| e-mail (afixo) | 7,799 | ~2.564 |
| data diária (core) | 9,328 | ~2.144 |
| data diária (spec) | 9,751 | ~2.051 |
| data dias úteis (spec) | 14,029 | ~1.425 |

O mesmo deadline vira fatias **9× diferentes** conforme o tipo. Isso é o que "a fatia deriva
da latência" quer dizer operacionalmente.

## A régua, fechada

A fatia sai de um intervalo, e **as duas pontas são medidas, nenhuma é de calendário**:

```
teto  = quantos valores cabem no deadline        (throughput — §5)
piso  = menor fatia que mantém o mecanismo ligado (o penhasco — §4)
fatia ∈ [piso, teto]
```

Para data diária com spec e 200 ms: **[100, 2051]**. Escolhe-se dentro do intervalo.

E há um ponto de decisão honesto que a régua expõe: o piso de 100 valores **custa 9,75 ms**.
Com um deadline abaixo disso, o teto cai abaixo do piso e o intervalo fica **vazio** — não dá
para atender sem desligar o mecanismo e pagar o penhasco. Isso é uma resposta clara para
"menor latência possível": há um chão, ele é medível, e ele não é o período.

## O que isso implica para os registros

1. `deadline_ms` **não** deve ter "corte alinhado ao período". O corte vem do tempo; a
   grafia se adapta.
2. `MAX_PERIODO = 24` está documentado no código como *"cobre mensal (12) e quinzenal-ano
   (24)"* — justificativa de **calendário** para um mecanismo genérico (o próprio comentário
   ao lado cita "ids por turno `10,10,10,50`"). O teto real é de **custo de detecção**
   (o detector é O(n·P)), que é orçamento de tempo — o mesmo eixo da latência.
3. `T-MAX-PERIODO-31` pede 31 "porque dia-do-mês"; a inspeção de hoje (`a5`) quase pediu 48
   "porque bissexto". Os dois raciocínios são de domínio, e a escalada 12→24→31→48 é o
   sintoma do enquadramento errado.
4. O que falta medir para um `deadline_ms` honesto: o **tempo** (ms), não só os bytes. Esta
   rodada mediu o preço em bytes; a régua de latência precisa do throughput de encode por
   fatia para converter "200 ms" em "N valores".

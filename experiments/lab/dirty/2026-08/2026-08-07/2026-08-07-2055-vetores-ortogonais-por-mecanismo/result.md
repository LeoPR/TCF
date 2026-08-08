# Resultado — vetores ortogonais por mecanismo, encode × decode

**2026-08-07 · dirty · first-order (uma máquina, um momento)**

`n=2000`, 12 repetições × 4 rodadas **intercaladas entre variantes**. Números completos em
[`outputs/medicoes.md`](outputs/medicoes.md).

---

## O que este lab derruba

Os welds recentes fecharam com "encolheu N bytes". Medindo os outros vetores, **um dos dois
mecanismos soldados não é win-win — é troca, e troca ruim no caso que expõe.**

## Regra de leitura: sinal ≠ magnitude

O CV desta máquina fica em **±14% a ±24%**. Nesse ruído:

- **o SINAL é confiável** quando a mesma direção aparece nas 4 rodadas intercaladas;
- **a magnitude NÃO é.** Medindo a polaridade em rodadas *separadas* (o jeito errado) saiu
  **+86%, +60%, +37%, +11%** — quatro números para o mesmo fenômeno. Intercalado, virou
  **+34%, +42%, +25%, +38%**: sinal firme, magnitude entre +25% e +42%.

O lab marca `INDEFINIDO` quando o sinal troca entre rodadas (aconteceu em `+bN(C)` no
`cat-100`). Magnitude publicável vem do `bench_perf`, com calibrador e gate térmico — não
daqui.

---

## Mecanismo 1 — bN de domínio: **TROCA**, favorável em 3 dos 4 vetores

| vetor | direção | resultado | veredito |
|---|---|---|---|
| **bytes** | — | −5108 a −5654 B (−68% a −94%) | **ganha** |
| **CPU** | decode | mais rápido em 5 dos 6 casos, sinal firme (−17% a −59%) | **ganha** |
| **memória** | decode | 243→34 KiB (k=2) · 265→127 KiB (k=100) | **ganha** |
| **online-ness** | decode | **perde no início, ganha no resto** — ver abaixo | **troca** |

### A troca, medida

| | valor `j=0` | `j=1` | `j=n/2` | `j=n-1` |
|---|---|---|---|---|
| `core` | **0,1–0,3%** | 0,2–0,4% | ~50% | 100% |
| `+bN(B)` | 2,1–7,0% | 2,1–7,0% | **2,1–7,0%** | **2,1–7,0%** |

O core é **line-oriented e forward-only**: o 1º valor sai depois de ~0,2% do fio, mas o
custo **cresce linearmente** — o último valor precisa de 100%.

O bN é **plano**: qualquer valor custa cabeçalho + domínio + 1 quarteto base64. Pior no
começo (0,2% → 6%, ~30× mais), melhor a partir de ~3% da coluna, e **muito** melhor em
acesso aleatório.

**Nenhum domina.** A escolha depende da condição:

| condição | melhor | por quê |
|---|---|---|
| stream, consumo sequencial, latência do 1º valor importa | `core` | 0,2% vs 6% |
| stream, coluna inteira | `+bN(B)` | menos bytes na rede, menos CPU, menos memória |
| acesso aleatório / poucas células de muitas | `+bN(B)` | plano em `j`; o core paga O(j) |
| coluna curta (poucas dezenas) | medir | o domínio vira custo fixo dominante |

### O modo `C`, agora com número

| | j=0 | j=1 | j=n/2 | j=n-1 |
|---|---|---|---|---|
| `+bN(C)` | 100% | 100% | 100% | 100% |

O domínio vem **depois** do payload: nenhum valor sai antes do fio inteiro. Por 1 byte a
menos que o modo `B`. A ADR-0036 decidiu isso **por argumento**; agora tem número:
**6% → 100%** de prefixo, para ganhar **1 byte**. A decisão estava certa e passa a ser
defensável com medida.

---

## Mecanismo 2 — polaridade: **TROCA RUIM** no caso que a expõe

Caso `cat-100` (o único da bateria em que a polaridade ativa):

| vetor | resultado | veredito |
|---|---|---|
| **bytes** | 7489 → 7488 = **−1 B** | ganha (marginal) |
| **CPU decode** | **+25% a +42%**, sinal firme nas 4 rodadas | **perde** |
| **memória decode** | 264,7 → 279,4 KiB = **+5,5%** | **perde** |
| **online-ness** | 0,2% / 0,4% / 47,7% / 100% — igual ao core | empata |

**−1 byte por +25–42% de CPU e +5,5% de memória.**

O mecanismo é uma camada de borda: o decode **despolariza antes de despachar**, o que é uma
passada extra sobre o corpo inteiro. O custo é estrutural, não acidental.

### O problema não é o mecanismo — é o critério

O FLOOR da polaridade compara **bytes**. Com `−1 B` ele escolhe polarizar, e paga o CPU sem
nunca ter olhado pra ele. Numa coluna onde o bN não se qualifica (`k > 256`), essa escolha
é a que vai pro fio.

**Isto é a preocupação do owner materializada num caso concreto**, e não é hipótese: está
medido, com sinal firme em 4 rodadas intercaladas.

> **Ressalva honesta:** um caso, um `k`, uma máquina. Não é "a polaridade é ruim" — é "a
> polaridade **pode ser** troca ruim, e o critério de hoje não consegue nem ver isso".
> Caracterizar em quantos casos reais o ganho é 1–2 B é trabalho que falta.

---

## A escada de 4 degraus, aplicada

O processo pedido: (1) focar numa coisa · (2) ver se é barato implementar as variações ·
(3) estudar se dá pra escolher · (4) ver se dá pra deixar automático.

| mecanismo | 1. foco | 2. variações baratas? | 3. dá pra escolher? | 4. dá pra automatizar? |
|---|---|---|---|---|
| **bN modo B/C** | ✅ soldado | ✅ **as duas já existem** — o `C` é decodável, falta só o opt-in de emissão (`T-BN-LOTE`) | ⚠️ falta o **parâmetro**; hoje o `min()` decide sozinho | ❌ falta o sinal: quem sabe se o consumidor é stream ou random? |
| **bN ligado/desligado** | ✅ soldado | ✅ o candidato já é materializado e descartável | ⚠️ falta parâmetro (`T-FORCAR-MECANISMO-PARAM`, já aberto) | ⚠️ o `min()` automatiza **por byte**; automatizar por vetor exige custo no FLOOR |
| **polaridade** | ✅ soldada | ✅ ligar/desligar é trivial (o sufixo vazio já é a forma de hoje) | ❌ **não há parâmetro** | ❌ e o critério automático de hoje escolhe **contra** o CPU |

O degrau 2 está barato nos três — as variações **já existem no código**. O gargalo é o
degrau 3: **nenhum mecanismo tem parâmetro**, então nem dá pra medir a alternativa em
produção, quanto mais escolher.

---

## Direções

Nenhuma é ticket novo por conta própria; duas encaixam em tickets já abertos.

1. **Um `min()` que enxergue mais de um vetor.** Hoje é `min(candidatos, key=bytes)`. O
   mínimo viável: um critério de desempate que, entre candidatos **dentro de uma margem de
   bytes** (ex.: ≤ 0,5%), prefira o mais barato nos outros vetores. Isso sozinho resolve o
   caso da polaridade (−1 B em 7489 = 0,013%). **Custo: baixo** — é uma função de chave, não
   uma reestruturação.
2. **Parâmetro de mecanismo** (`T-FORCAR-MECANISMO-PARAM`, já aberto). Sem ele não se mede
   a alternativa. É o degrau 3 da escada, e está bloqueando os outros dois mecanismos também.
3. **Registrar o perfil por mecanismo na documentação** — mesmo sem código. O manual da
   família bN já descreve o wire; falta a tabela "em que condição este mecanismo é a
   escolha certa". **Custo: zero de runtime**, e é o que o owner pediu como piso ("nem que
   seja na documentação").
4. **Levar online-ness pro `bench_perf`.** Hoje ele mede wall/cpu/heap/rss e **nada** de
   streaming — nenhum grep por `first_byte`/`streaming` acha coisa alguma. O método de
   truncamento deste lab é barato e usa o decoder real.
5. **`T-BN-LOTE` ganhou argumento contrário medido.** O modo `C` custa 1 byte a menos e
   **100% de prefixo**. Se um dia for emitido, que seja opt-in explícito para quem lê o
   arquivo inteiro em disco — nunca default, e nunca em transmissão.

---

## O que este lab NÃO fecha

- **Encode não foi separado por mecanismo.** O corpo do core é o mesmo em todas as
  variantes, então a CPU de encode medida seria idêntica por construção — o custo marginal
  do candidato bN (materializar e descartar quando perde) **não foi medido**. É a metade
  que falta do "por encode e decode" pedido.
- **Uma máquina, um momento, sem calibrador.** Magnitude não é publicável.
- **`n=2000` fixo.** A curva em `n` (onde o domínio deixa de dominar) não foi varrida.
- **Um caso só de polaridade.** A bateria tem 6 datasets e a polaridade ativa em 1.
- **O `src/tcf` não faz nada disso.** Toda a online-ness medida é do **formato**; o decoder
  de hoje lê o fio inteiro em todas as rotas. Sem acessor, "o TCF decodifica online" seria
  overclaim.

## Duas tentativas jogadas fora antes desta

Registradas no cabeçalho de [`dependencia.py`](dependencia.py) porque o método importa:

1. **Leitor mínimo por rota** — mentiu em ~1/3 das células. Ler o corpo do core exige a
   tabela de apelidos do OBAT e a compressão de afixo: um leitor mínimo correto **é** o
   decoder.
2. **Mutação de cauda** — deu 100% em tudo. Não porque o formato seja sequencial, mas
   porque quase toda mutação invalida o fio e o método (conservador) empurrava o prefixo pra
   cima. Sólido e inútil.

O que ficou são dois métodos construtivos: **truncamento** com o decoder real (core) e
**extração aritmética** conferida contra o decode (bN modo B).

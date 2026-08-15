# Resultado — float e hora nas vertentes que o fechamento não tinha passado

6 vertentes × 6 colunas (float/hora sintéticos e reais + int/str como réguas), **0 falhas**
de RT. Orienta, não fecha.

## A matriz — o que os fechamentos cobriram e o que este lab acrescenta

| vertente | float | hora | status |
|---|---|---|---|
| 5 eixos estruturais | ✓ lab `1616` | ✓ lab `2230` | já estava |
| specs com especialidades | ✓ escala/fração, adiadas com razão | ✓ ordinal + `H-DENSE-MODE-03` | já estava |
| wire fecha spec→saída (single) | ✓ tag `n`, RT com tipo | ✓ string, RT | já estava |
| **wire fecha na TABELA** | ✓ `.8H`, RT com tipo | ✓ | **novo** |
| **saída lazy (`view`)** | ✗ **não abre** | ✗ **não abre** | **novo — gap** |
| **latência (fatiar)** | 1,11×–2,62× | 0,96×–1,33× | **novo** |
| **granularidade de entrega** | bN-B: domínio streamável + payload 1 bloco | linha-a-linha (até 1999 pontos) | **novo** |
| **velocidade (dev-run)** | 13,5–133 µs/val | **154–218 µs/val** | **novo** |
| **memória (pico)** | 470 KB–1,3 MB | **até 3 MB (126× a entrada)** | **novo** |
| **transporte (pós-gzip)** | **−18,8% a −175,9%** | −5,7% a −30,2% | **novo — duro** |

## 1. O dispatch de tabela é type-coherent — e a ponta lazy não abre tipos

Descoberta da 1ª rodada (eu rotulava errado): **dict de só-strings sai `#TCF.8M`; dict com
qualquer tipo sai `#TCF.8H`**. O RT com tipo fecha no `.8H` (medido: 3 colunas, `True`).

Mas o **`view` só abre `.8M`** — recusa o single tipado, o single de strings e o `.8H`. E o
`.8M` interno, se alimentado com float, **devolve string** (`1.5` → `'1.5'`).

**Consequência**: hoje **não existe caminho lazy para coluna tipada nenhuma**. Uma tabela com
float ou hora obrigatoriamente sai `.8H`, e o `.8H` não tem view. É a **5ª divergência da mesma
causa** que a direção *"single-col é multi-col de UMA"* já nomeou (solda dupla) — agora vista
da ponta de leitura.

## 2. Latência: o custo de fatiar depende da CLASSE do vencedor

| coluna | p=1 | p=8 | mult | por quê |
|---|---:|---:|---:|---|
| `float-sint` (bN, k=97) | 3039 | 7953 | **2,62×** | o **domínio viaja em cada fatia** |
| `float-real` (literal `n!`) | 10137 | 11251 | **1,11×** | linha-a-linha quase não paga |
| `hora-sint` (polaridade `!`) | 18650 | 17933 | **0,96×** | fatiar **ficou menor** |
| `hora-real` | 10619 | 14176 | 1,33× | misto |
| réguas int/str | — | — | 1,16–1,17× | |

Duas leituras:

- **O bN é o pior candidato para fatiar** — cada fatia repete o domínio. A régua da data
  (14–18× no spec) e esta (2,62× no bN) apontam a mesma lei: *quanto mais global o mecanismo,
  mais caro o corte*. O modo-pulso deveria escolher fatia **ciente da classe** do vencedor.
- **`hora-sint` fatiada fica MENOR (0,96×)** — achado sem causa provada: fatias menores
  permitem à polaridade eleger caracteres diferentes por fatia. Registrado como orientação.

## 3. Velocidade e memória — a primeira medição por tipo (dev-run declarado)

Com o int como régua (mesma máquina, mesmo instante, mesmo n=2000):

| coluna | enc µs/val | vs int | pico KB | vs entrada |
|---|---:|---:|---:|---:|
| `int-regua` | 10,3 | 1× | 429 | — |
| `float-sint` | 13,5 | 1,3× | 470 | — |
| `float-real` | 132,6 | **13×** | 1294 | 77× |
| `hora-real` | 153,7 | **15×** | 893 | 37× |
| `hora-sint` | 217,6 | **21×** | **3039** | **126×** |

O que encarece **não é o tipo — é a cardinalidade do texto**: as colunas caras são as de k
alto e linha-a-linha, onde OBAT+HCC trabalham de verdade. O pico de memória de 3 MB para 24 KB
de entrada é evidência nova para o `T-BUDGET-DE-BUSCA`.

## 4. Transporte: o ganho é TERMINAL — e no transporte o sinal INVERTE

| coluna | terminal (wire vs JSON) | transporte (gzip vs gzip) |
|---|---:|---:|
| `float-sint` (bN) | **+75,2%** | **−175,9%** |
| `int-regua` (bN) | +80,2% | −137,9% |
| `str-regua` (bN) | +90,1% | −67,6% |
| `float-real` | +39,3% | −18,8% |
| `hora-real` | +55,8% | −5,7% |

**Em todas as seis colunas o gzip do JSON cru é menor que o gzip do wire.** O caso extremo é o
bN: o base64 é ruído para o gzip, enquanto o JSON regular comprime a quase nada.

Isso não é novidade qualitativa — o gate do bN já tinha visto 8,8% terminal contra 1,7%
pós-brotli, e a direção do owner já diz que *"byte NÃO é o eixo do bN (latência/terminal é)"* —
mas é a primeira vez que a leitura dupla é feita **por tipo**, e o sinal aqui é **negativo**,
não só menor. **A vertente transporte precisa entrar no ritual de fechamento**, nem que seja
para declarar "este tipo é para leitura terminal".

## 5. O que segue faltando (gaps declarados, não resolvidos)

1. **A ponta lazy para tipos** — ou o `view` aprende `.8H`/single, ou a rota de strings ganha
   tag de tipo. Evidência nova para a direção *single-col é multi-col de UMA*.
2. **Guarda `compressible > 0` no FLOOR** — o carimbo `:cpf` do fechamento da hora.
3. **Perfil de transporte** — um modo que prefira grafias gzip-friendly quando o destino é
   recomprimido (variante declarada, nunca default calado — a mesma regra de sempre).
4. **Fatia ciente da classe** — o pulso deveria saber que bN fatia caro e literal fatia grátis.

## O ritual de fechamento, estendido

O owner: *"às vezes esqueço de cobrar"*. Para não depender de cobrança, o fechamento de tipo
passa a ter **os 5 eixos estruturais + as 4 vertentes de execução** (tabela/lazy, latência de
fatia, velocidade+memória dev-run, terminal×transporte). Float e hora agora têm as dez;
`int` e `data` têm as seis primeiras — completá-las é barato com este `run.py` como gabarito.

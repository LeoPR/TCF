# 2026-08-21-0600 — as quatro camadas que eu vinha misturando

> *"só não quero misturar a entrada do dataset e o roundtrip pra construir, a saída em arquivo
> que possa ser útil, e o transporte. tudo é coisa diferente [...] temos só que possibilitar um
> flag e um default pra cada situação [...] Só não pode atrapalhar o encode/decode. [...] o
> transporte pode omitir tudo que não precise, já em saída pra arquivo pode ser conveniente o
> `\n`, mas se mesmo esse não tiver necessidade, avise."*

## A correção que a separação expõe

Eu vinha tratando "o wire" como uma coisa só, e por isso discutindo **1 byte** (o LF terminador)
como se fosse a questão. Separando as camadas, o que aparece é outro:

| camada | o que precisa |
|---|---|
| **C1 entrada** | o dataset |
| **C2 roundtrip** | **tudo** — é o contrato de correção, intocável |
| **C3 arquivo** | o cabeçalho (auto-descrição; é por ele que `file`/libmagic identifica) |
| **C4 transporte** | **nada** que o canal já declare |

E o cabeçalho vale **7–8 bytes**, não 1.

## M2 — o transporte: eu estava discutindo o troco

| caso | wire | −LF | −cabeçalho | −ambos | economia |
|---|---:|---:|---:|---:|---:|
| 1 CPF | 24 B | 23 B | 16 B | **15 B** | **37,5%** |
| 3 curtos | 16 B | 15 B | 9 B | **8 B** | **50,0%** |
| 10 valores | 17 B | 16 B | 10 B | **9 B** | 47,1% |
| multi 2×2 | 21 B | 21 B | 6 B | **6 B** | **71,4%** |
| hierárquico | 44 B | 43 B | 19 B | **18 B** | 59,1% |
| 100 valores | 36 B | 35 B | 29 B | 28 B | 22,2% |
| 1000 valores | 61 B | 60 B | 53 B | 52 B | 14,8% |

**O LF vale 1 byte; o cabeçalho vale 7–8.** Em payload minúsculo — o alvo declarado do `.8`
(`O-FMT-15/16`) — o cabeçalho é **a maior fatia do wire**. Passei três ciclos discutindo o
byte errado.

### ⚠ Revisão crítica do meu próprio experimento

A função `para_transporte` deste lab devolve `(payload, contrato)`, e o `contrato` é
literalmente o cabeçalho virado dicionário. **Isso não é economia — é mudança de lugar.** O
número da tabela é o **teto do que é omissível**, não um ganho líquido.

O ganho só é real quando a declaração fora de banda é **amortizada**:

- **ganha**: WebSocket/gRPC/MQTT onde o tipo é negociado uma vez para N mensagens; campo dentro
  de um envelope maior que já declara o schema; fila com um tópico por formato.
- **não ganha**: requisição HTTP avulsa — o `Content-Type: application/x-tcf; v=8; route=M`
  custa muito mais que os 7 bytes economizados.

Sem essa ressalva a tabela mente. Com ela, ela diz a coisa certa: **existe 22–71% de cabeçalho
omissível esperando um canal que o amortize.**

## M2b — omitir não é ideia nova: já existe um flag

```
multi-col normal          21 B   '#TCF.8M!3=a,!b'
+ drop_names=True         18 B   '#TCF.8M!3,!'      (−3 B)
+ sem cabeçalho (C4)       6 B                       (−12 B)   total −71%
```

O **`drop_names`** já é exatamente uma omissão de transporte: o contrato vive nas pontas e os
nomes não viajam (ADR-0029). E o `T-SPEC-SEM-CARIMBO` registra a mesma ideia para o `:id` de
nature — **registrado, não implementado**.

Ou seja: **a família já começou.** Faltava o conceito que a une, que é o que você acabou de
nomear. `drop_names` não é um knob solto — é o primeiro membro de um **perfil de transporte**.

## M3 — o LF do arquivo: você pediu para eu avisar. Aviso.

**Ele tem utilidade real, mas estreita**, e não é a que você lembrava:

| onde importa | onde **não** importa |
|---|---|
| `wc -l` (subconta a última linha sem ele), `head`/`tail`/`split` | **identificação de tipo** — `file`/libmagic lê magic, e o TCF tem um forte no início |
| `git diff` marca `\ No newline at end of file` | o próprio decode do TCF |
| `while read` de shell perde a última linha | |

**E a boa notícia**: o encode **já emite** o LF em 7 das 10 rotas. Ou seja, na maioria dos casos
a conveniência de arquivo **vem de graça** — exatamente a situação que você descreveu ("se por
conveniência já atende o formato de arquivo, ótimo").

**O aviso**: para as 3 rotas que não emitem (multi-col, multi-col n=1, tipado bool),
**acrescentar o LF para arquivo exigiria um leitor que o tire de volta** — porque `decode` de
um multi-col com LF extra dá `ValueError`, e em `{'a':['1']}` acrescenta um valor vazio. Então
o default de arquivo deve ser **o wire como está**, e a uniformização POSIX seria um flag com
leitor casado, não um "acrescente e pronto".

## M4 — a prova de que separar não toca `encode`/`decode`

As duas transformações foram implementadas como **funções puras sobre o wire**, com inversa
exata: **7 casos, ida e volta, 0 falhas**. Nenhuma linha de `encode`/`decode` muda — que era a
sua condição.

```
exemplo (1 CPF):  wire 24 B  ·  arquivo 24 B  ·  transporte 15 B + contrato fora de banda
```

## O desenho que isso sugere (não implementado)

Um **perfil** por situação, com default explícito, sobre o wire canônico:

| perfil | default | o que faz |
|---|---|---|
| `wire` (C2) | — | o que `encode` devolve. **Intocável.** |
| `arquivo` (C3) | = `wire` | nada por padrão; flag opcional para uniformizar o LF (com leitor casado) |
| `transporte` (C4) | = `wire` | flag que omite cabeçalho e/ou LF, devolvendo o contrato fora de banda |

O `drop_names` seria absorvido como membro do perfil de transporte, em vez de knob solto.

## Não medido (declarado)

- **O custo do contrato fora de banda** em canais reais — a tabela dá o teto, não o líquido.
- Se omitir o cabeçalho **interage** com `drop_names` de forma não-aditiva (medi os dois no
  mesmo caso, não em cruzamento completo).
- Nada disto foi implementado: é desenho com números, não weld.
- O `stamp=False` **não** é a omissão que eu supus — testei e economiza 0 B; a omissão do `:id`
  é o `T-SPEC-SEM-CARIMBO`, que não existe.

## Evidência

[`run.py`](run.py) com M1–M4 e assert em M4 (inversa exata em 7 casos). 25 arquivos em
[`inputs/`](inputs/)+[`outputs/`](outputs/), incluindo as três formas do mesmo dado
(`exemplo-C2-wire-canonico.tcf`, `exemplo-C3-arquivo.tcf`, `exemplo-C4-transporte.bin` +
contrato). [`resultado.json`](resultado.json).

## Conexões

- Direção *"contrato externalizado + aceleradores"* — é onde este perfil mora
- [ADR-0029](../../../../../../docs/adr/) (`drop_names`) · `T-SPEC-SEM-CARIMBO`
- **H-15-08** — o LF como candidato a omissão de transporte; este lab mostra que ele é o
  **menor** dos candidatos
- Labs do arco: [`0400`](../2026-08-21-0400-lf-final-do-wire/) ·
  [`0500`](../2026-08-21-0500-lf-final-tem-funcao/)

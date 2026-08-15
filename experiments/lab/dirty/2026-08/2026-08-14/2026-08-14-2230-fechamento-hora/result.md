# Resultado — HORA fechada, com uma peculiaridade INVERTIDA

7 regimes sintéticos + 9 bordas + 1 coluna real + a ciclicidade medida em 4 escalas.
**0 falhas** de RT.

## O que mais importa: a ciclicidade **ajuda**

Estava registrado — por mim, na avaliação de 2026-08-14 — que a hora é **cíclica** e que isso é
a diferença estrutural contra a data, cujo ordinal é *absoluto e monotônico*: *"o seq-RLE vê um
salto negativo a cada meia-noite"*. Isso está certo sobre o seq-RLE e **errado sobre o
resultado**.

Mesmo batimento de 15 min, cíclico (volta a zero) contra absoluto (cresce sem voltar):

| dias | n | cíclico | absoluto | delta |
|---:|---:|---:|---:|---:|
| 1 | 96 | 751 B | 751 B | 0 |
| 2 | 192 | **980 B** | 1386 B | **−29,3%** |
| 3 | 288 | **1093 B** | 2041 B | **−46,4%** |
| 7 | 672 | **1541 B** | 5707 B | **−73,0%** |

**Ciclar é repetir.** No dia 2 o `00:00:00` volta, e o que perde o seq-RLE ganha o **dedup** —
o wire de 2 dias sai como `#TCF.8B7c0`, o **bN de domínio** com `w=7`, porque há 96 valores
distintos em 192 linhas. Aos 7 dias são os mesmos 96 em 672.

A peculiaridade correta não é *"a ciclicidade atrapalha"*, é: **a ciclicidade troca um
mecanismo por outro, e o `min()` faz a troca sozinho.** É a distinção igualdade × proximidade
que o projeto já tem nomeada — a hora cai do lado da igualdade justamente por ciclar.

## O ordinal é complementar, não substituto

Hora como segundos-desde-meia-noite — o desenho irmão do `data-iso`:

| dias | texto | ordinal | ganho |
|---:|---:|---:|---:|
| 1 | 751 B | **42 B** | **94,4%** |
| 2 | 980 B | 561 B | 42,8% |
| 7 | 1541 B | 1434 B | **6,9%** |

A 1 dia o ordinal é uma **progressão aritmética perfeita** (0, 900, 1800…) e o seq-RLE a
esmaga: 42 B. A partir do dia 2 a progressão quebra no wrap, o ordinal perde a vantagem — e o
texto, esse sim, ganha com a repetição.

**Os dois mecanismos servem regimes opostos**: ordinal onde não há wrap, dedup onde há. Um
spec de hora que emitisse ordinal sempre seria pior que o núcleo na maioria dos dias.

## Os 5 eixos

| eixo | hora |
|---|---|
| **1 dispatch** | chega como **string** — a hora não é tipo nativo do Python no wire; sem tag |
| **2 candidatos** | percorre o **mesmo `min()`**: literal, polaridade (`!`, `!!`) e **bN de domínio** (`B7c0`) — o mesmo bN de bool/int/float/string |
| **3 API** | `min_len=` aceito; `nature=` processado com FLOOR — **exceto uma anomalia, abaixo** |
| **4 wire** | sem tag (é string); discriminador no índice 6 como todos |
| **5 RT** | 19/19 casos fecham, incluindo todas as bordas |

**Comunidade: máxima.** A hora não tem caminho próprio em lugar nenhum do núcleo.

## As bordas — o formato preserva o que a norma discute

Todas as 9 atravessam com RT ok, **porque o núcleo trata hora como string e não a
interpreta**. Isso é bom para o formato e é exatamente onde um *spec* teria de decidir:

| borda | o que a norma diz | quem recusaria |
|---|---|---|
| `24:00:00` | **válido em ISO** (removido em 2019, reintroduzido em Amd 1:2022), **proibido em RFC 3339** | Python recusa; e está **fora de 0..86399** |
| `23:59:60` | leap second, **válido em ISO e RFC 3339** | Python recusa; Arrow manda corrigir com perda; Temporal coage p/ `:59` |
| `.5` / `.500000` | mesmo instante, duas grafias; **sem limite normativo** de dígitos | Python emite sempre 6, e **trunca em silêncio** o excesso |
| `12:00` × `12:00:00` | precisão reduzida é ISO válido | `isoformat()` sempre emite segundos |
| `120000` | forma **básica** do ISO | ambígua com o inteiro 120000 |
| `-00:00` | RFC 3339 dava semântica própria; **RFC 9557 (2024) reverteu** | ISO proíbe; Python colapsa em `+00:00` |

O núcleo preserva todas byte-a-byte hoje. **Um spec de hora teria de recusar** as que não têm
volta (`24:00`, `:60`, `-00:00`, offsets sub-minuto) e tratar as demais como **flag de coluna**,
não como grafia por célula.

## O achado que não era do escopo: uma nature que aplica em 0% **vence e carimba**

`nature=SPEC_CPF` numa coluna de horas `HH:MM`:

```
sem nature : 831 B   header='#TCF.8'
com CPF    : 773 B   header='#TCF.8 :cpf'      <- 58 B MENOR, e venceu o FLOOR
telemetria : {'spec':'cpf', 'total':96, 'compressible':0, 'apply_rate':0.0,
              'by_status':{'length_wrong':96}, 'used':True}
```

**Zero valores comprimidos** (`length_wrong` em 96/96) — todo valor virou `_HH:MM`. O prefixo
`_` uniforme dá ao OBAT um afixo compartilhado que ele fatora, e o candidato sai menor. O FLOOR
faz o que promete (escolhe o menor) e **o wire sai declarando `:cpf` numa coluna de horas**.

O RT fecha, então não é corrupção — é **metadado falso**. E o `:id` é justamente o campo
self-describing que um leitor usa para saber o que a coluna é.

É a **4ª situação** do `T-NATURE-IGNORADA-CALADA`, e a inversa das três registradas: lá o
usuário pede spec e não recebe; aqui ele passa um spec irrelevante e o formato **o adota e o
carimba**. Registrado no ticket.

## As peculiaridades da HORA (declaradas)

1. **Não é tipo nativo.** Chega como string; é da família "spec sobre STRING" (data, CPF, IP),
   não da família nativa (int, float, bool). Sem tag no wire.
2. **É cíclica — e a ciclicidade AJUDA.** Troca seq-RLE por dedup, e o `min()` faz a troca. É a
   inversão do que estava registrado.
3. **O ordinal é complementar, não substituto** — 94,4% sem wrap, 6,9% com.
4. **Tem grafia válida-na-norma e irrepresentável-no-pivô**: `24:00:00` é ISO legal, está fora
   de `0..86399`, e o Python recusa. **Nenhum outro tipo fechado tem isso.**
5. **Não pode validar leap second sozinha**: `23:59:60` só é legítimo em 30/06 ou 31/12 — e uma
   coluna de hora pura **não tem a data**.
6. **A detecção é minada de falsos positivos** (varredura de 102 colunas): `0..86399` pega **44
   colunas** que não são hora; `HHMMSS` pega chaves (`o_orderkey`, `fnlwgt`); e `AM`/`PM` por
   substring pega **`uf_sigla='AM'` — o Amazonas**.
7. **O corpus não tem hora pura.** Zero colunas. A única parte-hora é o `InvoiceDate`, com
   **segundo constante `00`**, resolução de minuto, 774 distintos, 97,61% em 08–18h, sem sábado,
   e **95,71% de repetição adjacente** — que o `*N|` já cobre.

## Veredito

**A hora está fechada para o `.8`**: os 5 eixos passam, as 9 bordas estão caracterizadas contra
a norma, a comunidade é máxima e as 7 peculiaridades estão declaradas — uma delas **corrigindo**
o que eu havia registrado.

O spec fica **adiado com razão escrita e agora com número**: o ganho do ordinal existe só no
regime sem wrap (94,4%), e some no regime com wrap (6,9%), onde o núcleo já resolve por
repetição. E o corpus não tem onde exercitá-lo.

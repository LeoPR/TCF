# Lab 2026-07-13-2301 — TCF.8H recuperado: o modelo do TABELÃO

**Status**: pesquisa/medido, sintético. **Ticket**:
[T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md).
**Base recuperada**: lab 1509 (tabelão) + contrato de header 1830/EXP-015/ADR-0031.

Volta à prancheta a pedido do owner (2026-07-13): *"o TCF com hierarquia já tínhamos
prototipado como simplesmente uma expansão de uma grande tabela combinatória e só."*
Este lab **reproduz essa estrutura** — sem nulos, sem def-levels, sem tipos. Só a
tabela e o RLE.

## A ideia (recuperada, não reinventada)

Hierarquia = **tabela combinatória denormalizada**, IDÊNTICA à multi-coluna. Nome com
2 telefones vira (`intermediates/01-telefones-denormalizado.csv`):

```
nome         cidade      telefones
Ana Souza    Sao Paulo   +55 11 99999-0001
Ana Souza    Sao Paulo   +55 11 3333-0001     <- o pai REPETE por filho
Bruno Lima   Sao Paulo   +55 11 99999-0002
Carla Nunes  Curitiba    +55 41 98888-0003
Carla Nunes  Curitiba    ...
```

Encoda com a **mesma máquina multi-col** (`tcf.encode`). O pai que repete colapsa
sozinho no RLE — e **o comprimento do run RLE = a multiplicidade do array**:

```
#TCF.8H nome:54,cidade:43,telefones[
*2|Ana Souza          <- *2 = Ana tem 2 telefones
Bruno Lima
*3|Carla Nunes        <- *3 = 3 telefones
*2|Diego Rocha
*3|Sao Paulo ...      <- cidade também colapsa
+\55 *\11 *\99999...  <- os 8 telefones (OBAT/HCC do motor real)
```

- **Header de colchetes** (contrato consagrado, ADR-0031 / lab 1830 / EXP-015):
  `nome:size,cidade:size,telefones[` — `[` marca telefones como array 1:N;
  última folha omite size; omit-closes dropa o `]` final; sizes decimais bytes-incl-LF.
- **Decode**: decodifica cada coluna → re-agrupa linhas contíguas pela tupla de pais
  (o run RLE) → cada grupo vira um registro; a coluna do array vira a lista.

Dual do EXP-015 (que guarda o pai UMA vez, ragged, e deduz N do tamanho do filho).
Aqui o pai repete e o RLE conta — **"exatamente a mesma estrutura" da multi-col**,
como o owner pediu.

## Dois casos exercitados

| entrada | árvore | mostra |
|---|---|---|
| `inputs/01-pessoas-telefones.json` | escalares + **array de escalares** | `telefones[` + RLE de pai |
| `inputs/02-pessoas-pedidos.json` | escalares + **array de objetos** | `pedidos[item:40,qtd` + o motor cruzando colunas (`^1` ref, seq-RLE `*2+1|`) |

## Estrutura (convenção de labs)

```
inputs/        .json de entrada
intermediates/ o tabelão (.csv visível) + RLE por coluna (.txt) + canônicos (.json p/ diff)
outputs/       .tcf real + roundtrip .json (byte-idêntico ao canônico) + escada de bytes + contraprova
```

## Rodar

```powershell
python experiments/lab/dirty/2026-07-13-2301-tcf8h-tabelao-recuperado/run.py
```

Zero `src/tcf` (uso read-only de `tcf.encode`/`decode`). RT: `decode(encode(records))
== records` + roundtrip `.json` byte-idêntico ao canônico (asserted; dê `diff`).

## Limites (registrados, para evoluir depois)

- **Um array por registro** (o resto = escalar pai). Objetos 1:1 `{}` aninhados e
  **multi-array por nível** (produto cartesiano) = próxima extensão.
- **Re-nest agrupa por tupla-de-pais contígua**: dois registros ADJACENTES com a
  MESMA tupla de pais se fundiriam (a ambiguidade FD/chave que o lab 1509 já
  sinalizou — a fronteira pai/filho tem de ser carregada, não deduzida da constância).
- Valores como **string** (tipos/null/NaN = a camada que estávamos discutindo antes;
  fica FORA daqui de propósito — primeiro a estrutura).
- Sintético, N=1 lab; sem gate real-world.

Ver [result.md](result.md).

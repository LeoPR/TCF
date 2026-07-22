# Resultado — TCF.8H tabelão (a estrutura recuperada)

**[probatório]** `run.py` valida RT antes dos bytes. Contra-prova:
[`outputs/08-contraprova.txt`](outputs/08-contraprova.txt); roundtrips `.json`
byte-idênticos aos canônicos de `intermediates/` (diffáveis).

## RT + bytes (LF-only, após RT verde)

| entrada | árvore | tabelão | JSON | #TCF.8H | RT |
|---|---|---:|---:|---:|---|
| 01-telefones (array de escalares) | `nome:54,cidade:43,telefones[` | 8×3 | 452 B | **263 B** | ✅ |
| 02-pedidos (array de objetos) | `cliente:39,plano:23,pedidos[item:40,qtd` | 6×4 | 456 B | **167 B** | ✅ |

## Escada de bytes do header (como o lab 1830)

`outputs/07-header-byte-ladder.txt` — cada regra consagrada tira 1 byte:

```
01-telefones:
  base (todos sizes, closes explícitos)   telefones[]:129   268 B
  +última-folha-sem-size                   telefones[]       264 B
  +omit-closes (CONSAGRADO)                telefones[        263 B
```

## O que o wire prova (abra `outputs/*.tcf`)

1. **O RLE de pai É a multiplicidade**: `*2|Ana Souza` (2 telefones), `*3|Carla Nunes`
   (3). Nenhum contador de multiplicidade é escrito — ele já está no run RLE, que o
   motor multi-col produz sozinho. Exatamente *"o nome ficar repetido pode ter um
   comportamento RLE de 2×nome"*.
2. **É a MESMA máquina multi-col**: em `02-pedidos.tcf` o motor faz `plano` = `*2|Premium`,
   `Basic`, `*3|^1` (o `^1` é referência cross-linha de volta a "Premium") e `qtd` =
   `*2+1|\1` (seq-RLE). Nada foi adicionado ao codec — a hierarquia é a tabela
   denormalizada passando pelo `tcf.encode` normal.
3. **O header de colchetes só guarda a árvore**: tirar os colchetes e o meta
   `nome,cidade,telefones` é uma tabela multi-col plana comum. A semântica de
   hierarquia é uma camada que só existe pra re-aninhar o JSON no decode.

## Onde estávamos nos perdendo (registro honesto)

Os labs 1835/1955/2019 foram para **nulos/NaN/def-levels/representação de tipos** —
uma camada que é REAL, mas veio ANTES de recuperar a estrutura-base. Este lab volta
à base: **a estrutura do tabelão + RLE + header de colchetes**, que já estava deduzida
e é o chão de tudo. Tipos/nulos/def-levels voltam a ser a evolução SEGUINTE, sobre
esta base — não antes dela.

## Próximo (evoluir sobre esta base, um passo por vez)

1. Objetos 1:1 `{}` aninhados (endereço{rua,cidade,geo{lat,lon}}) — parent columns
   que também repetem; só re-aninhar num dict. (o EXP-015 já fez a gramática `{}`.)
2. Fronteira pai/filho carregada (resolver a fusão de registros adjacentes de mesma
   tupla — a ambiguidade FD do 1509).
3. Multi-array por nível (produto cartesiano vs tabelas separadas — a dualidade
   RLE↔fk do 1509).
4. SÓ ENTÃO a camada de tipos/nulos/especiais (labs 1835/1955/2019) sobre esta base.

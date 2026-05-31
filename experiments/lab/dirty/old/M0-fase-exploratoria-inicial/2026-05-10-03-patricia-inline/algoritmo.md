# Algoritmo — serialização inline

A árvore Patricia é a mesma do exp 02 (`patricia.py` copiado sem
modificações). Aqui muda apenas a **serialização**: encoder produz
texto diferente, decoder lê texto diferente. Roundtrip preserva o
input do CSV.

## Identidade implícita por ordem de aparição

No exp 02, cada nó tinha id estável desde a fase 1 da construção.
No exp 03, o **emit_id** (id no arquivo TCF) é alocado por **ordem
de aparição no body**:

- Quando uma string nova aparece pela 1ª vez como ocorrência → ganha
  o próximo emit_id (1, 2, 3, ...) e sua declaração é emitida inline.
- Quando uma string nova aparece como **pai** de outra (via
  `filho_de(noP)`), ela ganha emit_id na hora da renderização da
  forma do filho — antes de ser declarada. Essa declaração vem como
  **decl tardia** no fim.

Os emit_ids do exp 03 não correspondem aos ids internos da árvore
do exp 02. Os dois arquivos para o mesmo input descrevem a mesma
árvore com numerações diferentes.

## Encoder — duas fases

### Fase 1 — body inline

Itera sobre `body_rle` (`[(no_id_interno, count), ...]`):

```python
for no_id, count in body_rle:
    eid = emit_id(no_id)             # aloca se primeiro uso
    if eid não foi declarado inline:
        forma = render(nos[no_id])   # "folha 'X'" ou "filho_de(noP) + 'X'"
        emit(f"no{eid}: {count}x {forma}")
        marca eid como declarado_inline
    else:
        emit(f"{count}x ref:no{eid}")
```

`render` para um nó com pai chama `emit_id(pai)` — pode alocar emit_id
para o pai sem que ele apareça inline. O pai fica registrado em
`map_emit` mas ausente de `declarado_inline`. **Esse é o forward ref**.

### Fase 2 — decls tardias até estabilizar

```python
while houver pendentes (em map_emit mas não em declarado_inline):
    para cada pendente em ordem de emit_id:
        forma = render(nos[pendente])  # pode alocar mais forward refs
        emit(f"no{eid}: decl {forma}")
        marca como declarado
```

Loop necessário porque renderizar a forma de um pai Patricia
intermediário (ex: `USR000` que é filho de `USR00`) pode introduzir
um avô novo no `map_emit`. O loop converge porque a árvore é finita.

## Decoder — duas passadas

### Passada 1 — registra tudo

Lê linha por linha. Reconhece 5 padrões via regex:

```
RE_DECL_FOLHA_OCC      = noN: Mx folha "X"
RE_DECL_FILHO_OCC      = noN: Mx filho_de(noP) + "X"
RE_DECL_FOLHA_TARDIA   = noN: decl folha "X"
RE_DECL_FILHO_TARDIA   = noN: decl filho_de(noP) + "X"
RE_REF                 = Mx ref:noN
```

Para decls (com ou sem ocorrência) registra `nos[eid] = (pai_eid, frag)`.
Para decls com ocorrência, **adicionalmente** registra
`(eid, count)` em `body_seq`. Para refs puros, só registra em
`body_seq`.

### Passada 2 — reconstrói

Função recursiva com cache:

```python
def texto(eid):
    pai_eid, frag = nos[eid]
    return frag if pai_eid is None else texto(pai_eid) + frag
```

Para cada `(eid, count)` em `body_seq`, expande `count` cópias do
texto reconstruído. Resultado é a lista de strings idêntica ao input
original.

Forward refs resolvem automaticamente porque a passada 1 registra
todos os nós (inline e tardios) antes da passada 2 começar.

## Comportamento das duas serializações lado a lado

Cenário B, primeira linha do CSV é `USR0001`. No exp 02:

```
<patricia>
  no18 = folha "USR00"               # (no fim do header)
  no16 = filho_de(no18) + "0"
  no1 = filho_de(no16) + "1"         # USR0001
  ...
</patricia>
<body>
  2x ref:no1
  ...
</body>
```

No exp 03, mesma linha vira:

```
<body>
  no1: 2x filho_de(no2) + "1"        # 1a ocorrência declara + usa
  ...                                 # (no2 e no17 são forward refs)
  no2: decl filho_de(no17) + "0"     # decl tardia
  no17: decl folha "USR00"           # decl tardia
</body>
```

A reconstrução de `no1` precisa esperar `no2` ser declarado, que por
sua vez precisa de `no17`. Em decode de 2 passadas, isso é resolvido
naturalmente.

## Decisão registrada

A serialização inline **não altera a árvore Patricia**. Ela move a
declaração para o ponto da 1ª ocorrência. O algoritmo de construção
da árvore (`patricia.py`) e o body com RLE adjacente
(`rle_adjacente`) são idênticos ao exp 02.

Isso permite responder à pergunta de viabilidade da serialização
isoladamente, sem confundir com mudanças no algoritmo da árvore.

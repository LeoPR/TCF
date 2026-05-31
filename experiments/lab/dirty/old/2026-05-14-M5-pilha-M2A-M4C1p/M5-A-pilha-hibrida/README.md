# M5.A — Detector hibrido (M2.A inline + M4.C1' por candidato)

**Estado**: foi (fechado apos rodagem)
**Pergunta**: detector hibrido seleciona aliases M2.A em algum caso?

## Tecnica

Detector iterativo greedy que, para CADA candidato (subseq contigua
K >= 2), calcula NET sob ambas sintaxes:

- **M2.A** (preambulo): `net = R*(Lr-1-len(N)) - (Lr+3+len(N))`
- **M4.C1'** (inline): `net = (R-1)*(Lr-1-len(N)) - 2`

Seleciona o de maior net global. Marca o tipo escolhido. Substitui
ocorrencias. Repete.

## Sintaxe (coexistencia)

Aliases M2.A: preambulo + uso
```
$1=3,11,5,6     (decl no preambulo)
...$1...        (uso em linha)
```

Aliases M4.C1': inline + uso
```
...~3,11,5,6~...   (1a aparicao define)
...&1...           (2a+ aparicoes usam)
```

Namespaces SEPARADOS (`$N` vs `&N`). Decoder distingue por prefixo.

## Esperado (per algebra do macro README)

M2.A economiza `2 + 2*len(N)` chars MENOS que M4.C1' para o mesmo
padrao. Logo, o detector NUNCA seleciona M2.A — todo alias vira tipo
M4.C1'. Resultado esperado: identico ao M4.C1' alone.

## Caveat

Greedy NAO e' otimo. Pode existir caso em que decisao precoce muda o
quadro. So' o empirico confirma.

# M6.A — M2.A inline (sem preambulo)

**Tecnica**: detector identico ao M2.A original (sufixos K>=3), mas
**serializacao inline**: 1a aparicao do alias e' `$N=tupla` no body
(no momento que apareceria a tupla); demais aparicoes sao `$N`.

## Diff vs M2.A com preambulo

Per alias de Lr chars usado R vezes:

```
M2A_preambulo_savings = R*(Lr-1-len(N)) - (Lr+3+len(N))
M2A_inline_savings    = R*(Lr-1-len(N)) - (Lr+1)

Diff = 2 + len(N) bytes/alias a favor de inline
```

## Diff vs M4.C1' atual

```
M2A_inline_savings = R*(Lr-1-len(N)) - (Lr+1)
M4C1p_atual_savings = R*(Lr-1-len(N)) - Lr - 1 + len(N) - 2
                    = R*(Lr-1-len(N)) - (Lr+3-len(N))

Diff M2A_inline - M4C1p_atual = (Lr+3-len(N)) - (Lr+1) = 2-len(N)
```

Para len(N)=1: M2A inline economiza **1 byte/alias a mais** que M4.C1'
atual. **Reverte a conclusao M5**.

Para len(N)>=2: M2A inline ainda perde.

## Sintaxe

Body com aliases mistos:
- Definicao: `$N=tupla` na 1a aparicao da tupla
- Uso: `$N` em aparicoes subsequentes
- Sem bloco separado de preambulo

Decoder: ao ver `$N=`, registra `aliases[N] = tupla_parsed`. Ao ver
`$N` sem `=`, expande do dicionario.

## Esperado

- D1: ~135 bytes (vs M2.A preambulo 141, M4.C1' atual 138)
- D2/D3/D4: a verificar empiricamente

# Proveniência dos dados

Todos **sintéticos**, gerados por `run.py` (seed 20260813), materializados em
`inputs/<caso>.entrada.json`. Nenhum dado externo, nenhum acesso a `Z:`.

Sintético é o correto aqui pela mesma razão do lab irmão: cada caso precisa **isolar um
mecanismo de compressão** (RLE por bloco, bN de domínio, seq-RLE, OBAT por afixo), porque
é o mecanismo — não o tipo — que determina a granularidade de entrega. Corpus real
misturaria os mecanismos numa mesma coluna e a curva ficaria ilegível.

| caso | n | mecanismo que vence | forma no corpo |
|---|---:|---|---|
| `bool-blocos` | 600 | RLE por bloco | 3 marcadores autocontidos |
| `bool-alternado` | 600 | bN de domínio | domínio + 1 linha densa |
| `bool-aleatorio` | 600 | bN de domínio | idem |
| `bool-tudo-true` | 600 | RLE total | 1 marcador |
| `categoria-k5` | 600 | bN de domínio (k=5) | domínio + 1 linha densa |
| `data-spec` | 600 | seq-RLE aritmético + spec | 1 linha |
| `data-uteis-spec` | 600 | seq-RLE periódico + spec | 1 linha |
| `texto` | 600 | OBAT por afixo | 5 linhas |
| `email` | 600 | OBAT por afixo | 4 linhas |

**CONSTANTE na comparação**: n=600; o wire é encodado **uma vez** e entregue em prefixos de
linhas íntegras — zero re-encode, zero custo de bytes. Só o tipo/regime varia.

Contrapartida honesta: as curvas medidas **não** são previsão para dado real, onde uma
coluna pode alternar mecanismos. São a demonstração de que a granularidade acompanha o
mecanismo, não o tipo.

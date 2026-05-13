# 03 — patricia inline (cabeçalho embutido no body)

## Princípio / motivação

Continua a árvore Patricia do experimento 02. A motivação é verificar
**outra forma de serializar** a mesma árvore: em vez de manter
`<patricia>` como seção separada do `<body>`, embutir cada declaração
de nó direto no body, na primeira vez que aquela string aparece como
ocorrência.

Aceita explicitamente o conceito de **forward ref**: um filho Patricia
pode referenciar o id do seu pai antes do pai ser declarado. O pai
fica "pendente" no decode até aparecer (decl tardia) ao final do body.

A ferramenta é atemporal — a serialização inline pode ser usada para
qualquer formato que use árvore de prefixos, independente de versão.

## Propósito

Responde a duas perguntas:

1. **Viabilidade**: é possível embutir o cabeçalho no body, com
   forward refs para pais ainda não declarados, e ainda obter
   roundtrip?
2. **Comparação ponto a ponto com exp 02**: como muda o número de
   linhas, bytes, e onde está cada declaração?

## Comparação

- **Compara com**: [02-patricia-nomes](../2026-05-10-02-patricia-nomes/).
- **É comparável?** Sim. Mesmo input (`data/input-A.csv` e
  `data/input-B.csv` copiados do 02), mesma árvore Patricia
  (mesma `patricia.py`), mesma ordem do body. **Só muda a serialização**.
- O que se compara: bytes do TCF gerado, contagem de linhas por
  categoria (decl inline / decl tardia / ref), localização da
  declaração na sequência.

## Cenários e valores possíveis

Mesmos cenários do exp 02:

| Cenário | Input | Patricia ativo? |
|---|---|---|
| A | 50 linhas, 5 nomes simples | não (nenhum prefixo ≥ 3 chars) |
| B | 30 linhas, USR0001..USR0010 + PRD0001..PRD0005 | sim (3 nós internos) |

Marcadores TCF (deliberadamente verbosos):

- `noN: Mx folha "valor"` — primeira ocorrência declara folha top-level
- `noN: Mx filho_de(noP) + "suf"` — primeira ocorrência declara filho
  Patricia (`noP` pode ser forward ref ainda não declarado)
- `Mx ref:noN` — ocorrência de nó já declarado
- `noN: decl folha "valor"` — declaração tardia de pai sem ocorrência
- `noN: decl filho_de(noP) + "suf"` — declaração tardia de pai
  Patricia intermediário

## Resultado observado

Roundtrip OK nos 2 cenários.

### Análise por camada de custo

Convenção do dirty (registrada em [`../README.md`](../README.md)): ao
comparar serializações, separamos quatro camadas. **Comentários não
contam**; **marcadores macro são escala pequena** (lembrados, não
medidos); **marcadores de referência** e **dados efetivos** são onde a
comparação tem sentido.

#### Dados efetivos

Idênticos entre 02 e 03. Mesma árvore Patricia (mesmo `patricia.py`),
mesmas strings, mesma sequência de RLE adjacente. Não há diferença
nesta camada.

#### Marcadores macro / estruturais

- **02** tem `<patricia>` + `</patricia>` + `<body>` + `</body>`.
- **03** tem só `<body>` + `</body>` (cabeçalho some).

Existe, portanto, uma economia macro no 03 — mas não quantificamos
em bytes aqui, porque essa camada pode ser implícita por regra de
formato em uma versão futura.

#### Marcadores de referência

Aqui está a diferença intrínseca entre as duas serializações.

| | 02 (separado) | 03 (inline) |
|---|---|---|
| decls de folha/filho | `N_unique` no header | `N_unique` no body, **fundidas** com a 1ª ocorrência |
| refs no body | `N_total` (todas as ocorrências, incluindo a 1ª) | `N_total - N_unique` (só ocorrências subsequentes) |
| decls tardias | — | `N_patricia_interno` (pais sem ocorrência própria) |
| **total marcadores** | `N_unique + N_total` | `N_total + N_patricia_interno` |
| **diferença (02 − 03)** | — | `N_unique − N_patricia_interno` |

O 03 elimina **um marcador por nó único** (a 1ª ref vira parte da
decl). Adiciona **um marcador por nó interno Patricia** (decl tardia).
Em saldo:

- **Cenário A**: `N_unique=5, N_patricia_interno=0` → 03 tem **5
  marcadores a menos**.
- **Cenário B**: `N_unique=15, N_patricia_interno=3` → 03 tem **12
  marcadores a menos**.

A magnitude da economia é **proporcional à razão `N_unique / N_total`**:
em datasets com muitas ocorrências por nó, o ganho é pequeno (a 1ª ref
do 02 já era amortizada); em datasets com poucas ocorrências por nó
(cardinalidade alta), o ganho é maior.

#### Comentários

Não contam. O 03 atual tem 1 linha de comentário a mais que o 02; isso
é poluição da medição, não da serialização.

### Medição bruta (com poluição)

Reportada para registro, **não para conclusão**. Inclui comentários e
marcadores macro:

| | Cenário A | Cenário B |
|---|---|---|
| TCF 02 (separado) | 571 bytes | 848 bytes |
| TCF 03 (inline)  | 689 bytes | 824 bytes |
| diferença bruta | +118 (+20.7%) | -24 (-2.8%) |

Auditando a fonte da diferença:

| Fator | Pertence à... | Em A | Em B |
|---|---|---|---|
| linha extra de comentário | comentários (não conta) | +70 bytes | +70 bytes |
| `1x` explícito em refs count=1 | divergência arbitrária | +57 bytes (19 ocorrências) | +33 bytes (11 ocorrências) |

Removendo essas duas inflações artificiais, a estimativa do 03 fica:

| | Cenário A | Cenário B |
|---|---|---|
| TCF 03 normalizado | ~562 bytes | ~721 bytes |
| diferença vs 02 | **-9 bytes (-1.6%)** | **-127 bytes (-15%)** |

Sentido **consistente com a análise de marcadores**: o 03 economiza,
e a magnitude segue `N_unique / N_total`. A medição bruta original
foi rejeitada como evidência por estar contaminada.

Ver [conclusoes.md](conclusoes.md) para o output completo e leitura
linha-a-linha.

## Limitações

- Apenas 2 cenários e cardinalidade pequena. Não fala sobre
  comportamento em N grande, em colunas com cardinalidade
  intermediária ou em strings longas.
- A medição bruta de bytes está contaminada por escolhas de formato
  (comentário extra, `1x` explícito) que não pertencem à diferença
  intrínseca entre as serializações. A estimativa normalizada (-1.6%
  em A, -15% em B) é só estimativa; será medida em formato
  normalizado no exp 04.
- Marcadores verbosos. Comparar com formato compacto exigiria outro
  experimento.
- Forward refs no decode foram resolvidos por 2 passadas. Não foi
  testado: corrupção de input, refs não resolvidas, ciclos.
- Algoritmo Patricia (`patricia.py`) é byte-a-byte idêntico ao do
  exp 02 — nenhuma diferença vem dele.
- Fórmula `N_unique − N_patricia_interno` para marcadores
  economizados não foi validada em mais de 2 cenários. Exp 04 vai
  testar com cenários expandidos e variantes de ordenação.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-10-03-patricia-inline
python run.py
```

Saída no console mostra contagens, bytes lado a lado vs exp 02,
e status do roundtrip.

# 0034 — Header `#TCF.8` é DEFAULT em 100% dos casos (corrige o default do ADR-0029)

- **Status**: aceito (2026-07-24)
- **Supersede**: o **default** do [ADR-0029](0029-version-format-identification-semi-implicit.md)
  (single-col órfão). O restante do 0029 — a tabela de discriminadores, o `#TCF.8 :id`
  self-describing, o `drop_names` — continua válido.
- **Relacionado**: [ADR-0024](0024-pre-1-0-versioning-git-as-compat.md) (git-as-compat,
  baselines re-pináveis), [ADR-0030](0030-freeze-single-col-body-at-1.0.md) (freeze do body).

## Contexto

O ADR-0029 registrou o single-col como **órfão** (body puro, zero marcador) sendo o *formato
default*, com o `#TCF.8\n` como carimbo **opt-in**. O código implementava exatamente isso
(`stamp: bool = False`), e havia teste com nome próprio para o comportamento
(`test_version_stamp_nao_e_default`).

O owner (2026-07-24) revisou e declarou que **a premissa do 0029 está errada e foi mal
interpretada no registro**: provavelmente descrevia uma *condição específica* (transmissão,
container externo) e o **default escapou** para o texto do ADR.

O achado apareceu por acaso: um lab (`2026-07-24-2010`) foi o primeiro a codificar uma
`list[str]` pura e gerou saídas sem cabeçalho. Todos os labs anteriores usavam `.8H`/`.8M`,
que já carregam header por construção — por isso a divergência ficou invisível por tanto tempo.

## Decisão

**O header é default em 100% dos casos, mesmo com conteúdo vazio.** O artefato se
auto-explica em vez de depender de quem o produziu.

A inflação de 7 B no single-col é **inevitável e aceita**: o custo de identificação é o preço
de o arquivo ser interpretável sozinho.

**O escape existe, mas só EXPLÍCITO** — `encode(..., stamp=False)`:
- **transmissão**: formato minimalista onde o contrato vive nas pontas, não no payload
- **container que já carrega o contrato** (ex.: parquet), onde repetir o header não paga

Fora esses casos, sair do default é erro.

### Um header por ARTEFATO, não por coluna

O `encode` é reusado internamente como compressor de coluna (L1) pelo `.8H`. Essas chamadas
passam `stamp=False`: o `#TCF.8` identifica o **arquivo**, não cada coluna aninhada — o
container `.8H` já carrega o contrato. É o mesmo caso de escape acima.

Verificado: `.8H`, `.8M`, single-col e single-col tipado emitem **exatamente 1** header.

## Consequências

**Byte-canonical re-pinado** (permitido pelo ADR-0024; os valores antigos vivem no git):

| gate | antes | depois | delta |
|---|---:|---:|---|
| D1-D9 | 1523 B | 1586 B | +63 = 9 × 7 |
| real-world | 89616 B | 89637 B | +21 = 3 × 7 |
| D17a (`.8M`) | 300 B | 300 B | inalterado |

**Não é regressão de compressão**: o core não mudou 1 byte — só o header entrou. O delta é
exatamente `7 × n_datasets_single_col`, o que é a própria prova disso.

`stamp` mudou de `bool = False` para `bool | None = None`: `None`/`True` → com header;
`False` → escape explícito. Antes não havia como pedir órfão *explicitamente* (o `False` era
o default, indistinguível de "não passado").

**Ambiguidade resolvida junto**: antes, `#TCF.8\n<corpo>` e `<corpo>` decodavam para o mesmo
valor — duas grafias, nenhuma declarada canônica. Agora a canônica é a com header, e a órfã é
uma forma de escape declarada.

**Tensão registrada**: contraria a diretriz "cada byte conta em payload minúsculo"
([`project_byte_level_compression_focus`]). O owner decidiu explicitamente que
auto-explicação vence identificação implícita no default, e que quem precisa dos 7 B tem o
escape à mão.

## Alternativas descartadas

- **Manter o 0029**: rejeitada — o próprio owner não reconhece a premissa registrada.
- **Header só quando o body não se auto-identifica**: seria um default condicional, o oposto
  do que se quer (regra previsível).
- **Adiar para o formato de transmissão**: adiaria também a ambiguidade das duas grafias.

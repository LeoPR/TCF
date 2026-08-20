# 2026-08-17-1600 — split como GRUPO no meta (reavaliação pedida pelo owner)

## A crítica

Ao reestudar o split, o owner apontou quatro coisas:

1. *"a estrutura não precisa [do #TCF no meio] — poderia comprimir normalmente o algoritmo
   de duas colunas sem criar um #TCF de fato... não faz sentido"*
2. *"é mais fácil pensar que são realmente duas colunas, só que indicar algo no header pra
   dizer que as duas colunas são um grupo de uma coluna só"*
3. *"o split me parece pouco stream, e só faria sentido em colunas que têm um spec que peça
   pra avaliar isso antes"*
4. a preocupação de fundo: *"um IF bem grande em vez de reaproveitar tudo que já está
   pronto — basta tratar como dois campos dict, sem nome, com a dica de um nome agrupador"*

**Veredito deste lab: a crítica procede nos quatro pontos.** O mock da forma-grupo é menor,
mais simples e destrava o que o slot atual bloqueia.

## O mock

Grafia (detalhe reversível — o que se avalia é a **estrutura**, não o char):

```
meta:   &<nf><template-esc>=<nome> , [modo]<size> , [modo]<size> , … , [modo]
corpo:  os corpos dos campos, concatenados — como QUALQUER coluna do .8M
```

O template viaja no **meta** (é meta de verdade: descreve como reintercalar). Os campos são
**colunas anônimas normais** — o mecanismo já existe (ADR-0029).

## Resultado — 4/4 casos, RT validado nos dois formatos

| caso | n | atual (slot aninhado) | grupo (mock) | delta |
|---|--:|--:|--:|--:|
| c1-decimal | 24 | 137 | 121 | **−16** |
| c2-data-iso | 24 | 130 | 109 | **−21** |
| c6-telefone | 24 | 334 | 313 | **−21** |
| **cep-real** (Receita, Shaper seed=42) | 19 988 | 164 510 | 164 494 | **−16** |

Os metas, lado a lado (telefone):

```
atual : #TCF.8M%c6-telefone          <- slot opaco; template+sub-header DENTRO do blob
grupo : #TCF.8M&3(|) |-|=c6-telefone,e,!8f,!
        └─ 3 campos, template "(", ") ", "-", "" — e cada campo com modo+size no meta
```

## Ponto a ponto

**1. "O #TCF no meio não precisa" — confirmado.** O decoder do mock reusa
`_decode_raw_body`, `_decode_v2b` e o `decode` público — **nenhuma primitiva nova de
decode**. A única lógica própria é parse do meta + reintercalação, que o split atual
**também tem** (template + reintercala). A recursão, o sub-header, a moldura `<ntmpl>` e os
nomes `c0..cN` eram camada pura de embrulho. (A redundância já tinha sido apontada na
[nota 1400](../../../notas/2026-08/2026-08-17-1400-split-teoria-e-o-magic-aninhado.md); a
crítica do owner vai além: não é tirar o magic — é **não aninhar**.)

**2. "Duas colunas + marca de grupo" — confirmado e é menor.** Byte não é o critério
(é redundância — memória `feedback_criterio_e_redundancia_nao_byte`), mas registra-se: a
forma certa também não custa nada; sobra byte em 4/4.

**3. "Pouco stream" — correto, em DUAS pontas.**
- *Decode*: hoje o slot é **caixa-preta** — `view.py:232,:438`: split *"exige decode"* e
  *"cai em fallback"*; nem contar linhas dá sem decodar o slot. Na forma-grupo o plano de
  fatias `[ini:fim)` de **cada campo** sai da linha 1 sem decodar nada (demonstrado no
  mock) — a view e o decode paralelo passam a alcançar os campos.
- *Encode*: o gate atual é batch por natureza (template 100% uniforme exige ver tudo). Duas
  saídas registradas como hipóteses (Pacote 13, H-13-03/H-13-04): o **avaliador paralelo**
  esboçado pelo owner (núcleo encoda a coluna enquanto outro processo acumula evidência de
  template e decide o momento de parar e forkar em N colunas — questões abertas: o que fazer
  com o prefixo já emitido; conecta com *encode em pulsos* do contrato-externalizado), e a
  **dica/spec pré-declarada de template** (*spec orienta, não manda*), que valida por valor
  e dispensa o buffer.

**4. "O IF grande" — confirmado.** O caminho atual é: slot → moldura própria → sub-wire →
parser inteiro de novo. O mock mostra que o caminho pode ser: meta → fatias → os decoders
de coluna **que já existem**. Um nível a menos, zero código de decode novo.

## O que o mock NÃO é

- **Não é weld.** `src/tcf` intocado; a grafia `&` é ilustrativa; mudar o wire do split
  re-pina D17a/real-world e exige ADR. Triagem: **`.9`** (reorganização lógica/legibilidade
  pro port), registrado no
  [Pacote 13 do roadmap-hipoteses](../../../notas/2026-05/roadmap-hipoteses.md).
- **Não resolve o streaming do encode** — só o do decode. H-13-03/04 ficam abertas.
- O parse do meta do mock é simplificado (escapes `| , =` tratados; não cobre toda borda
  do meta real).

## Evidência

8 wires em `outputs/` (por caso: `.atual.tcf` + `.grupo.mock-tcf`), roundtrip validado nos
**dois** formatos, portão de completude no `main()`.

## Conexões

- Crítica que originou: owner 2026-08-17 (verbatim no docstring do `run.py`)
- [ADR-0026](../../../../../docs/adr/0026-structural-split-weld.md) (o slot atual) ·
  [ADR-0029](../../../../../docs/adr/0029-version-format-identification-semi-implicit.md) (colunas anônimas)
- [nota 1400](../../../notas/2026-08/2026-08-17-1400-split-teoria-e-o-magic-aninhado.md) (a redundância do magic) ·
  [lab 1500](../2026-08-17-1500-split-didatico/) (o didático)
- Registro de direção: [roadmap-hipoteses Pacote 13](../../../notas/2026-05/roadmap-hipoteses.md)

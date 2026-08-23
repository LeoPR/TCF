# EXP-018: `IntPadSpec` + abertura da rota tipada

**Protótipo do que vai soldar.** Clean, na definição do owner: *"pegar o que foi o melhor
concluído do dirty e praticamente fazer o protótipo que já vai soldar […] um misto de soldar
e testar só pra ver se nada quebra."*

`src/tcf` **não é tocado**: o spec e a rota entram pela API pública, e o **FLOOR real**
decide. O weld em si aguarda aprovação.

## Estado: era / foi / é / será

- **Era**: número é tipo nativo (`stype='n'`) mas sem pré-transformação; a rota tipada custa
  +1 byte e recusa **tanto** `nature=` **quanto** `min_len=`.
- **Foi**: quatro labs dirty (22h58, 23h26, 00h32, 01h12) reduziram três alvos a **um**:
  o `OFFPAD` saiu (a base não viajava, o wire de 26 B omitia 19 dígitos); o `B94` é marginal
  (mediana 1,14×, 33 vitórias de ≤1 byte); o `min_len` não ganha em nenhuma coluna do corpus.
  Sobrou o **PAD**: mediana **1,72×** em 39 colunas reais, **zero empates**, auto-contido.
- **É**: este protótipo. 18 casos (8 sintéticos + 10 reais), **0 falhas**, todos os pins
  verdes, e a suíte do repositório segue em **1252**. O spec vence em **6**, com mediana
  **1,79×** e máximo **2,80×**.
- **Será**: o weld, `src/tcf/natures/int_pad.py` + a abertura da porta tipada. Aguarda o
  "pode soldar".

## O que este lab prova

| # | prova | como |
|---|---|---|
| 1 | **RT estrito com TIPO** | `type(x) is type(y)` elemento a elemento, em Python `True == 1` e `1 == 1.0`, e comparar só valor mascararia |
| 2 | **RT do alvo, isolado** | `decode_value(encode_value(x)) == x` para todo valor |
| 3 | **RT em arquivo** | `outputs/<c>.roundtrip.json` **diffável** contra `inputs/<c>.entrada.json` |
| 4 | **NUNCA-PIOR** | o wire com spec nunca maior que o que o encoder emite hoje |
| 5 | **determinismo** | encodar duas vezes dá byte-idêntico |
| 6 | **o artefato é o wire** | o `.tcf` lido em binário == o wire medido |
| 7 | **o núcleo não regride** | baseline gravado em `intermediates/<c>.baseline.tcf` |

E o **PIN** por caso: quem deve vencer o FLOOR. Divergência é **falha do lab**, não nota de
rodapé.

## Os arquivos

| arquivo | o que é |
|---|---|
| `spec_int_pad.py` | **o candidato a weld**: escrito como o código que iria para `src/tcf/natures/` |
| `rota_tipada.py` | o protótipo da abertura, com os pontos de encaixe documentados (`encoder.py:539`, `decoder.py:410-411`) |
| `casos.py` | os 18 casos com ideia e pin |
| `inputs/fontes/` | corpus real congelado (roda **sem** `Z:`) |
| `intermediates/<c>.candidatos.json` | baseline × wire, headers, ganho |
| `outputs/<c>.tcf` · `.roundtrip.json` · `INDEX.md` | wire, contra-prova, tabela |

## Como rodar

```
python run.py     # sai 0 só se as 7 provas e os 18 pins fecharem
```

## O que o weld exigiria (localizado, não estimado)

| ponto | arquivo | o que entra |
|---|---|---|
| encode | `encoder.py:539` | o spec depois do `render` (que para `n` é a builtin `str`) |
| FLOOR | `encoder.py:549-600` | um `candidatos.append`, como o bool já faz |
| decode | `decoder.py:410-411` | o spec antes do `_cast_tipo` |
| header | slot do índice 7 | `#TCF.8n [nome]:id`, verificado livre |
| registry | `natures/__init__.py` | `IntPadSpec` com `wire_id="ipad"` |

A diferença entre este protótipo e o destino é **de uma linha**: aqui o spec vai out-of-band
no decode porque `ipad` não está no registry; soldado, o decode o resolveria sozinho.

## Ressalvas

- **Viés do corpus**: 25 das 39 colunas do lab de origem são TPC-H, que favorece este regime.
  Aqui foram escolhidas 10 colunas reais incluindo **6 onde o PAD perde**: um lab que só
  mostra o caso favorável não prova nunca-pior.
- Um pin foi **corrigido** durante a rodada (`real-tpch-lineitem-orderkey`): eu esperava
  `spec` e veio `core`. A expectativa era minha, a coluna é monótona mas tem **três passos
  distintos**, e repetição quebra a progressão. Está documentado em `casos.py`, no caso.

## Vínculo

`T-NUMERO-SPEC` · `T-INT-CONFORMIDADE-DE-FLUXO` · `T-NATURE-IGNORADA-CALADA` ·
ADR-0015 (natures) · ADR-0041 (wire_id em dois planos).
Labs dirty de origem: `2026-08-13-2258`, `2026-08-13-2326`, `2026-08-14-0032`,
`2026-08-14-0112`.

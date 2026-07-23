# Modo denso + marcador de binarização — estudo aberto [estudo]

**Data**: 2026-07-23 03:45. Direção do owner, sobre a escada do bool
([`2026-07-23-0336`](../../2026-07/2026-07-23/2026-07-23-0336-implicitude-bool-escada-base64/)):
**estudar tudo primeiro e ir registrando; NÃO soldar ainda**. Extensão da
[regra de implicitude](2026-07-23-0259-implicitude-singlecol-logica.md).

## Duas camadas ortogonais (confirmadas pela escada)

1. **Implicitude do tipo** (ganho garantido, sempre): a tag `b` já fixa o domínio {false,true}
   (verificado no core — decoder rejeita fora-do-domínio ANTES do body), então `true`/`false`/`^N`
   no body são redundantes. Vale pra todo single-col tipado, sem depender de dados.
2. **Modo denso** (ganho condicional, alta entropia): bit-packing (8 bools/byte) atinge o piso
   (500 bools = 63 B), mas **só ganha na alta entropia** — na baixa o `.8H` atual já vence
   (`all-true` 36 B < 97 do base64). ⇒ candidato de `min()` por-coluna, nunca-pior.

## Decisão de forma do modo denso: **base64 como default implícito**

Medido (âncora `alt`, 500 elems): cru=63 B (payload) mas **não é UTF-8 válido** (quebra o
invariante textual/inspecionável + gate byte-canônico); base64=84 B (+33%) e **textual**; hex=126 B
(+100%). **Pós-gzip a diferença some** (cru=37 = b64=37). Logo:

- **base64 é o default do modo denso**: (a) não gera caracteres estranhos ao abrir num editor de
  texto (só o alfabeto imprimível A–Za–z0–9+/); (b) mantém o ganho sob pós-compressão binária (gzip);
  (c) é reversível trivialmente. Hex fica como fallback legível-por-nibble; cru só em side-channel.

## Generalização: **marcador de binarização no começo** (não só bool)

O modo denso não é bool-específico. A ideia (owner): um **marcador líder** que declara O QUE foi
binarizado e COMO — self-describing — pra o mesmo mecanismo servir a:

- **bool** → 1 bit/elem (domínio implícito {false,true}).
- **low-card genérico** → `bN` (w bits/símbolo, domínio embutido) — família já prototipada
  (`bitpack.py`, `bn_codec.py`).
- **campo binário arbitrário** (bytes crus, não só {0,1}) → base64 do stream, 8 elementos/byte
  quando cada elemento é 1 bit, ou N bytes/elemento pro caso geral.

Forma conceitual (a ESTUDAR, não fixada): `<marcador-modo><n>\n<payload base64>`, onde o marcador
diz {tipo do elemento, largura em bits, alfabeto de saída}. Fica **legível na abertura** (o marcador
é texto) e **denso no corpo** (base64). Precisa casar com o slot `:` do `#TCF.8` (livre hoje) e com
o desvio opt-in MARCADO da [ADR-0030](../../../../docs/adr/0030-freeze-single-col-body-at-1.0.md).

## Conclusão VERIFICADA do 1º ciclo (bool/RLE/denso) — 2026-07-23

Técnica aplicada (guardar e repetir): **entender-grounded → medir no lab com gates → verificar
adversarialmente → CORRIGIR a evidência**. Cadeia de 3 labs:
- [`1533`](../../2026-07/2026-07-23/2026-07-23-1533-decisao-rle-vs-denso-passe-unico/) — a decisão
  RLE-vs-denso é **determinística** (tamanho por fórmula == real) e de **passe único** (`reads/n==1.0`).
- [`1548`](../../2026-07/2026-07-23/2026-07-23-1548-telemetria-decide-lote-rle-vs-b64/) — decisão por
  segmento pela telemetria. **v1 OBSOLETA** (reportou −23% do batch de S FIXO — era artefato de
  bloco==S; achado pela verificação `wf_876541f7`). **v2 ATUALIZADA**: batch de S fixo é frágil
  (perde no desalinhado, até +72); **segmentação ADAPTATIVA** (fronteira na virada de regime, do
  run-list) ganha independente de alinhamento (−22 a −49), **nunca-pior sob FLOOR**.

O que fica **fixado como verdade** (evidência gravada + verificada):
1. Composição vencedora = **adaptativa por regime**, NÃO lote de tamanho fixo.
2. Decisão sai da telemetria + materializa só o vencedor + passe único + RT — mecanismo válido.
3. **Enquadramento honesto do custo** (grounding `wf_876541f7`): só o **run-list** é "de qualquer
   forma" (o `_rle_adjacente` já roda no bool); o **tamanho base64** e a **segmentação** são passo
   NOVO barato; `emitted_mode` é do `.8M` — o `.8H` single-col **não tem ponto de seleção hoje** (é a
   mudança de código real que isto implicaria).

## Aberto — o que estudar antes de fixar (sem tocar src/tcf)

- [ ] **Outros tipos single-col** na mesma escada: int/float (a nota 0259 já aponta), pra ver se o
      modo denso (bN/base64) e a implicitude do tipo se comportam igual.
- [ ] **Onde mora o `n`** num single-col denso (hoje os labs bN carregam `n` out-of-band).
- [ ] **Gramática do marcador**: quais campos precisa (tipo, bit-width, alfabeto), e como não colide
      com nature (`#TCF.8 :cpf`, forma-espaço) nem com o `:` tipado.
- [ ] **Campo binário puro** (bytes, não bool): medir base64 vs o que o `.8H` faz hoje com bytes.
- [ ] **Post-compress honesto**: quando o modo denso é NET-negativo pós-gzip/brotli (memory F3).

Relaciona: [ficha de fatos wf_8ac9d847] (workflow 5-leitores) ·
[escada bool `0336`](../../2026-07/2026-07-23/2026-07-23-0336-implicitude-bool-escada-base64/) ·
[regra de implicitude `0259`](2026-07-23-0259-implicitude-singlecol-logica.md) ·
[T-OPT-INFERENCE](../../../../tickets/T-OPT-INFERENCE.md) · ADR-0030 · família bN
([`2026-07-07-0028`](../../2026-07/2026-07-07/2026-07-07-0028-spec-bitwidth-bN/)).

# Resultado — estudo P1 presença/ragged

**[probatório]** Protótipo em [proto.py](proto.py) (fora de `src/tcf`; L1 reusado read-only).
Números: [outputs/00-medicoes.txt](outputs/00-medicoes.txt). Exemplos vistoriáveis:
[inputs/](inputs/) → [outputs/*.tcf](outputs/) → [outputs/*-rt.json](outputs/) (diffáveis).

## AUDITORIA + WELD (2026-07-15) — correções e desfecho

> **Estado**: WELDADO no core (aprovação do owner), com os furos da verificação adversarial
> (workflow `wf_e548aeaa-055`) CORRIGIDOS antes de tocar `src/tcf`. Ver
> [ADR-0033 §Update P1](../../../../docs/adr/0033-hierarchical-codec-weld.md).

A verificação adversarial (3 lentes + síntese) confirmou que a **forma sobrevive** (gramática,
máscara, corpo denso, byte-idêntico no uniforme — zero redesign), mas o PROTÓTIPO tinha furos que o
weld fechou. **Correções a claims deste estudo** (eram imprecisas/falsas no protótipo):

- ❌→✅ "fail-loud pra tipos mistos" **era FALSO no protótipo** (str()-engolia scalar/dict, list/str).
  **No weld: fail-loud tipado** (`_derive_schema` varre TODOS os presentes; tipo estrutural misto ou
  null = `HierarchicalError`). Testes: `test_p1_tipos_estruturais_mistos_fail_loud`.
- ❌→✅ **null em ELEMENTO de array** virava `'None'` calado no protótipo. **No weld: fail-loud** por
  elemento (aponta P3). Teste: `test_p1_null_em_elemento_de_array_fail_loud`.
- ❌→✅ **array de objetos VAZIOS** `[{}]` colidia com `arr_scalars` (corrupção silenciosa, **também
  no weld anterior**). **No weld: fail-loud** ("sem chaves"). Teste dedicado.
- ✅ **decode endurecido** (furos de frame): size negativo, size omitido fora da última coluna,
  máscara `0`/inválida, coluna não-exaurida, `[{}]`/raiz-não-lista → todos `HierarchicalError`
  (nunca corrupção silenciosa). Fecha bugs pré-existentes do weld (size-None-no-meio).
- ⚠️ **custo da máscara**: o §3 abaixo dizia "comprimida de graça"; no regime ALTERNADO o L1
  INFLA ~1 B/registro (refs `^1`/`^2` no lugar do literal). Bracket 0.5–3 B/reg CONFERE; a
  inflação é do L1, não da máscara — candidato ao knob "L1 não emitir ref quando ref≥literal"
  (futuras-otimizações, não fazer). Alfabeto: o `0` reservado trafega **L1-escapado** (`\0`, ~3 B).
- ⚠️ **última-folha-sem-size é indetectável a truncamento de cauda** (limitação herdada do weld;
  vale p/ `.8M`/`.8H`). Declarada; decisão de emitir size explícito na última (~4 B) fica pro owner.

**Gate do weld**: suíte **684 passed**; pins flat byte-canônicos verdes; uniforme byte-idêntico;
os repros da auditoria viram testes red→green. Falta o probe real-world (JSON aninhado real com
opcionais) — registrado pro PW3 (mesma esteira TPC-H/receita do weld anterior).

## O que o estudo estabelece

1. **A máscara integra LIMPO na gramática weldada**: `nome?:msize` é uma extensão local (o parser
   só ganha um branch no `?`); máscara = coluna de controle como o `#count`, comprimida pelo L1
   (o wire mostra `*2|-` e o HCC referenciando `^1`/`^2` — de graça, sem código novo de compressão).
2. **Compat total**: dado uniforme → **byte-idêntico** ao weld atual (M3). O `?` é DEDUZIDO do dado
   (campo faltando em algum registro), como todo o resto do header. Zero custo pra quem não usa.
3. **Custo honesto**: ~0,5 B/registro no regime API típico (ausência rara, RLE colapsa);
   pior caso alternado ~3 B/registro (declarado; candidato a knob L3 — máscara-como-string
   ~1 B/registro — registrar, não fazer).
4. **Semântica completa**: ausente ≠ `""` ≠ `[]` (M2/M5) — o sentinela é LOSSY, máscara é o canal
   certo. Mask por INSTÂNCIA cobre opcional dentro de array/objeto aninhado (M5 5/5).
5. **Fronteiras não engolidas**: null → fail-loud claro apontando P3; `0` na máscara reservado.

## Alternativas consideradas (e por quê não)

| alternativa | por quê não |
|---|---|
| sentinela `""` p/ ausente | LOSSY (M2): colide com string vazia legítima |
| union-rectangle (todas as chaves sempre, valor dummy) | mesmo problema + paga valor dummy por buraco |
| `?` sem msize (máscara embutida no corpo) | quebra o modelo header-declara-frames; header deixa de bastar p/ fatiar (L2) |
| máscara-como-string única (n chars, 1 linha) | não reusa L1/RLE; ganha só no caso alternado — fica como knob L3 futuro |
| Parquet def-levels binários | quebra o pilar texto/explicabilidade; a máscara `.`/`-` é o def-level TEXTUAL |

## Plano de WELD (após aprovação do owner — em etapas, como sempre)

- **PW0 — aprovação deste estudo** (gramática `?`, alfabeto 3-estados, escape de `?`, semânticas).
- **PW1 — port pro core**: `src/tcf/hierarchical.py` ganha (a) `optional` no schema-node
  (`_derive_schema` deixa de exigir chave em todos — vira união + flag); (b) coluna `mask` em
  `_leaves`/`_emit_row`/`_read_object`; (c) `?` no meta (emit+parse) e no `_H_NAME_SEP` (escape).
  Estimativa: ~40 linhas de delta, aditivo, mesma forma do protótipo.
- **PW2 — testes red→green**: `test_ragged_fail_loud` INVERTE (ragged agora RT) — é mudança de
  CONTRATO declarada, não regressão; migram os casos M1–M5 do estudo (clássicos + bordas +
  fail-loud null/`0`-reservado); fuzz seedado ganha `optional` no gerador (~25% dos campos).
- **PW3 — gate**: suíte completa + pins flat byte-canônicos (D1-D9/D17a/real-world) + M3 do estudo
  vira teste (uniforme byte-idêntico pré/pós — a não-regressão do PRÓPRIO `.8H`).
- **PW4 — probes adversariais** (lição da auditoria): nomes com `?`/meta-chars em campos opcionais;
  máscara corrompida (`0`, char inválido, tamanho errado) → fail-loud, nunca corrupção silenciosa;
  hang-check com timeout.
- **PW5 — docs**: ADR curto (ou apêndice no ADR-0033) + atualizar T-CODE-TCF8H-JSON-PARITY (P1 ✅)
  + registro do knob L3 (máscara-string) em tcf-camadas-arquitetura.
- **Depois** (fora do P1): P2 tipos → P3 null (`0` já reservado) → P4 rep-level, cada um com seu estudo.

## Riscos conhecidos

- `?` estrutural muda o wire p/ nomes que contêm `?` (raros; passam a `\?`) — declarar no ADR.
- Corpus heterogêneo demais (schema union explode se cada registro tem chaves diferentes) — é o
  regime union-schema/Jaccard do inventário (H-*), fora do P1; fail-loud continua pra tipos mistos.
- Custo do pior caso (alternado ~3 B/registro) — declarado; knob L3 futuro se doer em dado real.

`confianca: Media-Alta` p/ a forma (RT 100% no estudo; falta o gate real do weld). Sintético
declarado (inputs construídos pra vistoria; M4 gerado com seed).

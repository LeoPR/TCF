# Archive v0.1 — Experimentos e Capitulos Antigos

Esta pasta contem materiais do encoder v0.1 e Phase 1+2 que NAO sao
usados no paper final (v0.2). Sao preservados apenas como **registro
historico** para rastreabilidade metodologica.

## Por que arquivado

O encoder v0.1 foi substituido pelo v0.2 em 2026-04-08 por razoes de
design (niveis progressivos de compressao, JOIN flat, notacao `N*val`
ao inves de `N:val`). Os experimentos executados com v0.1 usavam:

- **Dataset pequeno:** 41 vendas (v0.2 usa 509+)
- **Dataset multi-tabela:** 3 tabelas separadas (v0.2 faz JOIN flat)
- **Encoder com fk_mode:** variantes id_raw/dict/inline/hint (v0.2 abstraiu em L0-L3)
- **Notacao:** `N:val` (v0.2 usa `N*val`)
- **Numeric encoding:** raw_float/int_scaled/bins_16 (v0.2 usa raw)

Ver [T-cleanup-naming](../../../tickets/closed/T-cleanup-naming.md) para detalhes
da transicao.

## Conteudo arquivado

| Arquivo | O que e | Conteudo |
|---------|---------|----------|
| `00-innovations-v01.md` | Inovacoes originais | I1-I5 do encoder v0.1 (fk_mode, 3-layer original, stats) |
| `01-introduction-v01.md` | Introducao v0.1 | Versao anterior ao reposicionamento com STATS shortcut |
| `04-methodology-v01.md` | Metodologia v0.1 | Dataset 41 vendas, variantes fk_mode |
| `06-results-e3-v01.md` | Phase 1 v0.1 | 210 combinacoes, JSONL 63% > CSV 48% > TCF 43% |
| `07-mixed-v01-v02.md` | Mix v0.1 + v0.2 | Phase 2 v0.1 (F8-F11) + Etapa 1/2 v0.2 (F30-F55) |

## Findings v0.1 ainda relevantes

Alguns findings v0.1 informam decisões do paper v0.2:

- **F6 (v0.1):** math_control separa modelos em 2 classes → inspirou o
  diagnostic 3-layer v0.2 (confirmado com F80 em 2026-04-09)
- **F12-F14 (v0.1):** stats melhoram accuracy +12pp global, -22pp em FK → 
  reinterpretado como "STATS shortcut" (F81, F90-F94) no v0.2
- **F8 (v0.1):** TCF raw_float/dict 67% > JSONL 63% → superado em Etapa 2
  v0.2 (gemma3 TCF L0 88%)

Esses findings antigos estao citados no paper v0.2 como **trabalho
preliminar que motivou o design atual**, nao como resultados atuais.

## Por que NAO reusar os numeros v0.1

1. **Dataset diferente:** 41 vs 509 vendas — magnitudes nao comparaveis
2. **Encoder diferente:** v0.1 tem overhead de multi-tabela que v0.2 elimina
3. **Modelos diferentes:** alguns v0.1 (phi3, qwen2.5) sao obsoletos
4. **Metodologia refinada:** diagnostic 3-layer so foi feito em v0.2

Qualquer comparacao direta seria metodologicamente invalida.

## Acesso

Para ver o historico completo de como chegamos aqui:
- Git log: `git log --all --oneline`
- Tickets v0.1 fechados: [../../../tickets/closed/](../../../tickets/closed/)
- Archive source: [../v01/](../v01/)
- Historia consolidada: [../../history.md](../../history.md)

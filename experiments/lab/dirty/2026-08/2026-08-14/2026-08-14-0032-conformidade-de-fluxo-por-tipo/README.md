# Conformidade de fluxo por tipo — onde o int diverge do bool

> **Owner (2026-08-14)**: *"o fluxo tem que ser generalizado […] ter um código exclusivo pros
> tipos deixa o código mais engessado, mas ao mesmo tempo podemos admitir que os tipos mais
> primitivos como string, bool e int (e até float) são especiais no python. porém, também
> precisamos que isso seja uma **otimização, não um padrão do tcf**. então como mesmo o bool
> respeita o fluxo, então é justo pensar no int também […] só vamos padronizar pro int
> também, ver o que de algoritmos já temos que se encaixa nele, reaproveitar e usar."*

## Estado — era / foi / é / será

- **Era**: dois labs mediram **ganho** do int (22h58 e 23h26). Nenhum respondia se o int
  percorre o **mesmo caminho** que os outros tipos.
- **Foi**: a direção acima — o critério do `.8` é **estrutura**, e tipo especial só se justifica
  como candidato, não como rota.
- **É**: este lab mede **conformidade**, não compressão. Resultado em [`result.md`](result.md):
  **int, float e str são idênticos** em todos os 5 regimes (muda a tag, não o mecanismo); o
  **bool diverge só no denso**, com razão escrita no código; e o RT preserva tipo em **12 de
  12** combinações. Falta uma peça (spec na rota tipada) e sobra uma assimetria
  (`nature_per_col` em single tipado é silencioso, para string é recusado).
- **Será**: soldar os itens 1–3 da lista (todos `.8`, nenhum muda byte de quem não usa spec);
  o denso de int fica no `.9`, como o owner colocou.

## Os 5 eixos

| eixo | pergunta |
|---|---|
| 1. dispatch | o tipo é detectado? qual tag sai? |
| 2. candidatos | qual mecanismo vence, por regime? |
| 3. API | `nature` é aceito, recusado, ou sem efeito e sem aviso? |
| 4. wire | a tag aparece? convive com `:id`? |
| 5. RT | volta com o tipo certo, comparado por `type()`? |

Os regimes são **os mesmos** para todos os tipos (constante, duas-classes, com-nulo,
progressão, baixa-card) — é isso que torna a matriz comparável.

## Como rodar

```
python run.py     # regenera inputs/, intermediates/, outputs/ e resultado.json
```

Sai 0 só se todos os round-trips fecharem **com tipo**. `src/tcf` não é tocado.

## Onde olhar

| arquivo | o que é |
|---|---|
| `intermediates/matriz-completa.json` | a matriz inteira, célula a célula |
| `outputs/<tipo>.<regime>.tcf` | o wire de cada célula |
| `outputs/<tipo>.<regime>.roundtrip.json` | contra-prova |
| `inputs/<tipo>.<regime>.entrada.json` | a entrada, com os tipos preservados no JSON |

## Ressalva de método (importante)

O eixo 3 precisou de **três correções** antes de valer — todas do mesmo erro: tomar "wire
idêntico ao baseline" como prova de "parâmetro ignorado", quando pode ser o FLOOR recusando
um candidato que não paga. A terceira correção veio de eu **verificar antes de reportar** um
resultado que parecia achado (`.8H` "ignorando" nature) e era ponto cego do instrumento.

O `_vered()` no `run.py` documenta o critério final e as três tentativas. Isso é diligência,
**não** contra-prova independente — verificação adversarial externa não foi feita.

## Vínculo

`T-INT-CONFORMIDADE-DE-FLUXO` · `T-NUMERO-SPEC` · `T-NATURE-IGNORADA-CALADA` ·
ADR-0036 (bN) · ADR-0037/0038/0039 (denso, índice tipado, lazytype bool).
Ciclo que originou: [`…-0100-tipos-como-fluxo-nao-como-ramo.md`](../../notas/2026-08/2026-08-14-0100-tipos-como-fluxo-nao-como-ramo.md).

# Um spec de INTEIRO faz sentido?

> **Owner (2026-08-13)**: *"vamos ver o número, e mais especificamente inteiros de início,
> ver se um spec faz sentido, provavelmente sim… podemos fazer um lab dos inteiros primeiro,
> fazendo o ritual clássico, com os sintéticos controlados, e até vendo que o percurso de
> revisão desde a bN, bool, date e tudo mais pode generalizar otimizações que já podem ser
> usadas em int."*

## Estado — era / foi / é / será

- **Era**: número é tipo nativo (`stype='n'`) mas **sem pré-transformação nenhuma** — vira
  string e passa pelo núcleo. A rota tipada custa **1 byte a mais** que a string.
- **Foi**: o levantamento de 2026-08-13 mediu folga de 1,9× a 3,0× em regimes de progressão
  e largura fixa.
- **É**: este lab testa três alvos **herdados** de tipos já soldados — PAD (do `IP`), B94 (do
  `CPF`), OFFPAD (do ordinal do `data-iso`) — em 16 casos controlados. **0 falhas de RT, 16
  pins verdes.** Resposta em [`result.md`](result.md): sim, em três regimes com gatilho
  detectável; fora deles o FLOOR recusa (9 dos 16 casos).
- **Será**: medir os gatilhos em **corpus real** (o corpus dita o default), decidir
  um-alvo-com-parâmetro × três-specs-irmãos, e resolver como o parâmetro viaja no wire.

## O percurso que generaliza (a pergunta do owner)

Nenhum dos três alvos é ideia nova — cada um é uma técnica já soldada, aplicada a inteiro:

| alvo | técnica | de onde vem |
|---|---|---|
| **PAD** | zero-pad para largura fixa, ativando o seq-RLE | `TemplatedPaddedSpec` (IP, ADR-0015) |
| **B94** | base-94 densa de largura fixa | `TemplatedCheckedSpec` (CPF, ADR-0015) |
| **OFFPAD** | trocar a grafia por uma em que a aritmética fica curta | ordinal do `data-iso` |

E as recusas também são herdadas: `zeros-a-esquerda` cai no **guard de canonicidade por
re-emissão** que o `data-iso` introduziu (`000001` não é o inteiro `1`, então vira literal), e
os regimes de baixa cardinalidade caem no **bN de domínio** (ADR-0036) que já os cobre.

## Como rodar

```
python run.py     # regenera inputs/, intermediates/, outputs/ e resultado.json
```

Sai 0 só se todos os round-trips fecharem. `src/tcf` **não é tocado**: os alvos entram pela
API pública (`encode(vals, nature=alvo)`), então quem decide é o **FLOOR real**.

## Onde olhar

| arquivo | o que é |
|---|---|
| `specs.py` | os 3 alvos, cada um com o precedente que generaliza |
| `inputs/<c>.entrada.json` · `.fonte.json` | o que entrou + procedência, ideia e pin |
| `intermediates/<c>.candidatos.json` | **todos** os candidatos com bytes, header e quem venceu |
| `outputs/<c>.tcf` | o wire vencedor |
| `outputs/<c>.roundtrip.json` | contra-prova: `diff` contra a entrada |
| `outputs/INDEX.md` | tabela caso → ideia → espera → vencedor → ganho |

## Ressalvas

- Dirty: conclusão **orientativa**. Sintético controlado isola o mecanismo, mas **não** prevê
  frequência em dado real — é o que falta antes de soldar.
- Spec de terceiro precisa ser passado no `decode` também (resolução estrita do ADR-0041). O
  `run.py` faz isso; não fazer foi erro meu na primeira execução, e o erro apareceu como 9
  falhas de RT.

## Vínculo

`T-NUMERO-SPEC` · `T-MIN-LEN-CANDIDATO` · ADR-0015 (natures) · ADR-0036 (bN) · ADR-0040
(seq-RLE periódico) · ADR-0041 (wire_id).
Levantamento que originou:
[`…-2030-proximo-tipo-e-ordem-por-roi.md`](../../../notas/2026-08/2026-08-13-2030-proximo-tipo-e-ordem-por-roi.md)
· ciclo da ordem:
[`…-2115-ciclo-ordem-coluna-antes-de-MH.md`](../../../notas/2026-08/2026-08-13-2115-ciclo-ordem-coluna-antes-de-MH.md).

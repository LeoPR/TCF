# Hora binarizada pelo espaço do tipo

> **Owner (2026-08-14)**: *"a hora usa bem os algoritmos que já tem, talvez se ele tiver uma
> forma binarizada própria para o espaço de números dele, já que vai de 0-24 e 0-60 por
> exemplo, não sei se isso foi explorado nas nossas pesquisas anteriores."*

**Uma pergunta**: binarizar pelo espaço do **TIPO** (que as duas pontas conhecem) vence
binarizar pelo domínio **OBSERVADO** (que tem de viajar)?

## A distinção

| | largura de bits | o domínio viaja? |
|---|---|---|
| **`bN` de domínio** (o núcleo faz) | `w = ceil(log2 k)`, **k = distintos observados** | **sim** |
| **espaço do tipo** (a ideia) | `w` fixo pela **definição** do tipo | **não** |

É a **inversão consciente** do ADR-0036, cujo README resume: *"densidade por **cardinalidade**,
não por tipo declarado"*.

## Foi explorado antes? Em parte

- **O princípio, sim** — ADR-0037 se chama literalmente *"domínio implícito"*: *"a pergunta não
  é 'como declarar o domínio', é **quando o domínio pode NÃO viajar** — quando ele é fixo por
  tipo"*. Mas só para domínio **fechado de 2–3 valores** (bool).
- **`H-DENSE-MODE-01`** (sua, de 2026-07-23) chega perto — fala em bit-width e "campo binário
  arbitrário" —, mas ali isso é **blob de bytes**, e a largura é sempre *do elemento*.
- **Derivar `w` de uma FAIXA: não existe.** As 9 ocorrências de `log2` no repo são todas
  `ceil(log2 k)` sobre distintos observados.
- E a hora é **o exemplo canônico do ponto cego**, registrado desde 2026-05-27 (ADR-0018):
  *"beijing `hour`, 24 únicos → 228,8% de inflação"* — nunca perseguido por esta via.

## Estado — era / foi / é / será

- **Era**: a hora fechou conforme nos 5 eixos, usando bem o que já existe.
- **Foi**: você perguntou se o espaço próprio dela (0–23, 0–59) daria uma forma densa.
- **É**: 6 casos × 5 formas, 0 falhas. **Tem nicho, e ele é preciso** — começa exatamente onde
  o `bN` acaba, por um limite de **namespace** do header. Na coluna real: **−46,5%**.
  Resultado em [`result.md`](result.md).
- **Será**: registrada como `H-DENSE-MODE-03`, com 3 condições de aplicabilidade medidas.

## A aritmética que motivou o lab

`0..23` → 5 bits, `0..59` → 6, `0..59` → 6 ⇒ **17 bits**. E `ceil(log2 86400)` = **17** também,
porque `2^5 · 2^6 · 2^6 = 131072 = 2^17`. Medido: **5682 contra 5683 B**. As duas formas custam
o mesmo — a escolha entre elas não é de tamanho.

## O defeito que o lab pegou em mim

Na 1ª rodada eu variava `k` gerando `_hh((i % k) * (86400 // k))` — o que muda a cardinalidade
**e a regularidade** ao mesmo tempo. O resultado saiu **não-monotônico** (k=1440 vencia
enquanto k=288 perdia). É o mesmo erro do artefato de alinhamento de 2026-07-23. Corrigido:
as horas passam a ser sorteadas (LCG determinístico) de um pool de `k`, então a ordem é
irregular em todo `k` e **só a cardinalidade varia**.

## Como rodar

```
python run.py     # sai 0 só se todas as formas fizerem RT
```

Roda **sem `Z:`** (o caso real é pulado). Não toca `src/tcf/` — usa o `pack_w`/`unpack_w`
públicos, os mesmos do bool denso e do `bN`.

## Onde olhar

| arquivo | o que é |
|---|---|
| `inputs/<caso>.entrada.json` · `.fonte.json` | as horas e a procedência |
| `outputs/<caso>.<forma>.tcf` · `.roundtrip.json` | as 5 formas de cada caso |
| `intermediates/ponto-de-virada.json` | **a virada, com `k` isolado da regularidade** |
| `intermediates/formas.json` | as medições com `CONSTANTE_na_comparacao` |

## Vínculo

`H-DENSE-MODE-01`/`02` (as irmãs) · **`H-DENSE-MODE-03`** (registrada aqui) ·
ADR-0036 (bN, `MAX_W=8`) · ADR-0037 (domínio implícito — o precedente) · ADR-0039 (cabeça
congelada + extras) · ADR-0018 (o ponto cego da hora, 2026-05-27) ·
`T-HORA-SPEC` (fechada; este lab a reabre por mecanismo novo) ·
`T-TIPOS-CONFORTO-MAP` (⛔ bloqueado no owner) ·
lab irmão: [`…-2230-fechamento-hora`](../2026-08-14-2230-fechamento-hora/)

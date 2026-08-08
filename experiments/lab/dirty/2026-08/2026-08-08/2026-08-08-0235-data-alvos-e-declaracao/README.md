# Data — alvos de transformação × declaração da grafia

**2026-08-08 · dirty · exploratório**

```
python run.py     # 56 medições, n=600; exit ≠ 0 se algum RT quebrar
```

Só **data** (sem hora) — recorte do owner.

## As duas partes

**Parte 1 — os alvos.** Sete formas de reescrever a data antes de ir pro core, cada uma com
a inversa. O RT é conferido em **dois níveis**: o wire, e a inversa do alvo (as datas voltam
iguais). A pergunta não é "qual é o melhor" — o lab anterior já mostrou que a resposta
inverte entre regimes. É **quantos alvos bastam**.

| alvo | o que explora |
|---|---|
| `iso` | linha de base — o que o TCF faz hoje |
| `ordinal-dec` | decimal: o `*N+M\|` enxerga a progressão aritmética |
| `ordinal-denso` | base-80 largura 4 — o alvo da nature do CPF |
| `ordinal-b64` | base64 de 3 bytes = 4 chars, sem padding |
| `epoch-seg` | segundos desde 1970 — o formato timestamp |
| `compacto` | `YYYYMMDD`: numérico E legível |
| `delta-dias` | 1ª data por extenso + diferenças |

**Parte 2 — declarar a grafia.** Três opções, e o que custam:

| | onde | custo |
|---|---|---|
| **H1** | spec no header (`#TCF.8 :data-iso`) | **10 B** fixos |
| **H2** | template no 1º registro (`%Y-%m-%d`) | 7–9 B + uma linha do corpo |
| **H3** | inferir do 1º registro | **0 B** — se ele desambiguar |

> Adivinhar a grafia **não substitui declará-la**: se o encoder escolhe e não registra a
> escolha, o decode não tem como inverter. O sniff é front-end do H1/H2, não uma quarta via.

## Os oito regimes

`diario` · `semanal` · `mensal` · `agrupado` · `repetido-k12` · `espalhado` ·
`espalhado-ord` · `decada-espalhada`

## O que sai daqui

- **Dois alvos morreram**: `epoch-seg` (×86400 = 5 dígitos sem informação) e `ordinal-b64`
  (base-64 contra o base-80 que já temos).
- **A declaração inverte metade do quadro.** Pagando os 10 B, o `ordinal-dec` — campeão sem
  declaração, até 275× — deixa de vencer em qualquer regime.
- **`delta-dias` vence 5 de 8** porque guarda o 1º valor **verbatim**: a grafia viaja de
  graça. Isso responde à ideia do "primeiro registro formatador" — um alvo já faz isso
  sozinho.
- **Inferir do 1º valor: 100% para ISO.** Só o par BR/US é ambíguo, e só entre si (60,4%).

Detalhe em [`result.md`](result.md); tabelas em [`outputs/medicoes.md`](outputs/medicoes.md).

## Arquivos

- [`alvos.py`](alvos.py) — os 7 alvos, as inversas, e a inferência de grafia
- [`run.py`](run.py) — as duas partes + o relatório
- `outputs/*.tcf` — os wires de `diario` e `espalhado` em cada alvo, diffáveis

`src/tcf` **não é tocado**.

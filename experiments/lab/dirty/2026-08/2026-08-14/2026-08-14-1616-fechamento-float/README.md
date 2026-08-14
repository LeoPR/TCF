# Fechamento do tipo FLOAT

> **Owner (2026-08-14)**: *"seria interessante fechar todos os tipos primeiro até pra ver se
> o fluxo de spec está padronizado e cada um tem suas peculiaridades declaradas, quanto mais
> coisa em comum melhor."*

**Um tipo não fecha porque compensa — fecha porque foi verificado.**

## Estado — era / foi / é / será

- **Era**: eu havia recomendado float para o `.9`, por ROI de bytes (8% agregado). Erro de
  critério: o `.8` é estrutura.
- **Foi**: a correção acima. Float volta ao `.8`, e o que falta não é ganho — é
  caracterização.
- **É**: 12 bordas + 5 colunas reais nos 5 eixos, **0 falhas**. Resultado em
  [`result.md`](result.md): o float é **conforme em tudo**, e tem **6 peculiaridades**
  declaradas — a principal sendo que ele divide a tag `n` com o int (união `int|float`, o
  `number` do JSON), e o tipo concreto vem da **grafia**, não da tag.
- **Será**: hora (sintéticos + eixos) e datetime (tudo).

## O RT que vale para float

`==` **não basta**, por duas razões independentes:

- **tipo** — em Python `1 == 1.0`; comparar valor mascara troca de tipo;
- **sinal do zero** — `-0.0 == 0.0` é `True`. Só `math.copysign` distingue.

O `igual_float()` cobre os dois. Um lab de float que use `==` é cego para a segunda.

## Como rodar

```
python run.py     # sai 0 só se as 12 bordas e os 5 eixos fecharem
```

Roda **sem `Z:`** (as colunas reais são puladas). `src/tcf` não é tocado.

## Onde olhar

| arquivo | o que é |
|---|---|
| `intermediates/bordas.json` | as 12 bordas com o veredito e o wire |
| `intermediates/eixos-reais.json` | os eixos 1–4 nas 5 colunas reais |
| `outputs/borda-*.tcf` · `real-*.tcf` | os wires |
| `outputs/*.roundtrip.json` | contra-prova |

## Vínculo

`T-FLOAT-SPEC` · `T-INT-CONFORMIDADE-DE-FLUXO` · ADR-0036 (bN) · EXP-018 (a porta tipada,
que este lab confirma funcionar para float também).
Critério: [`…-0430-fechar-todos-os-tipos-no-08.md`](../../notas/2026-08/2026-08-14-0430-fechar-todos-os-tipos-no-08.md).

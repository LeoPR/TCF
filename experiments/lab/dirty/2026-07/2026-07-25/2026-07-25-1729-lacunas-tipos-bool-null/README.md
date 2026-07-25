# 2026-07-25-1729 — Lacunas da frente de tipos (evidência em arquivo)

Levanta o estado **real** do `src/tcf` na frente cabeçalho / string / bool, para decidir o
que falta antes de abrir int, float e specs. Nada de memória — 23 casos rodados contra a API
pública, cada um com os arquivos do fluxo §3.2 no disco.

## Onde estão as evidências

Para cada `<ID>`:

| arquivo | o que é |
|---|---|
| `inputs/<ID>-fonte.json` | dataset de entrada + nota do caso |
| `intermediates/<ID>-dataset-consumido.json` | o que o TCF consome |
| `outputs/<ID>-wire.tcf` | **wire REAL** emitido pelo `encode()` |
| `outputs/<ID>-equivalente.json` | JSON compacto equivalente (referência de escala) |
| `outputs/<ID>-dataset.roundtrip.json` | `decode` do wire — prova de RT |

Blocos: `A*` rotas por tipo · `B*` varredura de tamanho do bool · `C*` as lacunas ·
seção D do `result.md` = o que o namespace aceita.

## Fatos

**RT: 23/23.** Nenhuma lacuna aqui é perda de dado — todas são bytes.

**12 de 23 casos o TCF sai MAIOR que o JSON compacto**, e eles se separam em dois grupos:

| grupo | casos | causa |
|---|---|---|
| rota `.8H` | `int` +343% · `int+null` +320% · `float` +300% · `bool+null` +227%/+171%/+24% · `multi+null` +47% | o envelope hierárquico custa mais do que economiza nesses tamanhos |
| rota flat/tipada | `[]` +250% · `[None,None]` +9% · `[true]` +117% · `[true,false]` +17% · `["a","b","a"]` +8% | o cabeçalho de 7 B (ADR-0034) contra um JSON de 2–13 B |

O segundo grupo é **consequência declarada** do ADR-0034, não lacuna nova. O primeiro é a
mesma classe que foi fechada para `str + null` em 2026-07-25 — e continua aberta para bool,
multi-col, int e float.

**Namespace hoje**: só a tag `b` decoda (`#TCF.8n` e `#TCF.8s` são fail-loud); o denso do bool
só aceita `w=1` (`b2`/`b4`/`b8` fail-loud).

**Crossover do bool vs JSON: ~4 elementos.** Abaixo, o cabeçalho domina; acima, o ganho vai
de −36% (n=4) a −97% (n=1000).

## Erro DESTE lab (corrigido, registrado)

A 1ª rodada varria só o bloco C e afirmava *"5 casos em que o TCF é maior que o JSON, todos
com null fora da rota flat"*. **Falso** — `int`, `float`, `[]` e bool com n≤2 também estavam,
e não têm null nenhum. A varredura passou a cobrir A+B+C e a separar por rota.

## Rodar

```
python run.py     # 23 casos; regenera todos os arquivos de evidência + result.md
```

**Não toca `src/tcf`.** Contexto:
[revisão da frente de tipos](../../notas/2026-07/2026-07-25-1649-revisao-tipos-fechado-e-lacunas.md).

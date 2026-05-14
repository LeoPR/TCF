# Conclusoes M5 — Pilha M2.A + M4.C1' (teste de ortogonalidade)

**Data**: 2026-05-14
**Vem de**: [`../README.md`](../README.md) — analise algebrica previa
indicava dominacao; experimento confirmou.
**Sucede**: orienta decisao protótipo (M2.A fora).

## Resultado

| Sintaxe | D1-D4 total | delta vs M1.E |
|---|---:|---:|
| M1.E (baseline) | 676 | 0 |
| M2.A alone | 666 | -10 (-1.5%) |
| M4.C1' alone | 636 | -40 (-5.9%) |
| **M5.A (detector hibrido)** | **636** | **-40 (-5.9%)** |

RT 16/16 OK em todos micros.

M5.A == M4.C1' **exatamente** em cada dataset:
- D1: 138 = 138
- D2: 174 = 174
- D3: 196 = 196
- D4: 128 = 128

## Achado central — M4.C1' subsume M2.A

Detector hibrido NUNCA selecionou alias tipo M2.A (preambulo) em
nenhum dos 4 datasets. Todos os aliases viraram tipo M4.C1' (inline
`~...~` def + `&N` uso).

Os TCFs gerados nao tem `$N=...` no preambulo nem `$N` no body —
sao identicos byte-a-byte aos do M4.C1' alone.

## Por que dominou (algebra)

Para uma tupla de Lr chars usada R vezes:

```
M2.A_net  = R*(Lr-1-len(N)) - (Lr+3+len(N))
M4C1p_net = (R-1)*(Lr-1-len(N)) - 2
```

Diferenca:
```
M2A - M4C1p = (Lr-1-len(N)) - (Lr+3+len(N)) + 2
            = -2 - 2*len(N)
```

**Para QUALQUER R, Lr, e len(N) >= 1: M2.A economiza 2+2*len(N)
bytes menos que M4.C1' para o mesmo padrao.**

Para len(N)=1: -4 bytes por alias.
Para len(N)=2: -6 bytes por alias.

A constante e' fixa — independe de R (numero de usos) e Lr
(tamanho da tupla). M2.A NAO pode vencer M4.C1' para o mesmo
padrao mesmo escalando R → infinito.

## Por que essa diferenca existe

M2.A paga **+Lr** (decl no preambulo escreve a tupla inteira) +
**+3** (chars `$N=` e newline) + **+len(N)** (id do alias na decl).
M4.C1' paga **+2** (chars `~` e `~` na 1a ocorrencia inline) +
+(1+len(N)) (uso `&N`) na 2a+ ocorrencia.

Trocando "preambulo separado" por "def inline":
- M2.A duplica a tupla (uma vez no preambulo + uma vez ja' como
  uso) → 1 ocorrencia "perdida" no custo
- M4.C1' fund a 1a ocorrencia com a def (`~tupla~`) → so' paga +2
  acima do custo original (vs +Lr+3+len(N) do M2.A)

Em datasets de qualquer tamanho, essa fusao gera economia constante.

## Implicacao para protótipo

**M2.A NAO vai para o protótipo.** Esta dominado pelo M4.C1'.

Sintaxe core do protótipo:
- M1.E (range + escape escopo) — base
- M4.C1' (subseq inline + idx implicito) — captura redundancia
  entre linhas

M2.A fica registrado em disco como sintaxe historica/superseded
(igual M1.A, M1.A', M1.B, M1.D, M3.A, M3.B na triagem do dirty).

## Observacao — quando M2.A poderia ainda existir

So' faria sentido se o ambiente NAO suportasse markers inline (`~`,
`&`) — e.g., se houver restricao de charset ou se o decoder fosse
forcado a duas passadas (uma pelo preambulo, uma pelo body). Em
TCF como esta definido (single-pass com escape escopo), inline
sempre vence.

## Pendencias / proximo passo

Fechar dirty lab. Migrar para protótipo:

1. TCF-CORE intocado de `M0-fase-exploratoria-inicial/2026-05-11-16-online-cleanup/online.py`
2. Sintaxe core: M1.E + M4.C1'
3. Camadas pre-tx opcionais (delta, estrutural) — ver
   [`../../notas/comparacao-modular-camadas.md`](../../notas/comparacao-modular-camadas.md)
4. Cleanup: header formal, sem dependencias do dirty

## Conexoes

- [[../../2026-05-13-M4-desfragmentacao-arvore/notas/conclusoes_M4_C1.md]]
  — M4.C1' como tecnica
- [[../../2026-05-13-M2-redundancia-entre-linhas/]] — M2.A original
- [[../../notas/comparacao-modular-camadas.md]] — modos de
  comparacao na pre-tx

# Proveniência — fiação do lazy bool na rota real (2026-08-01-0322)

## Por que este lab existe

O lab `2026-08-01-0229-lazytype-bool-extras` mediu o lazy `bB` (cabeça congelada + extras
declarados). O owner decidiu desde então: **lazy será DEFAULT** e o **decode emite lista
mista** (contrato união fechado). Antes do weld, este lab responde às 6 perguntas de
fiação — com a regra: **se aparecer bloqueador, o run sai 1 e o veredito é PARE**.
`src/tcf` INTOCADO.

## Dados — reúso + bordas, determinísticos, sem RNG

- **Casos do lab 0229** (mesmos geradores, importados via `lazy_bn.py` — o protótipo é
  importado, não copiado): `extras-raro`, `extras-frequentes`, `k-extras-05/20`,
  `armadilha-tipos` (`"true"/"0"/"1"` como strings), e a coluna real-ish Adult `sex` → bool
  com null a cada 11º e `" ?"` a cada 23º (conversão/injeção DO LAB, declarada no lab 0229).
- **Bordas de detecção (Q1)**: 8 casos nomeados (str+null sem bool, 1 único extra,
  bool+str+int, bool puro, ternário, str pura, só-null) + **varredura FP/FN** sobre os
  `intermediates/*-dataset-consumido.json` do lab 0229 (expectativa derivada da definição
  do detector, não de rótulo manual).
- **Bordas de domínio (Q4)**: extras `"=foo"` (escape `\=`), `"true"` (armadilha), `""`
  (linha vazia invisível — o caso do bugfix `[:-1]` do `dominio_bn`), e LF embutido
  (a recusa que NÃO vem de graça — medido: `_encode_column(["a\nb"])` devolve calado).
- **Gates (Q6)**: as 12 colunas carregadas PELOS PRÓPRIOS testes
  (`test_regression_v1_baseline._load_single_col` D1-D9 + D17a,
  `test_real_world_snapshots._load_single_col`), comparando `encode_com_lazy` × `encode`
  real byte a byte.

## Validação — e por que não é circular

O protótipo (`fiacao.py`) importa `lazy_bn.py` do lab 0229 e funções do `src/tcf`
(`_decode_column`, `_le_grafia`, `unpack_w`, `MARCADOR`) — a única lógica nova é o
detector, o check de LF e a checagem anti-redeclaração da cabeça, que são exatamente o que
o weld adicionaria. RT é tipo-estrito (NoneType/bool/str) contra os dados consumidos;
roundtrip é ARQUIVO byte-idêntico (`outputs/<nome>-dataset.roundtrip.json` ×
`intermediates/<nome>-dataset-consumido.json`, assert no `run.py`).

## Limites declarados

- **Nada soldado**; os `.tcf` são proposta — o decode público não lê `#TCF.8bB`.
- Sintéticos dirigidos (viés declarado); real = Adult com injeções do lab.
- O lazytype NUMÉRICO (bool+str+int) fica fora — outro ticket.
- Estrito-forçado por parâmetro fica fora — T-FORCAR-MECANISMO.
- gzip e CPU não medidos.

## Reprodutibilidade

`python run.py` regenera byte a byte — sem RNG, sem relógio, sem rede. Sai `0` só se as 6
perguntas fecharem sem bloqueador.

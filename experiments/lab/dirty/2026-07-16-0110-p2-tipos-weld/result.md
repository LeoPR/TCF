# Resultado — WELD P2 (tipos escalares number/bool)

**[probatório]** `run.py` pelo CORE weldado, RT obrigatório em cada etapa. Números:
[outputs/00-resultado.txt](outputs/00-resultado.txt). Evidência diffável: `outputs/*.tcf` + `-rt.json`.

## Confirmado (didático → realista → massa, RT 120%)

- **Didático 10/10**: int (`idade:9n`), float, int+float misto (JSON number), bool (`ativo:11b`),
  todos-os-tipos-juntos (string sem tag ao lado de tipados), array-de-number/bool, disambiguação,
  number nullable (`x?:8:10n` = mask+size+tag), array-number com null-elemento (`xs#:3?:8[]:8n`).
- **Realista**: pedidos com int/float/bool + `cupom` null + itens tipados aninhados → RT byte-exato.
- **Massa**: fuzz seedado 6000/6000 (colunas str/number/bool, nullable, arrays tipados).

## Mecanismo (aditivo, L2 — insight Python-tipado)

O codec recebe objetos Python → tipo CONHECIDO (não deduzido). `_scalar_type` deduz do valor
(bool antes de int). `_enc_scalar`/`_dec_scalar`: number via `json.dumps`/`json.loads` (int/float
por-valor); bool `true`/`false`; string identidade. Tag 1-letra após size; **coluna tipada sempre
emite `:size`+tag** (regra que resolve a ambiguidade da última folha). Compõe com P1/P3a/P3b.

## Disambiguação (a assinatura do P2)

`string "30" ≠ int 30 ≠ ""; string "true" ≠ bool True`. Campos NOMEADOS `n`/`b` não colidem com o
tag (o tag vem após o size). Distinção estrutural por-coluna, RT-exata.

## Fronteira (fail-loud, nunca silencioso)

Tipos escalares MISTOS numa coluna (int+str, number+object) = **P5 union**. NaN/±Inf = não-JSON.
Array de objetos sem chaves. Todos `HierarchicalError`.

## Gate

Suíte **727 passed**, 2 skipped, 1 xfailed; flat byte-canônico (D1-D9/D17a/real-world) intacto;
**all-string byte-idêntico** (sem tag). `confianca: Alta` p/ P2 (3 etapas + suíte + massa + auditoria
adversarial `wf_10194874-083`, achados dobrados quando fechar).

## Próximo

Escalares JSON COMPLETOS (string/number/bool/null). Falta ESTRUTURA: **P4** (rep-level: array-em-array,
N-raízes, null-na-raiz) e **P5** (union: array polimórfico / tipo-misto). Bool via índice-interno =
otimização a medir sob H-PROFILE-01 (a letra `b` já marca).

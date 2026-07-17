# Lab 2026-07-17-0230 — ESCAPE D_json: fecha as 3 lacunas de dataset

**Aprovação do owner**: *"O caminho feliz me parece bom, pode revisar mais uma vez e fazer."*
A revisão **refutou a premissa** que segurava a lacuna mais cara.

## A revisão que mudou o plano

A escala classificava `\n` em valor como **E6 = "SEGURAR" (custo ALTO)**, com a justificativa
*"toca o L1 → re-pina D1-D9/D17a/real-world"*. **Medição refutou**: o LF morria em
`encoder.py:220`→`core.py:668` **chamado de `hierarchical.py:311`** — era o `.8H` entregando o
valor cru ao L1. O `.8H` tem **framing próprio** (é o que o T-API-BOUNDARY-CONTRACTS já dizia:
*"H precisa de framing próprio; não herdar a delimitação flat sem teste"*). Escapando na
**própria camada**, o L1 fica intocado e as 3 lacunas fecham juntas — mesmo mecanismo.

## O mecanismo (alfabeto do próprio JSON)

| | escape | por quê |
|---|---|---|
| **valor** (folha string) | `\` → `\` · LF → `\n` | o corpo do L1 é delimitado por LF |
| **nome** (meta) | idem + **vazio → `\z`** | o meta é 1 linha; `{"": v}` é JSON válido |

**Invariante que dá injetividade** (a lógica do JSON): o backslash é **sempre dobrado primeiro**
⟹ no fluxo escapado, `\`+letra **nunca vem de dado** ⟹ `\n`=LF, `\z`=vazio, `\n`=backslash+n.

**Por que `\z` e não "emitir nada"**: hoje *"nome vazio no header"* é o **sentinela de corrupção**
do parse. Emitir nada tornaria `{"":1}` legítimo indistinguível de meta corrompido. Com `\z` o
sentinela fica de pé (o parse passou a checar o **token cru**, não o nome já unescapado).

## Dois scripts, dois papéis

| script | papel | saída |
|---|---|---|
| `study.py` + `proto.py` | **pré-weld**, prova a IDEIA (o protótipo extrai a ideia, não copia o core) | `outputs/00-estudo.txt` |
| `run.py` | **pós-weld**, o WIRE REAL do core | `outputs/*.tcf` (9) + `00-resultado.txt` |

## Resultado

**Estudo**: injetividade **exaustiva** (85 strings do alfabeto crítico, **0 colisões**) · fuzz
**20000/20000** (valor e nome) · o valor escapado **atravessa o L1** 14/14 · adversarial **8/8
fail-loud** · sentinela preservado (`z` real ≠ `\z`).

**Weld**: suíte **821 passed** · **flat byte-canônico INTACTO** (D1-D9=1523B, D17a=300B,
real-world=89616B — 31 passed) · os **3 `xfail(strict)` viraram XPASS** e foram promovidos a
PARIDADE (o pino não deixou fechar em silêncio) · pinos de navegação dos sintéticos de controle
passaram **sem re-pinar** = prova de byte-compat.

**Custo**: **+0 char em todo valor sem `\`/LF** (a camada é no-op no caso comum); 1 char por `\`
e por LF, que o L1 depois re-escapa (duplo) → no wire, ~3B por `\`. Só paga quem tem.

## Fronteira

Fecha **as 3 lacunas de dataset de D_json**. Resta o **eixo raiz** (P4b, 7 formas). Fora de
D_json (NaN/Inf/tuple/chave-não-str/surrogate) segue fail-loud — não é lacuna
([dataset-json-dois-contratos](../notas/dataset-json-dois-contratos.md)).

**Camadas (medido)**: o L1 tem escape próprio e já consome `\X`→`X` (leniência **pré-existente**
dele). Para o nosso `_unesc_leaf` ver um `\q`, o wire precisa trazer `\q` — aí é fail-loud.

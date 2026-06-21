# Result — composicao perdida no detector HCC (H-HCC-01) [probatório]

**Data**: 2026-06-14
**Origem**: owner inspecionou a saida 0.7 do README (coluna e-mails) e achou
`diego` = `dieg5,3` (`o`+`@acme.com.br`), onde `o@acme.com.br` recorre (sufixo de
`bruno`) e deveria virar UM fragmento composto (`diego` = `dieg5`).

## Diagnostico (confirmado por trace + codigo)

`_detect_compositions` ([syntax.py:246-255](../../../../../../src/tcf/composicional/syntax.py))
conta sub-tuplas recorrentes **so' dentro de pecas `'refs'`**. A ocorrencia de
DEFINICAO de um atom (onde ele e' literal) nao entra na contagem. Logo:
- `bruno` = `brun`(lit) + **`o`(lit)** + ref3 -> peca refs e' so' `[3]` -> nao conta.
- `diego` = `dieg`(lit) + refs`[5,3]` -> conta `(5,3)` R=1.

`(5,3)` aparece R=1 (so' diego) -> filtro `if R < 2` -> 0 candidatos -> STOP.
A unidade `o@acme.com.br` recorre de fato (define em bruno, usa em diego = R=2 no
nivel de ATOM), mas e' contada R=1. Mesma coisa com `(a,@acme)` (ana define,
carla usa).

## Caracterizacao (analyze.py): upper-bound da contagem estendida

Contagem ESTENDIDA = adjacencias de atoms na sequencia completa (lit+ref,
incluindo a def-as-lit) vs. a refs-only do detector. Pares R>=2 no estendido mas
R<2 no refs-only = composicoes perdidas. 6 datasets reais (5k linhas/coluna).

| coluna | body B | ~saved | %body | shareRisk |
|---|---:|---:|---:|---:|
| tpch l_comment | 133426 | 5967 | **4.47%** | 426 |
| ibge municipio | 64581 | 2466 | **3.82%** | 215 |
| retail Description | 51854 | 1326 | **2.56%** | 113 |
| receita nome_fantasia | 20003 | 389 | 1.94% | 68 |
| ibge microrregiao | 27539 | 394 | 1.43% | 32 |
| receita cnae_principal | 23492 | 244 | 1.04% | 48 |
| br-pessoas nome / data / email | — | — | 0.6-0.8% | 39-90 |
| numericos / categoricos curtos | — | 0 | ~0% | 0 |
| **TOTAL (upper-bound)** | **990121** | **11962** | **1.21%** | — |

## Leitura

1. **A oportunidade e' real mas modesta** (~1.2% weighted upper-bound) e
   **concentrada em FREE-TEXT** (comments, nomes de municipio, descricoes,
   nome_fantasia). Colunas numericas/categoricas-curtas: ~0% (sem afixos
   recorrentes pra compor).
2. **shareRisk alto exatamente nos hotspots** (l_comment 426, municipio 215,
   Description 113): os pares perdidos envolvem atoms muito compartilhados
   (ex: `@`, palavras comuns). Compor esses pares **embute** o atom compartilhado
   numa composicao, podendo **enfraquecer o sharing flat** que hoje funciona.
   Logo o ganho REAL de um prototipo fica **abaixo** deste upper-bound.
3. **Valida H-HCC-02 (custo dinamico, owner)**: o estimador estatico SUPERCONTA
   porque ignora (a) overlap entre pares, (b) que compor um par muda a largura
   dos ids seguintes, (c) o trade-off com o sharing flat. O ganho otimo nao e' a
   soma dos nets individuais — e' interdependente.

## Decisao / proximo passo

> **ATUALIZADO 2026-06-14**: o prototipo dinamico FOI feito (`dynamic_sim.py`,
> `dynamic_sim_result.md`). A estrutura abstrata e' Re-Pair sobre a sequencia
> completa de atoms; simulado com custo dinamico (overlap + width), RT OK.
> Ganho realista **1.30% weighted (teto)**, free-text only, em **cauda longa**
> (centenas-milhares de regras, net/rule 0.34-2.10). **Decisao: ADIAR o weld**
> (closed-insufficient-gain) — ROI baixo / risco alto no detector core. Ver
> `dynamic_sim_result.md`.

Contexto que levou a essa decisao (preservado):
- A contagem estendida **pega composicoes reais que o detector perde** —
  confirmado. Mas o upper-bound weighted (1.2%) e' modesto e o trade-off de
  sharing morde nos hotspots.
- **H-HCC-02** (custo dinamico/relativo) foi pensada NO desenho do prototipo: o
  estimador de net e' sequencial (recalcula conforme composicoes sao montadas).

## Artefatos
- `analyze.py` — upper-bound da contagem estendida vs refs-only (6 datasets)

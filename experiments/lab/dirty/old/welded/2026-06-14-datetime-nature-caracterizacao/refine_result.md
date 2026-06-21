# Result — refinamento do split estrutural (pre-weld)

**Data**: 2026-06-14 · **Status**: confirmada-empirica (Alta) · **Tipo**: [probatorio]
· FORK · Refina `result.md` (19.4% weighted) com as perguntas de desenho do owner.

## A. Cobertura do detector de template (80 colunas reais, >=3 unicos)

| classe | n | implicacao |
|---|---:|---|
| exact-uniform (>=99.9%) | **23** | weldavel HOJE, sem mecanismo de excecao |
| near-miss (90-99.9%) | **1** | (beijing.Iws 99.5%) — so' 1 coluna |
| baixa cobertura (<90%) | 4 | nao splita (fallback) |
| sem estrutura digito | 52 | free-text/categorico (nao aplica) |

**Decisao de desenho #1**: o **gate "template 100% uniforme"** captura
essencialmente todo o ganho. Mecanismo de excecao por-valor **NAO vale** (1
near-miss em 80 colunas). Mantem o weld simples e seguro.

## B. Breakdown do ganho (exact-uniform)

```
decimal (`.`)            gain=151224 / base=338540  (44.7%)
estruturado c/ separador gain=195293 / base=349429  (55.9%)  [datas + cpf/cnpj]
TOTAL exact              gain=346517  (= os 19.4% weighted)
```
Decimal sozinho ja' e' ~8% weighted -> ate' um weld so'-decimal captura metade
com complexidade minima. Datas/ids sao o resto.

## C. Overlap com natures CPF/CNPJ (ADR-0015) — COMPLEMENTARES

| coluna | base | nature | split generico |
|---|---:|---:|---:|
| br.cpf | 94260 | **34038** | 58148 |
| receita.cnpj | 97054 | 53827 | **32668** |

Nenhum subsume o outro: a nature CPF (check digits, dominio) vence em cpf; o
split generico vence em cnpj. **Decisao de desenho #2**: manter as natures; o
split generico e' um candidato AMPLO (cobre decimais/datas onde nao ha' nature).
Quando ambos aplicam -> `min()`.

## D. Bordas (gate uniforme faz o seguro)

| caso | template dom | cov | acao |
|---|---|---:|---|
| negativos uniformes `-1.5` | `-.` | 100% | splita, RT OK |
| zero-pad `01.02` | `.` | 100% | splita, RT OK |
| datas ok | `--` | 100% | splita, RT OK |
| sinais mistos | `-.` | 50% | **nao splita** (fallback) |
| vazios mistos | `.` | 50% | **nao splita** (fallback) |
| estrutura mista | `.` | 50% | **nao splita** (fallback) |

**Decisao de desenho #3**: sob o gate uniforme, negativos/zero-pad/datas uniformes
splitam corretamente (RT OK); qualquer mistura cai abaixo do gate -> fallback.
Zero risco de lossy. (Sinal `-` so' splita se TODOS forem negativos -> template
`-.` uniforme; caso contrario o `-` quebra a uniformidade -> safe.)

## Desenho do weld proposto (refinado)

- **Candidato per-coluna** no pipeline multi-col: se o template e' uniforme
  (>=99.9%) e ha' >=2 campos com variacao real, split -> sub-table de campos ->
  cada campo passa pelo fallback (tcf/raw/**dict V2-B**) -> escolhe
  `min(coluna_inteira, split)`. Zero-regressao por min().
- **Sem mecanismo de excecao** (decisao A). **Compoe com natures** via min (decisao C).
- **Marcador** novo no header #TCF.7 (ex: `%<size>=<name>` = split estrutural).
  Slot = template + sub-table de campos. Decoder reinterleia.
- **GATE intocado**: free-text -> nao splita. **Re-pin** D1-D9/D17a se algum mudar.
- **Escopo aberto** (owner): auto-detect gated (consistente com V2-A/B/dict) vs
  nature opt-in. Recomendacao: auto-detect gated — e' so' mais um candidato do
  `min()` per-coluna, mesma filosofia do fallback; zero-regressao garante seguranca.

## Artefatos
- `analyze.py` (caracterizacao 19.4%), `refine.py` (cobertura/breakdown/overlap/bordas)

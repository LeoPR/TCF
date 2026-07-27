# Mapa do pipeline (o que EXISTE) e o que falta antes do float — 2026-07-27

Levantamento a pedido do owner, que descreveu um modelo ilustrativo (detector de entrada,
3 etapas de disparo, pré-filtro por spec, execução paralela que pode "matar" o núcleo,
heurísticas dinâmicas com default estatístico) e pediu **o mapa do que temos**.

Tudo abaixo tem `file:line`. Onde a peça descrita **não existe**, está dito.

---

## 1. O funil, de verdade

```
ENTRADA        validacao de kwargs + PREDICADOS DE TIPO       encoder.py:265-295, 86-138
               (nao ha' detector de CONTEUDO aqui)
   |
ROTEAMENTO     if-chain de 5, primeira que casa vence         encoder.py:296/376/391/445/489
   |           flat -> [] -> tipado -> multi .8M -> .8H
   |
CAMADA 0       nature/spec — PASSADO, nunca detectado         encoder.py:306-352
   |
CAMADA 1       pre-passe: analyze_column + cadence + min_len  encoder.py:539-548
   |
CAMADA 2       OBAT (tokenizer online, por afixos)            core/online.py:202-248
   |                                                          obat_shape.py:68-124
CAMADA 3       NUCLEO: syntax.encode fases A->C               syntax.py:752-779
   |
POS            seq-RLE                                        hcc_seqrle.py:310-329
POS            POLARIDADE (weld 2026-07-26)                   polaridade.py:148-203
POS            header / serializacao                          encoder.py:375, 427-444
```

`side_outputs` é **byte-neutro** e populado por efeito colateral (`side_outputs.py:27-81`).

---

## 2. Confronto com o modelo que o owner descreveu

| peça descrita | existe? | onde / por que não |
|---|---|---|
| detector/filtro na **entrada** | **não** para conteúdo | só validação de kwargs e predicados de TIPO (`encoder.py:265-295`). O único filtro de conteúdo é `_stringify_checked` (`multi/core.py:653-681`), que valida `\n`/`\r` |
| **identificador de padrão** (ex.: "isto é CPF") | **NÃO EXISTE** | o spec tem de ser passado (`nature=`/`nature_per_col=`). Registry fechado de 3 ids — `cpf`, `cnpj`, `ip` (`natures/__init__.py:56-60`) — usado **só no decode**. Placeholders admitem a lacuna: `schema.py:194`, `side_outputs.py:36-37` |
| **pré-filtro** que transforma antes do núcleo (tirar DV) | **sim** | é exatamente o que a nature faz: `encode_value` transforma, e o transformado passa pelo núcleo (`encoder.py:319-324`) |
| "passa o filtro **e** vai pro núcleo" | **sim** | é o caminho da nature vencedora |
| "**não** passa e vai pro núcleo" | **sim** | nature perde o FLOOR → cai no stamp sem marcador (`encoder.py:352`) |
| "passa e **não** vai pro núcleo" | **não existe** | todo candidato passa pelo núcleo inteiro |
| "faz **os dois** e escolhe no final" | **sim, sempre** | é o único modo. Ver §3 |
| **paralelo especulativo** | **não** | `parallel=` é `ProcessPoolExecutor` **por COLUNA**, multi-col apenas (`multi/parallel.py:72`, gate em `multi/core.py:345-352`). Data-parallel, não especulativo. Doc explícita: "parallel apenas reordena computacao, nao bytes" (`encoder.py:250`) |
| **"matar" o núcleo em voo** | **não existe** | todos os aborts são *não começar*, nunca *cancelar*. Não há `future.cancel()`, timeout, nem orçamento |
| heurística **dinâmica** | **sim** | `analyze_column` mede o dado; `obat_shape` adapta a cada string |
| default **estatístico** calibrado nos testes | **sim** | `auto_min_len` — árvore de decisão com constantes calibradas (§4) |
| "muda para outro comportamento estatístico se fugir" | **não existe** | as constantes são fixas; não há segunda tabela nem re-calibração |

---

## 3. Os 7 FLOORs — e por que isso é a "esteira" que o owner criticou

| # | o que compete | onde |
|---|---|---|
| 1 | spec single-col × baseline (já polarizado) | `encoder.py:337-338` |
| 2 | tipado: `min(core, core+polaridade, denso-b64)` | `encoder.py:444` |
| 3 | polaridade: polaridade inicial `R` × `L` | `polaridade.py:160` |
| 4 | polaridade: FLOOR nunca-pior | `polaridade.py:162-163` |
| 5 | multi-col por coluna: `min(tcf, raw, dict, split)` | `multi/core.py:420-434` |
| 6 | spec multi-col: blob serializado inteiro | `multi/core.py:472-474` |
| 7 | seq-RLE por corpo | `hcc_seqrle.py:329` |

**Seis dos sete MATERIALIZAM os dois lados e comparam bytes.** Só o **3/4 (polaridade)** decide
por contagem, sem materializar — e foi isso que o owner exigiu quando disse *"a gente NÃO
PODE ficar testando cada um pra ver qual é mais barato"*. O comentário do próprio código
admite a dívida: refino do preditor fica pro `.9` (`encoder.py:404-405`).

Aborts existentes (todos "não começar"): prune por upper-bound no HCC (`syntax.py:437-441`),
cap de 99 iterações (`syntax.py:522-523`), teto no OBAT (`core/online.py:133-134`),
cardinalidade > 8192 no dict (`multi/dict_v2b.py:57-58`), gates do split
(`multi/split.py:33-45`).

---

## 4. As constantes calibradas (o "default estatístico")

`auto_min_len.py:56-75` — árvore rasa sobre `(avg_len, cardinality, is_numeric)`:

```
n_rows < 100                          -> 3     (gating: preserva o baseline D1-D9)
card < 0.2                            -> 3
avg_len >= 25                         -> 6
avg_len >= 8  and card >= 0.4         -> 6
avg_len >= 5  and is_num and card>=.8 -> 6
avg_len >= 12 and card >= 0.7         -> 5
avg_len >= 3  and card >= 0.2         -> 4
else                                  -> 3
```

`auto_cadence.py:34-36` — `n_sample=5`, `threshold=0.7`, `numeric_card_threshold=0.5`.

`column_features.py:78` — `sample=values[:20]` para `is_numeric`.

---

## 5. Duas dívidas achadas ao mapear (verificadas, não relatadas de segunda mão)

### 5.1 `parallel=` é ignorado em silêncio na rota flat

```python
encode(['a1','b2','c3'], parallel=True)   # -> '#TCF.8!!\na1\nb2\nc3\n'   aceito, sem efeito
encode([1,2,3],          parallel=True)   # -> ValueError (fail-loud correto)
```

As rotas 2/3/5 rejeitam o kwarg; a rota 1 (a mais usada) o aceita e não faz nada. É
inconsistência de fail-loud, barata de fechar.

### 5.2 O trigrama do índice é fixo em 3, mesmo com `min_len` 4-6

`core/online.py:115,141,219-220,245-246` e `obat_shape.py:90-91,121-122` sempre usam `s[:3]`
/ `s[-3:]`. Quando o pré-passe decide `min_len=6`, os buckets continuam agrupando por 3 —
o índice fica mais largo do que o necessário. Não é bug de correção (o `min_len` é aplicado
depois), é **trabalho desperdiçado**. Não medido.

---

## 6. Float — o que já funciona, e o que falta

A tag `n` **já cobre float** (`encoder.py:98-123`: `int` ou `float` → tag `n`, render `str`).
Probe direto, RT pelo `decode` público comparando **valor, tipo e sinal**:

| caso | wire | RT |
|---|---|---|
| `[1.5, 2.25, 3.0]` | `#TCF.8n!!` | OK |
| `[1.0, 2.0, 3.0]` | `#TCF.8n` + seq-RLE `*3+1,0\|` | OK |
| `[1e20, 2e20, 3e20]` | `#TCF.8n` — corpo `\1*e+\20` | OK |
| `[1e-7, ...]` | `#TCF.8n` — corpo `\1*e-\07` | OK |
| `[0.1, 0.2, 0.30000000000000004]` | `#TCF.8n!!` | OK |
| `[-0.0, 0.0, 1.0]` | `#TCF.8n!` | OK — **sinal preservado** |
| `[1, 2.5, 3]` (mistura) | `#TCF.8n!!` | OK — int volta int, float volta float |
| `[1.5, None, 2.5]` | `#TCF.8n!` — `!1.5 / 0 / !2.5` | OK |
| **`NaN`**, **`±Inf`** | — | **fail-loud** (`HierarchicalError`) |

### Portanto: o float não precisa de rota nova. Precisa de 3 decisões

1. **NaN / ±Inf** — hoje fail-loud (`encoder.py:118-121` recusa não-finito e manda pro `.8H`,
   que rejeita por RFC 8259). É a lacuna real: coluna float de dado real tem NaN
   (`beijing-pm25` usa `"NA"`). Encaixa na mesma ideia do **slot 0 pré-alocado do null** —
   slots reservados 1 e 2. O owner já sinalizou que *"o NaN e o inf são tipos difíceis"*; a
   pergunta em aberto é a **ordem canônica** dos slots reservados, que nunca foi fixada.

2. **Notação científica** — funciona, mas o `e+`/`e-` **parte a corrida de dígito** e o corpo
   fica `\1*e+\20`. Interação com polaridade e seq-RLE não foi medida. Vale um lab.

3. **Canonicidade do `repr`** — o `str(float)` do Python é *shortest round-trip*, o que é
   correto **em Python**. Para o port em Rust do 1.0 isso vira contrato de formato: o wire
   `0.30000000000000004` só volta idêntico se o outro lado usar o mesmo algoritmo (Ryū /
   Grisu). Hoje isso não está escrito em lugar nenhum.

### O que revisar antes, na ordem

| # | item | custo | por quê |
|---|---|---|---|
| 1 | ordem canônica dos slots reservados (null=0, e depois?) | baixo | bloqueia NaN/Inf, e é decisão de formato, não de código |
| 2 | polaridade × notação científica | 1 lab | único regime de float não medido |
| 3 | declarar o contrato de `repr` de float | doc | dívida de port pro 1.0 |
| 4 | `parallel=` fail-loud na rota flat | trivial | §5.1 |
| 5 | trigrama fixo × `min_len` | 1 lab | §5.2, só desempenho |

Os itens 4 e 5 **não bloqueiam o float** — ficam registrados.

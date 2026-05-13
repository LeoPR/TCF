# Comparações não-literais — nota conceitual para resgate futuro

Data: 2026-05-11
Contexto: registro de ideia trazida pelo user durante a fase de exp 16/17.
Status: **fora do foco do ciclo atual**; nota arquivada para retomada futura.

---

## Arquivos a revisar quando o tema voltar

1. [`experiments/lab/dirty/old/2026-05-09-delta-datas/`](../old/2026-05-09-delta-datas/)
   — laboratório completo sobre delta encoding em datas (5 documentos:
   `00-conceito.md`, `01-dataset.md`, `02-formas-delta.md`,
   `03-aplicado.md`, `04-conclusoes.md`)

2. [`docs/workbench/_archive/tickets/open/23-P-numeric-precision.md`](../../../docs/workbench/_archive/tickets/open/23-P-numeric-precision.md)
   — ticket sobre tratamento numérico com perda controlada (2 camadas:
   Shaper pré-encoding + TCF core)

Ambos são **blueprint** (ciclo anterior). Quando retomar, re-verificar
no dirty v0.6 antes de citar como evidência.

---

## O que o algoritmo atual (exp 16) faz

Toda comparação no dirty lab v0.6 é **literal byte-a-byte**:

- `lcp_len(a, b)` percorre chars iguais do início
- `lcs_len(a, b)` percorre chars iguais do fim
- Igualdade exige sequências idênticas em cada posição comparada

Isso preserva **roundtrip lossless** (a reconstrução é o input
caractere por caractere), que é requisito declarado do TCF.

---

## Modalidades alternativas levantadas

O user observou que comparações poderiam ser mais expressivas em
três regimes distintos:

### 1. Comparação aproximada (texto)

```
Ana   ≈  Anna   ?
```

Algoritmos típicos: Levenshtein/edit distance, Jaro-Winkler,
metaphone/soundex, similaridade por n-grams.

**Onde encaixa**: busca, deduplicação fuzzy, junção aproximada
entre tabelas. **Não encaixa em compressão lossless** — usar
"Anna" como ref de "Ana" perderia 1 char na reconstrução.

Encaixa potencialmente em:
- Camada de **query** sobre TCF decodificado
- Camada de **dedup pré-encoding** (Shaper), com aviso explícito
  de perda
- Modo **lossy opt-in** (não default), com tolerância configurável

### 2. Comparação numérica aproximada

```
0.98834  ≈  0.98833   ?
```

Algoritmos: tolerância absoluta (`|a − b| < ε`), tolerância
relativa (`|a − b| / max(|a|, |b|) < ε`), comparação por casas
decimais, arredondamento controlado, ULP comparison.

**Onde encaixa**: similar ao item 1 — **fora de compressão
lossless**. Encaixa em:
- **Shaper** (pré-encoding) com perda controlada — ticket
  arquivado [`23-P-numeric-precision`](../../../docs/workbench/_archive/tickets/open/23-P-numeric-precision.md)
  já discutia isto em ciclos anteriores
- Modo **lossy opt-in** declarado no header (qualquer dado lossy
  precisa marcação explícita; o decoder não pode reconstruir
  os bytes originais)

### 3. Comparação relativa (delta)

```
2026-10-01   →   2026-10-02   (delta = +1 dia)
```

Algoritmos: delta encoding (inteiro/data/timestamp), delta-of-delta
(timestamps com cadência), zigzag (deltas com sinal).

**Onde encaixa**: esta é **lossless** quando o delta é exato. Pode
entrar em compressão sem violar roundtrip.

**Já foi explorado em ciclo anterior** (laboratório arquivado em
[`dirty/old/2026-05-09-delta-datas/`](../old/2026-05-09-delta-datas/)).
As conclusões daquela mesa registraram:

- Delta é **pré-transformação**, não substitui RLE/dict
- Dois ganhos: representação curta (`+1` vs `2026-10-02`) e
  padrões repetitivos induzidos (deltas iguais)
- Falha em ordens não-cronológicas e em colunas não-numéricas

Essas conclusões são **ideias** para o v0.6 — precisam ser
re-verificadas dentro do dirty lab atual antes de virarem
evidência viva.

---

## Distinção operacional

| Modalidade | Lossless? | Camada apropriada |
|---|---|---|
| Literal byte-a-byte (atual) | sim | algoritmo de compressão (exp 16) |
| Relativa/delta exato | sim | pré-transformação por coluna |
| Aproximada texto | não | query / dedup / lossy opt-in |
| Aproximada numérica | não | Shaper / lossy opt-in com tolerância |

O algoritmo do exp 16 trabalha sob o regime lossless. Adicionar
delta encoding como **pré-transformação** é compatível: a coluna
passa por `δ` antes do encoder, e o decoder aplica `δ⁻¹` depois.
O TCF interno continua comparando byte-a-byte.

Modalidades aproximadas (texto/numérica) **não cabem dentro do
encoder lossless**. Precisariam ser uma camada separada do TCF,
com marcação explícita.

---

## Por que isto não é foco agora

O ciclo v0.6 está estabelecendo o algoritmo lossless de
compressão estrutural de strings (exps 13-16). Antes de adicionar
modalidades não-literais, precisa:

1. Estabilizar o algoritmo lossless atual (em curso)
2. Mapear seu comportamento em famílias variadas (próximo exp)
3. Validar em escala (exp seguinte)
4. Eventualmente cobrir as variantes algorítmicas pendentes
   (par A+B independente, revisão retroativa, janela deslizante)

Comparações não-literais entram **depois** dessa base estar
firme, como camada superior ou como pré-transformações opt-in.

---

## Pontos a registrar

1. **Delta encoding é lossless e cabe no fluxo de compressão**
   como pré-transformação. Existe trabalho anterior arquivado em
   `dirty/old/2026-05-09-delta-datas/` que precisa ser
   re-verificado antes de virar evidência v0.6.

2. **Aproximada texto e numérica são lossy** — não cabem dentro
   do algoritmo de compressão lossless atual. Encaixam em
   camadas superiores (query, dedup, Shaper) ou em modos opt-in
   declarados.

3. **O algoritmo do exp 16 não precisa mudar** para acomodar
   delta encoding. A pré-transformação `δ` opera na coluna
   antes da entrada no encoder; o encoder vê a coluna
   transformada como qualquer outra coluna de strings.

4. **Ticket arquivado** [`23-P-numeric-precision`](../../../docs/workbench/_archive/tickets/open/23-P-numeric-precision.md)
   trata especificamente da camada lossy numérica. Bom ponto de
   partida quando esse tema voltar.

---

## Quando retomar

Esta nota se torna acionável quando algum dos critérios bater:

- O algoritmo lossless do v0.6 estiver estabilizado e validado em
  famílias variadas + escala
- Surgir requisito explícito de dataset onde delta encoding daria
  ganho significativo (timestamps densos, IDs sequenciais)
- Surgir requisito explícito de dataset numérico onde precisão
  controlada é aceitável

Até lá, a nota fica como registro de direção — não como tarefa.

# OBAT — Online Bidirectional Affix Tokenizer

**Codnome de origem**: `alg16` (16º experimento da fase M0 do dirty
lab v0.6).

**Camada**: TCF camada 1 (núcleo de tokenização).

## O que é

OBAT é o núcleo de tokenização do TCF. Recebe uma sequência ordenada
de strings únicas (tipicamente uma coluna de dados tabulares textuais)
e produz, para cada string, uma lista de **tokens** descrevendo como
ela pode ser reconstruída usando trechos das strings anteriormente
vistas.

Não produz bytes comprimidos; produz **estrutura discreta** que a
camada superior (HCC) usa para gerar a saída textual final.

## Estrutura

Para cada string nova `s_i` da sequência:

1. Para cada string anterior `s_j` (com `j < i`):
   - Calcular o maior **prefixo comum** entre `s_i` e `s_j` (LCP)
   - Calcular o maior **sufixo comum** entre `s_i` e `s_j` (LCS)
2. Filtrar matches com `length < min_len` (default 3).
3. **Escolher gulosamente** os matches que maximizam cobertura de
   `s_i` sem sobreposição.
4. Trechos não cobertos viram `TokLit` (literal puro).

### Tokens raiz

| Token | Significado |
|---|---|
| `TokLit(text)` | Trecho literal |
| `TokRefPref(string_id, length)` | Prefixo de `s_{string_id}` de tamanho `length` |
| `TokRefSuf(string_id, length)` | Sufixo de `s_{string_id}` de tamanho `length` |

Token-level garante **ortogonalidade**: a camada de sintaxe (HCC) pode
serializar esses tokens de qualquer forma, sem que OBAT precise saber.

## Funcionamento (sub-linguagem matemática)

Sequência de strings únicas: `S = (s_1, s_2, ..., s_n)`.

Definições:
- `LCP(a, b) = max{ k | a[0:k] == b[0:k] }`
- `LCS(a, b) = max{ k | a[-k:] == b[-k:] }`

Para cada `s_i` com `i ≥ 2`:

```
P_i = { (j, LCP(s_i, s_j)) | j < i, LCP(s_i, s_j) ≥ min_len }
Q_i = { (j, LCS(s_i, s_j)) | j < i, LCS(s_i, s_j) ≥ min_len }
```

Algoritmo guloso de cobertura:
1. `C := P_i ∪ Q_i` ordenado por `length` decrescente
2. `cobertura := ∅`
3. Para cada `(j, k, tipo) ∈ C`:
   - Se o range coberto por esse match **não sobrepõe** com `cobertura`:
     - Adicionar à lista de tokens (`TokRefPref` ou `TokRefSuf`)
     - `cobertura := cobertura ∪ range`
4. Trechos de `s_i` não em `cobertura` viram `TokLit`.

Para `i = 1` (primeira string), todos tokens são `TokLit` (não há
referência anterior).

**Reconstrução** (decoder):
- `TokLit(t)` → emite `t`
- `TokRefPref(j, l)` → emite `s_j[0:l]` (resolve recursivamente se
  `s_j` é descrito por tokens)
- `TokRefSuf(j, l)` → emite `s_j[-l:]`

**Terminação garantida**: como `j < i` sempre, o grafo de
dependências é acíclico. Caso base: `s_1` é totalmente literal.

## Por que o nome

| Componente | Significado |
|---|---|
| **Online** | Processa strings em ordem de aparição, sem reler. Cada nova string só vê as anteriores. |
| **Bidirectional** | Usa prefixo (LCP) **e** sufixo (LCS) simultaneamente. Não é só "front-coding" (LCP-only). |
| **Affix** | Termo linguístico que unifica prefixo, sufixo (e infixo em alguns contextos). Captura "trecho em extremidade". |
| **Tokenizer** | Produz tokens (não bytes comprimidos). Permite camadas superiores trabalharem com estrutura discreta. |

## Diferencial vs literatura

### vs LZ77 (Lempel-Ziv 1977)

LZ77 usa janela deslizante de bytes anteriores e busca match de
**substring qualquer** (em qualquer posição). OBAT restringe a
**afixos** (prefixo/sufixo). Mais simples computacionalmente, mais
adequado a domínios tabulares onde estruturas têm cabeças/caudas
estáveis (URLs com path comum, emails com `@dominio.com`, IDs com
formato fixo).

### vs Front-coding (Witten et al., dictionaries)

Front-coding tradicional codifica string `s_i` pelo **LCP** apenas
com a string IMEDIATAMENTE anterior `s_{i-1}`. OBAT estende em duas
dimensões:
- Usa **LCS** também (não só LCP)
- Considera **qualquer** `j < i`, não só `j = i-1`

### vs HTFC / RPDac (Brisaboa et al. 2011)

Variantes de front-coding com bucketing (agrupamento em blocos para
suporte a busca). OBAT é totalmente online, sem bucketing. Não tem
suporte direto a busca aleatória (todas as referências são
resolvidas sequencialmente).

### vs Suffix tree / Suffix automaton (Weiner 1973, etc.)

Estruturas de **busca** em strings. OBAT é estratégia de
**codificação por afixos**, não índice. Pode ser combinada com índice
se necessário (não é o caso atual).

### vs Re-Pair (Larsson & Moffat 1999)

Re-Pair é **offline** (analisa o corpus todo antes de codificar) e
substitui pares mais frequentes recursivamente. OBAT é **online**
(uma string de cada vez) e trabalha em nível de afixos.

## Inovações próprias do OBAT

1. **Combinação simultânea de LCP + LCS**: distingue OBAT de front-coding
   clássico. Captura padrões "tipo email" onde prefixo (`joao@`) varia
   mas sufixo (`@gmail.com`) é estável.
2. **Min-len threshold**: filtro de cost-benefit. Matches muito curtos
   não compensam o overhead de marcadores em camadas superiores.
3. **Output discreto (tokens)**: separa "achar redundância" de
   "serializar redundância". HCC pode evoluir sem afetar OBAT.
4. **Adequado a colunar**: cada coluna é uma sequência de strings com
   similaridade tipicamente alta. OBAT explora essa similaridade
   localmente, sem precisar de modelo global.

## Onde se encaixa

OBAT é a **camada 1** do TCF. Pipeline:

```
Lista de strings (coluna de dados)
       ↓
   OBAT
       ↓ tokens raiz (TokLit / TokRefPref / TokRefSuf)
   HCC (camada 2)
       ↓ texto TCF
   Arquivo TCF
```

A implementação canônica está em
[`src/tcf/core/online.py`](../../src/tcf/core/online.py). Origem
experimental: `experiments/lab/dirty/old/M0-fase-exploratoria-inicial/2026-05-11-16-online-cleanup/online.py`
(intocado desde 2026-05-11).

## Conexões

- [HCC](HCC.md) — camada que consome os tokens de OBAT
- [TCF-format](TCF-format.md) — posicionamento do formato
- `experiments/lab/dirty/notas/historia-dirty-lab.md` — narrativa do desenvolvimento

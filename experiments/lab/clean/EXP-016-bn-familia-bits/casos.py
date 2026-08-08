"""Catálogo de casos da família bN/bits — declarativo e auto-verificável.

Cada caso declara **o que se espera** antes de rodar. O lab não descreve o que aconteceu:
ele afirma o que deve acontecer e falha quando não acontece. É o que separa um lab
comprobatório de um descritivo.

## O que cada caso declara

    nome        identificador estável (vira nome de arquivo em outputs/)
    familia     agrupamento para o relatório
    valores     o dado (ou um gerador determinístico)
    porque      por que este caso existe — o que ele exerce/ataca
    espera      'ativa' (o bN vence o FLOOR) | 'recusa' (o core vence) | 'qualquer'
    falha       se o encode deve levantar (tipo de exceção esperado) ou None

## `espera` é um PIN, não uma descrição

Todo caso que chega a produzir wire declara `'ativa'` ou `'recusa'` — **52 e 17**. Só os
3 casos de `falha` ficam em `'qualquer'`, e ali por construção: eles levantam antes de
haver rota pra classificar.

`'qualquer'` era o default e 25 casos o herdavam por omissão. Um caso que aceita qualquer
rota não prova nada sobre o FLOOR: ele vira um teste de RT com nome de teste de decisão.
Foram fixados no que de fato acontece, e a partir daí **mudar a decisão do FLOOR quebra o
lab** — que é o ponto. Quando um ticket mover a fronteira de propósito (o `T-BN-TIPADO`
vai mover 6 destes de `recusa` pra `ativa`), re-pinar é parte do weld, do mesmo jeito que
os baselines de bytes são re-pináveis (ADR-0024).

`src/tcf` NÃO é tocado por este lab.
"""
from __future__ import annotations

BS = chr(92)
N = 200                                   # tamanho padrão das colunas sintéticas


def _cic(vals, n=N):
    """Cicla `vals` até `n` — determinístico, sem RNG."""
    return [vals[i % len(vals)] for i in range(n)]


# ─────────────────────────────────────────────────────────────────── o catálogo
CASOS: list[dict] = []


def _c(nome, familia, valores, porque, espera="qualquer", falha=None):
    # `espera` continua com default por causa dos casos de `falha`; caso NOVO que produza
    # wire deve declarar. Ver "espera é um PIN" no topo.
    CASOS.append({"nome": nome, "familia": familia, "valores": valores,
                  "porque": porque, "espera": espera, "falha": falha})


# ── F1. BOOL e binário — as formas de "dois estados" ─────────────────────────
_c("bool-nativo", "F1 bool/binário", [bool(i % 2) for i in range(N)],
   "bool Python puro: o modo denso `b1` tem domínio IMPLÍCITO e deve vencer o bN",
   espera="recusa")
_c("bool-nativo-null", "F1 bool/binário", [None if i % 3 == 0 else bool(i % 2) for i in range(N)],
   "com null o denso `b1` não se aplica; quem cobre é o `b2`/lazy", espera="recusa")
_c("bool-constante-true", "F1 bool/binário", [True] * N,
   "k=1: o core resolve com RLE; o bN nem se qualifica", espera="recusa")
_c("str-01", "F1 bool/binário", _cic(["0", "1"]),
   "o caso que abriu a investigação: `\"0\"`/`\"1\"` como STRING", espera="ativa")
_c("str-01-null", "F1 bool/binário", [None if i % 4 == 0 else str(i % 2) for i in range(N)],
   "`\"0\"` como dado E o slot nulo na mesma coluna — a colisão que custou 4 bugs", espera="ativa")
_c("str-sn", "F1 bool/binário", _cic(["S", "N"]),
   "binário não-numérico: nenhum escape de dígito envolvido", espera="ativa")
_c("str-true-false", "F1 bool/binário", _cic(["true", "false"]),
   "as PALAVRAS que o denso usa implicitamente, mas como string de dado", espera="ativa")
_c("int-01", "F1 bool/binário", _cic([0, 1]),
   "`0`/`1` como int: rota tipada `n` COM bN (weld T-BN-TIPADO) — 608 B viraram 55", espera="ativa")

# ── F2. NULL em todas as densidades ──────────────────────────────────────────
_c("null-so", "F2 null", [None] * N,
   "coluna 100% null: k=1, o core resolve com RLE", espera="recusa")
_c("null-um-so", "F2 null", [None] + ["x"] * (N - 1),
   "1 null em N-1 iguais: k=2 mas RLE domina", espera="recusa")
_c("null-metade", "F2 null", [None if i % 2 == 0 else f"v{i % 3}" for i in range(N)],
   "null alternado — exerce o slot 0 no meio do stream", espera="ativa")
_c("null-e-vazio", "F2 null", _cic([None, "", "x"]),
   "null E string vazia na MESMA coluna: dois 'nadas' que não podem se fundir",
   espera="ativa")
_c("null-e-zero", "F2 null", _cic([None, "0"]),
   "o par crítico mínimo: slot nulo (`0` cru) × literal `\"0\"` (`\\0`)", espera="ativa")
_c("null-e-zero-e-escape", "F2 null", _cic([None, "0", BS + "0"]),
   "os TRÊS: null, `\"0\"` e `\"\\0\"` — a injetividade de `_grafa` no limite", espera="ativa")

# ── F3. Bordas de tamanho e cardinalidade ────────────────────────────────────
_c("n-zero", "F3 bordas", [],
   "coluna vazia: `[]` tem grafia própria (`#TCF.8\\n`)", espera="recusa")
_c("n-um", "F3 bordas", ["x"],
   "1 valor: k=1", espera="recusa")
_c("n-dois", "F3 bordas", ["a", "b"],
   "k=2 com n=2: o cabeçalho+domínio não se pagam", espera="recusa")
_c("n-dez-k2", "F3 bordas", _cic(["a", "b"], 10),
   "n=10 é ~onde o bN passa a ganhar (medido no lab 1608)", espera="ativa")
_c("k-256", "F3 bordas", [f"v{i % 256}" for i in range(512)],
   "k=256 = 2^8: o TETO do namespace, w=8", espera="ativa")
_c("k-257", "F3 bordas", [f"v{i % 257}" for i in range(514)],
   "k=257: PASSA do teto — o bN deve recusar e o core assumir", espera="recusa")
_c("k-3-folga", "F3 bordas", _cic(["a", "b", "c"]),
   "k=3 com w=2: sobra 1 slot — é onde o guard de largura NÃO pega slot extra",
   espera="ativa")

# ── F4. Espaços e whitespace ─────────────────────────────────────────────────
_c("espaco-simples", "F4 espaços", _cic([" ", "x"]),
   "o valor É um espaço", espera="ativa")
_c("espaco-borda", "F4 espaços", _cic([" a", "a ", " a "]),
   "espaço no início/fim/ambos: o core NÃO faz strip (regressão conhecida)",
   espera="ativa")
_c("tab-e-espaco", "F4 espaços", _cic(["\t", " ", "\t "]),
   "tab é whitespace mas não é o separador do formato", espera="ativa")
_c("so-vazio", "F4 espaços", [""] * N,
   "todos vazios: k=1", espera="recusa")
_c("vazio-no-fim-do-dominio", "F4 espaços", _cic(["a", "b", ""]),
   "string vazia como ÚLTIMO valor do domínio — o bug do `rstrip` (2026-07-28)",
   espera="ativa")

# ── F5. Confusão com número / gramática de dígito ────────────────────────────
_c("zeros-a-esquerda", "F5 número", _cic(["0", "00", "000"]),
   "`0`, `00`, `000` são valores DISTINTOS — não podem colapsar", espera="ativa")
_c("numero-negativo", "F5 número", _cic(["-0", "0", "-1"]),
   "`-0` × `0`: distintos como string", espera="ativa")
_c("notacao-cientifica", "F5 número", _cic(["1e5", "1E5", "100000"]),
   "três grafias do mesmo número — distintas como string", espera="ativa")
_c("hex-e-prefixo", "F5 número", _cic(["0x10", "16", "0X10"]),
   "o que `int(x,16)` aceitaria no cabeçalho, mas aqui é DADO", espera="ativa")
_c("digito-nao-ascii", "F5 número", _cic(["٢", "2", "²"]),
   "dígito árabe-índico e sobrescrito: `str.isdigit()` aceita, o formato não deve confundir",
   espera="ativa")
_c("underscore-numerico", "F5 número", _cic(["1_000", "1000"]),
   "PEP 515: `int('1_000')` funciona — como dado são distintos", espera="ativa")

# ── F6. Valores que imitam o CABEÇALHO e a gramática do wire ────────────────
_c("imita-magic", "F6 cabeçalho", _cic(["#TCF.8", "x"]),
   "o valor É o magic do formato", espera="ativa")
_c("imita-wire-bn", "F6 cabeçalho", _cic(["#TCF.8B2c8", "x"]),
   "o valor é um CABEÇALHO bN completo", espera="ativa")
_c("imita-marcador", "F6 cabeçalho", _cic(["=AAAA", "x"]),
   "o valor começa com o marcador `=` que abre o bloco de bits", espera="ativa")
_c("imita-marcador-escapado", "F6 cabeçalho", _cic([BS + "=x", "=y", "z"]),
   "o valor É a forma ESCAPADA do marcador — a inversa não pode desfazer demais",
   espera="ativa")
_c("imita-referencia", "F6 cabeçalho", _cic(["^1", "^2", "x"]),
   "o valor parece referência de linha do core", espera="ativa")
_c("imita-rle", "F6 cabeçalho", _cic(["*3|x", "*2+1|y", "z"]),
   "o valor parece marcador RLE / seq-RLE", espera="ativa")
_c("imita-b64", "F6 cabeçalho", _cic(["GGGGGGGG", "AAAA", "x"]),
   "o valor É base64 válido — não pode ser confundido com payload", espera="ativa")

# ── F7. Gramática de escape do core ──────────────────────────────────────────
_c("todos-os-especiais", "F7 escape", _cic(["*", "~", "^", ",", "|", BS]),
   "os 6 chars da gramática do corpo, um por valor", espera="ativa")
_c("escape-duplo", "F7 escape", _cic([BS, BS + BS, BS + BS + BS]),
   "1, 2 e 3 barras: a injetividade sob repetição", espera="ativa")
_c("escape-mais-digito", "F7 escape", _cic([BS + "1", BS + "12", "1"]),
   "`\\1` (literal) × `1` (que o core escaparia) — a colisão de grafia", espera="ativa")
_c("circunflexo-lider", "F7 escape", _cic(["^topo", "meio^", "^"]),
   "`^` líder é escapado à parte pelo core", espera="ativa")
_c("til-e-asterisco", "F7 escape", _cic(["a~b", "a*b", "a|b"]),
   "os separadores dentro do valor", espera="ativa")

# ── F8. Tipos especiais (rota tipada — o bN não alcança hoje) ───────────────
_c("float-simples", "F8 tipos", _cic([1.5, 2.5, 3.5]),
   "float k=3 na rota tipada `n` com bN: a grafia canônica vira domínio", espera="ativa")
_c("float-integral", "F8 tipos", _cic([1.0, 2.0]),
   "float que parece int no `repr`", espera="ativa")
_c("float-neg-zero", "F8 tipos", _cic([-0.0, 0.0, 1.0]),
   "`-0.0 == 0.0` em Python: só o `copysign` distingue", espera="ativa")
_c("misto-int-float", "F8 tipos", _cic([1, 2.5, 3, 4.5]),
   "int e float na MESMA coluna", espera="ativa")
_c("bool-vs-int", "F8 tipos", _cic([True, 1, False, 0]),
   "`True == 1` em Python. FRONTEIRA DECLARADA: união bool+int no mesmo slot está fora do "
   "`.8H` (ratificada 2026-07-17) — tem de falhar alto, não deduplicar em silêncio",
   falha=Exception)
_c("int-grande", "F8 tipos", _cic([10 ** 18, 10 ** 18 + 1]),
   "int além de 64 bits", espera="ativa")
_c("nan", "F8 tipos", [1.0, float("nan")],
   "NaN: fora do JSON (RFC 8259) — deve FALHAR ALTO", falha=Exception)
_c("inf", "F8 tipos", [1.0, float("inf")],
   "±Inf: idem", falha=Exception)

# ── F9. Unicode e multibyte ─────────────────────────────────────────────────
_c("acentuado", "F9 unicode", _cic(["café", "ção", "naïve"]),
   "acentos: 2 bytes por char em UTF-8", espera="ativa")
_c("emoji", "F9 unicode", _cic(["🔥", "✅", "x"]),
   "4 bytes por char — o domínio paga, o corpo não", espera="ativa")
_c("cjk", "F9 unicode", _cic(["日本", "中文", "한글"]),
   "3 bytes por char", espera="ativa")
_c("zero-width", "F9 unicode", _cic(["a\u200bb", "ab", "a"]),
   "zero-width space: invisível mas distinto", espera="ativa")

# ── F10. bN × RLE / seq-RLE no DOMÍNIO ──────────────────────────────────────
# O domínio é uma mini-coluna comprimida pelo próprio core — então RLE e seq-RLE agem
# DENTRO dele. Foi isso que derrubou "leia k linhas" (lab 2026-07-27-1647): um domínio de
# 4 valores pode virar UMA linha.
_c("dom-seqrle-colapsa", "F10 bN×RLE", _cic(["100", "101", "102", "103"]),
   "o seq-RLE colapsa o domínio inteiro em `*4+1|\100` — 4 valores, 1 linha",
   espera="ativa")
_c("dom-seqrle-alfanum", "F10 bN×RLE", _cic(["A1", "A2", "A3", "A4", "A5"]),
   "idem com prefixo: `*5+1|A\1`", espera="ativa")
_c("dom-datas-incrementais", "F10 bN×RLE", _cic(["2026-01-01", "2026-01-02", "2026-01-03"]),
   "domínio que o seq-RLE encadeia — o caso mais realista do colapso", espera="ativa")
_c("dom-prefixo-comum", "F10 bN×RLE", _cic(["Self-emp-not-inc", "Self-emp-inc", "Self-gov"]),
   "domínio que o OBAT/HCC fatora por afixo, sem seq-RLE", espera="ativa")
_c("dom-sem-estrutura", "F10 bN×RLE", _cic(["zqx", "mfw", "pkv", "bhn"]),
   "domínio que NÃO comprime — o custo dele é o cru", espera="ativa")
_c("corpo-rle-vs-bn", "F10 bN×RLE", ["a"] * 100 + ["b"] * 100,
   "corpo perfeitamente RLE-ável (2 blocos): o core faz `*100|a`+`*100|b` e VENCE o bN",
   espera="recusa")
_c("corpo-rle-parcial", "F10 bN×RLE", _cic(["a", "a", "a", "b"]),
   "blocos de 3 iguais: RLE parcial contra bits fixos", espera="ativa")

# ── F11. A fronteira da decisão automática (o FLOOR) ────────────────────────
# O FLOOR é `min()` sobre candidatos materializados. Estes casos varrem a vizinhança da
# virada para checar que ela é ESTÁVEL (sem oscilação) e que o nunca-pior vale em cada passo.
for _n in (8, 9, 10, 11, 12):
    _c(f"fronteira-n{_n:02d}", "F11 fronteira", _cic(["a", "b"], _n),
       f"n={_n}: a vizinhança da virada em k=2 (medida em ~10 no lab 1608)",
       espera="ativa")
for _lv in (1, 8, 16, 32):
    _c(f"fronteira-len{_lv:02d}", "F11 fronteira",
       _cic([("x" * _lv + s)[-_lv:] for s in "abcd"]),
       f"len(valor)={_lv} com k=4: o teto real é `k x len(valor)`, não `k`",
       espera="ativa")

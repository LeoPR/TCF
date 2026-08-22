"""HCC com seq-RLE de linhas near-identical (canonical).


Origem: `experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/hcc_seqrle.py`
(do dirty lab `02-hcc-sozinho-rle-near-identical/hcc_fork.py`
post bug-fix do detector descoberto em sub-exp 04).

Subclass de M8AVirtualRefsSyntax. Post-process body canonical pra
detectar runs near-identical e compactar em `*N+delta|<template>`.

Detector valido:
- mesmo length
- escape-digit runs em mesmas posicoes (runs_a == runs_b)
- diffs APENAS dentro de escape-digit runs
- delta integer consistente entre runs (a -> b)

Decoder espelho: expande `*N+delta|<template>` em N linhas via
shift_escape_digits.

Sintaxe: `*N+delta|<template>` (compativel com `*N|` RLE puro
existente em M8A — distincao pelo `+`). Convencao de output (sem brackets,
LF unico) conforme `docs/algorithms/output-convention.md`.

PERIODICO (ADR-0040): `*N~d1,...,dp|<template>` — o delta CICLA entre
linhas. Cobre cadencias que o uniforme nao alcanca (dias uteis `1,3,1,1,1`, ids por turno
`10,10,10,50`, quinzenal/mensal). O ciclo paga UMA vez: 600 dias uteis viram
`*600~1,3,1,1,1|\739617`, e com n=6000 o wire cresce UM byte. Terceiro candidato do
MESMO `min()` — nunca-pior por construcao.

`src/tcf/composicional/syntax.py` intocado — importa e estende.

GATE byte-canonical: qualquer mudanca aqui (seq-RLE / detector) DEVE passar
`tests/test_real_world_snapshots.py` + `tests/test_core_rt.py`. Spec:
`docs/algorithms/HCC.md` (ADR-0016).
"""

from __future__ import annotations

from tcf.composicional.syntax import (
    M8AVirtualRefsSyntax,
    estouro_max_length,
    resolve_max_length,
    split_lf_body,
)


def _contador_declarado(linha: str) -> int:
    """Le o contador de um marcador `*N|` / `*N+d|` SEM expandir — a pre-checagem do teto
    tem que acontecer antes da materializacao, senao a memoria ja' foi. Retorna 0 se a
    linha nao declara contador (nao e' marcador)."""
    if not linha.startswith("*"):
        return 0
    bar = linha.find("|")
    if bar == -1:
        return 0
    i, head = 0, linha[1:bar]
    while i < len(head) and head[i].isdigit():
        i += 1
    return int(head[:i]) if i else 0


def find_escape_digit_runs(line: str) -> list[tuple[int, int]]:
    """Retorna runs (start, end_exclusive) de chars digit apos escape."""
    runs = []
    i = 0
    n = len(line)
    while i < n:
        if line[i] == "\\":
            i += 1
            if i < n and line[i].isdigit():
                start = i
                while i < n and line[i].isdigit():
                    i += 1
                runs.append((start, i))
        else:
            i += 1
    return runs


def compare_for_seq(line_a: str, line_b: str) -> list[int] | None:
    """Retorna lista de deltas se par e' near-identical compactavel.

    ADR-0016 (Fase 1 sub-exp 14 Bug #2): retorna LISTA de deltas
    (1 por run de escape-digit). Permite multi-run com deltas mistos
    [0, 0, 0, 1] (3 runs invariantes + 1 incrementing) — caso comum
    em strings com prefix invariante + suffix cadenced (ex: IPs sem
    atom HCC).

    Aceita:
    - Single non-zero (todos runs com mesmo delta): [1, 1, 1] OR [5]
    - Mixed zero+nonzero (1 non-zero, resto zero): [0, 0, 0, 1]

    Rejeita:
    - Multiple non-zero diferentes: [1, 2] OR [3, 5]
    - All zero (lines identical): [0, 0, 0, 0]
    - Estruturas runs_a != runs_b
    """
    if len(line_a) != len(line_b):
        return None
    diffs = [k for k in range(len(line_a)) if line_a[k] != line_b[k]]
    if not diffs:
        return None
    runs_a = find_escape_digit_runs(line_a)
    runs_b = find_escape_digit_runs(line_b)
    if runs_a != runs_b:
        return None
    if not runs_a:
        return None
    run_positions = set()
    for s, e in runs_a:
        run_positions.update(range(s, e))
    if any(d not in run_positions for d in diffs):
        return None
    deltas = []
    for start, end in runs_a:
        try:
            a_int = int(line_a[start:end])
            b_int = int(line_b[start:end])
        except ValueError:
            return None
        deltas.append(b_int - a_int)
    non_zero = [d for d in deltas if d != 0]
    if not non_zero:
        return None  # all zero (identical)
    if len(set(non_zero)) > 1:
        return None  # multiple different non-zero (Fase 2 reject)
    return deltas


def shift_escape_digits(template: str, delta) -> str:
    """Shifta runs de escape-digit por delta.

    `delta` aceita:
    - int (M10 compat): mesmo delta em TODOS runs
    - list[int] (ADR-0016): per-run delta
    """
    runs = find_escape_digit_runs(template)
    if not runs:
        return template

    # Normalize delta para list
    if isinstance(delta, int):
        deltas = [delta] * len(runs)
    else:
        deltas = list(delta)
        if len(deltas) != len(runs):
            return template  # mismatch, no-op safe fallback

    out = []
    cursor = 0
    for (start, end), d in zip(runs, deltas):
        out.append(template[cursor:start])
        old_val = int(template[start:end])
        new_val = old_val + d
        width = end - start
        new_str = str(new_val)
        if len(new_str) < width:
            new_str = new_str.zfill(width)
        out.append(new_str)
        cursor = end
    out.append(template[cursor:])
    return "".join(out)


def deltas_pares(body_lines: list[str]) -> list[list[int] | None]:
    """`compare_for_seq` de cada par adjacente, computado UMA vez (ADR-0040).

    Os DOIS detectores (uniforme e periodico) consomem este array. Sem compartilhar,
    ele e' recomputado inteiro: medido em 6,8 ms num corpo de 1200 linhas, contra 1,6 ms
    de toda a logica de periodo. Vizinho do `T-SEQRLE-INCREMENTAL`.
    """
    return [compare_for_seq(a, b) for a, b in zip(body_lines, body_lines[1:])]


def detect_seq_runs(
    body_lines: list[str], pares: list[list[int] | None] | None = None
) -> list[tuple[int, int, list[int]]]:
    """Retorna runs (start, end_exclusive, deltas) consecutivos near-identical.

    ADR-0016: deltas eh list[int] (per-run). Compat M10: quando todos
    deltas iguais e nao-zero, marker emit usa formato `*N+delta|` (single).

    `pares` (ADR-0040): o array de `deltas_pares` ja' computado. `None` = computa aqui,
    preservando a assinatura antiga. Comportamento identico nos dois casos.
    """
    if pares is None:
        pares = deltas_pares(body_lines)
    runs = []
    n = len(body_lines)
    i = 0
    while i < n - 1:
        deltas = pares[i]
        if deltas is None:
            i += 1
            continue
        run_end = i + 2
        while run_end < n:
            next_deltas = pares[run_end - 1]
            if next_deltas != deltas:
                break
            run_end += 1
        runs.append((i, run_end, deltas))
        i = run_end
    return runs


# ─────────────────────── seq-RLE PERIODICO (ADR-0040) ───────────────────────
#
# `*N~d1,...,dp|template`: o delta CICLA entre linhas — linha k+1 = linha k deslocada
# por pad[(k-1) % p]. Cobre cadencias que o `*N+d|` (uniforme) nao alcanca: dias uteis
# (`1,3,1,1,1`), ids por turno (`10,10,10,50`), quinzenal/mensal. O ciclo paga UMA vez:
# 600 dias uteis = `*600~1,3,1,1,1|\739617`, e com n=6000 o wire cresce UM byte.
#
# Distinto do multi-delta do ADR-0016 (`*N+d1,d2|`), que e' per-RUN dentro da MESMA
# linha, nao per-linha.

MAX_PERIODO = 24
"""Teto do periodo. Cobre mensal (12) e quinzenal-ano (24). Sem caso medido acima."""


def _pad_minimo(pad: list[int]) -> int:
    """Menor `d` que gera `pad` por repeticao: `pad[k] == pad[k % d]` para todo k.

    Calculado do PAD (p <= MAX_PERIODO), nunca de uma sequencia de `count-1` elementos
    materializada — ver a ordem das condicoes em `grafia_emissivel`.
    """
    p = len(pad)
    for d in range(1, p + 1):
        if p % d == 0 and all(pad[k] == pad[k % d] for k in range(p)):
            return d
    return p


def grafia_emissivel(pad: list[int], count: int) -> bool:
    """A grafia e' aceita? Canonica (injetiva) E produzivel pelo encoder.

    A ORDEM DAS CONDICOES E' DEFESA, nao estilo. Tudo aqui e' O(1) ou O(p^2) com
    p <= MAX_PERIODO, e NADA e' proporcional ao `count` que o WIRE declara. Uma versao
    anterior materializava `count-1` elementos e rodava O(n^2) sobre um pad sem teto:
    48,8 KB de wire hostil custavam 126,87 s (16.881x o tempo de recusar sem o
    mecanismo, que devolve o MESMO erro), e 22 B custavam 17,25 s e 85 MB. Depois desta
    ordem: 3,75 ms e 0 MB.

      1. `len(pad) <= MAX_PERIODO` — espelha o teto do DETECTOR. Sem isto o pad vindo do
         wire nao tem teto nenhum.
      2. `count - 1 >= 2*len(pad)` — RE-EMISSAO, e e' O(1), entao vem ANTES do resto. O
         detector so' emite com dois ciclos completos (`L >= 2p`), logo `*4~1,3|` nao e'
         produzivel por encoder TCF. Mesmo guard do `DataIsoSpec` (`d.isoformat() != v`,
         que recusa `20191204` porque `fromisoformat` aceita mais do que `isoformat`
         emite).
      3. `_pad_minimo(pad) == len(pad) >= 2` — INJETIVIDADE. Duas grafias com a mesma
         sequencia produzem o mesmo dado; a canonica e' a de periodo minimo:

             *5~1,4,9|    cauda morta (o 9 nunca e' lido)   recusa
             *9~1,3,1,3|  repeticao de [1,3]                recusa
             *5~1,4,1|    extensao parcial de [1,4]         recusa
             *600~1,1|    minimo 1 = `*N+d|` disfarcado     recusa
             *5~1,4|      minimo 2 == len(pad)              ACEITA

         Vale calcular do `pad` porque (2) ja' garantiu >= 2 ciclos (Fine-Wilf).
    """
    if not pad or count < 2:
        return False
    if len(pad) > MAX_PERIODO:
        return False
    if count - 1 < 2 * len(pad):
        return False
    d = _pad_minimo(pad)
    return d == len(pad) and d >= 2


def marcador_periodico(count: int, padrao: list[int], template: str) -> str:
    """`*N~d1,...,dp|template`. O caractere `~` e' reversivel pre-1.0 (ADR-0040):
    marcador e' abstrato por dentro, o char e' so' a saida."""
    return f"*{count}~{','.join(str(d) for d in padrao)}|{template}"


def detect_periodic_runs(
    body_lines: list[str], pares: list[list[int] | None]
) -> list[tuple[int, int, list[int], int]]:
    """Runs `(start, count, pad, economia)` onde o delta entre linhas CICLA (p >= 2).

    O(n * MAX_PERIODO). Escopo do 1o weld: pares de UM run de escape-digit — o multi-run
    e' territorio do ADR-0016, e periodico x multi-run e' produto cruzado sem caso medido.

    A forma ingenua desta funcao e' O(n^2) e foi medida: n=2400 levava 13,8 s contra
    47 ms do encode inteiro. Tres armadilhas, todas por indice em vez de por cadeia:
    rechar o fim da cadeia a cada `i`; fatiar os deltas a cada `i`; e o guard de padrao
    uniforme rodando por (posicao x periodo) — ~27.600 fatias so' pra concluir "pule".
    O pre-calculo `mudanca[]` mata a terceira em O(n).
    """
    d = [p[0] if p is not None and len(p) == 1 else None for p in pares]
    n, m = len(body_lines), len(d)

    # mudanca[k] = distancia de k ate' o proximo delta DIFERENTE. Qualquer periodo
    # p <= mudanca[k] tem padrao uniforme por construcao -> nem precisa ser testado.
    mudanca = [0] * m
    for k in range(m - 1, -1, -1):
        mudanca[k] = 1 if (k == m - 1 or d[k] != d[k + 1]) else mudanca[k + 1] + 1

    runs: list[tuple[int, int, list[int], int]] = []
    i = 0
    while i < n - 1:
        if d[i] is None:
            i += 1
            continue
        fim = i                                     # fronteira da cadeia: UMA vez
        while fim < n - 1 and d[fim] is not None:
            fim += 1
        pos = i
        while pos < fim:
            melhor = None                           # (economia, count, pad)
            for p in range(max(2, mudanca[pos] + 1), min(MAX_PERIODO, fim - pos) + 1):
                pad = d[pos:pos + p]
                L = p
                while pos + L < fim and d[pos + L] == pad[L % p]:
                    L += 1
                if L < 2 * p:                       # dois ciclos completos
                    continue
                count = L + 1
                if not grafia_emissivel(pad, count):
                    continue                        # nunca EMITIR grafia ambigua
                custo = len(marcador_periodico(count, pad, body_lines[pos])) + 1
                economia = sum(len(body_lines[pos + k]) + 1 for k in range(count)) - custo
                if economia > 0 and (melhor is None or economia > melhor[0]):
                    melhor = (economia, count, pad)
            if melhor is None:
                pos += 1
            else:
                runs.append((pos, melhor[1], melhor[2], melhor[0]))
                pos += melhor[1]
        i = max(fim, i + 1)
    return runs


def _is_uniform_delta(deltas: list[int]) -> int | None:
    """Se todos deltas sao iguais e nao-zero, retorna esse int. Senao None.

    Permite emit marker M10 compat `*N+delta|` em caso uniforme.
    """
    if all(d == deltas[0] and d != 0 for d in deltas):
        return deltas[0]
    return None


def compact_body(
    body_lines: list[str], pares: list[list[int] | None] | None = None
) -> tuple[list[str], list[dict]]:
    runs = detect_seq_runs(body_lines, pares)
    if not runs:
        return body_lines, []
    out = []
    info = []
    i = 0
    run_idx = 0
    while i < len(body_lines):
        if run_idx < len(runs) and runs[run_idx][0] == i:
            start, end, deltas = runs[run_idx]
            count = end - start
            # M10 compat: se uniforme, emit `*N+delta|` single
            uniform = _is_uniform_delta(deltas)
            if uniform is not None:
                sign = "+" if uniform >= 0 else ""
                marker = f"*{count}{sign}{uniform}|{body_lines[start]}"
            else:
                # ADR-0016 multi-delta: `*N+d1,d2,...|template`
                # Primeiro delta: sinal explicit (parser usa '+' ou '-' como
                # separador count/deltas). Quando negativo, str() ja' inclui '-';
                # quando >= 0, prependa '+'.
                deltas_str = ",".join(str(d) for d in deltas)
                sign_prefix = "+" if deltas[0] >= 0 else ""
                marker = f"*{count}{sign_prefix}{deltas_str}|{body_lines[start]}"
            out.append(marker)
            info.append(
                {
                    "start_line": start + 1,
                    "end_line": end,
                    "count": count,
                    "deltas": list(deltas),
                    "uniform_delta": uniform,
                    "template": body_lines[start],
                    "savings": sum(len(body_lines[k]) + 1 for k in range(start, end))
                    - (len(marker) + 1),
                }
            )
            i = end
            run_idx += 1
        else:
            out.append(body_lines[i])
            i += 1
    return out, info


def _info_periodico(pos, count, pad, economia, template) -> dict:
    """Mesmo dicionario do uniforme + `periodo`. `uniform_delta=None` distingue os dois
    sem quebrar quem ja' le' o formato de hoje (ADR-0040)."""
    return {
        "start_line": pos + 1,
        "end_line": pos + count,
        "count": count,
        "deltas": list(pad),
        "uniform_delta": None,
        "periodo": len(pad),
        "template": template,
        "savings": economia,
    }


def compact_body_periodico(
    body_lines: list[str], runs, pares: list[list[int] | None]
) -> tuple[list[str], list[dict]]:
    """Monta o corpo com os runs periodicos; o resto vai pro `compact_body` de hoje.

    FLOOR POR FRAGMENTO: o core aplica `compact_body` no corpo INTEIRO e so' aceita se
    encolher (o `min` no fim do `encode`) — e' assim que ele recusa o `*2+d|` espurio de
    17 B que substitui 16 B de linhas cruas. Reaplicar `compact_body` por fragmento SEM
    piso ressuscitava exatamente esses: bastava UM run periodico legitimo pra o candidato
    vencer o `min()` carregando dezenas deles de carona. E a conta nao fecha no corpo —
    cada `*2+d|` come uma corrida de escape, que valia mais 1 B de ganho de POLARIDADE
    (ADR-0035, camada de borda aplicada depois): medido, corpo 9 B MENOR embarcando wire
    19 B MAIOR, 963 regressoes em 28.985 casos parametricos. Com o piso: 0 regressoes.

    Vide `T-FLOOR-POS-POLARIDADE`: o `min()` mede o corpo CANONICO, mas o que embarca e'
    `polariza(corpo)`. Vale pro core de hoje; o periodico so' tornou visivel.
    """
    saida: list[str] = []
    info: list[dict] = []
    pend: list[str] = []
    pend_ini = 0
    i = 0
    ri = 0

    def _drena() -> None:
        nonlocal pend, pend_ini
        if not pend:
            return
        # `pares` do fragmento e' a fatia exata do array global (mesmos pares adjacentes)
        linhas_p, info_p = compact_body(pend, pares[pend_ini:pend_ini + len(pend) - 1])
        if sum(len(x) + 1 for x in linhas_p) > sum(len(x) + 1 for x in pend):
            saida.extend(pend)                      # piso: nao piorar o fragmento
            pend = []
            return
        saida.extend(linhas_p)
        for reg in info_p:
            r = dict(reg)
            r["start_line"] += pend_ini             # reancora no corpo INTEIRO: sem isto
            r["end_line"] += pend_ini               # a telemetria aponta linha errada
            info.append(r)
        pend = []

    while i < len(body_lines):
        if ri < len(runs) and runs[ri][0] == i:
            _drena()
            pos, count, pad, eco = runs[ri]
            saida.append(marcador_periodico(count, pad, body_lines[pos]))
            info.append(_info_periodico(pos, count, pad, eco, body_lines[pos]))
            i += count
            ri += 1
        else:
            if not pend:
                pend_ini = i
            pend.append(body_lines[i])
            i += 1
    _drena()
    info.sort(key=lambda r: r["start_line"])
    return saida, info


def expand_periodic_marker(linha: str) -> list[str] | None:
    """Expande `*N~d1,...,dp|template` (ADR-0040). `None` se nao e' marcador periodico
    CANONICO — a linha volta pro caminho de hoje e termina no erro canonico do core.

    `return None` em vez de `raise`: preserva o contrato de `expand_seq_marker` (None =
    nao e' marcador) e nao poe em risco valores legitimos que imitem a grafia, que fazem
    round-trip pela heuristica de separador do ADR-0007.
    """
    if not linha.startswith("*"):
        return None
    bar = linha.find("|")
    if bar == -1:
        return None
    head = linha[1:bar]
    til = head.find("~")
    if til <= 0 or not head[:til].isdigit():
        return None
    try:
        pad = [int(x) for x in head[til + 1:].split(",")]
    except ValueError:
        return None
    count = int(head[:til])
    if not grafia_emissivel(pad, count):
        return None
    template = linha[bar + 1:]
    out = [template]
    curr = template
    for k in range(1, count):
        curr = shift_escape_digits(curr, pad[(k - 1) % len(pad)])
        out.append(curr)
    return out


def expand_seq_marker(linha: str) -> list[str] | None:
    """Expande `*N+delta|template` (M10 compat), `*N+d1,d2,...|template` (ADR-0016) ou
    `*N~d1,...,dp|template` (periodico, ADR-0040).

    O ramo periodico vem PRIMEIRO: um head como `5~1,-4` seria mal-parseado pela varredura
    de `+`/`-` abaixo. Estar aqui dentro (e nao num passe separado antes do decode) e' o
    que mantem a pre-checagem do teto valendo pro marcador novo — `_contador_declarado`
    ja' le' `*2000000~1,2|` corretamente. Medido: rejeitar a bomba custa 0,03 ms aqui,
    contra 2,473 s se a expansao acontecesse antes do laco que checa o teto.
    """
    periodico = expand_periodic_marker(linha)
    if periodico is not None:
        return periodico
    if not linha.startswith("*"):
        return None
    bar = linha.find("|")
    if bar == -1:
        return None
    head = linha[1:bar]
    plus_pos = -1
    for k in range(len(head)):
        if head[k] in ("+", "-") and k > 0:
            plus_pos = k
            break
    if plus_pos == -1:
        return None
    try:
        count = int(head[:plus_pos])
    except ValueError:
        return None
    delta_str = head[plus_pos:]

    # ADR-0016: multi-delta format `+d1,d2,d3,d4`
    if "," in delta_str:
        try:
            deltas = [int(d) for d in delta_str.split(",")]
        except ValueError:
            return None
        delta_arg = deltas
    else:
        # M10 compat: single int
        try:
            delta_arg = int(delta_str)
        except ValueError:
            return None

    template = linha[bar + 1 :]
    out = [template]
    curr = template
    for _ in range(1, count):
        curr = shift_escape_digits(curr, delta_arg)
        out.append(curr)
    return out


class HCCSeqRLE(M8AVirtualRefsSyntax):
    """HCC com seq-RLE near-identical via post-process.

    Encode: super().encode → detect runs → compact em `*N+delta|template`
    Decode: expand `*N+delta|` → super().decode
    """

    name = "M8-A-seq-rle"

    def __init__(self):
        super().__init__()
        self._seq_info: list[dict] = []

    def get_seq_info(self) -> list[dict]:
        return self._seq_info

    def encode(self, linhas, unicas, tokens_por_string, header):
        body_text = super().encode(linhas, unicas, tokens_por_string, header)
        # super().encode termina com exatamente UM '\n' extra ("\n".join(body)
        # + "\n"). Tirar so' esse — rstrip('\n') comia tambem os '\n' de valores
        # VAZIOS finais, perdendo-os no decode (len mismatch). Para body sem
        # vazios finais, [:-1] == rstrip (byte-canonical preservado).
        # Bug T-CODE-EMPTY-FRAG-INDEX-RT (2o modo: valor vazio no fim).
        body_lines = body_text[:-1].split("\n")
        # UM array de deltas para os DOIS detectores (ADR-0040): recomputa-lo custa 6,8 ms
        # num corpo de 1200 linhas, contra 1,6 ms de toda a logica de periodo.
        pares = deltas_pares(body_lines)

        compacted, info = compact_body(body_lines, pares)
        compactado = "\n".join(compacted) + "\n"

        # FLOOR: o marcador `*N+delta|` tem CUSTO, e ate' agora ele nao
        # entrava na decisao — `compact_body` era aplicado incondicionalmente. Em dado sem
        # cadencia o detector acha pares espurios e o marcador fica MAIOR que as linhas que
        # substitui:
        #     *2+498217|\168116   17 B     vs     \168116 + \666333 + 2 LF   16 B
        # Medido (16 casos): piorava em 7; ~8-9% do corpo em ruido de
        # alta cardinalidade (ruido 1e6 n=1000: 8573 -> 7854). Onde ganha segue ganhando
        # (seq n=1000: 4890 -> 31) porque isto e' `min`, nunca-pior por construcao.
        #
        # Por CORPO, nao por marcador: a granularidade fina foi medida e deu resultado
        # IDENTICO em todos os casos (dentro de um corpo os marcadores sao uniformemente
        # bons ou uniformemente ruins) — nao paga a complexidade.
        #
        # Mesmo padrao do `min()` que ja' governa o multi-col (`min(tcf, raw, dict, split)`)
        # e a escolha de modo do single-col tipado.
        #
        # ADR-0040: o periodico entra como TERCEIRO candidato do MESMO `min()`. A ORDEM e'
        # load-bearing — `min()` devolve o PRIMEIRO minimo, entao `compactado` vem antes de
        # `body_text` para preservar a preferencia de hoje no EMPATE (o criterio antigo era
        # `<=`, nao `<`), e o periodico vem por ultimo para so' vencer com margem estrita.
        # Sem essa ordem, o wire de dado SEM nenhuma periodicidade era reescrito.
        candidatos: list[tuple[str, list[dict]]] = [(compactado, info), (body_text, [])]
        runs_p = detect_periodic_runs(body_lines, pares)
        if runs_p:
            linhas_p, info_p = compact_body_periodico(body_lines, runs_p, pares)
            candidatos.append(("\n".join(linhas_p) + "\n", info_p))

        # `_seq_info` e' do candidato VENCEDOR — vazio so' quando o corpo cru vence.
        # Antes o info era fixado antes da decisao, e o `seq_rle_runs` reportava runs que
        # o wire nao tinha (ou zerava com o wire cheio de marcador). O canal e' publico:
        # `encoder.py` -> `SideOutputs.seq_rle_runs` -> `schema.seq_rle_runs_count`.
        corpo, self._seq_info = min(
            candidatos, key=lambda t: len(t[0].encode("utf-8"))
        )
        return corpo

    def decode(self, tcf_text, max_length=None):
        expanded_lines = []
        # TETO tambem AQUI, nao so' no core: o seq-RLE expande `*N+d|` ANTES do
        # super().decode(), entao um `*99999999+1|x` estouraria a memoria antes de
        # qualquer guard la' embaixo. Pre-checa o contador SEM materializar.
        limite = resolve_max_length(max_length)
        # Contrato LF-only: FONTE ÚNICA em split_lf_body (BUG-14 + dedup C0 —
        # o fix vivia duplicado aqui e no decode do syntax; ver
        # T-CODE-CORE-CONSOLIDATE D1).
        raw_lines = split_lf_body(tcf_text)

        for raw in raw_lines:
            # NAO strip: expand_seq_marker preserva o whitespace do template
            # (`linha[bar+1:]`). O `raw.strip()` antigo comia o whitespace final do
            # valor no template -> RT FAIL em trailing-space + seq-RLE
            # (T-CODE-RT-EDGES bug 1; mesma classe do fix "NAO strip" de 2026-05-18 no
            # decode do syntax.py, que o wrapper seq-RLE reintroduziu).
            # Markers comecam com '*' na posicao 0 (compact_body nunca poe leading
            # whitespace); linha vazia/whitespace-only/nao-marker -> expand=None -> raw.
            # `startswith` inline ANTES da chamada: este laco e' caminho quente (roda por
            # linha em todo decode) e so' marcador comeca com '*' — evita call por linha.
            if limite and raw[:1] == "*":
                pedido = _contador_declarado(raw)
                if pedido and len(expanded_lines) + pedido > limite:
                    raise ValueError(
                        estouro_max_length(len(expanded_lines) + pedido, limite))
            expanded = expand_seq_marker(raw)
            if expanded is not None:
                expanded_lines.extend(expanded)
            else:
                expanded_lines.append(raw)
        expanded_text = "\n".join(expanded_lines) + "\n"
        return super().decode(expanded_text, max_length=max_length)

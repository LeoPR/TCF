"""Detector periódico v5 — o candidato DEFINITIVO de weld. `python detector_v5.py`

A v4 fechou o custo (O(n·P), +35%). A caçada adversarial (5 lentes, 12 achados brutos em
`outputs/cacada-achados-brutos.json`) apontou **cinco** defeitos distintos. A v5 é a v4
com os dois que faltavam:

    #1 teto de memória não cobria o marcador novo   -> v4 (expand dentro do core)   OK
    #2 detector O(n²)                               -> v4 (fronteira + mudanca[])    OK
    #3 FLOOR invertia o desempate do core           -> v4 (min(hoje, cru, cand))     OK
    #4 telemetria `seq_rle_runs` zerava CALADA      -> **v5**
    #5 pad aceita sufixo morto (não-injetivo)       -> **v5**

## #4 — a telemetria tem de descrever o corpo que FOI emitido

O achado é pior do que "o mecanismo novo não reporta": o protótipo zerava `_seq_info`
mesmo quando o corpo emitido era **byte-idêntico ao do core** e cheio de `*N+d|`. Medido
pelos caçadores: `seq_rle_runs` caía de 1 → 0 em `diario`, `semanal`, `ips`… O canal é
público e tem consumidores reais (`encoder.py:726` → `schema.py:192` →
`scripts/schema_gadget/sideouts_quality.py`, além dos próprios labs).

Duas armadilhas no conserto, as duas tratadas aqui:
  (a) o info tem de ser o do candidato **vencedor** — vazio quando o cru vence;
  (b) os trechos não-periódicos são compactados por `compact_body(pend)`, que devolve
      `start_line`/`end_line` **relativos ao pedaço**. Sem reancorar no corpo inteiro, a
      telemetria aponta linhas erradas — troca um silêncio por uma mentira.

## #5 — o pad não pode ter cauda morta

Com `count=3` só `pad[0]` e `pad[1]` são lidos: `*3~1,4,9|` decodifica **idêntico** a
`*3~1,4|`. Infinitas grafias válidas pro mesmo dado — o oposto do byte-canonical que o
projeto usa como gate. E `*4~1,3,1,3|` == `*4~1,3|` (pad que é repetição de um período
menor). A v5 rejeita as duas formas na EXPANSÃO (o decode recusa a grafia não-canônica) e
nunca as emite na DETECÇÃO.

Rejeitar = `return None`, que devolve a linha ao caminho de hoje e termina no erro
canônico do core (`contador RLE invalido`). Escolhido em vez de `raise` porque preserva o
contrato de `expand_seq_marker` (None = não é marcador) e não põe em risco valores
legítimos que imitem a grafia — que fazem RT hoje pela heurística de separador do ADR-0007.
"""
from __future__ import annotations

import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

import tcf.composicional.hcc_seqrle as H  # noqa: E402
from tcf.composicional.hcc_seqrle import (  # noqa: E402
    HCCSeqRLE,
    compact_body,
    compare_for_seq,
    shift_escape_digits,
)

MAX_PERIODO = 24


# ───────────────────────────── gramática do marcador ─────────────────────────────

def marcador(count, padrao, template):
    return f"*{count}~{','.join(str(d) for d in padrao)}|{template}"


def _periodo_minimo(seq):
    """Menor `q` tal que `seq[k] == seq[k % q]` para todo k. É o pad canônico de `seq`."""
    n = len(seq)
    for q in range(1, n + 1):
        if all(seq[k] == seq[k % q] for k in range(n)):
            return q
    return n


def _pad_canonico(pad, count):
    """#5 — a grafia tem de ser a ÚNICA que produz este dado.

    `count` linhas consomem exatamente `count-1` deltas, e o que o decode LÊ é
    `seq = [pad[k % len(pad)] for k in range(count-1)]`. Duas grafias com o mesmo `seq`
    produzem o mesmo dado — então a canônica é a de **período mínimo** de `seq`:

        *3~1,4,9|    seq=[1,4]   -> mínimo 2, pad tem 3  -> cauda MORTA, recusa
        *4~1,3,1,3|  seq=[1,3,1] -> mínimo 2, pad tem 4  -> repetição, recusa
        *4~1,3,1|    seq=[1,3,1] -> mínimo 2, pad tem 3  -> EXTENSÃO, recusa
        *600~1,1|    seq=[1,1,…] -> mínimo 1             -> uniforme (`*N+d|`), recusa
        *4~1,3|      seq=[1,3,1] -> mínimo 2 == len(pad) -> CANÔNICA

    A forma "repetição exata" (`[1,3,1,3]`) é caso particular da extensão — por isso a
    checagem é uma só. `mínimo == 1` cobre a guarda 1 (pad uniforme) de graça.
    """
    if not pad or count < 2:
        return False
    if len(pad) > count - 1:
        return False                      # mais deltas do que o decode consome
    seq = [pad[k % len(pad)] for k in range(count - 1)]
    q = _periodo_minimo(seq)
    return q == len(pad) and q >= 2


def _grafia_emissivel(pad, count):
    """Canônica **e** produzível pelo encoder — o guard de RE-EMISSÃO.

    `_pad_canonico` garante injetividade (uma grafia por dado). Isto garante o outro
    lado: o decode não aceita mais do que o encode emite. O detector só emite com DOIS
    ciclos completos (`L >= 2p`, logo `count-1 >= 2p`); sem esta linha, `*4~1,3|` —
    que nenhum encoder TCF produz — decodificaria calado.

    Precedente direto: o `DataIsoSpec` recusa `20191204` porque `fromisoformat` aceita
    mais do que `isoformat` emite (`d.isoformat() != v`). Mesma assimetria, mesma cura.
    """
    return _pad_canonico(pad, count) and count - 1 >= 2 * len(pad)


# ───────────────────────────── detecção (v4 + guarda #5) ─────────────────────────────

def deltas_da_coluna(body_lines):
    """O array que os DOIS detectores consomem. No weld, `detect_seq_runs` computa isto
    de qualquer jeito — compartilhar é parte do weld (6,8 ms num corpo de 1200)."""
    out = []
    for a, b in zip(body_lines, body_lines[1:]):
        v = compare_for_seq(a, b)
        out.append(v[0] if v is not None and len(v) == 1 else None)
    return out


def detecta_periodico(lines, d):
    """Runs `(start, count, pad, economia)` com período p >= 2. O(n · MAX_PERIODO)."""
    n, m = len(lines), len(d)

    # O(n): distancia ate' a proxima MUDANCA de delta. p <= mudanca[k] => pad uniforme.
    mudanca = [0] * m
    for k in range(m - 1, -1, -1):
        mudanca[k] = 1 if (k == m - 1 or d[k] != d[k + 1]) else mudanca[k + 1] + 1

    runs, i = [], 0
    while i < n - 1:
        if d[i] is None:
            i += 1
            continue
        fim = i
        while fim < n - 1 and d[fim] is not None:
            fim += 1
        pos = i
        while pos < fim:
            melhor = None
            for p in range(max(2, mudanca[pos] + 1), min(MAX_PERIODO, fim - pos) + 1):
                pad = d[pos:pos + p]
                L = p
                while pos + L < fim and d[pos + L] == pad[L % p]:
                    L += 1
                if L < 2 * p:                       # dois ciclos completos
                    continue
                count = L + 1
                if not _pad_canonico(pad, count):   # #5: nunca EMITIR grafia ambigua
                    continue
                custo = len(marcador(count, pad, lines[pos])) + 1
                economia = sum(len(lines[pos + k2]) + 1 for k2 in range(count)) - custo
                if economia > 0 and (melhor is None or economia > melhor[0]):
                    melhor = (economia, count, pad)
            if melhor is None:
                pos += 1
            else:
                runs.append((pos, melhor[1], melhor[2], melhor[0]))
                pos += melhor[1]
        i = max(fim, i + 1)
    return runs


# ───────────────────────────── expansão (espelho + guarda #5) ─────────────────────────────

def expande_periodico(linha):
    """`*N~d1,…,dp|template` -> N linhas. `None` se não é marcador periódico canônico."""
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
    if not _grafia_emissivel(pad, count):
        return None                       # grafia nao-canonica -> erro canonico do core
    template = linha[bar + 1:]
    out, curr = [template], template
    for k in range(1, count):
        curr = shift_escape_digits(curr, pad[(k - 1) % len(pad)])
        out.append(curr)
    return out


# ───────────────────────────── a camada (encode) ─────────────────────────────

def _info_periodico(pos, count, pad, economia, template):
    """Mesmo dicionário do uniforme + `periodo`. `uniform_delta=None` distingue."""
    return {"start_line": pos + 1, "end_line": pos + count, "count": count,
            "deltas": list(pad), "uniform_delta": None, "periodo": len(pad),
            "template": template, "savings": economia}


def compacta_com_periodico(body_lines, runs):
    """Devolve `(linhas, info)` — com o info REANCORADO no corpo inteiro (#4b)."""
    saida, info, pend, pend_ini, i, ri = [], [], [], 0, 0, 0

    def _drena():
        nonlocal pend, pend_ini
        if not pend:
            return
        linhas_p, info_p = compact_body(pend)
        saida.extend(linhas_p)
        for reg in info_p:
            r = dict(reg)
            r["start_line"] += pend_ini      # start_line e' 1-based no core
            r["end_line"] += pend_ini
            info.append(r)
        pend = []

    while i < len(body_lines):
        if ri < len(runs) and runs[ri][0] == i:
            _drena()
            pos, count, pad, eco = runs[ri]
            saida.append(marcador(count, pad, body_lines[pos]))
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


class SeqRLEPeriodicoV5(HCCSeqRLE):
    """O weld como ele iria pro core."""

    def encode(self, linhas, unicas, tokens_por_string, header):
        body_text = super(HCCSeqRLE, self).encode(linhas, unicas, tokens_por_string, header)
        body_lines = body_text[:-1].split("\n")

        compactado, info_hoje = compact_body(body_lines)
        hoje = "\n".join(compactado) + "\n"

        runs = detecta_periodico(body_lines, deltas_da_coluna(body_lines))
        candidatos = [(hoje, info_hoje), (body_text, [])]   # ORDEM = desempate do core
        if runs:
            linhas_p, info_p = compacta_com_periodico(body_lines, runs)
            candidatos.append(("\n".join(linhas_p) + "\n", info_p))

        corpo, self._seq_info = min(candidatos, key=lambda t: len(t[0].encode("utf-8")))
        return corpo


# ───────────────────────────── instalação da camada ─────────────────────────────

_ORIG_EXPAND = H.expand_seq_marker


def _expand_com_periodico(linha):
    p = expande_periodico(linha)
    return p if p is not None else _ORIG_EXPAND(linha)


def liga():
    """Instala a v5. O expand entra NO CORE (preserva a pré-checagem do teto, #1)."""
    import tcf.decoder as _d
    import tcf.encoder as _e
    H.expand_seq_marker = _expand_com_periodico
    _e.HCCSeqRLE = _d.HCCSeqRLE = SeqRLEPeriodicoV5


def desliga():
    import tcf.decoder as _d
    import tcf.encoder as _e
    H.expand_seq_marker = _ORIG_EXPAND
    _e.HCCSeqRLE = _d.HCCSeqRLE = HCCSeqRLE


if __name__ == "__main__":
    print(__doc__.split("\n\n")[0])
    print("\nEsta é a biblioteca da v5. A verificação dos 5 achados roda em:")
    print("    python v5_verificacao.py")

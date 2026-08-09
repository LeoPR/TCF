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


def _pad_minimo(pad):
    """Menor `d` que gera `pad` por repetição: `pad[k] == pad[k % d]` para todo k.

    v6 — calculado **do `pad`**, não de uma sequência de `count-1` elementos
    materializada. Com `count-1 >= 2·len(pad)` garantido antes (Fine–Wilf), o período
    mínimo da sequência expandida é exatamente este. Custo: O(p²) <= 24² = 576, zero
    alocação proporcional ao `count`.
    """
    p = len(pad)
    for d in range(1, p + 1):
        if p % d == 0 and all(pad[k] == pad[k % d] for k in range(p)):
            return d
    return p


def _grafia_emissivel(pad, count):
    """A grafia é aceita? Canônica (injetiva) **e** produzível pelo encoder.

    ORDEM É DEFESA (v6, achado da 2ª caçada). Tudo aqui é O(1) ou O(p²) com p <= 24, e
    **nada** é proporcional ao `count` declarado pelo wire. A v5 fazia o contrário —
    materializava `count-1` elementos e rodava um laço O(n²) sobre um pad sem teto —
    e virava amplificador: 48,8 KB de wire hostil custavam **126,87 s** (16.881× o
    tempo da camada desligada, que dá o MESMO erro em 7,5 ms); 22 B custavam 17,25 s e
    85 MB. O gate que eu criei pra fechar a canonicidade abriu um vetor de recursos.

    As três condições, na ordem em que se defendem:

      1. `len(pad) <= MAX_PERIODO` — espelha o teto do DETECTOR. O encoder nunca emite
         período maior que 24; sem esta linha o pad do wire não tinha teto nenhum.
      2. `count - 1 >= 2·len(pad)` — RE-EMISSÃO, e é O(1). O detector só emite com dois
         ciclos completos (`L >= 2p`), então `*4~1,3|` não é produzível por encoder TCF.
         Mesmo guard do `DataIsoSpec` (`d.isoformat() != v`, que recusa `20191204`
         porque `fromisoformat` aceita mais do que `isoformat` emite).
      3. `_pad_minimo(pad) == len(pad) >= 2` — INJETIVIDADE. Duas grafias com a mesma
         sequência produzem o mesmo dado; a canônica é a de período mínimo:

             *5~1,4,9|    cauda morta (o 9 nunca é lido)      recusa
             *9~1,3,1,3|  repetição de [1,3]                  recusa
             *5~1,4,1|    extensão parcial de [1,4]           recusa
             *600~1,1|    mínimo 1 = `*N+d|` disfarçado       recusa
             *5~1,4|      mínimo 2 == len(pad)                ACEITA

         `mínimo == 1` cobre a guarda de pad uniforme (ADR-0040) de graça.
    """
    if not pad or count < 2:
        return False
    if len(pad) > MAX_PERIODO:            # (1) teto: espelha o detector
        return False
    if count - 1 < 2 * len(pad):          # (2) re-emissão, O(1), ANTES do resto
        return False
    d = _pad_minimo(pad)                  # (3) injetividade, O(p²) com p <= 24
    return d == len(pad) and d >= 2


def _pad_canonico(pad, count):
    """Compat do lab: a canonicidade agora vive dentro de `_grafia_emissivel`."""
    return _grafia_emissivel(pad, count)


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
        """FLOOR POR FRAGMENTO (v6, achado da 2ª caçada).

        A v5 reaplicava `compact_body` em cada fragmento **sem piso**. O core aplica no
        corpo inteiro e só aceita se encolher (`hcc_seqrle.py:329`) — é assim que ele
        recusa o `*2+d|` espúrio que o próprio comentário do FLOOR descreve. Sem o piso,
        bastava UM run periódico legítimo pra o candidato vencer o `min()` **carregando
        de carona** dezenas de marcadores que o core tinha recusado.

        E a conta não fecha no corpo: cada `*2+d|` desses come uma corrida de escape, que
        valia mais 1 B de ganho de POLARIDADE — camada de borda aplicada depois. Medido
        pelos caçadores: um corpo 9 B menor embarcando 19 B maior; 963 regressões em
        28 985 casos paramétricos, pior +29 B. Com o piso: **0 regressões e 4905 B a
        MENOS** no total — melhor e nunca-pior.

        Isolamento importante: o marcador periódico sozinho já era nunca-pior (0/28 985).
        O defeito era inteiro deste `_drena`.
        """
        nonlocal pend, pend_ini
        if not pend:
            return
        linhas_p, info_p = compact_body(pend)
        cru = sum(len(x) + 1 for x in pend)
        compacto = sum(len(x) + 1 for x in linhas_p)
        if compacto > cru:                   # o mesmo piso do core, por fragmento
            saida.extend(pend)
            pend = []
            return
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

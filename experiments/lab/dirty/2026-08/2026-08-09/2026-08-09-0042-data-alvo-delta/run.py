"""Data — o alvo DELTA: transform de coluna × seq-RLE periódico. `python run.py`

Lab próprio do vencedor da triagem (lab `0024`, H6+H2). A pergunta de DESIGN:

    O spec ordinal soldado depende do `*N+M|` (delta UNIFORME entre linhas). Regimes
    com delta PERIÓDICO ([1,1,1,1,3] dos dias úteis) ou IRREGULAR (espalhado-ordenado)
    ficam na mesa. Dois candidatos de design:

    D1  transform de COLUNA (delta-coluna): a nature emite [1ª data absoluta, depois
        deltas] e o core comprime a coluna transformada. Wire NORMAL (sem gramática
        nova); precisa de protocolo novo (transform per-coluna + tag no header pra
        desfazer no decode). Aqui: transform naive + encode() REAL da coluna
        transformada + un-delta naive no decode. RT conferido contra o input.

    D2  seq-RLE PERIÓDICO (ideia do owner, anterior a esta rodada): o marcador aceita
        delta que CICLA entre linhas. Gramática nova (#TCF.8); protocolo intocado; vale
        pra QUALQUER coluna numérica. Aqui: mede o CANDIDATO da nature (encode_value
        REAL por valor → encode() REAL da coluna de ordinais) e re-compacta o corpo com
        o detector periódico, reusando compare_for_seq/shift_escape_digits do core
        (IMPORTADOS, não copiados). Marcador dirty `*N~d1,...,dp|template`. RT: expande
        os `~` de volta, decode() REAL, e decode_value REAL de cada payload.
        (sintaxe `~` é PROVISÓRIA do lab: a vírgula já é do multi-delta per-run
        ADR-0016, e `~` real é operador composicional — sintaxe final é assunto do weld)

LIÇÕES DA 1ª RODADA (corrigidas aqui, registradas no result.md):
  - medir o D2 sobre o wire EMITIDO repete o erro do H1 — quando o spec recusa, o
    candidato ordinal nem aparece; o periódico muda o próprio candidato. Medir o
    CANDIDATO sempre.
  - `_lcg % 30` é quasi-periódico (bits baixos do LCG têm período curto) — o
    "espalhado" não era irregular. Trocado por hash (sha256 por índice).

Controles: diário/semanal (uniforme — D2 tem de empatar byte com o wire de hoje);
desordenado (delta negativo irregular); k-baixo implícito nos D1 (rota bN aparece).

`src/tcf` NÃO é tocado. Tudo `min()` no espírito: candidato entra, nunca substitui.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402
from tcf.composicional.hcc_seqrle import (  # noqa: E402
    compare_for_seq,
    expand_seq_marker,
    shift_escape_digits,
)
from tcf.natures import SPEC_DATA_ISO, decode_value, encode_value  # noqa: E402

for x in ("inputs", "intermediates", "outputs"):
    (RAIZ / x).mkdir(parents=True, exist_ok=True)

B = _dt.date(2026, 1, 1)
N = 600
MAXP = 24  # período máximo que o detector tenta (mensal=12, quinzenal-ano=24)
AJUSTE_D1 = len(" :data-delta")  # header que o weld do transform pagaria
AJUSTE_D2 = len(" :data-iso")    # header do spec que o candidato pagaria


def _escreve(p, t):
    p.write_text(t, encoding="utf-8", newline="")


def _rnd(i, mod, salt=""):
    """Irregular DE VERDADE (sha256 por índice) — o LCG tinha bits baixos periódicos."""
    h = hashlib.sha256(f"{salt}:{i}".encode()).digest()
    return int.from_bytes(h[:4], "big") % mod


# ───────────────────────────── geradores de regime ─────────────────────────────

def dias_uteis(n, feriados=0):
    out, d, uteis = [], B, 0
    while len(out) < n:
        if d.weekday() < 5:
            uteis += 1
            if not (feriados and uteis % 21 == 0):
                out.append(d)
        d += _dt.timedelta(days=1)
    return out


def mensal_dia1(n):
    out, y, m = [], 2000, 1
    for _ in range(n):
        out.append(_dt.date(y, m, 1))
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return out


def quinzenal(n):
    out, y, m, dia = [], 2026, 1, 1
    while len(out) < n:
        out.append(_dt.date(y, m, dia))
        if dia == 1:
            dia = 15
        else:
            dia, m = 1, m + 1
            if m == 13:
                m, y = 1, y + 1
    return out


def espalhado(n, ordenado=True):
    ds, d = [], B
    for i in range(n):
        d = d + _dt.timedelta(days=_rnd(i, 30, "esp") + 1)  # 1..30 irregular
        ds.append(d)
    if not ordenado:
        ds = sorted(ds, key=lambda x: _rnd(x.toordinal(), 1 << 30, "perm"))
    return ds


def com_ruido(ds, pct):
    """Troca pct% das posições por lixo realista (a válvula do spec)."""
    vals = [d.isoformat() for d in ds]
    alvo = max(1, len(vals) * pct // 100)
    pos, i = [], 0
    while len(pos) < alvo:
        p = _rnd(i, len(vals), "ruido")
        if p not in pos:
            pos.append(p)
        i += 1
    for p in pos:
        vals[p] = "s/d"
    return vals


def ids_turno(n):
    """Coluna numérica NÃO-data com passo periódico [10,10,10,50] (generalidade do D2)."""
    out, v, ciclo = [], 700000, [10, 10, 10, 50]
    for i in range(n):
        out.append(str(v))
        v += ciclo[i % 4]
    return out


# ──────────────────── D1 — transform de coluna (delta-coluna) ────────────────────

def d1_transforma(vals):
    """[1º válido = ordinal absoluto; depois deltas vs anterior VÁLIDO; inválido = _literal].

    A MESMA válvula do spec: valor que não parseia canônico passa cru e NÃO entra na
    cadeia (decisão naive registrada: delta em relação ao anterior válido)."""
    col, prev = [], None
    for v in vals:
        try:
            d = _dt.date.fromisoformat(v)
            ok = d.isoformat() == v
        except (ValueError, TypeError):
            ok = False
        if not ok:
            col.append("_" + v)
            continue
        o = d.toordinal()
        col.append(str(o) if prev is None else str(o - prev))
        prev = o
    return col


def d1_reconstroi(col):
    out, prev = [], None
    for c in col:
        if c.startswith("_"):
            out.append(c[1:])
            continue
        n = int(c)
        o = n if prev is None else prev + n
        out.append(_dt.date.fromordinal(o).isoformat())
        prev = o
    return out


def d1_mede(vals, rotulo):
    col = d1_transforma(vals)
    w = encode(col)
    assert decode(w) == col, f"{rotulo}: RT do wire delta-coluna quebrou"
    assert d1_reconstroi(col) == vals, f"{rotulo}: un-delta nao devolveu o input"
    return {"bytes": len(w.encode()) + AJUSTE_D1, "rota": w.split("\n")[0], "wire": w}


def d1_mede_generico(vals, rotulo):
    """ids_turno: mesmo transform sem a parte de data (delta de inteiros)."""
    col = [vals[0]] + [str(int(vals[i]) - int(vals[i - 1])) for i in range(1, len(vals))]
    w = encode(col)
    assert decode(w) == col, f"{rotulo}: RT quebrou"
    rec, prev = [], None
    for c in col:
        n = int(c)
        v = n if prev is None else prev + n
        rec.append(str(v))
        prev = v
    assert rec == vals, f"{rotulo}: un-delta nao devolveu o input"
    return {"bytes": len(w.encode()) + AJUSTE_D1, "rota": w.split("\n")[0], "wire": w}


# ──────────────────── D2 — seq-RLE periódico (sobre o CANDIDATO real) ────────────────────
#
# ACHADO da sondagem: coluna digit-heavy roteia pro fallback RAW (`#TCF.8!!`) — linhas
# são dígitos CRUS (sem `\`) e o seq-RLE raw compacta `*2+1|739617` sem escape. O
# comparador do core (compare_for_seq) é só do modo escapado; o espelho raw é daqui.

def _delta_par(a, b, raw):
    """Delta ESCALAR entre duas linhas; None se o par não encadeia.
    Restrição do esboço: um run de dígito por linha (ordinal/inteiro). Multi-run
    periódico = produto cruzado com o ADR-0016, fica registrado como aberto."""
    if raw:
        if a.isdigit() and b.isdigit() and a != b:
            return int(b) - int(a)
        return None
    v = compare_for_seq(a, b)
    return v[0] if v is not None and len(v) == 1 else None


def _shift(t, d, raw):
    if not raw:
        return shift_escape_digits(t, d)
    s = str(int(t) + d)
    return s.zfill(len(t)) if len(s) < len(t) else s


def _expande_existente(linha, raw):
    """Expande os marcadores `*N+d|` que o CORE já emitiu (modo raw ou escapado)."""
    if not raw:
        return expand_seq_marker(linha)
    if not linha.startswith("*"):
        return None
    bar = linha.find("|")
    if bar == -1:
        return None
    head = linha[1:bar]
    pos = next((k for k in range(1, len(head)) if head[k] in "+-"), -1)
    if pos == -1:
        return None
    try:
        count, delta = int(head[:pos]), int(head[pos:])
    except ValueError:
        return None
    t = linha[bar + 1:]
    if not t.isdigit():
        return None
    out = [t]
    for _ in range(1, count):
        t = _shift(t, delta, raw=True)
        out.append(t)
    return out


def _deltas_encadeados(lines, raw):
    return [_delta_par(a, b, raw) for a, b in zip(lines, lines[1:])]


def _marcador(count, padrao, template):
    return f"*{count}~{','.join(str(d) for d in padrao)}|{template}"


def detecta_periodicos(lines, raw, min_ciclos=1):
    """Greedy: pra cada cadeia de deltas válidos, escolhe o período p (1..MAXP) de maior
    economia. p=1 (uniforme) NÃO emite — é território do mecanismo existente.

    DEGENERESCÊNCIA (achado do lab): com cobertas = p+1 o marcador não repete nada —
    vira LISTA literal de deltas (o transform de coluna expresso em gramática).
    `min_ciclos=2` exige 2 ciclos completos = periodicidade de verdade; `min_ciclos=1`
    permite a forma-lista. Medimos as duas separadas."""
    d = _deltas_encadeados(lines, raw)
    n, runs, i = len(lines), [], 0
    while i < n - 1:
        if d[i] is None:
            i += 1
            continue
        j = i
        while j < n - 1 and d[j] is not None:
            j += 1
        cadeia = d[i:j]
        melhor = None  # (economia, p, cobertas, padrao)
        for p in range(1, min(MAXP, len(cadeia)) + 1):
            pad = cadeia[:p]
            L = p
            while L < len(cadeia) and cadeia[L] == pad[L % p]:
                L += 1
            cobertas = L + 1
            if cobertas < min_ciclos * p + 1:
                continue
            custo = len(_marcador(cobertas, pad, lines[i])) + 1
            economia = sum(len(lines[i + k]) + 1 for k in range(cobertas)) - custo
            if melhor is None or economia > melhor[0]:
                melhor = (economia, p, cobertas, pad)
        if melhor is None:
            i += 1
            continue
        economia, p, cobertas, pad = melhor
        if p >= 2 and economia > 0:
            runs.append((i, cobertas, pad))
            i += cobertas
        else:
            i += 1  # uniforme/sem ganho: o _compact_uniforme cuida depois
    return runs


def _compact_uniforme(lines, raw):
    """Re-aplica o mecanismo EXISTENTE (`*N+d|`) nas linhas restantes, pulando
    marcadores. Mesmo greedy do detect_seq_runs do core, no modo da rota."""
    out, i, n = [], 0, len(lines)
    while i < n:
        if lines[i].startswith("*"):
            out.append(lines[i])
            i += 1
            continue
        j = i
        delta = None
        while j < n - 1 and not lines[j + 1].startswith("*"):
            v = _delta_par(lines[j], lines[j + 1], raw)
            if v is None or (delta is not None and v != delta):
                break
            delta = v
            j += 1
        if j > i:
            count = j - i + 1
            marcador = f"*{count}{'+' if delta >= 0 else ''}{delta}|{lines[i]}"
            if len(marcador) + 1 <= sum(len(lines[i + k]) + 1 for k in range(count)):
                out.append(marcador)
                i += count
                continue
        out.append(lines[i])
        i += 1
    return out


def expande_periodico(linha, raw):
    bar = linha.find("|")
    if not linha.startswith("*") or bar == -1 or "~" not in linha[:bar]:
        return None
    head, template = linha[1:bar], linha[bar + 1:]
    c_str, pat_str = head.split("~", 1)
    count, pad = int(c_str), [int(x) for x in pat_str.split(",")]
    out, curr = [template], template
    for k in range(1, count):
        curr = _shift(curr, pad[(k - 1) % len(pad)], raw)
        out.append(curr)
    return out


def d2_mede(vals, rotulo, e_data=True):
    """Candidato REAL (encode_value por valor → encode() da coluna) + periódico por cima.
    Mede DUAS variantes: estrito (>=2 ciclos = período de verdade) e lista (livre)."""
    if e_data:
        col = [encode_value(SPEC_DATA_ISO, v)[0] for v in vals]
        ajuste = AJUSTE_D2
    else:
        col, ajuste = vals, 0  # coluna numérica crua: o periódico é do CORE, sem nature
    w = encode(col)
    assert decode(w) == col, f"{rotulo}: RT do candidato quebrou"
    hdr, _, corpo = w.partition("\n")
    construido = False
    if hdr in ("#TCF.8", "#TCF.8!!"):
        raw = hdr == "#TCF.8!!"
        corpo_lns = corpo[:-1].split("\n")
    else:
        # A rota vencedora de HOJE não é corpo-de-linhas (ex.: split `%`). O periódico
        # soldado competiria DENTRO do min() como candidato raw — construímos esse
        # candidato e o decoder REAL valida que ele é um wire legítimo.
        hdr, raw, construido = "#TCF.8!!", True, True
        corpo_lns = list(col)
        if decode(hdr + "\n" + "\n".join(corpo_lns) + "\n") != col:
            return {"bytes": None, "nota": f"candidato raw construido nao decodou ({rotulo})"}
        w_base = hdr + "\n" + "\n".join(_compact_uniforme(corpo_lns, True)) + "\n"
        assert decode(w_base) == col, f"{rotulo}: candidato raw compactado nao decodou"
        w = w_base
    lines = []
    for ln in corpo_lns:
        e = _expande_existente(ln, raw)
        lines.extend(e) if e else lines.append(ln)

    def _monta(min_ciclos):
        runs = detecta_periodicos(lines, raw, min_ciclos=min_ciclos)
        out, i, ri = [], 0, 0
        while i < len(lines):
            if ri < len(runs) and runs[ri][0] == i:
                start, cobertas, pad = runs[ri]
                out.append(_marcador(cobertas, pad, lines[i]))
                i += cobertas
                ri += 1
            else:
                out.append(lines[i])
                i += 1
        return _compact_uniforme(out, raw), runs

    res = {"rota": hdr + (" (construido)" if construido else ""), "ajuste": ajuste}
    for nome, mc in (("estrito", 2), ("lista", 1)):
        out, runs = _monta(mc)
        novo = hdr + "\n" + "\n".join(out) + "\n"
        ganhou = len(novo.encode()) < len(w.encode())
        # RT SEMPRE: expande os `~`, decoder REAL devolve a coluna, decode_value REAL
        # devolve os valores — os dois níveis
        volta = []
        for ln in out:
            e = expande_periodico(ln, raw)
            volta.extend(e) if e else volta.append(ln)
        col_rt = decode(hdr + "\n" + "\n".join(volta) + "\n")
        assert col_rt == col, f"{rotulo}/{nome}: RT do periódico (nível coluna) quebrou"
        if e_data:
            assert [decode_value(SPEC_DATA_ISO, c) for c in col_rt] == vals, \
                f"{rotulo}/{nome}: RT do periódico (nível valor) quebrou"
        res[nome] = {"bytes": min(len(novo.encode()), len(w.encode())) + ajuste,
                     "ganhou_no_corpo": ganhou, "runs": len(runs),
                     "periodos": sorted({len(p) for _, _, p in runs})}
        if nome == "estrito" and ganhou:
            res["wire"] = novo
    return res


# ───────────────────────────────── harness ─────────────────────────────────

def caso(rotulo, vals, e_data=True, salva=False):
    vals = json.loads(json.dumps(vals))  # higiene json-lib-like
    _escreve(RAIZ / "inputs" / f"{rotulo}--json-lib-like.json",
             json.dumps(vals, ensure_ascii=False, indent=0))
    c0 = encode(vals)
    assert decode(c0) == vals, f"{rotulo}: RT sem spec quebrou"
    reg = {"caso": rotulo, "n": len(vals), "C0_sem_spec": len(c0.encode())}
    c1 = None
    if e_data:
        c1 = encode(vals, nature=SPEC_DATA_ISO)
        assert decode(c1) == vals, f"{rotulo}: RT com spec quebrou"
        reg["C1_com_spec"] = len(c1.encode())
    d1 = d1_mede(vals, rotulo) if e_data else d1_mede_generico(vals, rotulo)
    reg["D1_delta_coluna"] = d1["bytes"]
    reg["D1_rota"] = d1["rota"]
    d2 = d2_mede(vals, rotulo, e_data=e_data)
    reg["D2_periodo_estrito"] = d2.get("estrito", {}).get("bytes")
    reg["D2L_forma_lista"] = d2.get("lista", {}).get("bytes")
    reg["D2_detalhe"] = {k: v for k, v in d2.items() if k not in ("wire",)}
    candidatos = {"C0": reg["C0_sem_spec"], "C1": reg.get("C1_com_spec"),
                  "D1": d1["bytes"], "D2": reg["D2_periodo_estrito"],
                  "D2L": reg["D2L_forma_lista"]}
    validos = {k: v for k, v in candidatos.items() if v is not None}
    reg["floor"] = min(validos.values())
    reg["vencedor"] = min(validos, key=validos.get)
    trilha = {"caso": rotulo,
              "delta_prefixo_20": None,
              "d2_estrito": d2.get("estrito"),
              "d2_lista": d2.get("lista"),
              "rota_candidato_d2": d2.get("rota"),
              "nota_d2": d2.get("nota")}
    if e_data:
        ords = []
        for v in vals:
            try:
                ords.append(_dt.date.fromisoformat(v).toordinal())
            except (ValueError, TypeError):
                pass
        trilha["delta_prefixo_20"] = [ords[k + 1] - ords[k] for k in range(min(20, len(ords) - 1))]
    _escreve(RAIZ / "intermediates" / f"{rotulo}--trilha.json",
             json.dumps(trilha, ensure_ascii=False, indent=1))
    if salva:
        if c1 is not None:
            _escreve(RAIZ / "outputs" / f"{rotulo}--com-spec.tcf", c1)
        _escreve(RAIZ / "outputs" / f"{rotulo}--delta-coluna.tcf", d1["wire"])
        if "wire" in d2:
            _escreve(RAIZ / "outputs" / f"{rotulo}--seqrle-periodico.wire.txt", d2["wire"])
        rt = {"input_n": len(vals),
              "rt_wire_real_sem_spec": decode(c0) == vals,
              "rt_wire_real_com_spec": (decode(c1) == vals) if c1 else None,
              "rt_delta_coluna_undelta": True,          # asserts acima garantem
              "rt_seqrle_periodico_2_niveis": reg["D2_periodo_estrito"] is not None,
              "primeiros_5": vals[:5], "ultimos_2": vals[-2:]}
        _escreve(RAIZ / "outputs" / f"{rotulo}.roundtrip.json",
                 json.dumps(rt, ensure_ascii=False, indent=1))
    return reg


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    R = []

    # controles uniformes — D2 tem de empatar com o wire de hoje
    R.append(caso("diario-controle", [(B + _dt.timedelta(days=i)).isoformat() for i in range(N)]))
    R.append(caso("semanal-controle", [(B + _dt.timedelta(days=7 * i)).isoformat() for i in range(N)]))
    assert R[0]["D2_periodo_estrito"] == R[0]["C1_com_spec"], "diario: periódico mexeu no uniforme!"

    # o prêmio: período
    R.append(caso("uteis", [d.isoformat() for d in dias_uteis(N)], salva=True))
    R.append(caso("uteis-feriado-mensal", [d.isoformat() for d in dias_uteis(N, feriados=1)], salva=True))
    R.append(caso("mensal-dia1", [d.isoformat() for d in mensal_dia1(N)], salva=True))
    R.append(caso("quinzenal", [d.isoformat() for d in quinzenal(N)]))

    # irregular: onde o periódico NÃO deve alcançar e o delta-coluna sim
    R.append(caso("espalhado-ordenado", [d.isoformat() for d in espalhado(N)], salva=True))
    R.append(caso("espalhado-desordenado", [d.isoformat() for d in espalhado(N, ordenado=False)]))

    # ruído: a válvula sob os dois designs
    R.append(caso("uteis-ruido-1pct", com_ruido(dias_uteis(N), 1)))
    R.append(caso("uteis-ruido-5pct", com_ruido(dias_uteis(N), 5)))

    # generalidade: coluna numérica NÃO-data (o D2 é do CORE, não da nature)
    R.append(caso("ids-turno-nao-data", ids_turno(N), e_data=False, salva=True))

    # escala: o periódico é ~O(1) em marcadores; o delta-coluna cresce com n
    R.append(caso("uteis-n6000", [d.isoformat() for d in dias_uteis(6000)]))

    _escreve(RAIZ / "outputs" / "medicoes.json", json.dumps(R, ensure_ascii=False, indent=1))

    linhas = ["| caso | n | C0 sem spec | C1 com spec | D1 delta-col | D2 período | D2L lista | floor | vence |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in R:
        linhas.append(
            f"| {r['caso']} | {r['n']} | {r['C0_sem_spec']} | {r.get('C1_com_spec', '—')} "
            f"| {r['D1_delta_coluna']} | {r['D2_periodo_estrito'] or 'n/a'} "
            f"| {r['D2L_forma_lista'] or 'n/a'} | {r['floor']} | {r['vencedor']} |")
    tabela = "\n".join(linhas)
    _escreve(RAIZ / "outputs" / "medicoes.md",
             "# Medições — alvo DELTA (bytes de wire; D1 +12 B e D2 +10 B de header hipotético)\n\n"
             "D2 = seq-RLE periódico ESTRITO (>=2 ciclos completos). D2L = a forma degenerada\n"
             "descoberta no lab: 1 ciclo só = LISTA literal de deltas no marcador.\n\n"
             + tabela + "\n\n"
             + "Detalhe D2 por caso:\n\n"
             + "\n".join(f"- `{r['caso']}`: {json.dumps(r['D2_detalhe'], ensure_ascii=False)}" for r in R)
             + "\n\nRotas D1 (o delta-coluna muda a ROTA do core — k baixo cai no bN):\n\n"
             + "\n".join(f"- `{r['caso']}`: `{r['D1_rota']}`" for r in R) + "\n")
    print(tabela)
    print("\nOK — RT conferido em todos os casos (asserts, 2 níveis no D2).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

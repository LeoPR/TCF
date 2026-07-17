"""ESTUDO do escape D_json — injetividade, fuzz e adversarial ANTES de tocar o core."""
from __future__ import annotations

import itertools
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3] / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

from proto import BS, LF, esc_name, esc_val, unesc_name, unesc_val  # noqa: E402
from tcf import decode as _dec_col  # noqa: E402
from tcf import encode as _enc_col  # noqa: E402


def main():
    (HERE / "outputs").mkdir(exist_ok=True)
    out = ["ESTUDO — escape D_json (valores + nomes). Injetividade > fuzz > adversarial.", ""]
    ok_all = True

    # ---------- (1) INJETIVIDADE EXAUSTIVA: todas as strings de len<=3 sobre o alfabeto crítico
    out.append("(1) INJETIVIDADE EXAUSTIVA (alfabeto crítico {\\, n, LF, a}, len 0..3):")
    alfa = [BS, "n", LF, "a"]
    vistos_v, vistos_n, colisoes = {}, {}, []
    total = 0
    for k in range(0, 4):
        for tup in itertools.product(alfa, repeat=k):
            s = "".join(tup)
            total += 1
            # valor
            e = esc_val(s)
            if unesc_val(e) != s:
                colisoes.append(("val-rt", s)); ok_all = False
            if e in vistos_v and vistos_v[e] != s:
                colisoes.append(("val-colisao", s, vistos_v[e])); ok_all = False
            vistos_v[e] = s
            # nome (o core rejeita LF-inicial? não: nome é livre; só o vazio tem regra)
            en = esc_name(s)
            if unesc_name(en) != s:
                colisoes.append(("nome-rt", s)); ok_all = False
            if en in vistos_n and vistos_n[en] != s:
                colisoes.append(("nome-colisao", s, vistos_n[en])); ok_all = False
            vistos_n[en] = s
    out.append(f"    {total} strings · RT valor {len(vistos_v)}/{total} · RT nome {len(vistos_n)}/{total}"
               f" · colisões: {colisoes if colisoes else 'NENHUMA'}")

    # ---------- (2) O ESCAPE PASSA PELO L1? (é o ponto: não tocar o L1)
    out.append("")
    out.append("(2) O valor escapado atravessa o L1 intacto (o ponto do desenho):")
    casos = [f"x{LF}y", f"a{BS}b", f"a{BS}nb", "x", BS, LF, f"{BS}{LF}", f"{BS}n",
             f"{LF}{LF}", f"{BS}123", "café 中文", f"{BS}{BS}{LF}", "", "linha1" + LF + "linha2"]
    for v in casos:
        e = esc_val(v)
        try:
            rt_l1 = (_dec_col(_enc_col([e])) == [e])
        except Exception as ex:                                  # noqa: BLE001
            rt_l1 = f"{type(ex).__name__}"
        rt_tot = rt_l1 is True and unesc_val(e) == v
        ok_all &= bool(rt_tot)
        out.append(f"    {v!r:22} -> {e!r:26} L1={str(rt_l1):5} total={rt_tot}")

    # ---------- (3) FUZZ seedado
    out.append("")
    out.append("(3) FUZZ seedado (strings aleatórias sobre o alfabeto crítico + unicode):")
    rng = random.Random(20260717)
    pool = [BS, "n", LF, "a", "z", ",", ":", "#", "?", "[", "]", "{", "}", " ", "é", "中", "🎉", "0"]
    okv = okn = 0
    N = 20000
    for _ in range(N):
        s = "".join(rng.choice(pool) for _ in range(rng.randint(0, 12)))
        if unesc_val(esc_val(s)) == s:
            okv += 1
        if unesc_name(esc_name(s)) == s:
            okn += 1
    out.append(f"    valor {okv}/{N} · nome {okn}/{N}")
    ok_all &= (okv == N and okn == N)

    # ---------- (4) ADVERSARIAL: o unescape recusa o que o encoder NUNCA emite?
    out.append("")
    out.append("(4) ADVERSARIAL — unescape ESTRITO (blob estrangeiro nunca vira valor calado):")
    probes_v = [(BS, "backslash solto (dangling)"), (BS + "x", "escape invalido"),
                (BS + "t", "escape de outro alfabeto (tab-style)"), ("a" + BS, "dangling no fim"),
                (BS + "u0041", "escape unicode (nao emitimos)")]
    for p, rot in probes_v:
        try:
            r = unesc_val(p)
            out.append(f"    [FALHA-SILENCIOSA!] valor {p!r} -> {r!r}  ({rot})")
            ok_all = False
        except ValueError as e:
            out.append(f"    [fail-loud OK] valor {p!r:10} {rot:34} {str(e)[:34]}")
    probes_n = [(BS + "q", "escape nao-estrutural"), (BS, "dangling"), (BS + "z" + "a", "\\z + lixo")]
    for p, rot in probes_n:
        try:
            r = unesc_name(p)
            out.append(f"    [FALHA-SILENCIOSA!] nome {p!r} -> {r!r}  ({rot})")
            ok_all = False
        except ValueError as e:
            out.append(f"    [fail-loud OK] nome  {p!r:10} {rot:34} {str(e)[:34]}")

    # ---------- (5) O SENTINELA DE CORRUPÇÃO CONTINUA DE PÉ?
    out.append("")
    out.append("(5) O sentinela 'nome vazio no header' SOBREVIVE (nome vazio legítimo vira \\z):")
    out.append(f"    esc_name('')        = {esc_name('')!r}   -> meta NUNCA tem nome vazio literal")
    out.append(f"    unesc_name('')      = tratado pelo PARSE do core como corrupção (inalterado)")
    out.append(f"    esc_name('z')       = {esc_name('z')!r}      (nome 'z' real NÃO colide com \\z)")
    out.append(f"    esc_name(BS+'z')    = {esc_name(BS + 'z')!r}   (nome '\\z' real -> backslash dobrado)")
    ok_all &= (esc_name("z") == "z" and esc_name(BS + "z") == BS + BS + "z")

    # ---------- (6) CUSTO
    out.append("")
    out.append("(6) CUSTO em bytes (só paga quem tem '\\' ou LF):")
    reais = ["Ana Souza", "user@mail.com", "SP", "2026-07-17", "R$ 1.234,56", "path/to/file",
             "C:" + BS + "temp" + BS + "x", "linha1" + LF + "linha2"]
    for s in reais:
        e = esc_val(s)
        d = len(e.encode()) - len(s.encode())
        out.append(f"    {s!r:26} -> +{d}B {'(inalterado)' if d == 0 else ''}")

    out += ["", ("VEREDITO: escape injetivo (exaustivo len<=3 + 20k fuzz), atravessa o L1 sem tocá-lo,"
                 if ok_all else "HÁ FALHA — revisar desenho."),
            "unescape estrito recusa blob estrangeiro, sentinela de corrupção preservado.",
            "Fecha 3 lacunas de D_json: LF em valor · LF em nome · nome vazio."]
    (HERE / "outputs" / "00-estudo.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print("\n".join(out))
    assert ok_all, "estudo falhou"


if __name__ == "__main__":
    main()

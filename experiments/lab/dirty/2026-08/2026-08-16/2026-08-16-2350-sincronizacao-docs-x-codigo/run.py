"""Verificador da sincronizacao docs x codigo (auditoria 2026-08-16).

PERGUNTA: cada afirmacao que os docs vivos fazem sobre o comportamento do TCF
ainda e' verdade no codigo de hoje?

METODO: nao le' o doc e acredita. Para cada afirmacao, RODA o codigo e compara.
Cada caso grava input + output + roundtrip em `outputs/`, e o veredito vai pro
`RESULTADO.md`. Quem quiser conferir roda `python run.py` e le' os arquivos.

O QUE ISSO **NAO** E': prova de que os docs estao completos. E' prova de que as
afirmacoes ENUMERADAS AQUI batem com o codigo. O que nao esta' na lista nao foi
verificado — e a lista declara o que ficou de fora (secao "NAO COBERTO").
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))

OUT = AQUI / "outputs"
IN = AQUI / "inputs"
for d in (OUT, IN):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode, view, build_schema, SPEC_CPF, SPEC_CNPJ, SPEC_IP  # noqa: E402
from tcf.natures import classify_value, encode_value, decode_value  # noqa: E402
from tcf.side_outputs import SideOutputs  # noqa: E402

RESULTADOS: list[dict] = []


def grava_caso(nome: str, entrada, wire: str | None, *, extra: dict | None = None):
    """Grava input/output/roundtrip em disco. O diff E' o assert (feedback do owner)."""
    (IN / f"{nome}.json").write_text(
        json.dumps(entrada, ensure_ascii=False, indent=2, default=str), encoding="utf-8", newline=""
    )
    if wire is not None:
        ext = ".tcf"
        (OUT / f"{nome}{ext}").write_text(wire, encoding="utf-8", newline="")
        try:
            volta = decode(wire)
        except Exception as e:  # noqa: BLE001
            volta = f"<{type(e).__name__}: {e}>"
        (OUT / f"{nome}.roundtrip.json").write_text(
            json.dumps(volta, ensure_ascii=False, indent=2, default=str), encoding="utf-8", newline=""
        )
        if extra:
            (OUT / f"{nome}.meta.json").write_text(
                json.dumps(extra, ensure_ascii=False, indent=2, default=str), encoding="utf-8", newline=""
            )
        return volta
    return None


def afirma(doc: str, claim: str, fn):
    """Roda `fn` -> (ok: bool, observado: str). Registra o veredito."""
    try:
        ok, observado = fn()
    except Exception as e:  # noqa: BLE001
        ok, observado = False, f"EXCECAO {type(e).__name__}: {e}\n{traceback.format_exc(limit=2)}"
    RESULTADOS.append({"doc": doc, "claim": claim, "ok": bool(ok), "observado": str(observado)})
    print(f"  [{'OK ' if ok else 'FALHA'}] {doc}: {claim}")
    if not ok:
        print(f"          observado: {observado}")


# ---------------------------------------------------------------- os casos

def caso_none_preservado():
    orig = ["x", None, "y"]
    w = encode(orig)
    volta = grava_caso("none_preservado", orig, w)
    return volta == orig, f"decode={volta!r} wire={w!r}"


def caso_view_import():
    return callable(view), f"tcf.view = {view!r}"


def caso_nome_coluna_escapa():
    orig = {"id,bad": ["1", "2"], "email=principal": ["3", "4"]}
    w = encode(orig)
    volta = grava_caso("nome_coluna_escapa", orig, w)
    header = w.splitlines()[0]
    esperado = r"#TCF.8M!3=id\,bad,!email\=principal"
    return (volta == orig and header == esperado), f"header={header!r} rt={volta == orig}"


def caso_nome_coluna_so_lf_proibido():
    try:
        encode({"a\nb": ["1", "2"]})
        return False, "aceitou nome com \\n (deveria fail-loud)"
    except ValueError as e:
        return "\\n" in str(e) or "\n" in str(e), f"ValueError: {str(e)[:80]}"


def caso_tutorial_hello():
    data = ["abc", "abcd", "abcde"]
    w = encode(data)
    grava_caso("tutorial_hello", data, w)
    esperado = "#TCF.8\nabc\n1d\n1,2e\n"
    return w == esperado, f"wire={w!r}"


def caso_tutorial_hello_bytes():
    data = ["abc", "abcd", "abcde"]
    w = encode(data)
    raw = sum(len(s) + 1 for s in data)
    tcf = len(w.encode("utf-8"))
    # o doc agora afirma: raw 15, tcf 19, ratio 126.7%, economia -4
    return (raw, tcf) == (15, 19), f"raw={raw} tcf={tcf} ratio={tcf/raw*100:.1f}%"


def caso_tutorial_emails():
    emails = ["joao@gmail.com", "joao@hotmail.com", "maria@gmail.com",
              "maria@hotmail.com", "pedro@gmail.com", "pedro@hotmail.com"]
    w = encode(emails)
    grava_caso("tutorial_emails", emails, w)
    raw = sum(len(e) + 1 for e in emails)
    tcf = len(w.encode("utf-8"))
    return (raw, tcf) == (100, 71), f"raw={raw} tcf={tcf} ratio={tcf/raw*100:.1f}%"


def caso_tutorial_multicol():
    table = {"id": ["1", "2", "3"], "name": ["Alice", "Bob", "Charlie"]}
    w = encode(table)
    volta = grava_caso("tutorial_multicol", table, w)
    esperado = "#TCF.8M!5=id,!name\n1\n2\n3Alice\nBob\nCharlie"
    return (w == esperado and volta == table), f"wire={w!r}"


def caso_tutorial_view():
    table = {"cidade": ["SP", "SP", "RJ"], "valor": ["10", "20", "30"]}
    w = encode(table)
    grava_caso("tutorial_view", table, w)
    v = view(w)
    s = v.where("cidade", "SP").sum("valor")
    return s == 30.0, f"sum={s!r} touched={v.report()['touched']!r}"


def caso_natures_cpf_sem_filtro():
    col = ["111.444.777-35", "529.982.247-25", "111.444.777-35"]
    w = encode(col)
    grava_caso("natures_cpf_sem_filtro", col, w)
    b = len(w.encode("utf-8"))
    esperado = "#TCF.8!!\n111.444.777-35\n529.982.247-25\n^1\n"
    return (b == 42 and w == esperado), f"bytes={b} wire={w!r}"


def caso_natures_cpf_com_filtro():
    col = ["111.444.777-35", "529.982.247-25", "111.444.777-35"]
    w0 = encode(col)
    w1 = encode(col, nature=SPEC_CPF)
    grava_caso("natures_cpf_com_filtro", col, w1)
    b0, b1 = len(w0.encode("utf-8")), len(w1.encode("utf-8"))
    ratio = b1 / b0 * 100
    esperado = "#TCF.8 :cpf\n%gc\\9g\n\\2y/h-\n^1\n"
    ok = b1 == 29 and w1 == esperado and abs(ratio - 69.0) < 0.05
    return ok, f"bytes={b1} ratio={ratio:.1f}% wire={w1!r}"


def caso_natures_classify():
    esperados = {
        "111.444.777-35": "compressible",
        "111.444.777-99": "check_invalid",
        "11144477735": "format_unmasked",
        "111-444-777-35": "format_mismatch",
    }
    obtidos = {v: classify_value(SPEC_CPF, v) for v in esperados}
    return obtidos == esperados, f"{obtidos}"


def caso_natures_fallback():
    enc, st = encode_value(SPEC_CPF, "111.444.777-99")
    volta = decode_value(SPEC_CPF, enc)
    ok = enc == "_111.444.777-99" and st == "check_invalid" and volta == "111.444.777-99"
    return ok, f"enc={enc!r} status={st!r} volta={volta!r}"


def caso_natures_multi_e_ip_e_cnpj():
    tab = {"id": ["001", "002", "003"],
           "cpf": ["111.444.777-35", "529.982.247-25", "invalid-cpf"],
           "ip": ["192.168.1.1", "10.0.0.1", "10.0.0.2"]}
    w = encode(tab, nature_per_col={"cpf": SPEC_CPF, "ip": SPEC_IP})
    volta = grava_caso("natures_multi", tab, w)
    cnpjs = ["11.222.333/0001-81", "34.028.316/0001-00", "11.222.333/0001-81"]
    wc = encode(cnpjs, nature=SPEC_CNPJ)
    grava_caso("natures_cnpj", cnpjs, wc)
    ok = volta == tab and decode(wc) == cnpjs
    return ok, f"multi_rt={volta == tab} cnpj_rt={decode(wc) == cnpjs}"


def caso_inspect_multicol_bytes():
    data = {"id": ["1", "2", "3", "4"], "name": ["alice", "bob", "charlie", "alice"]}
    side = SideOutputs()
    w = encode(data, side_outputs=side)
    mi = side.multi_info
    grava_caso("inspect_multicol", data, w, extra={"multi_info": mi})
    obtido = (mi["total_bytes"], mi["header_bytes"], mi["body_bytes"])
    return obtido == (46, 18, 28), f"total/header/body = {obtido} (doc afirma (46, 18, 28))"


def caso_inspect_build_schema():
    data = {"id": ["1", "2", "3", "4"], "name": ["alice", "bob", "charlie", "alice"]}
    s = build_schema(data)
    obtido = (s.n_rows, s.n_cols, s.total_bytes, s.header_bytes, s.body_bytes)
    return obtido == (4, 2, 46, 18, 28), f"{obtido} (doc afirma (4, 2, 46, 18, 28))"


def caso_denso_b1_b2_bB():
    casos = {
        "b1": ([True, False] * 12, "#TCF.8b118"),
        "b2": ([True, False, None, True] * 6, "#TCF.8b218"),
        "bB": ([True, "abc", False], "#TCF.8bB23"),
    }
    linhas = []
    todos_ok = True
    for nome, (col, header_esp) in casos.items():
        w = encode(col)
        volta = grava_caso(f"denso_{nome}", col, w)
        h = w.splitlines()[0]
        ok = h == header_esp and volta == col
        todos_ok &= ok
        linhas.append(f"{nome}: header={h!r} rt={volta == col}")
    return todos_ok, " | ".join(linhas)


def caso_uniao_fora_de_bool_str_falha():
    falhas = []
    for col in ([1, "abc", 2], [True, 1, False]):
        try:
            encode(col)
            falhas.append(f"{col!r} ACEITOU (deveria fail-loud)")
        except Exception:  # noqa: BLE001
            pass
    return not falhas, "; ".join(falhas) or "int+str e bool+int seguem fail-loud"


def caso_H_esta_vivo():
    d = [{"a": 1, "b": {"c": 2}}, {"a": 3, "b": {"c": 4}}]
    w = encode(d)
    volta = grava_caso("H_vivo", d, w)
    return volta == d and w.startswith("#TCF.8H"), f"header={w.splitlines()[0]!r} rt={volta == d}"


def caso_tags_b_n_s_decodam():
    obs = []
    ok = True
    for col in ([True, False, True], [1, 2, 3], [1.5, 2.5]):
        w = encode(col)
        try:
            r = decode(w)
            ok &= r == col
            obs.append(f"{w.splitlines()[0]!r}->rt={r == col}")
        except Exception as e:  # noqa: BLE001
            ok = False
            obs.append(f"{w.splitlines()[0]!r}->{type(e).__name__}")
    for wire in ("#TCF.8s\nabc\ndef\n", "#TCF.8s!!\nabc\ndef\n"):
        try:
            r = decode(wire)
            ok &= r == ["abc", "def"]
            obs.append(f"s-explicita {wire!r}->{r!r}")
        except Exception as e:  # noqa: BLE001
            ok = False
            obs.append(f"s-explicita {wire!r}->{type(e).__name__}")
    return ok, " | ".join(obs)


def caso_legado_67_cortado():
    obs = []
    ok = True
    for wire in ("#TCF.7 M\nid,name\n1\n2", "#TCF.6 M\nid,name\n1\n2"):
        try:
            decode(wire)
            ok = False
            obs.append(f"{wire.splitlines()[0]!r} DECODOU (deveria fail-loud)")
        except ValueError as e:
            obs.append(f"{wire.splitlines()[0]!r} -> ValueError ok")
            ok &= "legado" in str(e).lower() or "nao suportado" in str(e).lower()
    return ok, " | ".join(obs)


def caso_bracket_nao_e_skipado():
    orig = ["a", "]", "b", "["]
    w = encode(orig)
    volta = grava_caso("bracket_e_valor", orig, w)
    return volta == orig, f"decode={volta!r}"


# --- as 3 correcoes da RAIZ (2026-08-17, pos-verificacao adversarial) ---

def caso_as_tres_nao_operacoes():
    """output-convention: nao strip, nao skipar vazia, nao skipar bracket.

    A revisao de 2026-08-16 tirou o skip de bracket e DEIXOU o `.strip()` no bloco —
    reintroduzindo a 2a perda dentro da propria correcao. Este caso pina as TRES juntas.
    """
    casos = {
        "nao_strip": ["a ", " b", "c"],
        "nao_strip_so_espacos": ["  ", "x"],
        "nao_skip_vazia": ["a", "", "b"],
        "nao_skip_bracket": ["a", "]", "b", "["],
    }
    ok, obs = True, []
    for nome, orig in casos.items():
        w = encode(orig)
        volta = grava_caso(f"tres_naos_{nome}", orig, w)
        ok &= volta == orig
        obs.append(f"{nome}={volta == orig}")
    # e o loop-do-doc-antigo (com strip) DEVE divergir — se nao divergir, o caso e' vazio
    w = encode(["a ", " b", "c"])
    corpo = w.split("\n", 1)[1]
    doc_antigo = [l.strip() for l in corpo.split("\n")][:-1]
    divergiu = doc_antigo != ["a ", " b", "c"]
    obs.append(f"loop-antigo-diverge={divergiu} ({doc_antigo!r})")
    return ok and divergiu, " | ".join(obs)


def caso_nove_discriminadores():
    """AGENTS.md/MAP.md: 9 valores, com `s` e `C` decode-only."""
    from tcf import SPEC_CPF
    import random
    emitidos = {}
    for rot, d in (
        ("\\n", ["abc", "abcd", "abcde"]),
        ("M", {"id": ["1", "2"], "n": ["a", "b"]}),
        ("H", [{"a": 1, "b": {"c": 2}}, {"a": 3, "b": {"c": 4}}]),
        ("b", [True, False] * 12),
        ("n", [1, 2, 3]),
    ):
        h = encode(d).splitlines()[0]
        emitidos[h[6:7] or "\\n"] = rot
    emitidos[encode(["111.444.777-35", "529.982.247-25", "111.444.777-35"],
                    nature=SPEC_CPF).splitlines()[0][6:7]] = "spec"
    random.seed(11)
    col = [f"v{random.randrange(4)}" for _ in range(300)]
    emitidos[encode(col).splitlines()[0][6:7]] = "bN"

    # `s` decoda mas NAO e' emitida
    s_decoda = decode("#TCF.8s\nabc\ndef\n") == ["abc", "def"]
    s_emitida = any(encode(c).splitlines()[0][6:7] == "s"
                    for c in (["a", "b"], ["abc", "abcd"], ["x"], ["a" * 300]))
    # `C` esta' no dispatch do decoder mas NAO e' emitido (ADR-0036: so' `B` sai por default)
    from tcf.decoder import _DISCS_BN
    from tcf.composicional.dominio_bn import DISC_LOTE
    c_no_dispatch = "C" in _DISCS_BN and DISC_LOTE == "C"
    c_emitido = False
    for n in (50, 200, 800, 3000):
        for k in (2, 5, 16, 120):
            cc = [f"v{random.randrange(k)}" for _ in range(n)]
            if encode(cc).splitlines()[0][6:7] == "C":
                c_emitido = True
    universo = set(emitidos) | {"s", "C"}
    ok = (len(universo) == 9 and s_decoda and not s_emitida
          and c_no_dispatch and not c_emitido)
    return ok, (f"emitidos={sorted(emitidos)} (7) + decode-only {{'s','C'}} = {len(universo)} | "
                f"s_decoda={s_decoda} s_emitida={s_emitida} | "
                f"C_no_dispatch={c_no_dispatch} C_emitido={c_emitido}")


def caso_carimbo_e_default_orfao_e_escape():
    """AGENTS.md dizia 'nada = orfao (default, 0 B)'. ADR-0034 inverteu isso."""
    d = ["abc", "abcd"]
    w_def = encode(d)
    w_esc = encode(d, stamp=False)
    grava_caso("carimbo_default", d, w_def)
    ok = (w_def.startswith("#TCF.8") and not w_esc.startswith("#TCF.8")
          and decode(w_def) == d and decode(w_esc) == d
          and len(w_def.encode()) - len(w_esc.encode()) == 7)
    return ok, (f"default={w_def!r} ({len(w_def.encode())} B) | "
                f"stamp=False -> {w_esc!r} ({len(w_esc.encode())} B) | delta=7 B")


def caso_contrato_pre_1_0_do_api():
    """api.md:79-82 mandava 3 de 4 pro `.8H`. Todas ficam no single-col."""
    esperado = {
        "[]":              ("#TCF.8",     []),
        "{}":              ("#TCF.8H#E",  {}),
        "[1,2,3]":         ("#TCF.8n",    [1, 2, 3]),
        "[1,None]":        ("#TCF.8n",    [1, None]),
        "[True,None]":     ("#TCF.8b",    [True, None]),
        "['x',None]":      ("#TCF.8",     ["x", None]),
        "{'a':['x',None]}": ("#TCF.8H#O", {"a": ["x", None]}),
    }
    ok, obs = True, []
    for rot, (pref, val) in esperado.items():
        w = encode(val)
        h = w.splitlines()[0] if w.splitlines() else ""
        rt = decode(w)
        bate = h.startswith(pref) and rt == val
        ok &= bate
        obs.append(f"{rot}->{h!r}{'' if bate else ' *** '}")
    return ok, " | ".join(obs)


def caso_gates_byte_canonical():
    """Os 3 numeros que os docs agora afirmam, lidos do PROPRIO teste (nao daqui)."""
    import re
    alvos = {
        "D1-D9": (RAIZ / "tests/test_regression_v1_baseline.py", r"D1_D9_TOTAL\s*=\s*(\d+)", "1545"),
        "D17a": (RAIZ / "tests/test_regression_v1_baseline.py", r"D17A_INVARIANT\s*=\s*(\d+)", "300"),
        "real-world": (RAIZ / "tests/test_real_world_snapshots.py", r"REAL_WORLD_TOTAL\s*=\s*(\d+)", "89430"),
    }
    obs, ok = [], True
    for nome, (arq, pat, esperado) in alvos.items():
        m = re.search(pat, arq.read_text(encoding="utf-8"))
        achado = m.group(1) if m else "<nao achado>"
        ok &= achado == esperado
        obs.append(f"{nome}={achado} (doc afirma {esperado})")
    return ok, " | ".join(obs)


def caso_doc03_natures_e_failloud():
    """F6/DOC-03: o registry tem 5 natures, e id desconhecido e' FAIL-LOUD.

    A spec ensinava "nature (cpf/cnpj/ip)" e "id desconhecido -> cru + warning".
    As duas eram falsas desde os welds de `dt` (2026-08-08) e `ipad` (2026-08-14).
    """
    import tcf.natures as N
    from tcf.natures import _resolve_nature_id
    ids = sorted({getattr(getattr(N, k), "wire_id", None) for k in dir(N)
                  if k.startswith("SPEC_")} - {None})
    resolviveis = sorted(i for i in ids if _resolve_nature_id(i) is not None)
    esperado = ["cnpj", "cpf", "dt", "ip", "ipad"]

    falhou_alto = False
    try:
        decode("#TCF.8 :xyz" + chr(10) + "abc" + chr(10))
    except ValueError as e:
        falhou_alto = "registry core fechado" in str(e)
    ok = resolviveis == esperado and falhou_alto
    return ok, (f"registry={resolviveis} (esperado {esperado}) | "
                f"id desconhecido fail-loud={falhou_alto}")


def caso_doc03_exemplo_do_meta():
    """F6/DOC-03: o exemplo do meta era auto-contraditorio (size NA ULTIMA +
    comentario 'ultima sem size'), e perdia o `@` da 2a coluna."""
    t = {"uf": ["SP", "RJ", "MG", "SP"] * 4, "nome": ["Ana", "Bruno", "Carla", "Diego"] * 4}
    w_def = encode(t)
    w_sem = encode(t, min_header=False)
    grava_caso("doc03_meta_exemplo", t, w_def,
               extra={"min_header_False": w_sem.splitlines()[0]})
    l1d, l1s = w_def.splitlines()[0], w_sem.splitlines()[0]
    ok = (l1d == "#TCF.8M@1b=uf,@nome" and l1s == "#TCF.8M@1b=uf,@29=nome"
          and decode(w_def) == t and decode(w_sem) == t)
    return ok, f"default={l1d!r} | min_header=False={l1s!r}"


CASOS = [
    ("TCF-format.*", "None e' preservado, nao vira ''", caso_none_preservado),
    ("README.*", "`from tcf import view` existe", caso_view_import),
    ("how-to/encode-csv-file", "`,` e `=` em nome de coluna sao ESCAPADOS, nao proibidos", caso_nome_coluna_escapa),
    ("how-to/encode-csv-file", "so' `\\n` e' proibido em nome de coluna", caso_nome_coluna_so_lf_proibido),
    ("tutorials/getting-started", "Passo 1: wire tem o header `#TCF.8`", caso_tutorial_hello),
    ("tutorials/getting-started", "Passo 3: 15 raw -> 19 tcf (o TCF CRESCE aqui)", caso_tutorial_hello_bytes),
    ("tutorials/getting-started", "Passo 3b: emails 100 raw -> 71 tcf", caso_tutorial_emails),
    ("tutorials/getting-started", "Passo 4: wire multi-col", caso_tutorial_multicol),
    ("tutorials/getting-started", "Passo 5: view().where().sum() == 30.0", caso_tutorial_view),
    ("how-to/use-natures", "sem filtro: 42 B, grafia com polaridade", caso_natures_cpf_sem_filtro),
    ("how-to/use-natures", "com filtro: 29 B, ratio 69,0%", caso_natures_cpf_com_filtro),
    ("how-to/use-natures", "os 4 rotulos de classify_value", caso_natures_classify),
    ("how-to/use-natures", "fallback `_` + round-trip", caso_natures_fallback),
    ("how-to/use-natures", "CNPJ, IP e nature_per_col rodam", caso_natures_multi_e_ip_e_cnpj),
    ("how-to/inspect-compression", "multi-col: total/header/body = 46/18/28", caso_inspect_multicol_bytes),
    ("how-to/inspect-compression", "build_schema multi-col idem", caso_inspect_build_schema),
    ("reference/api", "tag `b` tem 3 modos: b1, b2, bB", caso_denso_b1_b2_bB),
    ("reference/api + json-equivalence", "uniao FORA de bool+str segue fail-loud", caso_uniao_fora_de_bool_str_falha),
    ("src/tcf/decoder.py", "`.8H` esta' VIVO (nao reservado/fail-loud)", caso_H_esta_vivo),
    ("src/tcf/decoder.py", "tags b, n E s decodam", caso_tags_b_n_s_decodam),
    ("src/tcf/decoder.py", "legado #TCF.7/#TCF.6 esta' CORTADO", caso_legado_67_cortado),
    ("algorithms/output-convention", "`[` e `]` sao VALORES, nao skipados", caso_bracket_nao_e_skipado),
    ("core-data-model + README + specs", "gates 1545/300/89430 batem com os testes", caso_gates_byte_canonical),
    # --- as 3 da RAIZ (2026-08-17) ---
    ("algorithms/output-convention", "as TRES nao-operacoes: nao strip, nao skip vazia, nao skip bracket", caso_as_tres_nao_operacoes),
    ("AGENTS.md + MAP.md", "9 discriminadores, com `s` e `C` decode-only", caso_nove_discriminadores),
    ("AGENTS.md", "o carimbo e' DEFAULT; o orfao e' escape (stamp=False)", caso_carimbo_e_default_orfao_e_escape),
    ("reference/api", "o 'contrato pre-1.0': 3 de 4 ficam no single-col, nao no `.8H`", caso_contrato_pre_1_0_do_api),    # --- F6/DOC-03 (2026-08-20) ---
    ("algorithms/TCF-format.*", "registry tem 5 natures; id desconhecido e' FAIL-LOUD", caso_doc03_natures_e_failloud),
    ("algorithms/TCF-format.*", "o exemplo do meta bate com o encode real", caso_doc03_exemplo_do_meta),
]

NAO_COBERTO = """\
- **`docs/theory/**` e os blocos DATADOS do `STATUS.md`** — sao LOG historico, nao
  afirmacao normativa viva. Numeros antigos (1523/303/89616) la' dentro estao CERTOS
  pro momento que registram. Nao foram tocados, e por isso nao foram verificados.
- **`docs/adr/*.md`** — imutaveis por convencao (`docs/adr/README.md:8-11`). A vigencia
  vive no campo Status do INDICE, que foi atualizado (11 linhas).
- **Completude**: este verificador prova que as 23 afirmacoes ACIMA batem. Ele NAO
  varre os docs procurando afirmacoes novas — uma afirmacao errada que nao esteja
  nesta lista passa despercebida.
"""


def main() -> int:
    print("=" * 72)
    print("VERIFICADOR — sincronizacao docs x codigo (2026-08-16)")
    print("=" * 72)
    for doc, claim, fn in CASOS:
        afirma(doc, claim, fn)

    n_ok = sum(1 for r in RESULTADOS if r["ok"])
    n = len(RESULTADOS)
    print("=" * 72)
    print(f"RESULTADO: {n_ok}/{n} afirmacoes conferem com o codigo")

    linhas = [
        "# RESULTADO — sincronizacao docs x codigo",
        "",
        "Gerado por `run.py`. Re-rode com `python run.py` pra reconferir.",
        "",
        f"**{n_ok}/{n} afirmacoes conferem com o codigo vivo.**",
        "",
        "| # | doc | afirmacao | veredito | observado |",
        "|---|---|---|---|---|",
    ]
    for i, r in enumerate(RESULTADOS, 1):
        obs = r["observado"].replace("|", "\\|").replace("\n", " ")[:170]
        linhas.append(
            f"| {i} | `{r['doc']}` | {r['claim']} | {'OK' if r['ok'] else '**FALHA**'} | `{obs}` |"
        )
    linhas += ["", "## NAO COBERTO (declarado, nao varrido)", "", NAO_COBERTO]
    (AQUI / "RESULTADO.md").write_text("\n".join(linhas) + "\n", encoding="utf-8", newline="")
    print(f"-> {AQUI / 'RESULTADO.md'}")
    print(f"-> {OUT} ({len(list(OUT.glob('*')))} arquivos)")
    return 0 if n_ok == n else 1


if __name__ == "__main__":
    raise SystemExit(main())

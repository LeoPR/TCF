# -*- coding: utf-8 -*-
"""VERIFICAÇÃO DOS WELDS C1/C2/C3 — a prova vermelho→verde, reproduzível por terceiro.

    python run.py     # sai 0 só se, para CADA weld, o defeito aparecer no código
                      # PRÉ-weld e sumir no atual, com o wire byte-idêntico

## Por que este lab existe (owner, 2026-08-16)

*"não tenho como acreditar em você... só falar ou falar escondido é a mesma coisa que não
fazer se não tiver os resultados explícitos para outro conferir, isso é o básico do método
científico. Não adianta dizer que funcionou, tem que provar que funcionou."*

**Ele tem razão, e o furo é real.** Nos três welds eu provei o "vermelho antes" com
`git stash` — **em memória, sem gravar**. A afirmação *"13 dos 16 testes falhavam antes"*
existia só no chat e na mensagem de commit. Isso não é evidência: é a minha palavra.

## O que este lab faz de diferente

Ele **materializa o código PRÉ-WELD direto do git** (`git archive <sha>^ src`) num diretório
temporário, roda o repro contra ele **num subprocesso**, e roda o mesmo repro contra o `src/`
atual. A comparação é entre dois interpretadores com duas versões reais do código — não entre
duas afirmações minhas.

Qualquer pessoa com o repo roda `python run.py` e vê os dois lados.

## Os três welds verificados

| | commit | defeito |
|---|---|---|
| **C2** | `0dec1a06` | colisão nome-posicional: header declara 3 colunas, decode devolve 2 |
| **C3** | `ec08634c` | `nature_per_col` descartado calado em lista tipada / coluna inexistente |
| **C1** | `2464f561` | polaridade come o fim do nome: `{"obs.": …}` volta como `"obs"` |

## GATE

`src/tcf` **não é tocado** por este lab — ele só LÊ o git e executa subprocessos.
O diretório temporário é criado e removido a cada rodada.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"

INP, OUT = RAIZ / "inputs", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}

#: (rotulo, ticket, commit do weld, arquivo tocado, marcador que so' existe DEPOIS)
WELDS = [
    ("C2", "T-META-COLISAO-NOME-POSICIONAL", "0dec1a06",
     "src/tcf/multi/core.py", "_nomes_resolvidos"),
    ("C3", "T-NATURE-IGNORADA-CALADA", "ec08634c",
     "src/tcf/encoder.py", "T-NATURE-IGNORADA-CALADA"),
    ("C1", "T-POLARIDADE-COME-NOME", "2464f561",
     "src/tcf/decoder.py", 'not in ("M", "H")'),
]

#: O REPRO de cada weld. Roda isolado, imprime JSON numa linha. O MESMO codigo roda
#: contra o src pre-weld e contra o atual — a unica variavel e' o `sys.path`.
REPROS = {
    "C2": r'''
from tcf import decode, view
c0, c1, c2 = "x\ny\nz", "a\nb\nc", "f\ni\nm"
wire = f"#TCF.8M!{len(c0.encode()):x},!{len(c1.encode()):x}=0,!fim\n{c0}{c1}{c2}"
out = {"wire": wire, "colunas_no_header": 3}
try:
    d = decode(wire)
    out["decode"] = {"n_colunas": len(d), "valores": d, "perdeu_calado": len(d) < 3}
except Exception as e:
    out["decode"] = {"fail_loud": f"{type(e).__name__}: {e}"}
try:
    v = view(wire)
    cols = v.columns() if callable(v.columns) else v.columns
    out["view"] = {"columns": list(cols),
                   "serve_duplicado": len(set(map(str, [v._col(c) for c in cols]))) < len(cols)}
except Exception as e:
    out["view"] = {"fail_loud": f"{type(e).__name__}: {e}"}
''',
    "C3": r'''
from tcf import encode
from tcf.natures import SPEC_DATA_ISO as DT
out = {}
# (1) lista TIPADA: o spec e' aceito e descartado?
try:
    a = encode([738886, 738887, 738888])
    b = encode([738886, 738887, 738888], nature_per_col={"x": DT})
    out["tipada"] = {"byte_identico": a == b, "descartado_calado": a == b}
except Exception as e:
    out["tipada"] = {"fail_loud": f"{type(e).__name__}: {e}"}
# (2) coluna INEXISTENTE
T = {"d": ["2024-01-01", "2024-01-02"], "s": ["a", "b"]}
try:
    a = encode(T)
    b = encode(T, nature_per_col={"ZZZ": DT})
    out["inexistente"] = {"byte_identico": a == b, "descartado_calado": a == b}
except Exception as e:
    out["inexistente"] = {"fail_loud": f"{type(e).__name__}: {e}"}
# CONTRA-PROVA: as formas legitimas tem de funcionar NOS DOIS lados
D = [f"2015-{m:02d}-01" for m in range(1, 13)]
try:
    w = encode([{"d": x} for x in D], nature_per_col={"d": DT})
    out["contraprova_list_of_dict"] = {"bytes": len(w.encode()), "ok": True}
except Exception as e:
    out["contraprova_list_of_dict"] = {"ok": False, "erro": f"{type(e).__name__}: {e}"}
''',
    "C1": r'''
import string
from tcf import decode, encode
VALS = [f"v{i}" for i in range(26)]
out = {}
d = {"obs.": list(VALS)}
w = encode(d)
out["caso_concreto"] = {"header": w.split("\n", 1)[0]}
try:
    volta = decode(w)
    out["caso_concreto"]["chave_de_volta"] = list(volta)[0]
    out["caso_concreto"]["rt_ok"] = volta == d
except Exception as e:
    out["caso_concreto"]["fail_loud"] = f"{type(e).__name__}: {e}"
# o sweep completo: quantos dos 64 nomes quebram, em cada rota
fM = fH = 0
for p in string.punctuation:
    for nome in (f"ab{p}", f"ab{p}{p}"):
        dd = {nome: list(VALS)}
        try:
            fM += decode(encode(dd)) != dd
        except Exception:
            pass
        rr = [{nome: v} for v in VALS]
        try:
            fH += decode(encode(rr)) != rr
        except Exception:
            pass
out["sweep"] = {"de": 64, "M_rt_falso": fM, "H_rt_falso": fH}
# CONTRA-PROVA: o single-col que USA polaridade nao pode mudar
ctrl = [f"{i:02d}.{i:02d}-{i:03d}" for i in range(30)]
wc = encode(ctrl)
out["contraprova_single_col"] = {"header": wc.split("\n", 1)[0],
                                 "bytes": len(wc.encode()),
                                 "rt_ok": decode(wc) == ctrl}
'''
}

_MOLDE = """# -*- coding: utf-8 -*-
import sys, json, io, warnings
warnings.simplefilter("ignore")
sys.path.insert(0, sys.argv[1])
out = {{}}
{corpo}
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
print("@@JSON@@" + json.dumps(out, ensure_ascii=False))
"""


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def materializa_pre_weld(sha: str, destino: pathlib.Path) -> pathlib.Path:
    """`git archive <sha>^ src` -> `destino`. Devolve o caminho do `src` extraido.

    Usa `git archive` (nao `worktree`) porque o repo tem caminhos longos em
    `experiments/` que estouram o limite do Windows num checkout completo.
    """
    destino.mkdir(parents=True, exist_ok=True)
    tar = subprocess.run(["git", "archive", f"{sha}^", "src"],
                         cwd=REPO, capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", str(destino)],
                   input=tar.stdout, check=True, capture_output=True)
    return destino / "src"


def roda_repro(rotulo: str, src: pathlib.Path) -> dict:
    """Executa o repro num SUBPROCESSO com `src` no path. Isola versoes."""
    script = pathlib.Path(tempfile.gettempdir()) / f"_repro_{rotulo}.py"
    script.write_text(_MOLDE.format(corpo=REPROS[rotulo]), encoding="utf-8")
    r = subprocess.run([sys.executable, str(script), str(src)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    for linha in (r.stdout or "").splitlines():
        if linha.startswith("@@JSON@@"):
            return json.loads(linha[len("@@JSON@@"):])
    return {"_erro_do_subprocesso": (r.stderr or "")[-400:] or "sem saida"}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for p in (INP, OUT):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    falhas, reg = [], {}
    base = pathlib.Path("C:/Temp") if sys.platform == "win32" else pathlib.Path("/tmp")
    tmp = base / "tcf-preweld"

    print("VERIFICAÇÃO DOS WELDS — código PRÉ-weld vindo do git, em subprocesso\n")
    for rotulo, ticket, sha, arquivo, marcador in WELDS:
        print("=" * 78)
        print(f"{rotulo} — {ticket}   (weld {sha}, {arquivo})")
        print("=" * 78)
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        src_antigo = materializa_pre_weld(sha, tmp)

        # prova independente de que o src extraido E' o pre-weld
        txt_antigo = (src_antigo / pathlib.Path(arquivo).relative_to("src")).read_text(
            encoding="utf-8")
        txt_atual = (REPO / arquivo).read_text(encoding="utf-8")
        pre_ok = marcador not in txt_antigo
        pos_ok = marcador in txt_atual
        print(f"  marcador {marcador!r}: ausente no pré-weld={pre_ok} · presente no atual={pos_ok}")
        if not (pre_ok and pos_ok):
            falhas.append(f"{rotulo}: o src extraído não é o pré-weld esperado")

        antes = roda_repro(rotulo, src_antigo)
        depois = roda_repro(rotulo, REPO / "src")
        shutil.rmtree(tmp, ignore_errors=True)

        _js(OUT / f"{rotulo}-antes.json", antes)
        _js(OUT / f"{rotulo}-depois.json", depois)
        _js(INP / f"{rotulo}-repro.fonte.json", {
            "ticket": ticket, "commit_do_weld": sha, "arquivo": arquivo,
            "marcador_pos_weld": marcador,
            "como": f"git archive {sha}^ src -> tmp; o MESMO repro roda em subprocesso "
                    f"contra o src antigo e contra o atual",
            "repro": REPROS[rotulo].strip()})

        # veredito por weld
        if rotulo == "C2":
            d_a, d_d = antes.get("decode", {}), depois.get("decode", {})
            v_a, v_d = antes.get("view", {}), depois.get("view", {})
            print(f"  ANTES : decode devolveu {d_a.get('n_colunas')} de 3 colunas "
                  f"(perdeu calado={d_a.get('perdeu_calado')}) · "
                  f"view columns={v_a.get('columns')} serve_duplicado={v_a.get('serve_duplicado')}")
            print(f"  DEPOIS: decode -> {d_d.get('fail_loud', '(sem erro!)')[:60]}")
            print(f"          view   -> {v_d.get('fail_loud', '(sem erro!)')[:60]}")
            ok = (d_a.get("perdeu_calado") is True and "fail_loud" in d_d
                  and "fail_loud" in v_d)
        elif rotulo == "C3":
            print(f"  ANTES : lista tipada descartada calada="
                  f"{antes.get('tipada', {}).get('descartado_calado')} · "
                  f"coluna inexistente descartada calada="
                  f"{antes.get('inexistente', {}).get('descartado_calado')}")
            print(f"  DEPOIS: tipada -> "
                  f"{depois.get('tipada', {}).get('fail_loud', '(sem erro!)')[:56]}")
            print(f"          inexistente -> "
                  f"{depois.get('inexistente', {}).get('fail_loud', '(sem erro!)')[:56]}")
            cp_a = antes.get("contraprova_list_of_dict", {})
            cp_d = depois.get("contraprova_list_of_dict", {})
            print(f"  CONTRA-PROVA (list[dict] legítimo): antes {cp_a.get('bytes')} B · "
                  f"depois {cp_d.get('bytes')} B · idêntico={cp_a.get('bytes')==cp_d.get('bytes')}")
            ok = (antes.get("tipada", {}).get("descartado_calado") is True
                  and antes.get("inexistente", {}).get("descartado_calado") is True
                  and "fail_loud" in depois.get("tipada", {})
                  and "fail_loud" in depois.get("inexistente", {})
                  and cp_a.get("bytes") == cp_d.get("bytes"))
        else:  # C1
            ca, cd = antes["caso_concreto"], depois["caso_concreto"]
            sa, sd = antes["sweep"], depois["sweep"]
            print(f"  ANTES : {{'obs.': …}} -> chave {ca.get('chave_de_volta')!r} "
                  f"(RT ok={ca.get('rt_ok')}) · sweep .8M {sa['M_rt_falso']}/64 · "
                  f".8H {sa['H_rt_falso']}/64")
            print(f"  DEPOIS: {{'obs.': …}} -> chave {cd.get('chave_de_volta')!r} "
                  f"(RT ok={cd.get('rt_ok')}) · sweep .8M {sd['M_rt_falso']}/64 · "
                  f".8H {sd['H_rt_falso']}/64")
            pa, pd = antes["contraprova_single_col"], depois["contraprova_single_col"]
            print(f"  CONTRA-PROVA (single-col polarizado): header {pa['header']!r} -> "
                  f"{pd['header']!r} · bytes {pa['bytes']} -> {pd['bytes']} · "
                  f"IDÊNTICO={pa['header']==pd['header'] and pa['bytes']==pd['bytes']}")
            ok = (ca.get("rt_ok") is False and cd.get("rt_ok") is True
                  and sd["M_rt_falso"] == 0 and sd["H_rt_falso"] == 0
                  and sa["M_rt_falso"] > 0 and sa["H_rt_falso"] > 0
                  and pa["header"] == pd["header"] and pa["bytes"] == pd["bytes"])
        print(f"  VEREDITO: {'defeito ANTES, ausente DEPOIS' if ok else '>>> NAO CONFIRMADO <<<'}\n")
        if not ok:
            falhas.append(f"{rotulo}: vermelho→verde não confirmado")
        reg[rotulo] = {"ticket": ticket, "commit": sha, "antes": antes,
                       "depois": depois, "confirmado": ok}

    _esc(OUT / "INDEX.md", "\n".join(
        ["# INDEX — verificação vermelho→verde dos welds C1/C2/C3", "",
         "O código PRÉ-weld vem do git (`git archive <sha>^ src`) e o MESMO repro roda em",
         "subprocesso contra as duas versões. Não há afirmação minha no meio.", "",
         "| weld | ticket | commit | antes | depois | confirmado |",
         "|---|---|---|---|---|---|"] +
        [f"| {r} | `{reg[r]['ticket']}` | `{reg[r]['commit']}` | "
         f"[antes](./{r}-antes.json) | [depois](./{r}-depois.json) | "
         f"{'✓' if reg[r]['confirmado'] else '✗'} |" for r, *_ in WELDS]) + "\n")
    _js(RAIZ / "resultado.json", {**reg, "falhas": falhas})

    print("=" * 78)
    print(f"{len(WELDS) - len(falhas)}/{len(WELDS)} welds com vermelho→verde CONFIRMADO "
          f"contra o código real do git")
    for f_ in falhas:
        print(f"  FALHA: {f_}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())

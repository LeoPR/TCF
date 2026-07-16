"""EVIDÊNCIA P4a — wire REAL do core (.tcf inspecionável + roundtrip diffável).

Complementa study.py (protótipo, pré-weld: validou a IDEIA, não serializava wire).
Aqui o artefato é o wire de PRODUÇÃO: cada caso do gate vira um .tcf que se lê,
e o roundtrip é ARQUIVO byte-idêntico ao canônico de intermediates/ (assert).
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[4] / "src"))
sys.stdout.reconfigure(encoding="utf-8")  # console cp1252 não imprime '∘'/'→'
from tcf import decode, encode_hierarchical  # noqa: E402
from tcf.hierarchical import HierarchicalError  # noqa: E402


def slug(s: str) -> str:
    flat = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()  # nome de arquivo ASCII
    keep = "".join(c if (c.isalnum() or c in " -") else " " for c in flat)
    return "-".join(keep.split())[:38].strip("-").lower()


def wjson(path: Path, obj) -> bytes:
    b = (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(b)
    return b


def rt(docs, stem: str) -> tuple[int, str]:
    """input -> .tcf (wire real) -> roundtrip .json byte-idêntico ao canônico."""
    canon = wjson(HERE / "intermediates" / f"{stem}.json", docs)
    blob = encode_hierarchical(docs)
    (HERE / "outputs" / f"{stem}.tcf").write_bytes(blob.encode("utf-8"))
    back = decode(blob)
    got = wjson(HERE / "outputs" / f"{stem}-rt.json", back)
    assert back == docs, f"RT FALHOU (objeto) em {stem}"
    assert got == canon, f"RT FALHOU (arquivo não byte-idêntico) em {stem}"
    return len(blob.encode("utf-8")), blob.split("\n")[0]


def _tree(d: int, it):
    """Árvore binária cheia: d=1 -> [1,2]; d=2 -> [[1,2],[3,4]]; ..."""
    if d == 1:
        return [next(it), next(it)]
    return [_tree(d - 1, it), _tree(d - 1, it)]


def main():
    out = ["EVIDÊNCIA P4a — wire REAL do core. Cada caso tem .tcf inspecionável + roundtrip diffável.", ""]
    (HERE / "intermediates").mkdir(exist_ok=True)
    (HERE / "outputs").mkdir(exist_ok=True)

    # ---------- (1) o gate do owner, agora com wire ----------
    did = json.loads((HERE / "inputs" / "01-didatico-array-em-array.json").read_text(encoding="utf-8"))
    out.append("(1) DIDÁTICO — gate do checkpoint 2026-07-16 (wire real, header à direita):")
    for j, (nome, docs) in enumerate([(k, v) for k, v in did.items() if not k.startswith("_")], 1):
        stem = f"01-{j:02d}-{slug(nome)}"
        nb, header = rt(docs, stem)
        out.append(f"  [RT-OK] {nome}")
        out.append(f"          {stem}.tcf · {nb}B · header: {header}")

    # ---------- (2) custo por profundidade — o item 'medir, sem limite arbitrário' ----------
    # DESENHO: 'profundidade' e 'nº de folhas' são variáveis SEPARADAS. Medi-las juntas
    # (árvore cheia) confunde framing com carga. (2a) isola o framing; (2b) é o caso realista.
    out.append("")
    out.append("(2a) CUSTO DO FRAMING, ISOLADO — carga CONSTANTE ([1,2]), só a profundidade varia:")
    out.append("     prof |  .tcf | json |  Δ/nível | header")
    prev = None
    for d in range(1, 7):
        v = [1, 2]
        for _ in range(d - 1):
            v = [v]
        docs = [{"m": v}]
        stem = f"02a-framing-prof{d}"
        nb, header = rt(docs, stem)
        njson = len(json.dumps(docs, ensure_ascii=False, separators=(",", ":")).encode())
        delta = "—" if prev is None else f"+{nb - prev}B"
        prev = nb
        out.append(f"     {d:>4} | {nb:>4}B | {njson:>3}B | {delta:>8} | {header}")
    out.append("     → carga fixa: cada nível a mais custa SÓ o framing (coluna de count do nível).")

    out.append("")
    out.append("(2b) ÁRVORE BINÁRIA CHEIA — realista, mas CONFUNDIDO de propósito (folhas dobram junto):")
    out.append("     prof | folhas |  .tcf | json |  Δ/nível | header")
    prev = None
    for d in range(1, 6):
        docs = [{"m": _tree(d, iter(range(1, 2 ** d + 1)))}]
        stem = f"02b-arvore-prof{d}"
        nb, header = rt(docs, stem)
        njson = len(json.dumps(docs, ensure_ascii=False, separators=(",", ":")).encode())
        delta = "—" if prev is None else f"+{nb - prev}B"
        prev = nb
        out.append(f"     {d:>4} | {2**d:>6} | {nb:>4}B | {njson:>3}B | {delta:>8} | {header}")
    out.append("     → aqui o Δ NÃO é custo de nível: folhas dobram a cada linha. Ler (2a) pro framing.")
    out.append("     Artefatos: outputs/02a-framing-prof{1..6}.tcf · outputs/02b-arvore-prof{1..5}.tcf")

    # ---------- (3) adversarial no WIRE real (não no dict do protótipo) ----------
    out.append("")
    out.append("(3) ADVERSARIAL no wire REAL (blob adulterado → fail-loud, nunca silencioso):")
    base = [{"m": [[1, 2], [3]]}]
    blob = encode_hierarchical(base)
    (HERE / "outputs" / "03-adversarial-base.tcf").write_bytes(blob.encode("utf-8"))
    head, sep, body = blob.partition("\n")

    def mut(nome, novo_blob):
        try:
            r = decode(novo_blob)
            out.append(f"  [FALHA-SILENCIOSA!] {nome}: decodou {r!r}")
            return False
        except (HierarchicalError, ValueError) as e:
            out.append(f"  [fail-loud OK] {nome}: {type(e).__name__}: {str(e)[:58]}")
            return True

    ok = True
    ok &= mut("tag desconhecida (n->q)", head.replace("n", "q", 1) + sep + body if "n" in head else blob + "x")
    ok &= mut("']' interno deletado", head.replace("]", "", 1) + sep + body)
    ok &= mut("bytes apendados no corpo", blob + "LIXO")
    ok &= mut("corpo esvaziado", head + sep)
    (HERE / "outputs" / "03-adversarial-mutacoes.txt").write_bytes(
        ("\n".join(out[out.index("(3) ADVERSARIAL no wire REAL (blob adulterado → fail-loud, nunca silencioso):"):])
         + "\n").encode("utf-8"))

    out += ["", "VEREDITO: P4a tem evidência de WIRE, não só de prosa. Todo caso do gate é um .tcf legível;",
            "todo roundtrip é arquivo byte-idêntico ao canônico (assert); blob adulterado é fail-loud.",
            "study.py (protótipo, pré-weld) validou a IDEIA; este run.py mede o que foi SOLDADO."]
    (HERE / "outputs" / "00-resultado.txt").write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print("\n".join(out))
    assert ok, "houve falha silenciosa no adversarial"


if __name__ == "__main__":
    main()

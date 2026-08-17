"""Os LIMITES do `.8H`: profundidade, largura e as bordas do meta.

POR QUE ESTE LAB
----------------
O owner pediu: pesquisar estruturas complexas de hierarquia, ver limites, registrar.
A pesquisa no repo mostrou o que JA' temos (chave repetida: levantamento 2026-07-17;
int>2^53: json-equivalence §N2; array-em-array: P4a funciona) e o buraco: NINGUEM
mediu o limite de PROFUNDIDADE do `.8H`, nem as bordas do meta que a literatura
diz serem onde os parsers quebram.

A regua externa (verificada 2026-08-17, fontes no registro):
  serde_json 128 (default) · MongoDB/BSON 100 · Jackson 1000 · protobuf-go 10.000
  RFC 8259 §9: "An implementation may set limits on the maximum depth of nesting."
O JSON permite profundidade arbitraria NO TEXTO; quem limita e' o parser. A pergunta
aqui: onde o NOSSO quebra, e ele quebra fail-loud (mensagem tipada) ou feio
(RecursionError cru)?

A REGRA DO LAB (feedback do owner, lab 0500)
--------------------------------------------
Casos minusculos e representativos. As ESCADAS (profundidade) nao imprimem wire —
imprimem o degrau onde quebrou e COMO quebrou. Os casos de borda imprimem o wire
inteiro, porque cabem numa linha.

Roundtrip e' o assert em TODO caso que encoda (§RT). `src/tcf` INTOCADO.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))

IN = AQUI / "inputs"
OUT = AQUI / "outputs"
for d in (IN, OUT):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode  # noqa: E402

RESULT: dict = {"escadas": {}, "bordas": [], "python_recursion_limit": sys.getrecursionlimit()}


# ── as escadas: acha o degrau onde quebra ──────────────────────────────────
def obj_prof(d: int):
    """{"a": {"a": {... "x"}}} com d niveis de objeto."""
    v: object = "x"
    for _ in range(d):
        v = {"a": v}
    return [v, v] if isinstance(v, dict) else v   # dataset de 2 linhas iguais


def arr_prof(d: int):
    """[[["x"]]] com d niveis de array, dentro de 1 campo."""
    v: object = "x"
    for _ in range(d):
        v = [v]
    return [{"a": v}, {"a": v}]


def sobe_escada(nome: str, gera, degraus: list[int]) -> dict:
    """Sobe ate' quebrar; devolve o ultimo degrau OK, o primeiro que falhou e COMO."""
    ultimo_ok, primeiro_erro, como = 0, None, None
    for d in degraus:
        entrada = gera(d)
        try:
            w = encode(entrada)
            if decode(w) != entrada:
                primeiro_erro, como = d, "RT divergiu (sem excecao!)"
                break
            ultimo_ok = d
        except RecursionError:
            primeiro_erro, como = d, "RecursionError CRU (nao e' fail-loud tipado)"
            break
        except Exception as e:
            primeiro_erro, como = d, f"{type(e).__name__}: {str(e)[:70]}"
            break
    # refina por bissecao entre ultimo_ok e primeiro_erro
    if primeiro_erro is not None:
        lo, hi = ultimo_ok, primeiro_erro
        while hi - lo > 1:
            mid = (lo + hi) // 2
            entrada = gera(mid)
            try:
                w = encode(entrada)
                ok = decode(w) == entrada
            except Exception:
                ok = False
            if ok:
                lo = mid
            else:
                hi = mid
        ultimo_ok, primeiro_erro = lo, hi
    r = {"ultimo_ok": ultimo_ok, "primeiro_erro": primeiro_erro, "como": como}
    print(f"  {nome:18} ultimo OK = {ultimo_ok:>5}   quebra em {primeiro_erro} "
          f"({como if como else '—'})")
    RESULT["escadas"][nome] = r
    # evidencia minima: o wire do MAIOR caso que passou (so' o header + 1a linha)
    entrada = gera(min(ultimo_ok, 8))            # 8 niveis: legivel, representativo
    w = encode(entrada)
    (OUT / f"escada_{nome}_d8.tcf").write_text(w, encoding="utf-8", newline="")
    (OUT / f"escada_{nome}_d8.roundtrip.json").write_text(
        json.dumps(decode(w), ensure_ascii=False), encoding="utf-8", newline="")
    return r


# ── as bordas do meta: casos MINIMOS que nenhum lab cobriu ─────────────────
BORDAS: list[tuple[str, str, object]] = [
    ("chave_com_chaves",
     "nome de campo contendo `{` (o char de aninhamento do meta)",
     [{"a{b": "x"}, {"a{b": "y"}]),
    ("chave_com_cerquilha",
     "nome contendo `#` (o char de array/disc do meta)",
     [{"a#b": "x"}, {"a#b": "y"}]),
    ("chave_com_colchete",
     "nome contendo `[` (o char que fecha forma de array)",
     [{"a[b": "x"}, {"a[b": "y"}]),
    ("chave_com_interrogacao",
     "nome contendo `?` (o char da mascara)",
     [{"a?b": "x"}, {"a?b": "y"}]),
    ("chave_unicode",
     "nome unicode multi-byte (acento + emoji)",
     [{"endereço🏠": "x"}, {"endereço🏠": "y"}]),
    ("ordem_de_chaves",
     "decode devolve ordem do SCHEMA (1a aparicao), nao a por-registro",
     [{"b": "1", "a": "2"}, {"a": "3", "b": "4"}]),
    ("obj_no_array_no_obj",
     "objeto dentro de array dentro de objeto (3 formas alternadas)",
     [{"a": [{"b": "x"}]}, {"a": [{"b": "y"}, {"b": "z"}]}]),
    ("bigint_2e53",
     "int alem de 2^53 (⊃ I-JSON, ja' registrado; aqui o caso MINIMO)",
     [{"a": 2**53 + 1}, {"a": 2**53 + 2}]),
]


def bordas() -> None:
    print()
    print("== as bordas do meta (casos minimos, wire inteiro) ==")
    for cid, desc, entrada in BORDAS:
        (IN / f"{cid}.json").write_text(
            json.dumps(entrada, ensure_ascii=False), encoding="utf-8", newline="")
        try:
            w = encode(entrada)
            volta = decode(w)
            rt = volta == entrada
            (OUT / f"{cid}.tcf").write_text(w, encoding="utf-8", newline="")
            (OUT / f"{cid}.roundtrip.json").write_text(
                json.dumps(volta, ensure_ascii=False), encoding="utf-8", newline="")
            l1 = w.split("\n", 1)[0]
            marca = "ok " if rt else "*RT DIVERGE*"
            print(f"  {cid:24} {marca} {l1!r}")
            if cid == "ordem_de_chaves":
                print(f"  {'':24}     -> decode: {volta!r}")
            RESULT["bordas"].append({"id": cid, "desc": desc, "header": l1,
                                     "rt": rt, "bytes": len(w.encode())})
        except Exception as e:
            print(f"  {cid:24} {type(e).__name__}: {str(e)[:58]}")
            RESULT["bordas"].append({"id": cid, "desc": desc,
                                     "erro": f"{type(e).__name__}: {e}"})


# ── decode ADVERSARIAL: wire forjado com campo duplicado ───────────────────
def campo_duplicado_no_wire() -> None:
    """A chave repetida no OBJETO Python nao existe (dict deduplica). Mas no WIRE
    forjado? O decode aceita `a:2,a` calado ou falha alto? (O levantamento
    2026-07-17 cobriu o TEXTO json; o wire `.8H` ninguem testou.)"""
    print()
    print("== decode adversarial: campo duplicado FORJADO no wire ==")
    for rot, wire in [
        ("dup_simples", "#TCF.8Ha:2,a\nx\ny\n"),
        ("dup_com_size", "#TCF.8Ha:2,a:2,b\nx\ny\nz\n"),
    ]:
        try:
            r = decode(wire)
            print(f"  {rot:14} ACEITOU calado -> {r!r}   <- registrar")
            RESULT["bordas"].append({"id": f"forjado_{rot}", "wire": wire,
                                     "aceitou": True, "decode": repr(r)})
        except Exception as e:
            print(f"  {rot:14} fail-loud: {type(e).__name__}: {str(e)[:52]}")
            RESULT["bordas"].append({"id": f"forjado_{rot}", "wire": wire,
                                     "aceitou": False,
                                     "erro": f"{type(e).__name__}: {str(e)[:90]}"})


def main() -> int:
    print("=" * 76)
    print(f"LIMITES DO .8H  (sys.recursionlimit={sys.getrecursionlimit()})")
    print("=" * 76)
    print("== as escadas ==")
    degraus = [4, 16, 64, 128, 256, 512, 1024, 2048, 4096]
    sobe_escada("objeto", obj_prof, degraus)
    sobe_escada("array", arr_prof, degraus)

    # largura: muitas CHAVES (header cresce linear; existe teto?)
    def larg(k: int):
        return [{f"c{i}": "x" for i in range(k)}] * 2
    sobe_escada("largura_chaves", larg, [8, 64, 256, 1024, 4096, 16384])

    bordas()
    campo_duplicado_no_wire()

    (AQUI / "resultado.json").write_text(
        json.dumps(RESULT, ensure_ascii=False, indent=1), encoding="utf-8", newline="")
    print()
    print(f"-> {AQUI / 'resultado.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

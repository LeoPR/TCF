"""Os 9 casos de natureza em volume (3 naturezas x 3 codepaths), em escala CONSISTENTE.

Motivo (2026-07-21): o bloco 4 do `bench_evidencia_f3.py` roda estes 9 casos a
600k linhas / 100k unicos e NAO fecha — o `ip-spec` sozinho consumiu ~13h. A
causa foi medida: um penhasco de superlinearidade acima de ~64k valores UNICOS
com prefixos longos compartilhados (16k->1.1s, 64k->8.7s, 100k->150s+), com o
HCC respondendo por ~95% do tempo de camada.

Aqui o objetivo e' outro: fechar os NOVE com a MESMA escala, pra ter comparacao
consistente entre naturezas e codepaths — base pra atacar a otimizacao. Menos
dado, mas todos. E com o instrumento novo: amostras cruas, CPU-time, e
atribuicao por camada (que diz ONDE otimizar, nao so' que "demorou").

    python -m bench_perf.natures_9 --unicos 8000 --linhas 48000
    python -m bench_perf.natures_9 --sizing        # so' dimensiona, nao mede
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from tcf import encode, decode                                    # noqa: E402
from tcf.natures import SPEC_CNPJ, SPEC_CPF, SPEC_IP              # noqa: E402
from bench_perf import layers as L, probes as P                   # noqa: E402

SEED = 20260601        # mesma semente do bloco 4 original (comparabilidade)
SAIDA = ROOT / "experiments" / "results" / "perf-baseline" / "natures9"


# ------------------------------------------------------------------ dados
# Mesma construcao do bench_evidencia_f3.py, parametrizada em escala.

def _gen_cpf_digits(rng: random.Random) -> str:
    d = [rng.randrange(10) for _ in range(9)]
    for _ in range(2):
        s = sum(v * w for v, w in zip(d, range(len(d) + 1, 1, -1)))
        dv = 11 - s % 11
        d.append(0 if dv >= 10 else dv)
    return "".join(map(str, d))


def cpfs(n: int, rng: random.Random) -> list[str]:
    out, visto = [], set()
    while len(out) < n:
        v = _gen_cpf_digits(rng)
        if v not in visto:
            visto.add(v)
            out.append(f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}")
    return out


def cnpjs(n: int, rng: random.Random) -> list[str]:
    out, visto = [], set()
    while len(out) < n:
        d = [rng.randrange(10) for _ in range(8)] + [0, 0, 0, 1]
        for pesos in ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
                      [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]):
            s = sum(v * w for v, w in zip(d, pesos))
            dv = 11 - s % 11
            d.append(0 if dv >= 10 else dv)
        v = "".join(map(str, d))
        if v not in visto:
            visto.add(v)
            out.append(f"{v[:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:]}")
    return out


def ips(n: int) -> list[str]:
    return [f"10.{(i // 65536) % 255}.{(i // 256) % 255}.{i % 255}" for i in range(n)]


def repetir(base: list[str], n: int) -> list[str]:
    return [base[i % len(base)] for i in range(n)]


def construir(unicos: int, linhas: int) -> dict[str, tuple[list[str], list[str]]]:
    """{nature: (validos, invalidos)} — invalido = quebra o check, cai no literal."""
    rng = random.Random(SEED)
    v_cpf = repetir(cpfs(unicos, rng), linhas)
    v_cnpj = repetir(cnpjs(unicos, rng), linhas)
    v_ip = repetir(ips(unicos), linhas)
    return {
        "cpf": (v_cpf, [v[:-1] + str((int(v[-1]) + 1) % 10) for v in v_cpf]),
        "cnpj": (v_cnpj, [v[:-1] + str((int(v[-1]) + 1) % 10) for v in v_cnpj]),
        "ip": (v_ip, [v + "x" for v in v_ip]),
    }


SPECS = {"cpf": SPEC_CPF, "cnpj": SPEC_CNPJ, "ip": SPEC_IP}


def colunas(validos: list[str], invalidos: list[str]) -> dict[str, list[str]]:
    misto = [validos[i] if i % 2 == 0 else invalidos[i] for i in range(len(validos))]
    return {"spec": validos, "fallback": invalidos, "misto": misto}


# ------------------------------------------------------------------ medicao


def medir_caso(nature: str, codepath: str, col: list[str], *, com_camadas: bool) -> dict:
    spec = SPECS[nature]
    kw = {"nature_per_col": {nature: spec}}
    dados = {nature: col}

    blob = encode(dados, **kw)                       # RT e' gate: sem ele, nenhum numero
    volta = decode(blob)
    rt_ok = volta == dados
    reg: dict = {
        "case_id": f"nature9|{nature}|{codepath}",
        "nature": nature, "codepath": codepath,
        "n_rows": len(col), "n_unicos": len(set(col)),
        "rt_ok": rt_ok,
        "bytes": len(blob.encode("utf-8")),
        "bytes_raw": len("\n".join(col).encode("utf-8")),
    }
    if not rt_ok:                                    # nenhum numero orfao
        reg["error"] = "RT quebrado — bytes/tempo nao reportados"
        return reg

    reg["encode"] = P.medir(lambda: encode(dados, **kw))
    reg["decode"] = P.medir(lambda: decode(blob))
    if com_camadas:                                  # so' serial; monkeypatch nao cruza spawn
        _, cam = L.perfil_de(lambda: encode(dados, **kw))
        reg["layers"] = {k: v for k, v in cam.items() if not k.startswith("_")}
        reg["layers_total_ns"] = cam["_total_camadas_ns"]
    return reg


def dimensionar(unicos: int, linhas: int) -> None:
    """Custo de UM encode por caso, sem repeticao — pra escolher a escala antes de rodar."""
    dados = construir(unicos, linhas)
    print(f"dimensionamento @ {unicos} unicos x {linhas} linhas")
    total = 0.0
    for nature, (val, inval) in dados.items():
        for codepath, col in colunas(val, inval).items():
            t0 = time.perf_counter()
            encode({nature: col}, schema={nature: SPECS[nature]})
            dt = time.perf_counter() - t0
            total += dt
            print(f"  {nature:<5} {codepath:<9} {dt:7.2f}s", flush=True)
    print(f"  {'TOTAL':<15} {total:7.2f}s  (x~11 do protocolo => ~{total * 11 / 60:.1f} min)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="9 casos de natureza em escala consistente")
    ap.add_argument("--unicos", type=int, default=8000)
    ap.add_argument("--linhas", type=int, default=48000)
    ap.add_argument("--sizing", action="store_true", help="so' dimensiona, nao mede")
    ap.add_argument("--sem-camadas", action="store_true")
    args = ap.parse_args(argv)

    if args.sizing:
        dimensionar(args.unicos, args.linhas)
        return 0

    SAIDA.mkdir(parents=True, exist_ok=True)
    dados = construir(args.unicos, args.linhas)
    regs = []
    for nature, (val, inval) in dados.items():
        for codepath, col in colunas(val, inval).items():
            print(f"[{nature}/{codepath}] ...", flush=True)
            r = medir_caso(nature, codepath, col, com_camadas=not args.sem_camadas)
            r["escala"] = {"unicos": args.unicos, "linhas": args.linhas}
            regs.append(r)
            enc = r.get("encode", {})
            print(f"  RT={r['rt_ok']} enc={enc.get('point_ns', 0)/1e9:.2f}s "
                  f"tier={enc.get('tier')} n={enc.get('n')} bytes={r['bytes']}", flush=True)

    p = SAIDA / f"natures9-u{args.unicos}-r{args.linhas}.jsonl"
    with p.open("w", encoding="utf-8", newline="\n") as f:
        for r in regs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    ok = sum(1 for r in regs if r["rt_ok"])
    print(f"\n{ok}/{len(regs)} casos com RT ok -> {p}")
    return 0 if ok == len(regs) else 1


if __name__ == "__main__":
    raise SystemExit(main())

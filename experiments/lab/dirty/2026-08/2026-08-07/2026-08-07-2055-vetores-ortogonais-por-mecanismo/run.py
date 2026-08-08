"""Vetores ortogonais por MECANISMO e por DIREÇÃO (encode/decode).

    python run.py

## Por que este lab existe

Todo weld recente fechou com "encolheu N bytes". Bytes é a âncora — é o vetor mais justo
pra decidir — mas não é o único, e tratar os outros como nota de rodapé esconde TROCA
vestida de ganho. Aqui cada mecanismo é medido nos quatro vetores, **separando encode de
decode**, e classificado: **win-win** (melhora ou empata em tudo) ou **troca** (melhora num
eixo, piora noutro → a escolha vira condicional, e não existe "melhor de tudo").

## Os quatro vetores

    BYTES        a âncora — tamanho do fio
    CPU          ns por operação, mediana de R repetições + CV (Georges et al.: variação,
                 não número solto)
    MEMÓRIA      pico de alocação (tracemalloc), encode e decode separados
    ONLINE-NESS  de quanto do fio o valor j DEPENDE — o vetor que NÃO existe no repo
                 (`bench_perf` mede wall/cpu/heap/rss; nenhum grep acha streaming)

## Atribuição

Cada dataset é codificado em variantes que isolam o mecanismo:

    core       magic + corpo do core (sem polaridade, sem bN)
    +pol       core + camada de borda de polaridade
    +bN(B)     bN modo B — domínio primeiro
    +bN(C)     bN modo C — domínio por último (decodável, não emitido hoje)

A diferença entre variantes É o custo do mecanismo. Não é comparação com "o encode
default" (que já escolheu por `min()`), é comparação com a alternativa concreta.

## O que este lab NÃO faz

Não é `bench_perf`: não tem calibrador cross-máquina, não tem gate térmico, não tem
matriz congelada. É **first-order, uma máquina, um momento** — serve pra achar SINAL e
CLASSIFICAR troca, não pra pinar número. Número publicável vem do `bench_perf`.

A online-ness medida é do **formato**, não do código: o `src/tcf` de hoje lê o fio inteiro
em todas as rotas. É medida por métodos **construtivos** (truncamento com o decoder real;
extração aritmética conferida contra o decode) — ver o cabeçalho de `dependencia.py` pras
DUAS tentativas anteriores que foram jogadas fora, e por quê.

`src/tcf` NÃO é tocado.
"""
from __future__ import annotations

import json
import pathlib
import statistics
import sys
import time
import tracemalloc

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[4]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from dependencia import extrai_bn, prefixo_por_truncamento  # noqa: E402

from tcf import decode  # noqa: E402
from tcf.composicional.dominio_bn import candidatos  # noqa: E402
from tcf.composicional.polaridade import polariza  # noqa: E402
from tcf.decoder import _decode_column  # noqa: E402
from tcf.encoder import _encode_column  # noqa: E402

R = 12                                   # repetições por rodada
G = 4                                    # rodadas INTERCALADAS entre variantes
MAGIC = "#TCF.8"


def _escreve(p, texto):
    p.write_text(texto, encoding="utf-8", newline="")


# ────────────────────────────────────────────────────────────── os datasets
N = 2000


def _cic(vals, n=N):
    return [vals[i % len(vals)] for i in range(n)]


DADOS = [
    ("bool-2", "k=2, o regime-alvo do bN", _cic(["S", "N"])),
    ("cat-4", "k=4, categórico curto", _cic(["alfa", "beta", "gama", "delta"])),
    ("cat-16", "k=16, sem prefixo comum", _cic(
        ["alfa", "beta", "gama", "delta", "zeta", "eta", "teta", "iota",
         "capa", "lambda", "mi", "ni", "csi", "omicron", "pi", "ro"])),
    ("cat-100", "k=100, ids com prefixo", _cic([f"id{i:04d}" for i in range(100)])),
    ("uf-27", "k=27, realista (UF)", _cic(
        ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
         "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"])),
    ("digito", "k=2 que colide com dígito", _cic(["0", "1"])),
]


# ─────────────────────────────────────────────────────────────── as variantes
def variantes(vals) -> dict:
    """`nome -> wire`. Cada uma isola um mecanismo. `None` = não se aplica."""
    corpo = _encode_column(vals, header="val")
    v = {"core": MAGIC + "\n" + corpo}
    suf, pol = polariza(corpo)
    v["+pol"] = (MAGIC + suf + "\n" + pol) if suf else None
    cands = candidatos(vals, lambda vs: _encode_column(vs, header="val"), _decode_column)
    v["+bN(B)"] = cands[0] if cands else None
    v["+bN(C)"] = cands[1] if cands else None
    return v


# ──────────────────────────────────────────────────────────────── as medições
def amostra_ns(fn, *a) -> list[int]:
    """R amostras cruas. O agregado vem depois — intercalado entre variantes."""
    for _ in range(3):
        fn(*a)
    am = []
    for _ in range(R):
        t0 = time.perf_counter_ns()
        fn(*a)
        am.append(time.perf_counter_ns() - t0)
    return am


def resume(rodadas: "list[list[int]]") -> dict:
    """`{mediana_us, cv, medianas_por_rodada}` — a rodada é a unidade de comparação.

    Georges et al.: variação, não número solto. Aqui vai além: como as variantes são
    medidas INTERCALADAS dentro de cada rodada, a deriva térmica atinge todas igual, e o
    que se compara entre variantes é a mediana POR RODADA. O sinal do delta é confiável
    quando se repete em todas as rodadas; a magnitude, nesta máquina, não é.
    """
    meds = [statistics.median(r) for r in rodadas]
    todas = [x for r in rodadas for x in r]
    return {"mediana_us": round(statistics.median(todas) / 1000, 1),
            "cv": round(statistics.pstdev(todas) / statistics.mean(todas) * 100, 1),
            "por_rodada_us": [round(m / 1000, 1) for m in meds]}


def pico_kib(fn, *a) -> float:
    tracemalloc.start()
    tracemalloc.reset_peak()
    fn(*a)
    _cur, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return pico / 1024


def online(wire, vals, marcos) -> dict:
    """De quanto do fio o valor `j` depende. Dois métodos, cada um no seu domínio."""
    total = len(wire.encode())
    disc = wire[6:7]
    out = {}

    if disc == "B":
        # bN modo B: truncar nao serve (checagem de tamanho exato recusa fio curto), entao
        # EXTRAI de cabecalho + dominio + 1 quarteto, e confere contra o decode.
        fim_cab = wire.index("\n")
        pos_marc = wire.index("\n=", fim_cab)
        dom = _decode_column(wire[fim_cab + 1:pos_marc] + "\n")
        for j in marcos:
            valor, tocado = extrai_bn(wire, j, dom)
            out[j] = ({"metodo": "extracao", "prefixo_B": tocado,
                       "prefixo_pct": round(100 * tocado / total, 1)}
                      if valor == vals[j]
                      else {"metodo": "extracao", "prefixo_pct": None,
                            "motivo": f"extraiu {valor!r} != {vals[j]!r}"})
        return out

    if disc == "C":
        # Estrutural: o dominio vem DEPOIS do payload. Nao ha' atalho, e nao e' limitacao
        # do metodo. O numero e' 100% por construcao do fio.
        for j in marcos:
            out[j] = {"metodo": "estrutural", "prefixo_B": total, "prefixo_pct": 100.0,
                      "motivo": "domínio depois do payload"}
        return out

    for j in marcos:
        p = prefixo_por_truncamento(decode, wire, j, vals[j])
        out[j] = {"metodo": "truncamento", "prefixo_B": p,
                  "prefixo_pct": round(100 * p / total, 1) if p is not None else None}
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    tudo, falhas = [], []

    for nome, porque, vals in DADOS:
        _escreve(RAIZ / "inputs" / f"{nome}.json",
                 json.dumps({"caso": nome, "porque": porque, "n": len(vals),
                             "k": len(set(vals)), "amostra": vals[:8]},
                            ensure_ascii=False, indent=2) + "\n")
        marcos = [0, 1, len(vals) // 2, len(vals) - 1]

        vs = {k: w for k, w in variantes(vals).items() if w is not None}
        for var, wire in list(vs.items()):
            # o fio tem de fazer RT — sem isso nenhuma outra medida vale
            try:
                if decode(wire) != vals:
                    falhas.append(f"{nome}/{var}: RT quebrado")
                    del vs[var]
            except Exception as e:
                falhas.append(f"{nome}/{var}: decode levantou {type(e).__name__}")
                del vs[var]

        # CPU: G rodadas, e DENTRO de cada rodada todas as variantes. A deriva térmica
        # atinge todas igual, então o delta ENTRE variantes na mesma rodada é comparável —
        # medir uma variante inteira e depois a outra é o que produziu o "+86%" que não se
        # reproduziu (deu +60/+37/+11 em rodadas separadas).
        amostras: dict[str, list] = {v: [] for v in vs}
        for _g in range(G):
            for var, wire in vs.items():
                amostras[var].append(amostra_ns(decode, wire))

        base = "core"
        for var, wire in vs.items():
            dec = resume(amostras[var])
            reg = {
                "caso": nome, "variante": var, "n": len(vals), "k": len(set(vals)),
                "bytes": len(wire.encode()),
                "decode": dec,
                "pico_decode_KiB": round(pico_kib(decode, wire), 1),
                "online": online(wire, vals, marcos),
            }
            if var != base and base in amostras:
                b = resume(amostras[base])["por_rodada_us"]
                v_ = dec["por_rodada_us"]
                deltas = [x / y - 1 for x, y in zip(v_, b) if y]
                reg["delta_cpu_por_rodada"] = [f"{d * 100:+.0f}%" for d in deltas]
                # SINAL confiável = mesma direção em TODAS as rodadas. Magnitude não.
                reg["sinal_cpu"] = ("mais lento" if all(d > 0 for d in deltas)
                                    else "mais rápido" if all(d < 0 for d in deltas)
                                    else "INDEFINIDO (sinal troca entre rodadas)")
            tudo.append(reg)
            _escreve(RAIZ / "outputs" / f"{nome}--{var.replace('(', '').replace(')', '')}.tcf",
                     wire)

    _escreve(RAIZ / "intermediates" / "medicoes.json",
             json.dumps(tudo, ensure_ascii=False, indent=2) + "\n")
    _relatorio(tudo, falhas)
    print(f"{len(tudo)} medições, {len(falhas)} falhas")
    if falhas:
        print("FALHAS:", *falhas, sep="\n  ")
    return 1 if falhas else 0


def _relatorio(tudo, falhas):
    por_caso: dict[str, list] = {}
    for r in tudo:
        por_caso.setdefault(r["caso"], []).append(r)

    L = ["# Vetores ortogonais por mecanismo — encode × decode", "",
         f"`n={N}`, {R} repetições por medição, mediana + CV. First-order, uma máquina.",
         "Número publicável vem do `bench_perf`, não daqui.", "",
         "`prefixo%` = de quanto do fio o valor `j` depende, em % do fio. Dois métodos "
         "**construtivos**, cada um no seu domínio (ver `dependencia.py`):",
         "`truncamento` — menor `decode(wire[:p])` que já dá o valor `j` certo (core/pol);",
         "`extração` — valor `j` tirado só de cabeçalho + domínio + 1 quarteto b64, "
         "conferido contra o decode (bN modo `B`);",
         "`estrutural` — modo `C`: o domínio vem depois do payload, 100% por construção.", "",
         "É propriedade do **formato**. O `src/tcf` de hoje lê o fio inteiro em todas as "
         "rotas — a propriedade está no fio, não no código.", ""]

    for caso, regs in por_caso.items():
        base = next((r for r in regs if r["variante"] == "core"), None)
        L += ["", f"## {caso}  (k={regs[0]['k']})", "",
              "| variante | bytes | Δ bytes | CPU dec (µs) | CV | Δ CPU por rodada | sinal | pico dec (KiB) |",
              "|---|---:|---:|---:|---:|---|---|---:|"]
        for r in regs:
            db = f"{r['bytes'] - base['bytes']:+d}" if base else "—"
            dr = ", ".join(r.get("delta_cpu_por_rodada", [])) or "—"
            L.append(f"| `{r['variante']}` | {r['bytes']} | {db} | {r['decode']['mediana_us']} "
                     f"| ±{r['decode']['cv']}% | {dr} | {r.get('sinal_cpu', '—')} "
                     f"| {r['pico_decode_KiB']} |")
        L += ["", "**Online-ness** — de quanto do fio o valor `j` depende:", "",
              "| variante | j=0 | j=1 | j=n/2 | j=n-1 |", "|---|---|---|---|---|"]
        for r in regs:
            cels = []
            for j in sorted(r["online"], key=int):
                o = r["online"][j]
                if o.get("prefixo_pct") is None:
                    cels.append(f"— ({o.get('motivo', '?')})")
                else:
                    cels.append(f"{o['prefixo_pct']}%")
            L.append(f"| `{r['variante']}` | " + " | ".join(cels) + " |")

    L += ["", "---", "", f"**falhas: {len(falhas)}**"]
    if falhas:
        L += ["", *(f"- {f}" for f in falhas)]
    _escreve(RAIZ / "outputs" / "medicoes.md", "\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())

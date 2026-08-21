"""H-13-04 — template DECLARADO dispensa o gate global? (o S3 do streaming)

A HIPÓTESE
----------
*"Spec/dica pré-declarada de template (spec orienta, não manda) dispensa o gate global
batch: coluna com dica valida por VALOR e não bufferiza."*

É o **S3** do desenho do H-13-03: se o template vem do contrato, não há o que descobrir —
o gate deixa de precisar de lookahead e valida **por valor**, falhando no primeiro que
divergir. Em vocabulário de prefetch: é o *"prefetch orientado por pesquisa"* — não há
aposta, há informação.

O QUE ISTO PRECISA PROVAR (e o que derruba)
-------------------------------------------
  G1  EQUIVALÊNCIA — o gate declarado decide o MESMO que o gate global, quando o
      template está certo. Se divergir, a dica não é substituta: é outro mecanismo.
  G2  STREAMING — o gate declarado decide **sem ver o resto**: a decisão no valor `k`
      é a mesma com ou sem os valores `k+1..n` à frente.
  G3  FAIL-LOUD — dica ERRADA não pode degradar calado. Ou recusa (cai no fallback,
      como o gate global faz), ou falha alto. **Nunca** produzir wire que perde dado.
  G4  CUSTO — quanto de memória/varredura o declarado poupa contra o global.

O CONTRASTE
-----------
  GLOBAL     (hoje) varre `values[1:]` inteiro, decide, emite      -> batch
  DECLARADO  (mock) recebe o template, valida valor a valor        -> streaming
  ORÁCULO    o global rodando sobre TODA a coluna = a resposta certa (referência de G1)

Dados: sintéticos de controle (o gate é lógico, não estatístico) + CEP e telefone REAIS
via Shaper. `src/tcf` INTOCADO. §RT e evidência obrigatória.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "scripts"))

IN, OUT = AQUI / "inputs", AQUI / "outputs"
for d in (IN, OUT):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode                                # noqa: E402
from tcf.multi.split import _struct_split_encode              # noqa: E402
from tcf.pipeline import DEFAULT_PIPELINE                     # noqa: E402


def B(x):
    return len(x.encode("utf-8")) if isinstance(x, str) else len(x)


# ── o template, na mesma noção do split real ─────────────────────────────
def partes_de(v: str):
    """As partes NÃO-dígito de um valor. É o `sig` do `_struct_split_encode`."""
    seq, atual, dig = [], "", None
    for ch in v:
        d = ch.isdigit()
        if dig is None:
            dig, atual = d, ch
            continue
        if d != dig:
            seq.append((dig, atual)); atual, dig = ch, d
        else:
            atual += ch
    seq.append((dig, atual))
    partes, campos = ([""] if seq[0][0] else []), []
    for eh, tok in seq:
        (campos if eh else partes).append(tok)
    if seq[-1][0]:
        partes.append("")
    return tuple(partes), campos


# ── GATE GLOBAL: o de hoje. Precisa da coluna inteira. ───────────────────
def gate_global(values):
    """Devolve (aplica, template, n_varridos). Espelha `split.py`."""
    if len(values) < 2:
        return False, None, len(values)
    sig0, c0 = partes_de(values[0])
    if len(c0) < 2:
        return False, None, 1
    for i, v in enumerate(values[1:], 1):
        sig, c = partes_de(v)
        if sig != sig0 or len(c) != len(c0):
            return False, None, i + 1          # varreu ate' achar o divergente
    return True, sig0, len(values)             # varreu TUDO pra poder afirmar


# ── GATE DECLARADO: recebe o template. Valida por valor. ─────────────────
class GateDeclarado:
    """Streaming: cada valor é aceito/recusado sozinho, sem olhar o resto.

    `sem_ver_o_resto()` é o ponto do G2 — a decisão no valor k não consulta k+1..n.
    """

    def __init__(self, template: tuple):
        self.tmpl = template
        self.nf = len(template) - 1
        self.visto = 0
        self.recusou_em = None

    def aceita(self, v: str) -> bool:
        self.visto += 1
        sig, campos = partes_de(v)
        ok = (sig == self.tmpl and len(campos) == self.nf)
        if not ok and self.recusou_em is None:
            self.recusou_em = self.visto
        return ok

    def alimenta(self, values):
        for v in values:
            if not self.aceita(v):
                return False       # recusa NO VALOR — não precisa do resto
        return True


def rodada(cid, desc, values, *, template_dado=None):
    """Compara GLOBAL x DECLARADO na mesma coluna e registra os 4 gates."""
    g_aplica, g_tmpl, g_varridos = gate_global(values)

    # a dica: ou a que o caller deu (para testar dica ERRADA), ou a verdadeira
    dica = template_dado if template_dado is not None else (
        g_tmpl if g_tmpl is not None else partes_de(values[0])[0])
    gd = GateDeclarado(dica)
    d_aplica = gd.alimenta(values)

    # G1 — equivalência (só compara quando a dica é a verdadeira)
    g1 = None if template_dado is not None else (d_aplica == g_aplica)

    # G2 — a decisão no valor k não depende do que vem depois.
    #      Prova: alimentar prefixos crescentes e conferir que a decisão só muda
    #      quando o próprio valor k é visto.
    g2 = True
    for k in range(1, min(len(values), 40) + 1):
        gk = GateDeclarado(dica)
        parcial = gk.alimenta(values[:k])
        esperado = all(GateDeclarado(dica).aceita(v) for v in values[:k])
        if parcial != esperado:
            g2 = False
            break

    # G3 — com dica ERRADA, o mock recusa (não emite wire que perde dado)
    g3 = None
    if template_dado is not None:
        g3 = (d_aplica is False)

    # G4 — custo de varredura
    poupou = g_varridos - (gd.recusou_em or gd.visto)

    # evidência: o wire que o split REAL produz nesta coluna
    w = encode({cid[:12]: values})
    assert decode(w) == {cid[:12]: values}, f"{cid}: RT falhou"
    sb = _struct_split_encode(values, cfg=DEFAULT_PIPELINE, min_len=None)
    (IN / f"{cid}.json").write_text(json.dumps(values[:60], ensure_ascii=False),
                                    encoding="utf-8", newline="")
    (OUT / f"{cid}.tcf").write_text(w, encoding="utf-8", newline="")
    (OUT / f"{cid}.roundtrip.json").write_text(
        json.dumps(decode(w)[cid[:12]][:60], ensure_ascii=False),
        encoding="utf-8", newline="")

    reg = {"caso": cid, "desc": desc, "n": len(values),
           "global_aplica": g_aplica, "global_varridos": g_varridos,
           "declarado_aplica": d_aplica, "declarado_visto": gd.visto,
           "declarado_recusou_em": gd.recusou_em,
           "G1_equivalente": g1, "G2_streaming": g2, "G3_faillloud": g3,
           "G4_poupou_varreduras": poupou,
           "split_real_aplica": sb is not None,
           "dica_errada": template_dado is not None}
    marca = ("DICA ERRADA" if template_dado is not None else
             ("aplica" if g_aplica else "gate recusa"))
    print(f"  {cid:22} n={len(values):>6}  global:{g_varridos:>6} varridos  "
          f"declarado:{gd.recusou_em or gd.visto:>6}  poupou {poupou:>6}  "
          f"G1={g1} G2={g2} G3={g3}  [{marca}]")
    return reg


def main():
    print("=" * 100)
    print("H-13-04 — template DECLARADO dispensa o gate global?")
    print("=" * 100)
    print("G1 equivalência · G2 streaming (decide sem ver o resto) · G3 fail-loud · G4 custo\n")

    res = []
    # ── sintéticos de controle: o gate é lógico, casos mínimos bastam ──
    precos = [f"{p}.{c:02d}" for p in range(10, 40) for c in (0, 50, 99)]
    datas = [f"2026-{m:02d}-{d:02d}" for m in range(1, 13) for d in (5, 12, 19, 26)]
    misto_cedo = ["12.50", "R$ 9"] + [f"{i}.00" for i in range(200)]
    misto_tarde = [f"{i}.00" for i in range(200)] + ["R$ 9"]

    res.append(rodada("s1-decimal", "uniforme, o gate aplica", precos))
    res.append(rodada("s2-data-iso", "uniforme, 3 campos", datas))
    res.append(rodada("s3-quebra-cedo", "diverge no valor 2", misto_cedo))
    res.append(rodada("s4-quebra-tarde", "diverge no ULTIMO valor", misto_tarde))
    res.append(rodada("s5-dica-errada", "dica NAO bate com o dado", precos,
                      template_dado=("", "-", "")))

    # ── dado REAL via Shaper ──
    from shaper import Shaper, ShapeRequest
    r = Shaper().apply(ShapeRequest(dataset="receita-cnpj-enderecos", volume=20000,
                                    seed=42, stratify_by="uf"))
    rows = r.tables[list(r.tables)[0]]
    ceps = [f"{x['cep'][:5]}-{x['cep'][5:]}" for x in rows
            if x.get("cep") and len(x["cep"]) == 8 and x["cep"].isdigit()]
    fones = [f"({x['ddd_1']}) {x['telefone_1']}" for x in rows
             if x.get("ddd_1") and x.get("telefone_1")]
    res.append(rodada("r1-cep-real", "CEP real (uniforme)", ceps))
    res.append(rodada("r2-fone-real", "telefone real (1% SUJO)", fones))

    print("\n" + "=" * 100)
    print("VEREDITO")
    print("=" * 100)
    g1 = [x for x in res if x["G1_equivalente"] is not None]
    g3 = [x for x in res if x["G3_faillloud"] is not None]
    print(f"  G1 equivalência   : {sum(x['G1_equivalente'] for x in g1)}/{len(g1)}")
    print(f"  G2 streaming      : {sum(x['G2_streaming'] for x in res)}/{len(res)}")
    print(f"  G3 fail-loud      : {sum(x['G3_faillloud'] for x in g3)}/{len(g3)}")
    tot_g = sum(x["global_varridos"] for x in res)
    tot_d = sum(x["declarado_recusou_em"] or x["declarado_visto"] for x in res)
    print(f"  G4 varreduras     : global {tot_g:,} · declarado {tot_d:,} "
          f"({(tot_d/tot_g-1)*100:+.1f}%)")

    print("\n  o caso que mostra o ponto:")
    for x in res:
        if x["caso"].startswith(("s3", "s4", "r2")):
            print(f"    {x['caso']:18} global varreu {x['global_varridos']:>6} · "
                  f"declarado parou em {x['declarado_recusou_em']}")

    (AQUI / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                         encoding="utf-8", newline="")
    n = len(list(OUT.glob("*.tcf")))
    assert n == len(res), f"evidencia incompleta: {n}/{len(res)}"
    print(f"\n-> {n} wires + {n} roundtrips em outputs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

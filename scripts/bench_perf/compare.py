"""compare.py — junta a rodada .8 (baseline) com a .9 (candidata) por case_id.

Esta e' a ferramenta que o owner pediu: "o processo precisa repetir de forma
statisticamente similar pro .9 pra gente ter comparacao depois." Ela existe
AGORA (nao em 2027) e ja' e' auto-testada, senao o formato de armazenamento nao
esta' validado.

Tres salvaguardas contra concluir bobagem:

1. JOIN POR case_id, nao por posicao. Coordenada igual = comparavel; ausente de
   um lado = reportado, nunca casado errado.

2. NORMALIZACAO PELOS CAMINHOS DE REFERENCIA. Os caminhos csv/json da stdlib rodam na
   mesma rodada, com codigo identico dos dois lados. Para cada caso, a razao
   caso / referencia de mesma cauda do case_id e' tirada DENTRO de cada rodada, onde a
   maquina cancela por construcao, e o veredito le o delta dessa razao (metodo do lab
   2026-09-01-1937). Os calibradores C1/C2/C3 nao representam o workload: o fator
   deles fabricou +16,6% de regressao falsa, e so' normaliza quando a rodada nao tem
   referencia. Caso sem referencia pareada fica `sem-referencia`, nunca MELHOR/PIOR.

3. SINAL vs RUIDO. Um delta so' e' REAL se passa do maior entre: o MDE do tier
   daquele caso e o noise_floor_cv da rodada; na normalizacao por referencia entram
   tambem o MDE da referencia e o piso da rodada candidata. Abaixo disso: veredito RUIDO, nunca
   "ganho de 3%".

    python -m bench_perf.compare baseline.jsonl candidato.jsonl
    python -m bench_perf.compare --self baseline.jsonl   # auto-teste: tudo IGUAL
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def _carrega(p: Path):
    regs, resumo = [], {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():                              # pula linha em branco (robusto)
            continue
        regs.append(json.loads(line))
    rp = p.with_suffix(".run.json")
    if rp.exists():
        resumo = json.loads(rp.read_text(encoding="utf-8"))
    return {r["case_id"]: r for r in regs}, resumo


def _fator_calibrador(res_a: dict, res_b: dict) -> float:
    """mediana(C_b / C_a) sobre os 3 calibradores. 1.0 se faltar."""
    ca, cb = res_a.get("calibradores", {}), res_b.get("calibradores", {})
    razoes = []
    for nome in ca:
        if nome in cb:
            a = ca[nome].get("point_ns")
            b = cb[nome].get("point_ns")
            if a and b:
                razoes.append(b / a)
    return statistics.median(razoes) if razoes else 1.0


#: caminhos da stdlib que rodam na mesma rodada, com codigo identico dos dois lados
REFERENCIAS = ("csv-ref", "json-ref-str", "json-ref-typed", "json-ref-nested")


def _caminho(cid: str) -> str:
    return cid.split("|", 1)[0]


def _deltas_por_referencia(cid: str, ra: dict, rb: dict, validos: set) -> list:
    """(delta da razao caso / referencia, MDE da referencia), um por referencia de mesma cauda.

    Dentro de cada rodada a razao cancela a maquina por construcao: se o lado B inflou
    tudo, caso e referencia inflam juntos e a razao nao se move. Pareamento do lab
    2026-09-01-1937: `<referencia>|<cauda do case_id>`."""
    cauda = cid.split("|", 1)[1] if "|" in cid else ""
    fora = []
    for ref in REFERENCIAS:
        rid = f"{ref}|{cauda}"
        if rid not in validos:
            continue
        ta, tb = ra[cid]["encode"]["point_ns"], rb[cid]["encode"]["point_ns"]
        fa, fb = ra[rid]["encode"]["point_ns"], rb[rid]["encode"]["point_ns"]
        if ta and tb and fa and fb:
            fora.append(((tb / fb) / (ta / fa) - 1.0, ra[rid]["encode"].get("mde_pct", 10.0)))
    return fora


def _limiar(rec_a: dict, res_a: dict) -> float:
    """maior entre MDE do tier e noise_floor da rodada (fracao)."""
    mde = rec_a.get("encode", {}).get("mde_pct", 10.0) / 100.0
    piso = res_a.get("drift", {}).get("noise_floor_cv", 0.0) or 0.0
    return max(mde, piso)


def _adj(res: dict) -> tuple:
    """(validade_de_dados, termico) de um resumo, robusto ao schema.

    run-v3 (novo): `status` = validade ('completo'/'parcial'), `runner_thermal_status`
    = termico ('estavel'/'termicamente-suspeito') — ORTOGONAIS.
    run-v2 (antigo): `status` podia ser 'termicamente-reprovado' (fundia os dois);
    mapeia p/ (completo, termicamente-suspeito) — o termico era o unico problema."""
    st = res.get("status")
    thermal = res.get("runner_thermal_status")
    if thermal is None:  # schema antigo
        if st == "termicamente-reprovado":
            return "completo", "termicamente-suspeito"
        return st, "estavel"
    return st, thermal


def _protocolo_igual(ea: dict, eb: dict) -> bool:
    """Mesmo tier E mesmo n? (parecer §2) Mudar repeticao/tier sem registrar produz
    um join sintaticamente valido e cientificamente DESIGUAL. Nota: com `samples_ns`
    crus (R1) da' pra re-estatisticar a um n comum — refinamento futuro; aqui, o
    conservador: nao compara celula de protocolo divergente."""
    return ea.get("tier") == eb.get("tier") and ea.get("n") == eb.get("n")


def comparar(base: Path, cand: Path) -> dict:
    ra, resa = _carrega(base)
    rb, resb = _carrega(cand)
    fator = _fator_calibrador(resa, resb)

    # GUARDA DE RUN (parecer §2): matriz dos DOIS lados.
    ma = resa.get("manifest", {}).get("cases_sha256")
    mb = resb.get("manifest", {}).get("cases_sha256")
    matriz_igual = (ma is not None) and (ma == mb)        # matriz != => join INVALIDO

    # VALIDADE (dados) e TERMICO (estabilidade) sao ORTOGONAIS (parecer 2340 §1).
    # Validade bloqueia; termico so' avisa (--strict-thermal bloqueia). _adj le os
    # dois de forma robusta (schema novo run-v3; compat com run-v2 antigo).
    val_a, term_a = _adj(resa)
    val_b, term_b = _adj(resb)
    validade = {"baseline": val_a, "candidato": val_b}
    termico = {"baseline": term_a, "candidato": term_b}

    # GUARDA DE PLANO (Fase 3b): a cadencia e' parte da identidade. Mesma matriz mas
    # planos/intencoes diferentes => subconjuntos/aceites diferentes => join enganoso.
    # Um lado sem plano (None) so' casa com o outro sem plano.
    pa, pb = resa.get("plano"), resb.get("plano")
    plano_sha_a = (pa or {}).get("sha")
    plano_sha_b = (pb or {}).get("sha")
    plano_igual = (plano_sha_a == plano_sha_b)            # cobre None==None (ambos sem plano)
    intencao = {"baseline": (pa or {}).get("intencao"), "candidato": (pb or {}).get("intencao")}
    intencao_igual = (intencao["baseline"] == intencao["candidato"])

    so_base = sorted(set(ra) - set(rb))
    so_cand = sorted(set(rb) - set(ra))
    linhas = []
    contagem = {"MELHOR": 0, "PIOR": 0, "IGUAL": 0, "RUIDO": 0, "protocolo-desigual": 0,
                "n/a": 0, "controle": 0, "sem-referencia": 0}
    comuns = sorted(set(ra) & set(rb))
    validos = {cid for cid in comuns
               if ra[cid].get("status") == "ok" and rb[cid].get("status") == "ok"
               and ra[cid].get("encode") and rb[cid].get("encode")}
    # REFERENCIA quando a rodada tem caminho de referencia valido dos dois lados; senao o
    # fator do calibrador, que mantem comparaveis as matrizes sem referencia.
    modo = "referencia" if any(_caminho(c) in REFERENCIAS for c in validos) else "calibrador"
    deriva = []                                           # delta cru das referencias
    for cid in comuns:
        a, b = ra[cid], rb[cid]
        ea, eb = a.get("encode"), b.get("encode")
        if cid not in validos:
            contagem["n/a"] += 1
            continue
        if not _protocolo_igual(ea, eb):                  # tier/n divergem => nao compara
            contagem["protocolo-desigual"] += 1
            linhas.append({"case_id": cid, "verdict": "protocolo-desigual",
                           "tier_base": ea.get("tier"), "tier_cand": eb.get("tier"),
                           "n_base": ea.get("n"), "n_cand": eb.get("n")})
            continue
        ta, tb = ea["point_ns"], eb["point_ns"]
        delta_cal = (tb / fator - ta) / ta if ta else 0.0  # >0 = candidato mais lento
        pares = []
        if modo == "referencia":
            if _caminho(cid) in REFERENCIAS:              # o controle nao recebe veredito
                contagem["controle"] += 1
                deriva.append((tb - ta) / ta if ta else 0.0)
                continue
            pares = _deltas_por_referencia(cid, ra, rb, validos)
            if not pares:                                 # sem par de mesma cauda: indecidivel
                contagem["sem-referencia"] += 1
                linhas.append({"case_id": cid, "verdict": "sem-referencia",
                               "delta_calibrador_pct": round(delta_cal * 100, 2)})
                continue
            delta = statistics.median([d for d, _ in pares])
            # a razao depende do caso, da referencia e das duas rodadas: o limiar e' o maior
            # entre os MDEs envolvidos e os pisos de ruido dos DOIS lados
            lim = max(_limiar(a, resa), _limiar(a, resb), max(m for _, m in pares) / 100.0)
        else:
            delta = delta_cal
            lim = _limiar(a, resa)
        if abs(delta) <= lim:
            verdict = "RUIDO" if abs(delta) > 0.005 else "IGUAL"
        else:
            verdict = "PIOR" if delta > 0 else "MELHOR"
        contagem[verdict] += 1
        linhas.append({"case_id": cid, "delta_pct": round(delta * 100, 2),
                       "delta_calibrador_pct": round(delta_cal * 100, 2),
                       "pares_referencia": len(pares),
                       "limiar_pct": round(lim * 100, 2), "verdict": verdict,
                       "base_ns": ta, "cand_ns_norm": round(tb / fator)})
    return {
        "fator_calibrador": round(fator, 4),
        "normalizacao": modo,
        "deriva_referencias_pct": (round(statistics.median(deriva) * 100, 2)
                                   if deriva else None),
        "matriz_igual": matriz_igual,
        "matriz_sha": {"base": str(ma)[:12], "cand": str(mb)[:12]},
        "plano_igual": plano_igual, "intencao_igual": intencao_igual,
        "plano_sha": {"base": str(plano_sha_a)[:12], "cand": str(plano_sha_b)[:12]},
        "intencao": intencao,
        "validade": validade,          # dados: bloqueia se != completo
        "status_termico": termico,     # estabilidade: so' avisa (--strict-thermal bloqueia)
        "contagem": contagem,
        "so_no_baseline": so_base, "so_no_candidato": so_cand,
        "linhas": sorted(linhas, key=lambda x: x.get("delta_pct", 0)),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Compara baseline .8 vs candidato .9")
    ap.add_argument("baseline")
    ap.add_argument("candidato", nargs="?")
    ap.add_argument("--self", dest="autoteste", action="store_true",
                    help="auto-teste: baseline vs si mesmo -> tudo IGUAL, fator 1.0")
    ap.add_argument("--dev", action="store_true",
                    help="rebaixa o fail-closed p/ aviso (desenvolvimento) — NAO use p/ evidencia")
    ap.add_argument("--strict-thermal", action="store_true",
                    help="tambem BLOQUEIA se algum lado for termicamente-suspeito (precisao). "
                         "Default: termico e' so' aviso (comparacao first-order .8<->.9).")
    args = ap.parse_args(argv)

    if not args.autoteste and not args.candidato:
        ap.error("informe o <candidato> (ou use --self p/ auto-teste)")
    base = Path(args.baseline)
    cand = base if args.autoteste else Path(args.candidato)
    r = comparar(base, cand)

    # GUARDA DE RUN FAIL-CLOSED: BLOQUEIA (evidencia invalida) por matriz/plano/intencao
    # divergentes OU VALIDADE-DE-DADOS != completo (parcial/sem-resumo). O TERMICO NAO
    # bloqueia por default — first-order aceita suspeito (parecer 2340 §1); so' bloqueia
    # em --strict-thermal. --dev rebaixa tudo p/ aviso.
    invalido = []
    if not r["matriz_igual"]:
        invalido.append(f"matriz diferente ({r['matriz_sha']['base']} vs {r['matriz_sha']['cand']})")
    if not r["plano_igual"]:
        invalido.append(f"plano diferente ({r['plano_sha']['base']} vs {r['plano_sha']['cand']})")
    if not r["intencao_igual"]:
        invalido.append(f"intencao diferente ({r['intencao']['baseline']} vs {r['intencao']['candidato']})")
    for lado, st in r["validade"].items():
        if st != "completo":
            invalido.append(f"dados {lado}={st or 'sem-resumo'}")
    if args.strict_thermal:
        for lado, st in r["status_termico"].items():
            if st != "estavel":
                invalido.append(f"termico {lado}={st} (--strict-thermal)")
    if invalido and not args.dev:
        print("!! COMPARACAO RECUSADA (fail-closed): " + " · ".join(invalido))
        print("   corrija/re-rode os dois lados aceitos, ou use --dev p/ inspecionar (nao-evidencia).")
        return 2
    for m in invalido:
        print(f"!! AVISO (--dev): {m}")
    # AVISO termico (nao bloqueia): first-order tolera suspeito, mas registra o caveat.
    suspeito = [lado for lado, st in r["status_termico"].items() if st != "estavel"]
    if suspeito and not args.strict_thermal:
        print(f"!! AVISO termico (first-order, nao bloqueia): {', '.join(suspeito)} "
              f"termicamente-suspeito — deltas pequenos podem ser ruido; use --strict-thermal p/ precisao.")

    if r["normalizacao"] == "referencia":
        deriva = r["deriva_referencias_pct"]
        deriva_txt = "n/d" if deriva is None else f"{deriva:+.1f}%"
        print(f"normalizacao: razao caso/referencia dentro da rodada (deriva das referencias "
              f"{deriva_txt}; fator_calibrador {r['fator_calibrador']}, so' informativo)")
    else:
        print(f"normalizacao: calibrador, a rodada nao tem caminho de referencia "
              f"(fator_calibrador = {r['fator_calibrador']})")
    print(f"veredictos: {r['contagem']}")
    if r["contagem"]["protocolo-desigual"]:
        pd = [ln for ln in r["linhas"] if ln["verdict"] == "protocolo-desigual"][:3]
        print(f"  protocolo-desigual ({r['contagem']['protocolo-desigual']}): "
              + ", ".join(f"{ln['case_id'][:24]}(tier {ln['tier_base']}!={ln['tier_cand']} "
                          f"n {ln['n_base']}!={ln['n_cand']})" for ln in pd))
    if r["so_no_baseline"]:
        print(f"  so' no baseline ({len(r['so_no_baseline'])}): {r['so_no_baseline'][:3]}...")
    if r["so_no_candidato"]:
        print(f"  so' no candidato ({len(r['so_no_candidato'])}): {r['so_no_candidato'][:3]}...")
    comparaveis = [ln for ln in r["linhas"] if "delta_pct" in ln]
    melhores = [ln for ln in comparaveis if ln["verdict"] == "MELHOR"][:5]
    piores = [ln for ln in comparaveis if ln["verdict"] == "PIOR"][-5:]
    for ln in melhores:
        print(f"  MELHOR {ln['delta_pct']:+6.1f}% (lim {ln['limiar_pct']}%)  {ln['case_id'][:50]}")
    for ln in piores:
        print(f"  PIOR   {ln['delta_pct']:+6.1f}% (lim {ln['limiar_pct']}%)  {ln['case_id'][:50]}")

    if args.autoteste:
        # auto-teste: mesmo arquivo -> matriz igual, fator 1.0, zero PIOR/MELHOR/protocolo,
        # E os DADOS validos (validade completo). Um run 'parcial' nao passa nem contra si;
        # termico-suspeito NAO reprova (e' first-order, aviso).
        run_ok = r["validade"]["baseline"] == "completo"
        ok = (r["matriz_igual"] and r["fator_calibrador"] == 1.0 and run_ok
              and r["contagem"]["PIOR"] == 0 and r["contagem"]["MELHOR"] == 0
              and r["contagem"]["protocolo-desigual"] == 0)
        print(f"AUTO-TESTE: {'PASSOU' if ok else 'FALHOU'}"
              f"{'' if run_ok else ' (dados nao-completos: validade='+str(r['validade']['baseline'])+')'}")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

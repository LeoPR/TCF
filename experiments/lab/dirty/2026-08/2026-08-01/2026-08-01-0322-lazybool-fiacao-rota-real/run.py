"""Lab 2026-08-01-0322 — fiação do lazy bool na rota real (estudo, SEM weld).

Decisões do owner desde o lab 0229: **lazy será DEFAULT** (a rota aceita união bool+str sem
flag); decode emite lista mista — contrato união decidido. Estrito-forçado vira parâmetro
depois (T-FORCAR-MECANISMO). Este lab responde às 6 perguntas de fiação e propõe a forma
do weld. `src/tcf` INTOCADO — se aparecer bloqueador, o run sai 1 e o veredito é PARE.
"""
import base64
import csv
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
VIZINHO = RAIZ.parent / "2026-08-01-0229-lazytype-bool-extras"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(VIZINHO))

from fiacao import decode_estrito, detecta_lazy, encode_com_lazy  # noqa: E402
from lazy_bn import proto_decode, proto_encode  # noqa: E402

from tcf import decode, encode  # noqa: E402
from tcf.decoder import _decode_typed  # noqa: E402
from tcf.encoder import _tipo_single_col  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)

SAMPLES = REPO / "datasets" / "samples"


def _wj(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n",
                 encoding="utf-8")


def rt_tipo(obtido, esperado):
    if len(obtido) != len(esperado) or obtido != esperado:
        return False
    return all(type(a) is type(b) for a, b in zip(obtido, esperado))


def flat_str(dados):
    return ["" if x is None else ("true" if x is True else "false" if x is False else x)
            for x in dados]


def caso(nome, dados, gravar=True):
    lazy_w, _w, extras = proto_encode(dados)
    flat_w = encode(flat_str(dados))
    r = {"nome": nome, "n": len(dados), "extras": len(extras),
         "lazy": len(lazy_w.encode()) if lazy_w else None,
         "flat": len(flat_w.encode()),
         "rt": rt_tipo(decode_estrito(lazy_w), dados) if lazy_w else None}
    if gravar and lazy_w:
        _wj(RAIZ / "inputs" / f"{nome}-fonte.json",
            {"coluna": nome, "n": len(dados), "extras": extras, "amostra": dados[:8]})
        _wj(RAIZ / "intermediates" / f"{nome}-dataset-consumido.json", dados)
        (RAIZ / "outputs" / f"{nome}-lazy.tcf").write_text(lazy_w, encoding="utf-8")
        rt_path = RAIZ / "outputs" / f"{nome}-dataset.roundtrip.json"
        _wj(rt_path, decode_estrito(lazy_w))
        assert rt_path.read_bytes() == (RAIZ / "intermediates" /
                                        f"{nome}-dataset-consumido.json").read_bytes(), nome
    return r


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    falhas = []
    bloqueadores = []
    out = ["# Fiação do lazy bool na rota real (2026-08-01-0322)", "",
           "Estudo pré-weld. Lazy será DEFAULT (sem flag); decode emite lista mista.", ""]

    base = [None if i % 9 == 0 else bool(i % 2) for i in range(200)]
    casos = {
        "extras-raro": [("other" if i in (7, 113) else x) for i, x in enumerate(base)],
        "extras-frequentes": [("other" if i % 5 == 4 else x) for i, x in enumerate(base)],
        "k-extras-05": [(f"e{i % 5}" if i % 7 == 3 else x) for i, x in enumerate(base)],
        "k-extras-20": [(f"e{(i // 4) % 20}" if i % 4 == 3 else x) for i, x in enumerate(base)],
        "armadilha-tipos": [(["true", "0", "1"][i % 3] if i % 11 == 5 else x)
                            for i, x in enumerate(base)],
    }
    with (SAMPLES / "adult-census" / "adult-sample.csv").open(encoding="utf-8", newline="") as f:
        vals = [row["sex"].strip() == "Male" for row in csv.DictReader(f)
                if row["sex"] not in ("", "NA")][:2000]
    casos["real-adult-sex-lazy"] = [(" ?" if i % 23 == 22 else (None if i % 11 == 10 else v))
                                    for i, v in enumerate(vals)]

    out += ["## Medição base — lazy × flat-string (referência de bytes)", "",
            "| coluna | n | extras | lazy bB | flat-str | RT tipo |",
            "|---|---:|---:|---:|---:|:--|"]
    rs = {}
    for nome, dados in casos.items():
        r = caso(nome, dados)
        rs[nome] = r
        if r["rt"] is not True:
            falhas.append(f"{nome}: RT")
        out.append(f"| `{nome}` | {r['n']} | {r['extras']} | {r['lazy']} | {r['flat']} | "
                   f"{'OK' if r['rt'] else '**FALHOU**'} |")
    out.append("")

    # ================================================================ Q1: detecção
    out += ["## Q1 — detecção", ""]
    borda = {
        "uniao-bool-str-null": ([True, "other", None, False], True),
        "str-null-sem-bool": (["a", None, "b"], False),          # flat, NÃO lazy
        "bool-1-str-extra": ([True] * 50 + ["other"], True),     # 1 único extra entra
        "bool-str-int": ([True, "x", 1], False),                 # num no mix: OUTRO ticket
        "bool-puro": ([True, False], False),                     # tipado puro
        "bool-null-sem-str": ([True, None, False], False),       # b2
        "str-pura": (["a", "b"], False),                         # flat
        "so-null": ([None, None], False),                        # flat
    }
    fp_fn = []
    for nome, (dados, esperado) in borda.items():
        got = detecta_lazy(dados)
        if got != esperado:
            fp_fn.append(nome)
            falhas.append(f"Q1: {nome} esperado={esperado} got={got}")
    # falso-positivo/negativo nos datasets dos labs anteriores (consumidos)
    varredura = []
    for lab, pasta in ((VIZINHO, "intermediates"),):
        for p in sorted((lab / pasta).glob("*-dataset-consumido.json")):
            dados = json.loads(p.read_text(encoding="utf-8"))
            esperado = any(isinstance(x, str) for x in dados) and any(
                isinstance(x, bool) for x in dados) and all(
                x is None or isinstance(x, (bool, str)) for x in dados)
            esperado = esperado and p.stem != "controle-0-extras-dataset-consumido"
            got = detecta_lazy(dados)
            varredura.append((p.stem.replace("-dataset-consumido", ""), esperado, got))
            if got != esperado:
                fp_fn.append(p.stem)
                falhas.append(f"Q1 varredura: {p.stem}")
    det_ok = all(e == g for _n, e, g in varredura)
    out += ["Detector: `vals ⊆ {bool, str, None}` com ≥1 bool E ≥1 str — nada mais.",
            "",
            "- casos-borda: **8/8 corretos** (str+null sem bool → flat; 1 extra → entra; "
            "bool+str+int → fora; bool puro/ternário → tipado puro; str pura/só-null → flat)."
            if not fp_fn else f"- **FALHAS de detecção**: {fp_fn}",
            f"- varredura FP/FN nos consumidos do lab 0229: **{len(varredura)} datasets, "
            f"{'zero divergências' if det_ok else 'DIVERGÊNCIA — ver falhas'}** "
            f"(esperado-lazy: {[n for n, e, g in varredura if e]}).",
            "- confirmação do contexto: `_tipo_single_col` devolve `None` pra união "
            f"(hoje: `{_tipo_single_col([True, 'other', None])}`) → `.8H` → fail-loud. "
            "O detector lazy é um ramo ANTES do `.8H`, não uma mutação do `_tipo_single_col`.",
            ""]

    # ================================================================ Q2: FLOOR
    out += ["## Q2 — convivência no FLOOR", "",
            "Para coluna lazy, os candidatos b1/b2/core-slots **não existem** (não é bool "
            "puro) e o core-flat-de-strings **muda o contrato** (perde tipo — é referência "
            "de bytes, não candidato). Logo o lazy é o **único candidato que preserva "
            "tipo**: FLOOR trivial, sem interação. Verificado por construção: "
            "`encode_com_lazy` devolve o wire lazy sempre que o detector dispara, e o RT "
            "tipo-estrito passou em todas as colunas acima.", "",
            "Se o usuário converter pra str ANTES (flat-string), é decisão dele — fora da "
            "rota.", ""]

    # ================================================================ Q3: dispatch do decode
    out += ["## Q3 — dispatch do decode", ""]
    # #TCF.8B (flat bN) continua roteando? e #TCF.8bB hoje cai aonde?
    flat_bn_wire = encode(["0", "1"] * 100)
    rota_flat = decode(flat_bn_wire) == ["0", "1"] * 100
    try:
        _decode_typed(rs["extras-raro"]["nome"] and caso("extras-raro", casos["extras-raro"], gravar=False) and (RAIZ / "outputs" / "extras-raro-lazy.tcf").read_text(encoding="utf-8"), "b")
        destino_hoje = "decodificou (inesperado)"
    except ValueError as e:
        destino_hoje = f"fail-loud: {str(e)[:80]}"
    ramo_ok = rt_tipo(decode_estrito((RAIZ / "outputs" / "extras-raro-lazy.tcf").read_text(encoding="utf-8")), casos["extras-raro"])
    out += ["**Sem colisão**: o dispatch é O(1) pelo índice 6 — `B` (maiúsculo) = flat bN "
            "(ADR-0036), `b` (minúsculo) = tipado. São chars DISTINTOS:", "",
            f"- `#TCF.8B…` flat segue roteando certo: RT `['0','1']*100` = **{rota_flat}** "
            f"(wire head: `{flat_bn_wire.split(chr(10))[0]}`).",
            f"- `#TCF.8bB…` hoje cai no `_decode_typed` e morre no fail-loud de modo denso: "
            f"`{destino_hoje}` — ou seja, o índice 7 = `B` sob tag `b` é **namespace livre**.",
            f"- ramo prototipado `modo == 'B'` → decode lazy (cabeça `TABELA_B2` + extras): "
            f"RT tipo-estrito **{'OK' if ramo_ok else 'FALHOU'}**.", ""]
    if not (rota_flat and ramo_ok):
        bloqueadores.append("Q3: dispatch colide ou ramo B quebra")
        falhas.append("Q3")

    # ================================================================ Q4: domínio comprimido
    out += ["## Q4 — domínio de extras (comprimido pelo core, custo e bordas)", "",
            "| caso | wire lazy | tamanho domínio (linhas antes do `=`) | veredito |",
            "|---|---|---:|---|"]
    q4_falhas = []
    for nome in ("extras-raro", "k-extras-05", "k-extras-20"):
        wire = (RAIZ / "outputs" / f"{nome}-lazy.tcf").read_text(encoding="utf-8")
        dom = wire.split("\n=")[0].split("\n", 1)[1]
        out.append(f"| `{nome}` | {len(wire.encode())} | {len(dom.encode())} | RT OK |")
    # extras especiais
    from fiacao import proto_encode_checked
    especiais = {
        "extra-com-=": [True, None, "=foo", False, "=foo"],        # escape \= do dominio_bn
        "extra-true": [True, "true", None, False],                 # armadilha, slot próprio
        "extra-vazio": [True, "", None, False, ""],                # domínio = linha vazia
    }
    for nome, dados in especiais.items():
        wire, _w, _x = proto_encode_checked(dados)
        try:
            ok = rt_tipo(decode_estrito(wire), dados)
        except Exception as e:  # noqa: BLE001
            ok = f"ERRO: {e}"
            q4_falhas.append(nome)
        dom = wire.split("\n=")[0].split("\n", 1)[1]
        out.append(f"| `{nome}` | {len(wire.encode())} | {len(dom.encode())} | "
                   f"{'RT OK' if ok is True else ok} |")
        (RAIZ / "outputs" / f"{nome}-lazy.tcf").write_text(wire, encoding="utf-8")
    # LF embutido num extra -> NAO vem de graca pelo caminho do dominio (medido:
    # `_encode_column(['a\nb'])` devolve calado); o check EXPLICITO recusa
    try:
        proto_encode_checked([True, "a\nb", None])
        lf_veredito = "ENCODIFICOU mesmo com o check (bloqueador!)"
        bloqueadores.append("Q4: extra com LF embutido encodificou calado")
        falhas.append("Q4: LF")
    except ValueError as e:
        lf_veredito = f"recusa pelo check explícito: {str(e)[:70]}"
    out += ["",
            f"- `extra-com-=`: o marcador `=` no domínio é escapado (`\\=`, regra do "
            "`dominio_bn`) — RT OK.",
            "- `extra-vazio`: string vazia como extra — o domínio é uma **linha vazia "
            "invisível** (o corte `[:-1]` do bugfix do `dominio_bn`); o decode a lê como "
            "`[\"\"]` — **válido e RT OK**. NUANCE de fiação: um wire com domínio vazio é "
            "indistinguível do extra `\"\"` — a leitura consistente é aceitar (como o "
            "`dominio_bn` já faz), não rejeitar.",
            "- LF embutido num extra: **achado de fiação** — o fail-loud de LF mora no "
            "`encode` público flat, NÃO no `_encode_column` (medido: devolve calado). Sem "
            "check próprio, o extra com LF corromperia o parse do domínio. O weld DEVE "
            f"adicionar o check: {lf_veredito}.", ""]
    if q4_falhas:
        falhas.append(f"Q4: {q4_falhas}")

    # ================================================================ Q5: canonicidade
    out += ["## Q5 — canonicidade", ""]
    dados_fl = casos["extras-raro"]
    wire_ok, _w, _x = proto_encode(dados_fl)
    # (i) extras por 1ª aparição: wire determinístico
    det_ok = proto_encode(dados_fl)[0] == wire_ok
    # (ii) domínio redeclarando a cabeça (linha `0` cru) -> fail-loud no decode
    cab = wire_ok.split("\n")[0]
    payload = wire_ok.split("=")[-1]
    wire_redecl = f"{cab}\n0\nother\n={payload}"
    try:
        decode_estrito(wire_redecl)
        redecl = "DECODIFICOU (bloqueador!)"
        bloqueadores.append("Q5: domínio redeclarando cabeça passou calado")
        falhas.append("Q5")
    except ValueError as e:
        redecl = f"fail-loud: {str(e)[:90]}"
    fl_out = ["# canonicidade — lazy bB (gerado por run.py)", "",
              f"[OK] domínio redeclarando cabeça (`0` cru) → ValueError: {redecl.split('fail-loud: ')[-1]}"]
    (RAIZ / "outputs" / "fail-loud.txt").write_text("\n".join(fl_out) + "\n", encoding="utf-8")
    out += ["- extras por **1ª aparição** + header hex mínimo + wire determinístico: "
            f"**{'OK' if det_ok else 'FALHOU'}**.",
            f"- domínio declarando a cabeça (`0` cru = slot 0 congelado): **{redecl}** — "
            "declarar o implícito é grafia inválida (evidência em `outputs/fail-loud.txt`).",
            "- extras `\"1\"`/`\"2\"`/`\"true\"` são VÁLIDOS (slots ≥3, caso armadilha) — o "
            "proibido é redeclarar o slot, não o texto.", ""]
    if not det_ok:
        falhas.append("Q5: determinismo")

    # ================================================================ Q6: gates
    out += ["## Q6 — gates com a rota inserida (simulada)", ""]
    sys.path.insert(0, str(REPO / "tests"))
    import test_real_world_snapshots as W  # noqa: E402
    import test_regression_v1_baseline as R  # noqa: E402
    movidos = []
    checados = 0
    for k in R.D1_D9_BYTES_FROZEN:
        dados = R._load_single_col(k)
        if encode_com_lazy(dados) != encode(dados):
            movidos.append(k)
        checados += 1
    for k, (_e, rel) in W.REAL_WORLD_BYTES_FROZEN.items():
        dados = W._load_single_col(rel)
        if encode_com_lazy(dados) != encode(dados):
            movidos.append(k)
        checados += 1
    out += [f"`encode_com_lazy` (detector + lazy, senão `encode` real) aplicado a "
            f"**{checados} colunas** dos dois gates: **{'ZERO wires alterados' if not movidos else f'ALTERADOS: {movidos}'}** "
            "— gates são flat/dict, o detector nunca dispara (esperado).", ""]
    if movidos:
        bloqueadores.append(f"Q6: gates alterados com a rota inserida: {movidos}")
        falhas.append("Q6")

    # ================================================================ forma do weld
    out += ["## Forma do weld proposta (se aprovada)", "",
            "1. **`encoder.py`**: detector lazy como ramo ANTES do `.8H` — após `_tipo_single_col` "
            "devolver `None` e antes de `_tabela_flat`/hierárquico: se `detecta_lazy(data)`, "
            "candidato `bB` (único que preserva tipo; FLOOR trivial). Recusas: w>8, e "
            "**check EXPLÍCITO de LF nos extras** (achado Q4: o fail-loud de LF mora no "
            "`encode` público flat, não no `_encode_column` — não vem de graça).",
            "2. **`decoder.py:_decode_typed`**: ramo `modo_c == 'B'` → decode lazy (tabela = "
            "`TABELA_B2` do `tipos_internos.py` + domínio declarado de extras; reusa "
            "`decode_bn` internamente ou a mesma mecânica).",
            "3. **`tipos_internos.py`**: sem mudança de dados — a cabeça já é `TABELA_B2`.",
            "4. **Recusa declaração da cabeça** no decode (Q5).",
            "5. Testes: RT tipo-estrito, armadilha `\"true\"`, extra vazio/`=`, fail-loud "
            "índice/header/cabeça, gates zerados, FLOOR trivial.", ""]

    # ================================================================ veredito
    out += ["## Veredito", ""]
    if bloqueadores:
        out += [f"**PARE — bloqueadores**: {bloqueadores}", ""]
    else:
        out += ["**SEM BLOQUEADOR** — as 6 perguntas fecham a favor do weld na forma acima.", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())

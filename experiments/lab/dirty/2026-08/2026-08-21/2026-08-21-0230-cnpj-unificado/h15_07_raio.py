"""H-15-07: o raio exato do bug, e o que o conserto `$`->`\\Z` custaria."""
import random
import re
import sys
from dataclasses import replace

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[5] / "src"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from tcf.natures import SPEC_CPF, SPEC_CNPJ, SPEC_IP, SPEC_DATA_ISO   # noqa: E402
from tcf.natures.templated_checked import _cnpj_check_fn             # noqa: E402

LF = "\n"
ESPECS = [("cpf", SPEC_CPF), ("cnpj", SPEC_CNPJ), ("ip", SPEC_IP),
          ("data-iso", SPEC_DATA_ISO)]


def rt_ok(spec, v):
    return spec.decode_value(spec.encode_value(v)[0]) == v


print("=" * 88)
print("1) O RAIO: quais specs perdem o dado, e em quais formas")
print("=" * 88)
amostras = {
    "cpf": ["529.982.247-25", "111.444.777-35"],
    "cnpj": ["11.222.333/0001-81", "12.ABC.345/01DE-35"],
    "ip": ["192.168.0.1", "0.0.0.0", "192.168.001.001"],
    "data-iso": ["2026-08-21"],
}
for nome, spec in ESPECS:
    perdem = [v for v in amostras[nome] if not rt_ok(spec, v + LF)]
    ok = [v for v in amostras[nome] if rt_ok(spec, v + LF)]
    print(f"  {nome:9} PERDE em {len(perdem)}/{len(amostras[nome])}: {perdem}")
    if ok:
        print(f"  {'':9} escapa em: {ok}  (cai em outro status antes da regex)")
print("\n  data-iso escapa porque o classify dele CHECA O COMPRIMENTO explicitamente")
print("  (`len(v) != 10` -> length_wrong) — a defesa que os outros nao tem.")

print("\n" + "=" * 88)
print("2) O CONSERTO: `$` -> `\\Z`. Ele resolve? E quanto custa?")
print("=" * 88)
# aplica o conserto em copias dos specs (sem tocar src/)
CONS = []
for nome, spec in ESPECS:
    if not hasattr(spec, "regex") or spec.regex is None:
        CONS.append((nome, spec, None))
        continue
    pat = spec.regex.pattern
    novo = re.compile(pat[:-1] + r"\Z") if pat.endswith("$") else None
    CONS.append((nome, spec, replace(spec, regex=novo, name=nome + "-fix",
                                     wire_id="x" + nome[:4].replace("-", ""))
                 if novo else None))

for nome, spec, fix in CONS:
    if fix is None:
        print(f"  {nome:9} (regex nao termina em `$` — nada a consertar)")
        continue
    antes = sum(1 for v in amostras[nome] if not rt_ok(spec, v + LF))
    depois = sum(1 for v in amostras[nome] if not rt_ok(fix, v + LF))
    print(f"  {nome:9} valores que perdiam: {antes} -> depois do fix: {depois}")

print("\n" + "=" * 88)
print("3) O CUSTO: o fix muda BYTE de algum valor SEM LF?")
print("=" * 88)
rng = random.Random(11)
corpus = {"cpf": [], "cnpj": [], "ip": [], "data-iso": []}
for _ in range(3000):
    b = [rng.randint(0, 9) for _ in range(9)]
    d = SPEC_CPF.check_fn(b)
    s = "".join(map(str, b + d))
    corpus["cpf"].append(f"{s[:3]}.{s[3:6]}.{s[6:9]}-{s[9:]}")
    b2 = [rng.randint(0, 9) for _ in range(12)]
    s2 = "".join(map(str, b2 + _cnpj_check_fn(b2)))
    corpus["cnpj"].append(f"{s2[:2]}.{s2[2:5]}.{s2[5:8]}/{s2[8:12]}-{s2[12:]}")
    corpus["ip"].append(".".join(str(rng.randint(0, 255)) for _ in range(4)))
corpus["cpf"] += ["", "abc", "529.982.247-99", "52998224725"]
corpus["cnpj"] += ["", "abc", "12.abc.345/01de-35", "11222333000181"]
corpus["ip"] += ["", "x", "999.1.1.1", "192.168.001.001"]

total_div = 0
for nome, spec, fix in CONS:
    if fix is None:
        continue
    div = sum(1 for v in corpus[nome]
              if spec.encode_value(v) != fix.encode_value(v))
    total_div += div
    print(f"  {nome:9} {len(corpus[nome]):>5,} valores sem LF  ->  divergencias: {div}")
print(f"\n  TOTAL de divergencias em valores sem LF: {total_div}")
print("  (esperado 0: `\\Z` e `$` sao IDENTICOS quando nao ha LF no fim)")

print("\n" + "=" * 88)
print("4) ALCANCE: da' pra chegar nisso pela API publica?")
print("=" * 88)
from tcf import encode                                              # noqa: E402
try:
    encode(["11.222.333/0001-81" + LF], nature=SPEC_CNPJ)
    print("  tcf.encode ACEITOU — alcancavel pela porta principal")
except ValueError as e:
    print(f"  tcf.encode RECUSA: {str(e)[:88]}")
print("  MAS `from tcf.natures import encode_value` e' API publica documentada")
print("  (esta' no __all__ e no docstring do modulo) e nao tem essa guarda.")

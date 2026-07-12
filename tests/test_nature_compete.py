"""FLOOR — a nature COMPETE no min(tcf,raw,dict,split) (T-SPEC-DEEPDIVE-08 §5.1).

Decisão do owner (2026-07-12): a nature deixa de ser pré-transformação FORÇADA
de camada-0 e passa a ser CANDIDATO por-coluna. Contrato safe-by-construction:
com nature_per_col, a coluna NUNCA fica maior que sem — se a nature não ajuda,
o encode mantém o original e NÃO emite o `:id`. Resolve a regressão F4 (nature
CNPJ piorava +7339B em receita real) sem perder o ganho onde a nature vence.
"""
from __future__ import annotations

import random

import pytest

from tcf import SPEC_CNPJ, SPEC_CPF, decode, encode
from tcf.side_outputs import SideOutputs


def _cpf_dv(b9):
    ds = [int(c) for c in b9]
    d1 = (sum(d * w for d, w in zip(ds, range(10, 1, -1))) * 10) % 11 % 10
    d2 = (sum(d * w for d, w in zip(ds + [d1], range(11, 1, -1))) * 10) % 11 % 10
    return f"{d1}{d2}"


def _cpf(b9):
    return f"{b9[:3]}.{b9[3:6]}.{b9[6:9]}-{_cpf_dv(b9)}"


def _col(vals, spec=None):
    side = SideOutputs()
    kw = {"nature_per_col": {"c": spec}} if spec else {}
    encode({"c": vals}, side_outputs=side, **kw)
    pc = side.per_col["c"]
    return pc.emitted_bytes, pc.emitted_mode


def _clustered_cpfs(n=400, seed=1):
    rng = random.Random(seed)
    start = rng.randint(0, 999000000)
    return [_cpf(f"{start + i*3:09d}") for i in range(n)]


def _random_cpfs(n=400, seed=2):
    rng = random.Random(seed)
    return [_cpf(f"{rng.randint(0, 999999999):09d}") for _ in range(n)]


class TestNatureCompeteFloor:
    def test_never_worse_than_baseline_clustered(self):
        # regime onde a nature PIORAVA (estrutura inter-linha): agora <= baseline
        col = _clustered_cpfs()
        base, _ = _col(col)
        nat, _ = _col(col, SPEC_CPF)
        assert nat <= base, f"nature piorou: {nat} > {base} (FLOOR quebrado)"

    def test_still_helps_random(self):
        # regime onde a nature AJUDA (sem estrutura): continua ganhando
        col = _random_cpfs()
        base, _ = _col(col)
        nat, _ = _col(col, SPEC_CPF)
        assert nat < base, "nature devia vencer em random"

    def test_id_dropped_when_nature_loses(self):
        # nature perde -> :id NÃO é emitido; decode sem spec devolve o original
        col = _clustered_cpfs()
        blob = encode({"c": col}, nature_per_col={"c": SPEC_CPF})
        meta = blob.split("\n", 1)[0]
        if _col(col, SPEC_CPF)[0] == _col(col)[0]:
            assert ":cpf" not in meta            # perdeu/empatou -> sem :id
        assert decode(blob)["c"] == col          # RT sempre

    def test_id_kept_when_nature_wins(self):
        col = _random_cpfs()
        blob = encode({"c": col}, nature_per_col={"c": SPEC_CPF})
        assert ":cpf" in blob.split("\n", 1)[0]  # venceu -> :id presente
        assert decode(blob)["c"] == col

    def test_rt_both_regimes_and_specs(self):
        for col, spec in [(_clustered_cpfs(), SPEC_CPF), (_random_cpfs(), SPEC_CPF)]:
            blob = encode({"c": col}, nature_per_col={"c": spec})
            assert decode(blob)["c"] == col

    def test_multi_col_mixed(self):
        # tabela com uma coluna onde nature ajuda e outra onde piora
        table = {"help": _random_cpfs(50), "hurt": _clustered_cpfs(50)}
        base = encode(table)
        got = encode(table, nature_per_col={"help": SPEC_CPF, "hurt": SPEC_CPF})
        assert len(got.encode()) <= len(base.encode())   # nunca pior no total
        assert decode(got, nature_per_col={"help": SPEC_CPF, "hurt": SPEC_CPF}) == table

    def test_apply_rate_reported_even_when_nature_loses(self):
        # a telemetria da transformação (apply_rate) segue reportada
        side = SideOutputs()
        encode({"c": _clustered_cpfs()}, side_outputs=side,
               nature_per_col={"c": SPEC_CPF})
        na = side.nature_apply
        assert na and "c" in na and na["c"]["apply_rate"] == 1.0

    def test_receita_real_no_longer_regresses(self):
        # o achado F4: nature CNPJ piorava em receita real ordenada. Agora <=.
        pytest.importorskip("sqlite3")
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
        try:
            from dataset_reader import DatasetReader
            r = DatasetReader("receita-cnpj")
            rows = r.rows("estabelecimentos", limit=2000)
            r.close()
        except Exception:
            pytest.skip("hub receita-cnpj indisponível (requires_data)")
        cnpj = [x["cnpj"] for x in rows]
        base, _ = _col(cnpj)
        nat, _ = _col(cnpj, SPEC_CNPJ)
        assert nat <= base, f"nature CNPJ ainda regride: {nat} > {base}"

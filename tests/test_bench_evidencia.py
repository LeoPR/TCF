"""Guarda do runner do material comprobatório (T-QA-8 F1 — scripts/bench_evidencia.py).

O runner é FERRAMENTA de medição: precisa de validação própria antes de uso em
validação (regra de tools científicos). Aqui: contrato do registro + o pino
rápido (D17a) — a validação COMPLETA dos 3 pinos é `--validate-pins` (F1-4).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from bench_evidencia import (  # noqa: E402
    PIN_D17A, load_csv_multi, run_case, serialize_side, validate_pins,
)
from bench_evidencia_probes import env_fingerprint, measure_repeat  # noqa: E402


class TestRunnerContract:
    def test_record_fields_and_rt(self):
        rec = run_case("mini", {"a": ["x", "y"], "b": ["1", "2"]}, n=2, warmup=1)
        assert rec["schema"] == "evidencia-0.8/v1"
        assert rec["rt_ok"] is True and rec["rt_mode"] == "identidade"
        assert rec["deterministic"] is True
        assert rec["bytes"]["total"] > 0
        assert rec["bytes"]["header"] + rec["bytes"]["body"] == rec["bytes"]["total"]
        assert rec["timing"]["encode"]["median_ns"] > 0
        assert rec["timing"]["decode"]["n"] == 2
        assert rec["env"]["tcf_version"] is not None
        assert "probes" in rec["env"]
        # side: modos por coluna presentes (BUG-07 welded)
        assert set(rec["side"]["multi_info"]["col_modes"]) == {"a", "b"}

    def test_transform_uses_content_plus_idempotence(self):
        rec = run_case("mini-sort", {"k": ["b", "a", "b"], "v": ["1", "2", "3"]},
                       {"sort_by": "k"}, n=1, warmup=0)
        assert rec["rt_ok"] is True
        assert rec["rt_mode"] == "conteudo-sob-transformacao + idempotencia-2a-geracao"

    def test_transform_content_gate_catches_constant_decode(self, monkeypatch):
        # achado da verificação F1: idempotência sozinha aceitava decode
        # constante — o cheque de CONTEÚDO (multiset de linhas) tem que pegar
        import bench_evidencia as be
        const = {"k": ["z", "z", "z"], "v": ["9", "9", "9"]}
        monkeypatch.setattr(be, "decode", lambda blob: dict(const))
        rec = be.run_case("evil", {"k": ["b", "a", "c"], "v": ["1", "2", "3"]},
                          {"sort_by": "k"}, n=1, warmup=0)
        assert rec["rt_ok"] is False and "bytes" not in rec

    def test_stamp_header_classified(self):
        rec = run_case("stamped", ["alpha", "beta", "alpha"],
                       {"stamp": True}, n=1, warmup=0)
        assert rec["rt_ok"] and rec["bytes"]["header"] == len("#TCF.8\n")

    def test_rt_gate_no_numbers_without_rt(self):
        # registro de RT quebrado NAO pode carregar bytes/timing — o gate é o
        # contrato central (§2.1). Forçamos via monkeypatch do decode? Não:
        # basta conferir a forma do registro de erro construído pelo caminho
        # normal com um caso IMPOSSÍVEL de quebrar — então validamos o schema
        # do sucesso e confiamos no branch de erro por inspeção + pins.
        rec = run_case("single", ["a", "b", "a"], n=1, warmup=0)
        assert rec["rt_ok"] and "error" not in rec

    def test_d17a_pin_fast(self):
        cols = load_csv_multi(ROOT / "datasets" / "synthetic"
                              / "D17a-multi-column-mixed.csv")
        rec = run_case("D17a", cols, n=1, warmup=0)
        assert rec["bytes"]["total"] == PIN_D17A, (
            "runner divergiu do pino D17a — bug do RUNNER (F1-4)")

    def test_serialize_side_is_json_safe(self):
        import json
        from tcf.side_outputs import SideOutputs
        from tcf import encode
        side = SideOutputs()
        encode({"a": ["x", "x", "x"], "b": ["1", "2", "3"]}, side_outputs=side)
        json.dumps(serialize_side(side))    # não pode estourar


class TestProbesPortable:
    def test_measure_repeat_shape(self):
        m = measure_repeat(lambda: sum(range(100)), n=3, warmup=1)
        assert m["n"] == 3 and m["median_ns"] >= m["min_ns"]
        assert m["p95_ns"] <= m["max_ns"]

    def test_env_fingerprint_declares_probes(self):
        env = env_fingerprint()
        assert env["python"] and env["cpu_count"]
        assert set(env["probes"]) == {"wall", "cpu", "heap", "rss"}
        # rss pode ser None (plataforma sem sonda) — mas a CHAVE existe sempre


class TestPinsFull:
    def test_validate_pins_full(self):
        # F1-4 completo (D1-D9 + D17a + real-world 2k×3). Custo ~segundos;
        # é o gate que autoriza o runner a produzir material.
        assert validate_pins(verbose=False), (
            "runner divergiu da régua (D1-D9/D17a/real-world) — bug do RUNNER")

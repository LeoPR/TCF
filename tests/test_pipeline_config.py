"""Tests PipelineConfig (T-CODE-LAYERED-PIPELINE Fase 1).

Valida toggle declarativo das camadas TCF:
- pre_pass: ON/OFF (analyze + cadence + min_len)
- obat_shape_preserve: ON/OFF (processar_with_hint vs processar)
- hcc_seq_rle: ON/OFF (M10 vs M9 puro)

Critical: default config = M10 canonical byte-canonical.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tcf import encode, decode, PipelineConfig


ROOT = Path(__file__).resolve().parent.parent
DATASETS = ROOT / "datasets" / "synthetic"
LAB_DATA = ROOT / "experiments" / "lab" / "dirty" / "2026-05-24-cpf-templated-checked" / "data"


def _load_d17a() -> dict[str, list[str]]:
    with (DATASETS / "D17a-multi-column-mixed.csv").open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        cols = {h: [] for h in header}
        for row in r:
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


class TestPipelineConfigDefault:
    """Default config = comportamento canonical M10."""

    def test_default_all_layers_on(self):
        cfg = PipelineConfig()
        assert cfg.pre_pass is True
        assert cfg.obat_shape_preserve is True
        assert cfg.hcc_seq_rle is True

    def test_default_is_frozen(self):
        cfg = PipelineConfig()
        with pytest.raises(Exception):  # FrozenInstanceError
            cfg.pre_pass = False

    def test_d17a_default_invariant(self):
        """D17a com default config = 0.7 default 307B (era 322; ADR-0024)."""
        cols = _load_d17a()
        text = encode(cols)  # implicit default
        assert len(text.encode("utf-8")) == 307

    def test_d17a_explicit_default_byte_identical(self):
        """encode(data) == encode(data, layers=PipelineConfig())."""
        cols = _load_d17a()
        text_implicit = encode(cols)
        text_explicit = encode(cols, layers=PipelineConfig())
        assert text_implicit == text_explicit


class TestPipelineConfigToggleHCCSeqRLE:
    """Toggle hcc_seq_rle controla M10 vs M9 comportamento."""

    def test_disable_seq_rle_changes_output(self):
        cols = _load_d17a()
        text_m10 = encode(cols, layers=PipelineConfig(hcc_seq_rle=True))
        text_m9 = encode(cols, layers=PipelineConfig(hcc_seq_rle=False))
        assert text_m10 != text_m9

    def test_disable_seq_rle_rt_preserved(self):
        cols = _load_d17a()
        text = encode(cols, layers=PipelineConfig(hcc_seq_rle=False))
        decoded = decode(text)
        assert decoded == cols

    def test_seq_rle_dramatic_in_subnet(self):
        """D-IP-subnet 1000: seq-RLE essencial pra compressao boa."""
        if not (LAB_DATA / "D-IP-subnet.csv").exists():
            pytest.skip("D-IP-subnet.csv nao disponivel")
        with (LAB_DATA / "D-IP-subnet.csv").open(encoding="utf-8") as f:
            r = csv.reader(f)
            next(r)
            ips = [row[0] for row in r if row]

        text_seq = encode(ips, layers=PipelineConfig(hcc_seq_rle=True))
        text_no_seq = encode(ips, layers=PipelineConfig(hcc_seq_rle=False))

        bytes_seq = len(text_seq.encode("utf-8"))
        bytes_no_seq = len(text_no_seq.encode("utf-8"))

        # Seq-RLE deve ser dramaticamente menor (sub-exp 14: 560B vs 15747B)
        assert bytes_seq < bytes_no_seq // 10, (
            f"seq-RLE deveria ser muito menor: "
            f"com={bytes_seq}B, sem={bytes_no_seq}B"
        )

        # RT preservado em ambos
        assert decode(text_seq) == ips
        assert decode(text_no_seq) == ips


class TestPipelineConfigTogglePrePass:
    """Toggle pre_pass disabled = sem cadence + min_len=3."""

    def test_disable_pre_pass_rt_preserved(self):
        cols = _load_d17a()
        text = encode(cols, layers=PipelineConfig(pre_pass=False))
        decoded = decode(text)
        assert decoded == cols

    def test_disable_pre_pass_changes_output_in_cadenced(self):
        """D17a tem timestamp/id cadenced — pre_pass desligado deve mudar bytes."""
        cols = _load_d17a()
        text_with = encode(cols, layers=PipelineConfig(pre_pass=True))
        text_without = encode(cols, layers=PipelineConfig(pre_pass=False))
        assert text_with != text_without


class TestPipelineConfigToggleOBATShapePreserve:
    """Toggle obat_shape_preserve disabled = sempre processar canonical."""

    def test_disable_obat_shape_rt_preserved(self):
        cols = _load_d17a()
        text = encode(cols, layers=PipelineConfig(obat_shape_preserve=False))
        decoded = decode(text)
        assert decoded == cols


class TestPipelineConfigMultipleToggles:
    """Combinacoes de toggles."""

    def test_all_disabled_rt(self):
        """Pior caso: tudo desligado, deve preservar RT mesmo assim."""
        cols = _load_d17a()
        text = encode(cols, layers=PipelineConfig(
            pre_pass=False,
            obat_shape_preserve=False,
            hcc_seq_rle=False,
        ))
        decoded = decode(text)
        assert decoded == cols

    def test_ablation_each_layer_individually(self):
        """Ablacao: cada layer off mantem RT."""
        cols = _load_d17a()
        configs = [
            PipelineConfig(pre_pass=False),
            PipelineConfig(obat_shape_preserve=False),
            PipelineConfig(hcc_seq_rle=False),
        ]
        for cfg in configs:
            text = encode(cols, layers=cfg)
            decoded = decode(text)
            assert decoded == cols, f"RT FAIL com cfg={cfg}"


class TestPipelineConfigSingleColAndMulti:
    """layers= funciona em ambos list e dict input."""

    def test_single_col_default(self):
        values = ["abc", "abcd", "abcde"]
        text = encode(values, layers=PipelineConfig())
        assert decode(text) == values

    def test_single_col_no_seq_rle(self):
        values = ["abc", "abcd", "abcde"]
        text = encode(values, layers=PipelineConfig(hcc_seq_rle=False))
        assert decode(text) == values

    def test_multi_col_default(self):
        table = {"a": ["1", "2"], "b": ["x", "y"]}
        text = encode(table, layers=PipelineConfig())
        assert decode(text) == table

    def test_multi_col_no_seq_rle(self):
        table = {"a": ["1", "2"], "b": ["x", "y"]}
        text = encode(table, layers=PipelineConfig(hcc_seq_rle=False))
        assert decode(text) == table


class TestPipelineConfigD1D9Invariant:
    """CRITICAL: D1-D9 baseline preservado com default."""

    @pytest.mark.parametrize("name", [
        "D1-emails-simples", "D2-emails-quote-id", "D3-stress-substring",
        "D4-caos-mix", "D5-padroes-multiplos", "D6-poucos-em-ruido",
        "D7-aninhamento", "D8-cabeca-cauda", "D9-frequencia-alta",
    ])
    def test_default_matches_baseline(self, name):
        """Default config = M10 byte-canonical em cada D1-D9."""
        path = DATASETS / f"{name}.csv"
        with path.open(encoding="utf-8") as f:
            r = csv.reader(f)
            next(r)
            values = [row[0] for row in r if row]

        text_implicit = encode(values)
        text_explicit = encode(values, layers=PipelineConfig())
        assert text_implicit == text_explicit, (
            f"D1-D9 byte-canonical broken with default PipelineConfig em {name}"
        )

        # RT
        assert decode(text_explicit) == values

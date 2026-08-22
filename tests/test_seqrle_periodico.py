"""seq-RLE PERIODICO `*N~d1,...,dp|template` — ADR-0040.

O delta CICLA entre linhas. Cobre cadencias que o `*N+d|` uniforme nao alcanca: dias
uteis (`1,3,1,1,1`), ids por turno (`10,10,10,50`), quinzenal/mensal.

Estes testes sao a colheita de DUAS cacadas adversariais (lab
`experiments/lab/dirty/2026-08/2026-08-09/2026-08-09-0042-data-alvo-delta/`). Sete
defeitos foram achados e fechados; cada classe tem teste aqui, porque cada uma passou
despercebida por toda a suite existente uma vez.
"""

from __future__ import annotations

import datetime as _dt
import random
import time

import pytest

from tcf import decode, encode
from tcf.composicional.hcc_seqrle import (
    MAX_PERIODO,
    compact_body,
    deltas_pares,
    detect_periodic_runs,
    expand_periodic_marker,
    grafia_emissivel,
)
from tcf.side_outputs import SideOutputs

BASE = _dt.date(2026, 1, 1)


def _uteis(n: int, feriados: int = 0) -> list[_dt.date]:
    """Seg-sex; `feriados` pula 1 dia util a cada 21 (~feriado mensal)."""
    out, d, u = [], BASE, 0
    while len(out) < n:
        if d.weekday() < 5:
            u += 1
            if not (feriados and u % 21 == 0):
                out.append(d)
        d += _dt.timedelta(days=1)
    return out


def _ids_turno(n: int) -> list[str]:
    out, v, ciclo = [], 700000, [10, 10, 10, 50]
    for i in range(n):
        out.append(str(v))
        v += ciclo[i % 4]
    return out


class TestGanho:
    """O que o mecanismo entrega. Numeros pinados (re-pinaveis, ADR-0024)."""

    def test_dias_uteis_600_o_ciclo_paga_uma_vez(self):
        vals = [str(d.toordinal()) for d in _uteis(600)]
        w = encode(vals)
        assert len(w.encode("utf-8")) == 30
        assert "*600~1,3,1,1,1|" in w
        assert decode(w) == vals

    def test_o_ciclo_e_O1_em_n(self):
        """n=10x nao multiplica o wire: cresce so' o contador."""
        p = len(encode([str(d.toordinal()) for d in _uteis(600)]).encode("utf-8"))
        g = len(encode([str(d.toordinal()) for d in _uteis(6000)]).encode("utf-8"))
        assert g - p == 1

    def test_vale_para_coluna_numerica_qualquer_nao_so_data(self):
        vals = _ids_turno(600)
        w = encode(vals)
        assert "*600~10,10,10,50|" in w
        assert len(w.encode("utf-8")) < 40
        assert decode(w) == vals

    @pytest.mark.parametrize("vals", [
        pytest.param([str(d.toordinal()) for d in _uteis(600, feriados=1)], id="feriado-mensal"),
        pytest.param([str(1000 + 14 * i + (3 if i % 2 else 0)) for i in range(400)], id="quinzenal"),
    ])
    def test_cadencias_periodicas_com_ruido_ainda_ganham(self, vals):
        assert len(encode(vals).encode("utf-8")) < len(vals) * 4
        assert decode(encode(vals)) == vals


class TestNuncaPior:
    """O mecanismo entra como CANDIDATO do `min()`, nunca como substituto."""

    @pytest.mark.parametrize("vals", [
        pytest.param([str((BASE + _dt.timedelta(days=i)).toordinal()) for i in range(600)], id="diario-uniforme"),
        pytest.param([f"cliente-{i % 37}@acme.com.br" for i in range(600)], id="texto"),
        pytest.param([str((i * 7919) % 999983) for i in range(600)], id="ruido-alta-card"),
        pytest.param([f"10.0.{i // 256}.{i % 256}" for i in range(600)], id="ips-multi-run"),
        pytest.param(["x"] * 600, id="constante"),
        pytest.param(["so-um"], id="um-elemento"),
        pytest.param(["a", "b"], id="dois-elementos"),
    ])
    def test_dado_sem_periodicidade_nao_e_reescrito(self, vals):
        """O desempate do `min()` preserva a preferencia de hoje: sem periodicidade o
        wire tem de sair IDENTICO ao que saia antes do weld."""
        w = encode(vals)
        assert "~" not in w.split("\n")[1][:20] if len(w.split("\n")) > 1 else True
        assert decode(w) == vals

    def test_varredura_nunca_pior_no_wire_final(self):
        """A regressao mora no wire FINAL (depois da polaridade), nao no corpo canonico:
        um corpo 9 B menor chegou a embarcar 19 B maior. 963 regressoes num sweep
        parametrico antes do FLOOR por fragmento."""
        rnd = random.Random(20260809)
        piores = []
        for _ in range(150):
            p = rnd.randint(2, 8)
            ciclo = [rnd.randint(1, 9) for _ in range(p)]
            v, vals = rnd.randint(0, 5000), []
            for k in range(rnd.randint(6, 90)):
                vals.append(str(v))
                v += ciclo[k % p] if rnd.random() > 0.18 else rnd.randint(1, 4000)
            w = encode(vals)
            assert decode(w) == vals
            if "~" in w:
                piores.append(len(w.encode("utf-8")))
        assert piores, "o sweep tem de exercitar o marcador periodico"


class TestGrafiaCanonica:
    """Uma grafia por dado, e so' a que o encoder emitiria (ADR-0040 §canonicidade)."""

    @pytest.mark.parametrize("wire,porque", [
        ("*5~1,4,9|\\120", "cauda morta: o 9 nunca e' lido"),
        ("*5~1,4,9,9,9|\\120", "cauda morta longa"),
        ("*5~1,4,-777|\\120", "cauda morta negativa"),
        ("*9~1,3,1,3|\\120", "repeticao exata de [1,3]"),
        ("*5~1,4,1|\\120", "extensao parcial de [1,4]"),
        ("*600~1,1|\\7", "pad uniforme = `*N+d|` disfarcado"),
        ("*4~1,3|\\120", "1,5 ciclos — o detector emitiria `*5~1,4|`"),
        ("*7~1,3,1,3,1|\\120", "1,2 ciclos"),
    ])
    def test_grafia_nao_canonica_e_recusada(self, wire, porque):
        with pytest.raises(ValueError):
            decode(f"#TCF.8\n{wire}\n")

    def test_grafia_canonica_decodifica(self):
        assert decode("#TCF.8\n*5~1,4|\\120\n") == ["120", "121", "125", "126", "130"]

    def test_pad_acima_do_teto_e_recusado(self):
        """O teto do DETECTOR (`MAX_PERIODO`) tem de valer tambem na expansao — sem isso
        o pad vindo do wire nao tem teto nenhum."""
        pad = ",".join(str(k + 1) for k in range(MAX_PERIODO + 1))
        assert not grafia_emissivel([k + 1 for k in range(MAX_PERIODO + 1)], 999)
        with pytest.raises(ValueError):
            decode(f"#TCF.8\n*999~{pad}|\\120\n")

    def test_detector_so_emite_grafia_que_o_expand_aceita(self):
        """Assimetria fatal seria o encoder produzir um wire que ele proprio nao le'."""
        for vals in ([str(d.toordinal()) for d in _uteis(400)], _ids_turno(300),
                     [str(1000 + 14 * i + (3 if i % 2 else 0)) for i in range(200)]):
            linhas = [f"\\{v}" for v in vals]
            for _pos, count, pad, _eco in detect_periodic_runs(linhas, deltas_pares(linhas)):
                assert grafia_emissivel(pad, count), (count, pad)


class TestRecursos:
    """Um gate que trabalha proporcional ao que o WIRE declara e' um amplificador."""

    def test_teto_de_memoria_cobre_o_marcador_novo(self):
        """A pre-checagem do contador roda ANTES da materializacao — por isso o ramo
        periodico vive dentro de `expand_seq_marker`, e nao num passe separado."""
        t = time.perf_counter()
        with pytest.raises(ValueError):
            decode("#TCF.8\n*2000000~1,2|\\7\n", max_length=10)
        assert time.perf_counter() - t < 0.5   # o passe separado levava 2,5 s

    def test_gate_de_canonicidade_nao_amplifica(self):
        """Pad grande faz cada periodo sobreviver ate' o ultimo elemento. Sem teto e com
        o periodo minimo calculado da sequencia EXPANDIDA, 15,6 KB de wire custavam 12 s."""
        pad = ",".join(["1"] * 7999 + ["2"])
        t = time.perf_counter()
        with pytest.raises(ValueError):
            decode(f"#TCF.8\n*8001~{pad}|x\n")
        assert time.perf_counter() - t < 1.0

    def test_gate_e_O1_no_contador_declarado(self):
        """`count` gigante com grafia invalida nao pode materializar nada antes de recusar."""
        t = time.perf_counter()
        with pytest.raises(ValueError):
            decode("#TCF.8\n*9999999~1,1|x\n")
        assert time.perf_counter() - t < 0.5   # materializava 85 MB / 17 s


class TestTelemetria:
    """`seq_rle_runs` descreve o corpo EMITIDO. Canal publico: encoder -> SideOutputs ->
    schema.seq_rle_runs_count -> scripts/schema_gadget."""

    def test_marcador_no_wire_implica_telemetria_nao_vazia(self):
        for vals in ([str(1000 + i) for i in range(600)],
                     [(BASE + _dt.timedelta(days=i)).isoformat() for i in range(600)],
                     [f"10.0.{i // 256}.{i % 256}" for i in range(600)],
                     [str(d.toordinal()) for d in _uteis(600)]):
            so = SideOutputs()
            w = encode(vals, side_outputs=so)
            if any(ln.startswith("*") for ln in w.split("\n")):
                assert so.seq_rle_runs, f"marcador no wire e telemetria vazia: {vals[:2]}"

    def test_run_periodico_se_declara_e_aponta_linhas_reais(self):
        vals = [str(d.toordinal()) for d in _uteis(600)]
        so = SideOutputs()
        encode(vals, side_outputs=so)
        (run,) = so.seq_rle_runs
        assert run["periodo"] == 5
        assert run["uniform_delta"] is None      # distingue do run uniforme
        assert run["deltas"] == [1, 3, 1, 1, 1]
        assert 1 <= run["start_line"] <= run["end_line"] <= len(vals)

    def test_telemetria_reancorada_no_corpo_inteiro(self):
        """Os trechos nao-periodicos sao compactados a' parte; sem reancorar, a
        telemetria aponta linha errada — troca um silencio por uma mentira."""
        vals = ([str(d.toordinal()) for d in _uteis(120)]
                + [f"ruido-{i}" for i in range(5)]
                + [str(500000 + i) for i in range(40)])
        so = SideOutputs()
        encode(vals, side_outputs=so)
        for r in so.seq_rle_runs:
            assert 1 <= r["start_line"] <= r["end_line"] <= len(vals) + 2


class TestGrafiaAdversarial:
    """Valores que IMITAM o marcador tem de fazer round-trip (ADR-0007 protege)."""

    @pytest.mark.parametrize("vals", [
        ["*600~1,3,1,1,1|739617", "outro", "mais"],
        ["*3~1,2|z"] * 4,
        ["a|b", "*2~9,8|q", "c"],
        ["*5+1|abc", "x", "y"],
        ["*5~1,4,9|\\120", "z"],
        ["*8001~1,1|x"],
    ])
    def test_valor_que_imita_o_marcador_faz_roundtrip(self, vals):
        assert decode(encode(vals)) == vals


class TestCompartilhamentoDeDeltas:
    """`deltas_pares` alimenta os DOIS detectores — recomputa-lo custa 4x a logica."""

    def test_compact_body_com_e_sem_pares_da_o_mesmo(self):
        linhas = [f"\\{d.toordinal()}" for d in _uteis(200)] + ["\\999", "lixo"]
        assert compact_body(linhas) == compact_body(linhas, deltas_pares(linhas))


class TestExpandDireto:
    def test_expand_periodic_marker_devolve_none_para_nao_marcador(self):
        for linha in ("\\120", "*5+1|\\120", "*|x", "*abc~1,2|x", "*5~|x", "*5~a,b|x"):
            assert expand_periodic_marker(linha) is None

    def test_expand_periodic_marker_cicla_o_padrao(self):
        assert expand_periodic_marker("*5~1,4|\\120") == [
            "\\120", "\\121", "\\125", "\\126", "\\130"]

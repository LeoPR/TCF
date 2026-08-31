"""A superfície carrega só o presente, e a era anterior tem prazo escrito.

Invariante I1 do `AGENTS.md`. O owner precisou apontar o mesmo defeito três vezes (a última
em 2026-08-31, um `#TCF.7` no `datasets/coverage-matrix.md`), então ele virou teste em vez de
disciplina.

**A era vem do registro** (`src/tcf/wire.py`), nunca de uma constante escrita aqui. O registro
tem no máximo duas linhas, e é isso que dá a janela que o owner pediu:

- a era **vigente** pode ser citada sempre;
- a era **anterior** pode ser citada até a data de sunset dela, que foi escrita no commit que
  promoveu a sucessora. É o período de comparativo migratório;
- qualquer coisa mais velha reprova na hora.

Sem a janela, o teste seria binário e a virada de era reprovaria todas as citações de uma vez,
sem fila e sem prazo, que é o oposto do pedido. Com ela, a virada não quebra nada, e o
vermelho chega sozinho na data escrita.

**O relógio é o commit, não a máquina.** A data comparada é a do `HEAD` (`git log -1
--format=%cs`), com hoje como reserva. Assim rodar a suíte num commit de três meses atrás não
falha retroativamente: cada commit é julgado pela época dele. É o mesmo espírito do `go.mod`
escolhendo o default do `GODEBUG` pela linha de versão do artefato. Sem isso, uma política que
promete preservar a história poluiria a história.

**O que NÃO é varrido**, e por quê:
  - `docs/adr/`: ADR aceito nunca é editado (AGENTS §"o que não se apaga");
  - `docs/archive/`, `docs/findings/`, `docs/workbench/`, `experiments/`, `old/`: traço,
    append-only, e é onde a versão antiga é o assunto;
  - `CHANGELOG.md`: registrar a história é a função dele;
  - `src/`: o decoder precisa nomear o que ele recusa, e I5 proíbe mexer sem aprovação;
  - `tickets/`: um ticket sobre remover legado tem de poder nomear o legado;
  - `tests/`: este arquivo, entre outros, cita as grafias de propósito.

**O opt-out** é `<!-- legado-ok: motivo -->`, e ele cobre o parágrafo que abre. Com data,
`<!-- legado-ok: motivo (até AAAA-MM-DD) -->`, ele é dívida com vencimento e reprova depois
dela. Sem data, é isenção permanente, e só se justifica quando nomear a forma morta é a
**função** da linha: a lista de "não usar" do vocabulário, e a linha da spec que documenta o
erro nomeado que o decoder levanta.
"""

from __future__ import annotations

import datetime as _dt
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tcf.wire import ERA_ATUAL, ERA_EM_SUNSET  # noqa: E402

MORTO = re.compile(r"#TCF\.(\d+)")
MARCADOR_OK = "legado-ok:"
VALIDADE = re.compile(r"legado-ok:[^>]*?\(at[ée]\s*(\d{4}-\d{2}-\d{2})\s*\)")
AVISO_DIAS = 30

SUPERFICIE = [
    "README.md", "README.pt-BR.md", "README.pypi.md", "MAP.md", "INDEX.md",
    "ROADMAP.md", "STATUS.md", "CONTRIBUTING.md", "CONTRIBUTING.pt-BR.md",
    "docs", "datasets",
]
FORA = {"adr", "archive", "findings", "workbench", "_archive"}


def _hoje() -> _dt.date:
    """A data do commit do HEAD, para a história não ficar vermelha retroativamente."""
    try:
        saida = subprocess.run(["git", "log", "-1", "--format=%cs"], cwd=ROOT,
                               capture_output=True, text=True, timeout=10)
        if saida.returncode == 0 and saida.stdout.strip():
            return _dt.date.fromisoformat(saida.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return _dt.date.today()


HOJE = _hoje()


def _era_tolerada() -> int | None:
    """A era anterior, enquanto a janela dela não venceu."""
    if ERA_EM_SUNSET is None or not ERA_EM_SUNSET.sunset:
        return None
    return ERA_EM_SUNSET.n if HOJE <= _dt.date.fromisoformat(ERA_EM_SUNSET.sunset) else None


TOLERADA = _era_tolerada()


def _paginas() -> list[Path]:
    fora: list[Path] = []
    for alvo in SUPERFICIE:
        p = ROOT / alvo
        if p.is_file():
            fora.append(p)
            continue
        if not p.is_dir():
            continue
        for f in sorted(p.rglob("*.md")):
            if FORA & {x.name for x in f.parents}:
                continue
            fora.append(f)
    return fora


@pytest.mark.parametrize("pagina", _paginas(), ids=lambda p: p.relative_to(ROOT).as_posix())
def test_pagina_nao_cita_era_expirada(pagina: Path):
    """Só a era vigente, e a anterior enquanto a janela dela estiver aberta."""
    vivas = {ERA_ATUAL.n} | ({TOLERADA} if TOLERADA is not None else set())
    ruins, vencidos = [], []
    marcado_ate: _dt.date | None = None
    marcado = False

    for i, ln in enumerate(pagina.read_text(encoding="utf-8").splitlines(), 1):
        if MARCADOR_OK in ln:
            marcado = True
            m = VALIDADE.search(ln)
            marcado_ate = _dt.date.fromisoformat(m.group(1)) if m else None
            if marcado_ate is not None and HOJE > marcado_ate:
                vencidos.append(f"    linha {i}: o opt-out venceu em {marcado_ate}")
            continue
        if not ln.strip():
            marcado, marcado_ate = False, None
            continue
        if marcado and not (marcado_ate is not None and HOJE > marcado_ate):
            continue
        for n in MORTO.findall(ln):
            if int(n) not in vivas:
                ruins.append(f"    linha {i}: {ln.strip()[:100]}")
                break

    janela = f" (a era `#TCF.{TOLERADA}` está na janela até {ERA_EM_SUNSET.sunset})" if TOLERADA else ""
    assert not ruins and not vencidos, (
        f"{pagina.relative_to(ROOT).as_posix()} cita era que já expirou{janela}:\n"
        + "\n".join(ruins + vencidos) + "\n"
        "  Reveja: refaça a medição sob a era vigente, apague, ou (se nomear a forma morta "
        "for a função da linha) marque com `<!-- legado-ok: motivo -->`."
    )


def test_avisa_antes_de_a_janela_vencer(capsys):
    """Trinta dias antes do sunset o teste PASSA e diz o que vai vencer.

    O vermelho continua chegando sozinho na data, mas não chega sem ter avisado. É o único
    grama de processo que a política adiciona, e ele existe para que a data não pegue a
    virada no meio de outro trabalho.
    """
    if ERA_EM_SUNSET is None or not ERA_EM_SUNSET.sunset:
        pytest.skip("nenhuma era em sunset: janela fechada")
    fim = _dt.date.fromisoformat(ERA_EM_SUNSET.sunset)
    faltam = (fim - HOJE).days
    if 0 <= faltam <= AVISO_DIAS:
        with capsys.disabled():
            print(f"\n  [era] `#TCF.{ERA_EM_SUNSET.n}` deixa de ser citável em {fim} "
                  f"({faltam} dia(s)). Depois disso, toda citação dela reprova.")
    assert True


def test_a_varredura_encontra_o_que_deveria():
    """Se o extrator quebrar, ele passa vazio e mente."""
    assert ERA_ATUAL.n >= 8, f"era vigente lida do codigo veio {ERA_ATUAL!r}"
    assert len(_paginas()) >= 30, f"so' {len(_paginas())} paginas varridas; a lista encolheu?"

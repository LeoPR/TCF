"""O registro da era do wire, e a catraca que impede a dívida de crescer.

`src/tcf/wire.py` é o lugar único onde a era do formato vive. Dois testes o sustentam:

1. **O limite de duas eras.** A política só entrega limpeza se a janela for N-1. Se o
   registro virar tabela de N eras, a bagagem que ela existe para cortar voltou pela porta
   que ela abriu, e ninguém percebe até a próxima virada.

2. **A catraca dos literais.** No dia em que este registro nasceu havia 73 grafias
   executáveis de `#TCF.<n>` espalhadas por 14 arquivos do core. Reescrever as 73 num commit
   seria risco alto sem ganho proporcional, então a dívida não se paga de uma vez: ela para
   de crescer. Cada literal novo tem de ser justificado ou derivado do registro, e o número
   só desce. É o antipadrão que o Parquet confessa na própria documentação (carimbar a versão
   no arquivo e não honrar) que este teste existe para impedir.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tcf.wire import ERA_ATUAL, ERA_EM_SUNSET, WIRE_ERAS, caminho_de_volta  # noqa: E402

# A dívida no dia em que o registro nasceu (2026-08-31). Este número NUNCA sobe.
TETO_DE_LITERAIS = 73


def _literais_de_era(caminho: Path) -> int:
    """Grafias `#TCF.<n>` em constante de string EXECUTÁVEL, não em prosa.

    Docstring e comentário ficam de fora de propósito: eles não decidem comportamento, e
    quem cuida da prosa é o `test_superficie_sem_versao_morta`.
    """
    try:
        arv = ast.parse(caminho.read_text(encoding="utf-8"))
    except SyntaxError:
        return 0
    n = 0
    for no in ast.walk(arv):
        if isinstance(no, ast.Constant) and isinstance(no.value, (str, bytes)):
            v = no.value if isinstance(no.value, str) else no.value.decode("utf-8", "replace")
            if "#TCF." in v:
                n += 1
    return n


def test_no_maximo_duas_eras():
    assert len(WIRE_ERAS) <= 2, (
        f"o registro tem {len(WIRE_ERAS)} eras. A janela é N-1: a vigente e, no máximo, a "
        "anterior. Uma terceira era significa que uma janela venceu sem ninguém fechar."
    )


def test_a_vigente_nao_tem_sunset_e_a_anterior_tem():
    assert ERA_ATUAL.sunset is None, "a era vigente não tem data de fim"
    if ERA_EM_SUNSET is not None:
        assert ERA_EM_SUNSET.sunset, (
            "a era anterior entrou no registro sem data de sunset. A data se escreve no "
            "commit que promove a sucessora, com o contexto fresco: sem ela a janela não "
            "fecha sozinha e a política vira disciplina outra vez."
        )
        assert ERA_EM_SUNSET.n == ERA_ATUAL.n - 1, "a janela é da era imediatamente anterior"


def test_as_grafias_derivam_do_numero():
    assert ERA_ATUAL.base == f"#TCF.{ERA_ATUAL.n}"
    assert ERA_ATUAL.multi == ERA_ATUAL.base + "M"
    assert ERA_ATUAL.hier == ERA_ATUAL.base + "H"


def test_o_fail_loud_nomeia_o_caminho_de_volta():
    """Parar de servir só é aceitável se o dado continuar alcançável."""
    frase = caminho_de_volta(ERA_ATUAL.n - 1)
    assert "pip install tcf-format" in frase, "a frase tem de nomear o PyPI"
    assert "git" in frase, "a frase tem de nomear a tag do git"


def test_catraca_de_literais_nao_sobe():
    por_arquivo = {}
    for f in sorted((ROOT / "src" / "tcf").rglob("*.py")):
        if f.name == "wire.py":
            continue
        n = _literais_de_era(f)
        if n:
            por_arquivo[f.relative_to(ROOT).as_posix()] = n
    total = sum(por_arquivo.values())
    piores = sorted(por_arquivo.items(), key=lambda kv: -kv[1])[:5]
    assert total <= TETO_DE_LITERAIS, (
        f"a era do wire ganhou grafia nova fora do registro: {total} literais, teto {TETO_DE_LITERAIS}.\n"
        f"  Os arquivos com mais: {piores}\n"
        "  Derive de `tcf.wire` (ERA_ATUAL, MAGIC_BASE, MAGIC_MULTI_B, ...) em vez de escrever "
        "a grafia. Se a grafia for mesmo necessária, baixe o teto junto, com o porquê no commit."
    )

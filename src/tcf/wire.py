"""O registro da era do wire: onde a versão do FORMATO vive, e só aqui.

Motivo (2026-08-31, direção do owner): *"temos que ficar com um método esperto para que cada
mudança de versão a antiga seja esquecida, ao menos uma versão antes"*. O ADR-0024 §2 já
decidia isso em texto (*"no máximo a versão imediatamente anterior"*) desde 2026-06-14, e
nunca teve mecanismo: a era vivia espalhada em seis definições de magic e em dezenas de
literais, então virar de era era editar dezenas de lugares em vez de um.

**Dois eixos, e este arquivo é só o primeiro.** A era do WIRE é o contrato on-disk, e é o que
este registro guarda. A versão do PACOTE (`__version__`, o que o PyPI publica) é outro eixo,
e é justamente ela que torna o esquecimento barato: uma era que saiu do código continua
legível instalando o release que a escrevia. É a separação que o Apache Arrow faz entre
Format Version e Library Version.

**A regra**: o registro tem no máximo DUAS eras, a vigente e, quando existir, a anterior com
data de sunset escrita **no dia em que a nova nasceu**. Até essa data a anterior pode ser
citada na documentação, nunca servida pelo código. Passada a data, o teste de superfície
reprova sozinho toda citação que restar. Um teste garante o limite de duas: se isto virar
tabela de N eras, a bagagem que a política existe para cortar voltou pela porta que ela abriu.

**Esquecer tem três níveis**, e eles não acontecem juntos:

1. **parar de servir**, no dia da virada, sem janela. A emissão e o decode da era anterior
   saem do pacote, com fail-loud nomeando o caminho de volta. Não é perda: o comparativo
   migratório roda com a era anterior instalada do PyPI, num ambiente à parte, e por isso não
   precisa de decoder legado vivo aqui dentro. É a regra que o Kubernetes escreve como número
   um: a versão antiga não se edita, ela para de ser servida.
2. **parar de citar**, na data de sunset. É este nível que dá velocidade de busca.
3. **apagar do disco**, e só o que é regenerável: fixtures, blobs de lab, snapshots. Traço
   nunca: ADR aceito, `CHANGELOG.md`, git, tags e releases do PyPI ficam, e são justamente
   eles que tornam o esquecimento barato.
"""

from __future__ import annotations

from typing import NamedTuple


class Era(NamedTuple):
    """Uma era do wire: o número que aparece na assinatura, e quando ela para de ser citável."""

    n: int
    """A era, isto é, o `8` em `#TCF.8`."""

    sunset: str | None
    """Data ISO (`AAAA-MM-DD`) em que ela deixa de poder ser citada na superfície.

    `None` na era vigente. Na era anterior a data é obrigatória, e ela se escreve no commit
    que promove a sucessora: com o contexto fresco, e não no dia do cansaço.
    """

    @property
    def base(self) -> str:
        """A assinatura sem discriminador: `#TCF.8`. Também é a rota single-col."""
        return f"#TCF.{self.n}"

    @property
    def multi(self) -> str:
        """A assinatura multi-coluna: `#TCF.8M`."""
        return f"{self.base}M"

    @property
    def hier(self) -> str:
        """A assinatura hierárquica: `#TCF.8H`."""
        return f"{self.base}H"


# A vigente primeiro. No máximo duas linhas, e o teste garante.
WIRE_ERAS: tuple[Era, ...] = (
    Era(n=8, sunset=None),
)

ERA_ATUAL: Era = WIRE_ERAS[0]
ERA_EM_SUNSET: Era | None = WIRE_ERAS[1] if len(WIRE_ERAS) > 1 else None

# As grafias derivadas, para quem precisa delas prontas. Quem serve o wire usa estas; quem
# apenas fala sobre a era usa `ERA_ATUAL`.
MAGIC_BASE: str = ERA_ATUAL.base
MAGIC_MULTI: str = ERA_ATUAL.multi
MAGIC_HIER_STR: str = ERA_ATUAL.hier

MAGIC_BASE_B: bytes = MAGIC_BASE.encode("ascii")
MAGIC_MULTI_B: bytes = MAGIC_MULTI.encode("ascii")
MAGIC_HIER_B: bytes = MAGIC_HIER_STR.encode("ascii")


def e_da_era_atual(blob: str | bytes) -> bool:
    """O blob começa com a assinatura da era vigente?

    Não decide o modo (multi, hierárquico, single): só a era. Quem decide o modo é o
    discriminador, no índice 6.
    """
    if isinstance(blob, bytes):
        return blob.startswith(MAGIC_BASE_B)
    return blob.startswith(MAGIC_BASE)


def caminho_de_volta(n: int) -> str:
    """A frase que um fail-loud usa para dizer como ler um wire de era anterior.

    Ela nomeia os dois artefatos que sobrevivem ao esquecimento, que são o PyPI e as tags do
    git. Ficar sem esta frase é o que transforma "parar de servir" em "perder o dado".
    """
    return (f"wire `#TCF.{n}` é de uma era anterior e não é lido por este pacote; "
            f"para lê-lo, instale o release que o escrevia (`pip install tcf-format==0.{n}.*`) "
            f"ou volte à tag correspondente no git")

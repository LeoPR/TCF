"""Planos de execucao versionados — a CADENCIA, separada da matriz (parecer §1).

"Pertencer a uma cadencia NAO e' dimensao do dado medido." Entao `cases.json`
fica como catalogo-mestre INTOCADO (regra R2), e um PLANO seleciona um subconjunto
+ declara intencao + aceite (obrigatorio/opcional). Duas rodadas so' sao
comparaveis se usaram o MESMO plano (o comparador exige o hash do plano + intencao).

Tres cadencias:
  nucleo    — referencia recorrente, barata, comparavel .8<->.9 toda vez.
  campanha  — caro (B4 escala-cheia, R6e5, process-tree); 1x, fotografia pro .9,
              FORA do loop de comparacao recorrente.
  smoke     — validacao rapida do instrumento; ZERO valor probatorio.

Selecao por PREDICADO (dict {campo: [valores]}, AND entre campos; lista de
predicados = OR). Campos: bloco, caminho, forma, granularidade, compressao,
accel, fonte, fonte_prefix, escala (point_id).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PLANS_DIR = AQUI / "plans"


def _match(caso: dict, pred: dict) -> bool:
    """AND entre os campos do predicado."""
    vet = caso["vectors"]
    for campo, vals in pred.items():
        if campo == "bloco":
            if not (set(caso.get("blocos", [])) & set(vals)):
                return False
        elif campo == "fonte_prefix":
            if not any(caso["fonte"].startswith(p) for p in vals):
                return False
        elif campo == "fonte":
            if caso["fonte"] not in vals:
                return False
        elif campo == "escala":
            if vet["escala"].get("point_id") not in vals:
                return False
        elif campo in ("caminho", "forma", "granularidade", "compressao", "accel"):
            if vet.get(campo) not in vals:
                return False
        else:
            raise ValueError(f"campo de predicado desconhecido: {campo}")
    return True


def _match_any(caso: dict, preds: list[dict]) -> bool:
    return any(_match(caso, p) for p in preds)


def carregar(plan_id: str) -> dict:
    p = PLANS_DIR / f"{plan_id}.json"
    if not p.exists():
        raise SystemExit(f"plano '{plan_id}' nao existe em {PLANS_DIR} "
                         f"(opcoes: {[x.stem for x in PLANS_DIR.glob('*.json')]})")
    return json.loads(p.read_text(encoding="utf-8"))


def hash_plano(plan: dict) -> str:
    """Hash CANONICO do plano (independente de ordem de chave) — vai no manifesto."""
    canon = json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def selecionar(plan: dict, casos: list[dict]) -> list[dict]:
    inc = plan.get("incluir", [])
    exc = plan.get("excluir", [])
    return [c for c in casos if _match_any(c, inc) and not _match_any(c, exc)]


def e_opcional(plan: dict, caso: dict) -> bool:
    """Caso opcional pode ficar nao-medido/pendente sem invalidar o 'completo'."""
    return _match_any(caso, plan.get("opcional", []))


def pin_ok(plan: dict, cases_sha256: str | None) -> bool:
    """O plano e' PRA UMA matriz especifica — se a matriz mudou, o plano nao vale."""
    esperado = plan.get("pin_cases_sha256")
    return (esperado is None) or (esperado == cases_sha256)


__all__ = ["carregar", "hash_plano", "selecionar", "e_opcional", "pin_ok", "PLANS_DIR"]

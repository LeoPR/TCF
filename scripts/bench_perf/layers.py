"""Perfil por CAMADA sem tocar em `src/tcf`.

Achado que torna isto possivel (auditoria 2026-07-21): todos os pontos de juncao
das camadas sao NOMES GLOBAIS DE MODULO resolvidos em tempo de chamada.
`src/tcf/encoder.py:43-49` importa `analyze_column`, `detect_cadence_from_features`,
`detect_min_len_from_features`, `processar`, `processar_with_hint`, `HCCSeqRLE` e
`M8AVirtualRefsSyntax` no namespace do modulo, e `_encode_column` os consome como
globais. Logo, substituir o atributo do modulo por um wrapper que delega e
devolve o MESMO objeto:

  - nao muda um byte (o gate `bytes_identicos` abaixo prova, por celula);
  - custa zero quando nao instalado (nada e' instalado: os originais seguem la');
  - respeita a decisao do owner: o baseline mede o `.8` como ele e', de fora.

TRES LIMITES DUROS, declarados porque escondê-los invalidaria a leitura:

  1. NAO ATRAVESSA `spawn`. No Windows os workers de ProcessPoolExecutor
     re-importam `tcf` limpo, e `_encode_columns_parallel` cria o pool SEM
     `initializer=` (multi/parallel.py:72). Perfil por camada existe SO' no
     caminho serial; com `parallel` ligado os buckets saem baixos sem aviso.
     Medir dentro do worker exigiria tocar src (assunto do .9).
  2. CLOSURES sao invisiveis. `_serialize` e `_best_of` sao definidos DENTRO de
     `_encode_multi` (multi/core.py:525,560) e nao se envolvem por wrapper. O
     `fallback=False` desliga os candidatos raw, dict e split do `_best_of`, mas
     pode mudar o wire emitido, entao nao isola o custo deles.
  3. OS BUCKETS NAO SEPARAM PIPELINE DE CANDIDATO. O pipeline reentra:
     `_struct_split_encode` chama `_encode_multi` (multi/split.py:65),
     `_v2b_encode` chama `_encode_column` (multi/dict_v2b.py:64), e o bN de
     dominio, o `sort_by`, a natureza e o `.8H` codificam de novo. A reentrada
     acontece FORA das janelas: nenhum dos sete pontos roda dentro de outro, entao
     a soma dos buckets nao conta tempo em dobro no serial. O preco e' que cada
     bucket soma toda execucao do pipeline, a emitida e a so' avaliada, sem
     separar, e a profundidade registrada e' sempre 0. Comparar buckets entre
     regimes exige registrar quais candidatos rodaram: o V2-B, por exemplo, so'
     roda com repeticao e ate' 8.192 valores distintos. Medido no caderno local de
     diagnostico da `.9`, no sub-experimento `07-aninhamento`: 0 aninhamentos em
     49 execucoes de caso, de 20 estruturas de chamada distintas, com o `n_calls`
     daqui igual ao de um rastreador independente, e leitura estatica dos imports.

Granularidade proibida: nunca envolver funcao chamada POR VALOR. Um wrapper +
perf_counter_ns custa ~150-250 ns; por coluna (5 chamadas cronometradas, de 7
wrappers) e' <1% de um encode
tipico, mas por valor em 10k linhas seriam ~2,5 ms de instrumento puro.
"""

from __future__ import annotations

import time
from contextlib import contextmanager

_acc: dict[tuple[str, int], list[int]] = {}   # (bucket, depth) -> [ns_total, n_calls]
_depth = 0          # nunca muda: ver o limite 3; a chave fica pelos registros publicados
_instalado = False
_originais: dict[tuple[object, str], object] = {}


def _marcar(bucket: str, ns: int) -> None:
    chave = (bucket, _depth)
    slot = _acc.get(chave)
    if slot is None:
        _acc[chave] = [ns, 1]
    else:
        slot[0] += ns
        slot[1] += 1


def _wrap_fn(mod, nome: str, bucket: str) -> None:
    original = getattr(mod, nome)
    _originais[(mod, nome)] = original

    def wrapper(*a, **kw):
        t0 = time.perf_counter_ns()
        try:
            return original(*a, **kw)          # delega e devolve o MESMO objeto
        finally:
            _marcar(bucket, time.perf_counter_ns() - t0)

    wrapper.__name__ = getattr(original, "__name__", nome)
    setattr(mod, nome, wrapper)


def _wrap_syntax(mod, nome: str, bucket: str) -> None:
    """HCC entra por CLASSE: subclasse que cronometra .encode().

    Precisa herdar (nao compor) porque `encoder.py:1087` faz `hasattr(syn, 'get_seq_info')`
    e o atributo de classe `name` e' lido; a subclasse preserva os dois.
    """
    original = getattr(mod, nome)
    _originais[(mod, nome)] = original

    class Cronometrado(original):  # type: ignore[misc, valid-type]
        def encode(self, *a, **kw):
            t0 = time.perf_counter_ns()
            try:
                return super().encode(*a, **kw)
            finally:
                _marcar(bucket, time.perf_counter_ns() - t0)

    Cronometrado.__name__ = original.__name__
    setattr(mod, nome, Cronometrado)


def instalar() -> None:
    """Instala os wrappers. Idempotente."""
    global _instalado
    if _instalado:
        return
    from tcf import encoder as E

    _wrap_fn(E, "analyze_column", "prepass")
    _wrap_fn(E, "detect_cadence_from_features", "prepass")
    _wrap_fn(E, "detect_min_len_from_features", "prepass")
    _wrap_fn(E, "processar", "obat")
    _wrap_fn(E, "processar_with_hint", "obat")
    _wrap_syntax(E, "HCCSeqRLE", "hcc")
    _wrap_syntax(E, "M8AVirtualRefsSyntax", "hcc")
    _instalado = True


def desinstalar() -> None:
    """Restaura os originais. Sempre chamada no finally do medidor()."""
    global _instalado
    for (mod, nome), original in _originais.items():
        setattr(mod, nome, original)
    _originais.clear()
    _instalado = False


def zerar() -> None:
    _acc.clear()


def coletar() -> dict:
    """{'prepass': {...}, 'obat': {...}, 'hcc': {...}, '_total_camadas_ns': int}.

    `share_of_layers` e' a fracao da SOMA DOS TRES BUCKETS, nao do encode inteiro.
    `por_profundidade` sai sempre so' com a chave 0, porque o acumulador nao separa
    profundidade (limite 3 do modulo). A chave fica porque os registros publicados
    em `experiments/results/evidencia-0.8/perf-baseline/` a carregam.
    """
    fora: dict[str, dict] = {}
    for (bucket, depth), (ns, n) in sorted(_acc.items()):
        alvo = fora.setdefault(bucket, {"wall_ns": 0, "n_calls": 0, "por_profundidade": {}})
        alvo["por_profundidade"][depth] = {"wall_ns": ns, "n_calls": n}
        if depth == 0:
            alvo["wall_ns"] += ns
            alvo["n_calls"] += n
    total = sum(b["wall_ns"] for b in fora.values())
    for b in fora.values():
        b["share_of_layers"] = round(b["wall_ns"] / total, 4) if total else None
    fora["_total_camadas_ns"] = total          # type: ignore[assignment]
    return fora


@contextmanager
def medindo():
    """Contexto: instala, zera, mede, coleta e SEMPRE desinstala."""
    instalar()
    zerar()
    try:
        yield
    finally:
        desinstalar()


def perfil_de(fn, *, gate_bytes: bool = True) -> tuple[object, dict]:
    """Roda `fn` com perfil por camada. Devolve (resultado, camadas).

    Com `gate_bytes`, roda TAMBEM sem instrumentacao e exige saida identica:
    se divergir, o perfil sai marcado e nao deve ser publicado. Perfil que muda
    o resultado nao e' perfil, e' outro programa.
    """
    limpo = fn() if gate_bytes else None
    with medindo():
        instrumentado = fn()
        camadas = coletar()
    camadas["bytes_identicos"] = (limpo == instrumentado) if gate_bytes else None
    return instrumentado, camadas


__all__ = ["instalar", "desinstalar", "zerar", "coletar", "medindo", "perfil_de"]

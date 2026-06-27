# Enabler (1 linha) no syntax.py — pra o T-CI-3 comparar os 2 caminhos

O monkeypatch (syntax.py ~770) SOBRESCREVE `_detect_compositions` com a versao
Cython, perdendo a referencia pure-Python. Pra o teste comparar os dois no MESMO
processo, salvar a pure-Python ANTES de sobrescrever:

```python
try:
    from tcf._core.detect import _detect_compositions as _detect_compositions_cy
    M8AVirtualRefsSyntax._detect_compositions_py = M8AVirtualRefsSyntax._detect_compositions  # <-- ENABLER
    M8AVirtualRefsSyntax._detect_compositions = _detect_compositions_cy
    M8AVirtualRefsSyntax._detect_compositions_accelerated = True
except Exception:
    M8AVirtualRefsSyntax._detect_compositions_py = M8AVirtualRefsSyntax._detect_compositions  # idem (= a propria)
    M8AVirtualRefsSyntax._detect_compositions_accelerated = False
```

Aditivo, zero efeito em runtime (so' guarda uma referencia). Alternativa SEM
mexer no src: teste por SUBPROCESSO (com/sem .pyd), mais lento e hacky.

# Lab 2026-07-17-0140 — critério do FLUXO: caminho JSON vs caminho TCF

**Pedido do owner**: *"pra termos um ROI de implementação, podemos gerar um comportamento similar
ao json dentro das limitações dele... dataset→encode→json→transmite→recebe→json→decode→dataset;
basta o tcf ter comportamento similar."*

**O critério, executável**:

```
∀D:   J-RT-TX(D)  ⟹  T-RT(D)
      "se o caminho JSON faz round-trip ATRAVÉS DA TRANSMISSÃO, o caminho TCF tem de fazer"
```

A etapa **TRANSMITE** é o que torna o critério honesto: mede-se sobre **bytes UTF-8**, não sobre o
`str` em memória — é o fluxo que o owner descreve. Sem ela, o lone surrogate "passaria" (o escape
ASCII o esconde) e mediríamos uma paridade que não existe no fio.

**3 níveis por caso**: N0 = json realista (`ensure_ascii=False` → bytes) · N0a = json ASCII ·
**N1 = I-JSON (RFC 7493)**, o perfil interoperável restrito.

## Resultado — [outputs/00-resultado.txt](outputs/00-resultado.txt)

**PLACAR: PARIDADE=14 · LACUNA=3 · AMBOS-RECUSAM=7 · TCF-ESTRITO=2**

- **LACUNAS REAIS = 3** (json I-JSON-conforme faz RT, TCF não): chave vazia `""` · `\n` em valor ·
  chave contendo `\n`. **É a superfície inteira de implementação em nível de dataset.**
- **RAIZ (eixo separado, P4b)**: 7 formas onde o json faz RT e o TCF não (objeto único, array de
  escalares, escalar, string, null, `[]`, `[{}]`).
- **TCF-ESTRITO = 2**: `±Infinity` — o json só "passa" porque o CPython emite um token **inválido
  por RFC 8259 §6** (`allow_nan=True` é o default). Não é lacuna: é o json fora da norma.
- **AMBOS-RECUSAM = 7**: NaN, tuple, chaves não-str, lone surrogate — o **json também falha**
  (DIVERGE ou exceção). Nada a implementar.
- **TCF ⊃ I-JSON** em 1 eixo (medido): inteiros acima de 2^53 fazem RT no TCF; o I-JSON os
  proíbe (§2.2, faixa segura IEEE 754) — capacidade extra que já temos de graça.

## Leitura

A paridade com o fluxo JSON está a **3 lacunas de dataset + 1 decisão de raiz**. Escala de
implementação (ROI ordenado) em
[../notas/escala-implementacao-paridade-json.md](../notas/escala-implementacao-paridade-json.md).
Pinos: `tests/test_json_flow_parity.py`. Zero mudança em `src/tcf`.

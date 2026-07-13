# Lab 2026-07-13-1835 — DatasetH stage 2: escalares especiais (A vs C)

**Status**: pesquisa/medido · **Ticket**: [T-STUDY-HIERARCHICAL-TCF](../../../../tickets/T-STUDY-HIERARCHICAL-TCF.md)
· **Plano**: [dataseth-hierarquia-completa-plano.md](../notas/dataseth-hierarquia-completa-plano.md) (P1+P2)
· **Hipótese**: H-HIER-SCALAR-01

Executa a matriz de falsificação do plano (P1) e a comparação de representações (P2) para os
escalares especiais `NaN` / `+Infinity` / `-Infinity` / `-0.0`:

- **A — folha tipada**: kinds explícitos (`nan`/`pos_inf`/`neg_inf`, valor canônico `None`);
  no wire, tag própria `V<token>`.
- **C — string escapada**: especiais viajam no canal de string como léxico reservado
  (`NaN`/`Infinity`/`-Infinity`); strings literais colidentes (ou começando com `\`) pagam escape.

B (domínio `bN`) e D (dicionário interno) seguem **bloqueadas** pelo plano (só após semântica
definida / decisão de formato).

## Arquivos

- `model_ext.py` — estende o DatasetH do lab-ponte (importa, não copia): kinds especiais,
  `from_python_ext` (origem árvore-Python aceita não-finitos), `from_jsonlike` (2ª origem textual
  com **gramática declarada** JSON+constantes — não alega ser JSON padrão), e o **oráculo**
  `semantic_key` (NaN reflexivo; `-0.0` ≠ `0.0`; tipo separa `1`/`1.0`/`"1"`).
- `wire_ac.py` — as duas representações sobre o stream por-instância do stage 1 (ideia extraída).
- `run.py` — matriz 21 casos × 2 variantes, distinctness 10 pares, 2 origens, equivalência
  declarada (`1e3` ≡ `1000.0`), fail-loud, bytes por perfil. Gera `artifacts/`.

Rodar: `python run.py` (nesta pasta). Ver **`result.md`** para números e veredito.

## Por que o oráculo (e não `==` ingênuo)

- `float('nan') != float('nan')` → NaN como float nunca seria igual a si; como **kind tipado**
  (valor `None`) a reflexividade volta.
- `-0.0 == 0.0` em Python → o `==` de dataclass **colapsa** os dois; o oráculo distingue via
  `repr` (`'-0.0'` vs `'0.0'`), conforme "se a fonte declarar sinal relevante".

Nenhum arquivo do lab-ponte foi alterado; zero `src/tcf`.

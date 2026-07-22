# Resultado — ver README.md (placar) e outputs/00-resultado.txt (medições)

**[probatório]** Critério `J-RT-TX ⟹ T-RT` medido sobre bytes UTF-8, CPython 3.13, `.8H` no
estado `8e17b5e`. Reproduzível (`python run.py`, determinístico).

**Achado central**: a superfície de implementação para "comportamento similar ao json" é **3
lacunas de dataset** (chave `""`, `\n` em valor, chave com `\n`) **+ o eixo raiz (P4b, 7 formas)**.
Tudo o mais: 14 paridades já existentes, 9 casos onde o próprio json falha ou sai da norma.

`confianca: Alta` (medido, determinístico) para o placar; a classificação I-JSON usa um checker
próprio (implementado no run.py a partir da RFC 7493) — `confianca: Média` até verificação
independente das citações normativas.

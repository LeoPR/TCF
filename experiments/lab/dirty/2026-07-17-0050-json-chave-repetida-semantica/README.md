# Lab 2026-07-17-0050 — chave repetida em JSON: semântica pura, medida

**Pergunta do owner**: o que SIGNIFICA a chave repetida; o que o json CONSTRÓI dela; como fazer
estrutura dict+array que retorne; "o json colidiria chaves? se não, temos inferência de como
reconstruir"; e revisar se o fail-loud do S0 foi engessado ou limpo.

**Método**: medição pura (Python 3.13 `json`) — import de textos estrangeiros (simples + 2 níveis
+ difíceis, em `inputs/*.json`), export da matriz de tipos Python, representações de multi-valor
RT-medidas, e as bordas do `.8H` (API/wire/chave-não-str/NFC×NFD). Zero mudança em `src/tcf`.

**Resultado**: [outputs/00-resultado.txt](outputs/00-resultado.txt).
**Levantamento com as opções exaustivas + revisão**:
[../notas/json-chave-repetida-levantamento.md](../notas/json-chave-repetida-levantamento.md).

**Síntese**: (1) last-wins calado em todo nível é o que o json constrói; (2) com chaves STRING o
modelo NUNCA colide (colapsa antes de serializar) → duplicata no texto = origem fora do contrato
(a inferência do owner, provada); o único furo é chave NÃO-string (dumps emite duplicata por
coerção — medido); (3) collect→array COLIDE com array legítimo (provado ==True); lista-de-pares é
a única lossless e sai do modelo; (4) fail-loud do S0 = limpo (espelha a impossibilidade do
modelo); políticas alternativas viram opt-in de ADAPTADOR (gadget), nunca do core; (5) achado:
chave não-string no `.8H` rejeita (certo) mas com TypeError cru/mensagem enganosa → registrado.

**Nota sobre inputs**: os `.json` com chave repetida são textos ECMA-404 VÁLIDOS — objeto do
estudo, não erro do lab. Proveniência: `datasets-provenance.md`.

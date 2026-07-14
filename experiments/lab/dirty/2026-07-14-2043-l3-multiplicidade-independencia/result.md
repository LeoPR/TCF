# Resultado — L3 multiplicidade: independência × bytes (medido)

**[probatório]** `study.py` valida RT da forma explícita (o weld) antes dos bytes.
Contra-prova/números: [`outputs/01-resultado.txt`](outputs/01-resultado.txt). Sintético
(gerador paramétrico por largura), viés declarado
([datasets-provenance.md](datasets-provenance.md)).

## Veredito

A hipótese do owner — **explícita = independência/paralelismo; deduzida = menos bytes mas
colunas se conversam** — é **verdade, com crossover**:

- **Estreito (K=1–2)**: deduzida ganha em bytes (economiza o count). "Independência custa" ✅.
- **Largo (K≥4, o comum em transmissão)**: a EXPLÍCITA é **Pareto-melhor** — menos bytes E
  independência (a deduzida paga `*N|` em cada coluna-pai; a explícita, 1 count constante).
- **Dependência**: explícita = 1 coluna de controle minúscula → dado independente + estrutura
  legível sem dado (lazy). Deduzida = estrutura entrelaçada com o dado do pai → filho depende
  do pai → menos assíncrono.

**Mitigação**: o count é minúsculo/constante (20 B, seq-RLE) → a independência é quase-grátis
no caso comum. O default do weld (`#count` explícito) está certo; o trade vira **parâmetro**
só no nicho estreito.

## Ligação com o weld + a estratégia de etapas

- O weld atual (a20ddf7) já usa a forma EXPLÍCITA — confirmado como o default certo (independência
  + lazy + Pareto no comum). Nenhuma mudança necessária no core agora.
- **Otimização** (o knob `multiplicity` / `min()` por documento) = H-L3-MULTIPLICITY-01, **deixada
  pro fim** (owner: soldar em etapas, otimizações no final). NÃO implementar agora.

`confianca: Média` (sintético, medida de forma). Falta: dado real + a interação com brotli a
jusante (o Δ sobrevive à compressão externa?).

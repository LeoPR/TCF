# Resultado — L3 multiplicidade: independência × bytes (medido)

**[probatório]** `study.py` valida RT da forma explícita (o weld) antes dos bytes.
Contra-prova/números: [`outputs/01-resultado.txt`](outputs/01-resultado.txt). Sintético
(gerador paramétrico por largura), viés declarado
([datasets-provenance.md](datasets-provenance.md)).

## Sinal-piloto (NÃO veredito — 1 lente, sintético, N pequeno)

Owner (reforço): multiplicidade explícita×deduzida é **só UMA hipótese ilustrativa**, uma entre
várias condições de um futuro **bloco de otimizações** (eixos: latência, memória, velocidade,
compressão). Este experimento mediu **1 eixo (largura) × 1 métrica (bytes-pré-brotli)** — é sinal,
não conclusão:

- **Estreito (K=1–2)**: a forma deduzida gastou menos bytes (economizou o count).
- **Largo (K≥4)**: a forma explícita gastou menos E manteve independência (a deduzida repete `*N|`
  em cada coluna-pai; a explícita, 1 count constante ~20 B).
- **Dependência (qualitativo)**: explícita = 1 coluna de controle minúscula → dado independente +
  estrutura legível sem dado (lazy). Deduzida = estrutura entrelaçada no dado do pai → filho
  depende do pai → menos assíncrono.

## O que isto NÃO estabelece

- Só 1 eixo (largura) e 1 métrica (bytes). **Latência/memória/velocidade não medidas**; sem dado
  real; sem brotli a jusante (o Δ sobrevive à compressão externa?).
- O weld usa `#count` explícito **por ora** — não porque esteja "provado ótimo".

## Encaminhamento

- Nada a mudar no core agora. O bloco de otimizações (parâmetros L3) = **H-L3-OPT-BLOCK**, `aberta`,
  confiança **Baixa**, **deixado pro fim** (owner: fixar o óbvio primeiro). Multiplicidade = 1 item
  do bloco, não o bloco.

# Proveniência das entradas

Metodologia do owner (didático → realista → massa). Viés declarado por etapa.

- `inputs/01-didatico-null-campo.json` — **DIDÁTICO**: poucos dados construídos para FORÇAR cada
  forma de null-em-campo (escalar/objeto/array/all-null/null+ausente/4-vias/aninhado). Bias total
  (construído pra provar cada caso); serve pra INSPEÇÃO, não pra ganho. CPFs placeholder repetidos.
- `inputs/02-realista-cadastro.json` — **REALISTA pequeno**: cadastro API-like com opcionais E nulos
  distribuídos de forma plausível (email/obs/nascimento/complemento/endereco nulos em registros
  diferentes). Ainda sintético, mas sem apelar pra forçar um caso só. CPFs placeholder.
- **MASSA**: `Z:/tcf-data/interim/receita-cnpj.db` (real). `nome_fantasia=None` mantido como null
  REAL (P3a) — não coerido a `""` como o P1 fazia. Samples 5/10/25% (evitam o BUG-SEQRLE-RANGE-EMPTY-B
  no free-text; a população inteira o dispara, à parte do P3a). Determinístico (fatia `allk[::N]`).

Roundtrip é ARQUIVO diffável (`outputs/*-rt.json` byte-idêntico ao `intermediates/*.json`,
asserido no `run.py`) — pra o owner e o Claude inspecionarem a consistência da saída.

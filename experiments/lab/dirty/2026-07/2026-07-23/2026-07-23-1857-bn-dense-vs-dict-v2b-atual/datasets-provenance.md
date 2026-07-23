# Proveniência — bN-dense vs dict/V2-B atual

**Origem**: adult-census REAL — `Z:/tcf-data/external/adult-census/adult.csv` (48.842 linhas), dataset
canônico do projeto. Nenhum download (regra: usar `Z:/tcf-data/`). **Amostra**: primeiras 10.000
linhas, declarada no result.md. Determinístico (sem aleatório).

**Colunas** (9 categóricas low-card, k=2..41 → w=1..8): sex, class (k=2) · race (5) · relationship (6)
· marital-status (7) · workclass (9) · occupation (15) · education (16) · native-country (41).
Valores como estão no CSV, sem limpeza.

**Comparação**: total-vs-total, ambos **self-contained**.
- Lado TCF: `encode({col: vals})` COMPLETO (header `#TCF.8M...` + dicionário + corpo), com o
  `emitted_mode` real lido de `SideOutputs` (foi `dict` em 8, `tcf` na k=41). É o que o TCF emite hoje.
- Lado protótipo: header `#PB w n <domínio>` + corpo base64 dos índices empacotados a w bits.

**Dados sintéticos adicionais (v2)**: varredura de cruzamento de k — sequências uniformes
`c000..c{k-1}` com k ∈ {2,4,8,16,17,32,64,94,95,128,256}, N=10000, determinísticas (`i % k`). Servem
só para mapear ONDE o dict/V2-B muda de regime (base-94 esgota em k=94→95); não são dado real.

**Limites declarados (v2)**: (a) só **bytes** — não mede latência/CPU; (b) 1 dataset real
(adult-census); (c) a varredura de N vai só até 10k; (d) gzip é medido como SINAL (filosofia do
projeto: não é critério de descarte), não como veredito.

**Corrigido na v2** (a v1 tinha estes defeitos): o protótipo agora faz **escaping** de `\\`, `\n` e do
separador `\x1f` — na v1 um valor contendo `\x1f` decodificava ERRADO em silêncio (corrupção, não
questão de bytes). A largura passou de escada {1,2,4,8} para `ceil(log2 k)` exata. A objeção
multi-col foi VERIFICADA como não-material (o TCF é colunar: juntar 9 colunas economiza 0,0%).

**Sem dados sensíveis**: adult-census é público (UCI); colunas demográficas categóricas, sem PII
reconstruível nas colunas medidas.

**Reprodutibilidade**: `python run.py` regenera. RT obrigatório dos DOIS lados (`decode(wire_tcf)` e o
decoder do protótipo) — bytes só reportados com RT ✅. Wires salvos em `outputs/` para auditoria.

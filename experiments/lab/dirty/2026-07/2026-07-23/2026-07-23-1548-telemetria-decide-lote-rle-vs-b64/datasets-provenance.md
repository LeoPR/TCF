# Proveniência — telemetria decide modo por lote (corrigido)

**Origem**: 100% sintético/determinístico. Nenhum dado real, nenhum download. Ruído via LCG local
(seeds fixas), reprodutível byte-a-byte, sem `random` global. Domínio bool, bit1=true.

**Correção de viés (o motivo desta v2)**: a v1 usava blocos de 128 == S vencedor, o que INFLAVA o
ganho do batch fixo (artefato de alinhamento, apontado por `wf_876541f7`). Esta versão inclui de
propósito:
- **alinhado** (`het-align128`, bloco=128) — teto do ganho fixo, para contraste.
- **desalinhado** (`het-mis100` bloco=100, `het-mis77` bloco=77/51, `half-100-156` fronteira=100) —
  o caso realista onde nenhum S fixo casa. É onde o fixo perde e o adaptativo tem que provar valor.
- **homogêneo** (`noisy`, `alt`) — controle: nenhuma composição por-lote deve ganhar.

**Viés declarado**: `het-align128` favorece o batch fixo por construção; está rotulado como tal e
serve só de contraste (não de resultado). O resultado central vem dos desalinhados + homogêneos.

**Reprodutibilidade**: `python run.py` regenera. RT por composição (decode==orig==json_rt); Fonte
instrumentada prova passe único (`reads/n==1.0`). Bytes só com RT ✅. Comparação corpo-vs-corpo — mas
ver README: o corpo do batch-fix precisa de S,n externos; o do seg-adapt é auto-decodável (cada
segmento declara seu count).

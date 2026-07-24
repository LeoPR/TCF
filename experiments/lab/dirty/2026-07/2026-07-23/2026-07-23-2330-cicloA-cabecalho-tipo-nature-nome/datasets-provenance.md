# Proveniência — Ciclo A (cabeçalho) v3

**Fonte**: 100% sintético/determinístico, escrito literalmente em `inputs/<ID>-fonte.json`. Nenhum
download, nenhum dado real. Sem aleatório (nenhuma seed necessária).

**Dados por caso** (pequenos e inspecionáveis — o objeto de estudo é a MOLDURA, não o volume):
- e-mails com prefixo/sufixo compartilhado (A1) — exercita o órfão sem header.
- **CPFs placeholder SEGUROS** (A2–A6c): dígitos repetidos mod-11-válidos
  (`111.111.111-11`, `222.222.222-22`, `333.333.333-33`) — **nunca CPF real**, mesma convenção do
  catálogo `2026-07-23-0204` e da suíte.
- bool (A7) e int (A8) — materializam a lacuna: hoje não há forma single-col tipada.
- strings curtas (A9) — version-stamp.

**Nomes adversariais** (o eixo pedido pelo owner): `doc` (normal) · `b` (= tag de tipo hipotética) ·
`M` (= discriminador multi-col do Eixo-1) · `a:b` (separador) · `a\nb` (LF). Os dois últimos são
**contraprovas** — devem falhar alto.

**Cadeia materializada** (§3.2 do plano): a fonte JSON é lida com `json.loads` e o resultado é gravado
em `intermediates/<ID>-dataset-consumido.json` — é ele que vai pro `encode`. Assim fica visível onde
cada tradução acontece (fonte → dataset → wire → dataset de volta).

**Separação real × hipotético**: `outputs/` contém SÓ wire e roundtrip que o `src/tcf` realmente
produziu. As 6 formas candidatas do owner são **hipóteses** e vivem em `intermediates/*.debug.txt` e
`intermediates/00-analise-6-formas.txt`, rotuladas como tal.

**Reprodutibilidade**: `python run.py` regenera tudo byte-a-byte. Bytes e vereditos só são reportados
com RT ✅ (ou, nas contraprovas, com o erro real do encoder registrado). Zero toque em `src/tcf`.

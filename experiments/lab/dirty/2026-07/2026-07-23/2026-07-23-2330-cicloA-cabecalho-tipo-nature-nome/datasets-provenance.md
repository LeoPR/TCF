# Proveniência — Ciclo A (cabeçalho)

**Sem dataset externo.** Este ciclo estuda **moldura**, não representação: o BODY está CONGELADO e não
participa da medição. Portanto não há fonte de dados real nem sintética a declarar — os "dados" são as
**combinações de campos de header** enumeradas no [`MANIFESTO.md`](MANIFESTO.md).

**Enumeração (determinística, sem aleatório)**:
- `tipo` ∈ {ausente, `b`, `n`, **`M`**, **`H`**} — as duas últimas são **adversariais** (colidem com o
  Eixo-1 do registry) e foram acrescentadas na emenda `cicloA-v2`.
- `nature` ∈ {ausente, `cpf`}.
- `nome` ∈ 11 variações, incluindo adversariais: `a:b`, `a b`, `a\b`, `a\nb`, `M`, `H`, `b` (= tag de
  tipo), `cpf` (= id de nature), vazio, ausente.
- 4 gramáticas candidatas × 9 entradas malformadas.

**CPF**: usado apenas como **identificador de nature** (`cpf`), nunca como valor — não há CPF nos
dados. Nenhum dado pessoal envolvido.

**Reprodutibilidade**: `python run.py` regenera todos os artefatos byte-a-byte (produto cartesiano
puro, sem seed). Células inaplicáveis aparecem como `N/A` **com a regra que as torna inaplicáveis**,
nunca omitidas (§3.1 do plano).

**Limites declarados**: só os critérios §S1 mecanicamente testáveis entram como célula (autocontenção,
canonicidade, dispatch local, prefixo/hijack, fail-loud, extensibilidade, custo em bytes). Os de
julgamento (§S1.7 inspeção, §S1.9 streaming, §S1.10 paridade S/M/H) ficam como leitura. O custo em
bytes é do **header isolado** — não em contexto de body real.

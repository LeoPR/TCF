# Proveniência — vazio e canonicidade do LF

**Fonte**: 100% sintético/determinístico, escrito literalmente em `inputs/<nome>-fonte.json`. Nenhum
dado real, sem aleatório. O objeto de estudo é a **moldura/framing do vazio**, não volume.

**Corpus** (7 datasets que isolam o vazio e a fronteira): `[]` · `[""]` · `["",""]` · `["a"]` ·
`["a",""]` · `["","a"]` · `["a","b"]`.

**Duas convenções de LF** comparadas (protótipos lab-local, funções `encA/decA` e `encB/decB`):
(A) LF terminador — o que o `src/tcf` já produz; (B) LF separador — a proposta literal do owner.

**Âncora real**: `outputs/*-wire-real.tcf` = o que `encode` do `src/tcf` REALMENTE emite. Os
`intermediates/*-conv{A,B}.tcfp` são as DUAS grafias hipotéticas, marcadas como tal.

**Honestidade do teste de compatibilidade (§2)**: o corpo real contém marcadores (RLE `*N|`), então o
lab NÃO reimplementa o codec do corpo — aplica só a regra de FRAMING de cada convenção e delega o
corpo ao `decode` real. Assim o `❌` de (B) é do framing, não de um splitter ingênuo (erro que a 1ª
rodada deste lab cometeu e foi corrigido).

**Teste de robustez (§3)**: modela a normalização POSIX real — acrescenta LF **se e somente se** o
arquivo não termina em LF (é o que editores/git/linters fazem), não um LF arbitrário.

**Reprodutibilidade**: `python run.py` regenera byte-a-byte. Nenhuma alteração em `src/tcf` — o lab
mede convenções hipotéticas contra o comportamento real do decode.

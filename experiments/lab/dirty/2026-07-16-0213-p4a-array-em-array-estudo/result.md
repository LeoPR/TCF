# Resultado — P4a (array-em-array via count recursivo)

**[probatório]** Dois atos, dois scripts, papéis distintos:

| script | quando | o que prova | artefato |
|---|---|---|---|
| `study.py` | **pré-weld** | a IDEIA (count recursivo faz RT) via `proto.py` — extrai a ideia, não copia o core | `outputs/00-estudo-proto.txt` |
| `run.py` | **pós-weld** | o **WIRE REAL** do core: `.tcf` inspecionável + roundtrip diffável | `outputs/*.tcf` + `outputs/*-rt.json` |

Números: [outputs/00-resultado.txt](outputs/00-resultado.txt).

> **Correção 2026-07-16** (achado do owner): este lab foi commitado **sem nenhum `.tcf`** — o protótipo
> devolvia dicionários em memória e nunca serializava wire, então as conclusões se apoiavam em print,
> não em artefato inspecionável. Violava a convenção do dirty lab (`wire TCF → .tcf`, roundtrip =
> arquivo diffável). `run.py` corrige: **24 `.tcf`** + roundtrip byte-idêntico ao canônico (`assert`).

## Confirmado (agora com wire)

1. **Count recursivo cobre o gate inteiro** (o gate está em `notas/p4-replevel-nroots-levantamento.md`
   — revisão crítica marcada *opinião, não decisão*, que o owner **adotou** ao aprovar o lab): básico,
   matriz, profundidade 3, inners vazios, `[]`≠`[[]]`≠`[[1]]`, arrays de arrays de OBJETOS, null entre
   arrays, null no inner, compose total (P2+P3b+P4a), strings/bool aninhados, campo no meio —
   **RT 12/12, cada um com `.tcf`**; fuzz de profundidade (1–4, nulls e tipos) **4000/4000**.
2. **Null estrutural entre arrays = P3b∘P4a**: a element-mask do nível externo cobre `[[1],null,[2]]`
   (`m#:3?:8[...]`); a do interno cobre `[[1,null,2]]`. **Sem gramática nova, não é P5** (P5 = tipo-MISTO).
3. **Estrutura legível sem materializar folhas** — o wire de `[{"m":[[1,2],[3]]}]` é:
   ```
   #TCF.8Hm#:3[#:8[]:8n
   \2          <- 1 registro, 2 elementos no nível externo
   *2-1|\2     <- counts internos: 2, 1   (seq-RLE)
   *3+1|\1     <- folhas: 1, 2, 3
   ```
   counts por nível são **colunas próprias**: quantos/onde-reinicia se lê sem tocar nas folhas (O(1)/view, Ciclo 4).
4. **Blob adulterado → fail-loud** no wire real: tag desconhecida, `]` deletado, bytes apendados,
   corpo esvaziado — 4/4 `HierarchicalError`, nunca silencioso.

## Custo por profundidade — desenho corrigido

O item do gate ("custo medido por profundidade, sem impor limite arbitrário antes da evidência") exige
separar **profundidade** de **carga**. Medir só com árvore cheia confunde as duas (folhas dobram a cada
nível). Por isso duas tabelas:

- **(2a) framing ISOLADO** — carga constante `[1,2]`, só a profundidade varia: **+7 B por nível,
  exato e constante** (prof. 1→6: 28, 35, 42, 49, 56, 63 B). Este é o custo do nível.
- **(2b) árvore binária cheia** — realista, mas **confundido de propósito**: Δ = +10/+10/+20/+12 B
  **não** é custo de nível (as folhas dobram junto). Está no lab para não sugerir que o framing cresce.

O que paga o nível é o **framing** (a coluna de count daquele nível); os counts em si colapsam por RLE.

## Fronteira (declarada)

- **P5 union** (tipos mistos no mesmo array) segue fail-loud — fora do P4a.
- **P4b raiz generalizada** — ato separado (muda contrato público). **Nada decidido**; ver
  [notas/p4b-levantamento.md](../notas/p4b-levantamento.md).
- Reuso entre níveis / "colunas com buracos" (preocupação do owner) → `H-REPLEVEL-FLAT-VS-PORNIVEL-01`, `.9`.

`confianca: Alta` p/ o design no escopo medido (RT 12/12 com wire + fuzz 4000 + adversarial 4/4 +
weld: 117 no módulo, suíte 754, byte-compat nível-0 14/14). Sintético declarado (didático construído
pro gate; fuzz seedado). **Não medido**: profundidade > 6 com carga real; custo em dataset real-world
aninhado (não existe no hub — ver `T-SHAPER-NESTED-OUTPUT`).

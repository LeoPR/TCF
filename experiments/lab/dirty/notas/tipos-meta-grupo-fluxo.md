# Tipos como specs — meta-grupo de hipóteses + fluxo (quando o tipo é identificado) [projeto]

> **Pedido do owner (2026-07-07)**: fechar um **meta-grupo de hipóteses de tipo**, formalizar **quando** um
> tipo/spec é identificado (entrada / processo / pós-HCC), e **projetar** (por enquanto, juntando o que temos)
> como isso entra no header — pra fechar o contrato do header ao máximo. Complementa a nota-mãe
> [tipos-como-specs.md](tipos-como-specs.md). Levantado por workflow (fluxo real do pipeline + marcadores do
> header + contrato TCF.8H) + design + crítico adversarial; **as 4 correções do crítico já estão aplicadas**
> (bN=domínio+índices não `tcf_bytes`; dois contratos de header distintos; bN=irmão bit-packed do dict).

## 1. Meta-grupo de hipóteses de tipo (H-TYPE-*)

| id | uma linha | status |
|---|---|---|
| **H-TYPE-00** (regra transversal) | Uma spec de tipo só se induz com segurança quando o valor faz **round-trip** por ela; o que reverte induz de graça (sem marcador), o que não reverte fica string ou leva marcador na colisão. | `confirmada-conceitual` — fio que une 01/02/03; é a regra de indução, não uma medição |
| **H-TYPE-01** | Fidelidade de tipos no TCF.8H: string=default sem tag; tipo divergente = 1 letra colada no size (`idade:4i`); estratégia C-híbrida (deduz número/bool de graça, tag só na colisão). | `confirmada-conceitual` — RT em amostras minúsculas (Ciclos 1a/1b), não em produção |
| **H-TYPE-02** | Família `bN` (b/b2/b4/b8: k≤2/4/16/256 → 1/2/4/8 bits, domínio embutido = referência) empacota enum/bool de baixa cardinalidade; razão teórica `8/w` pré-brotli contra o baseline correto **V2-B** (ADR-0025, já weldado). | `confirmada-empírica COM RESSALVA` — sob brotli q11 o ganho colapsa a 1.01×-1.33× (só vale como TCF terminal); N<5 fontes; `confiança: A-revalidar`; **não** welding candidate nesta forma |
| **H-TYPE-03** | bN só entrega ganho líquido quando o `.tcf` é consumido direto, sem re-compressão a jusante — mesmo nicho terminal já declarado pra V2-L (ADR-0018). | `aberta` — reenquadramento não testado como decisão de produto; `confiança: Baixa` |
| **H-TYPE-04** (projetada) | bN encaixa como candidato adicional do `min(tcf,raw,v2b,split)` por-coluna no multi-col, reusando o mecanismo de marcador-de-modo do header (novo char-prefixo, ao lado de `!`/`@`/`%`). | `aberta/projetada` — o contrato do header suporta a forma; falta o char + o ramo no `min()` + o par enc/dec; **gated por 02/03** |

## 2. Taxonomia: QUANDO o tipo/spec é identificado

Aterrada no fluxo REAL do `encode()` (levantado em `src/tcf/encoder.py` + `src/tcf/multi/core.py`):

```
dispatch list/dict → [multi] sort_by/nature pre-tx → POR COLUNA _encode_column:
   analyze_column → detect_cadence → detect_min_len → OBAT → HCC
→ [multi] PÓS-HCC: por coluna min(tcf, raw '!', v2b '@', split '%') pelo MENOR bytes
→ emissão do header (magic + marcadores + sufixo :id de nature)
```

| fase | quando | specs identificadas aqui | como vai pro header |
|---|---|---|---|
| **ENTRADA** | declarado pelo produtor / estrutura do input, antes de olhar os valores | tabela-vs-coluna (list/dict); **nature** CPF/CNPJ/IP (param, `SPEC_REGISTRY` fechado); nomes/posição; autoridade (mandatório/natural/deduzido → canonicaliza vs preserva); sort_by | declarado → **marcador escrito**. Nature vira **sufixo `:id`** do par (força `#TCF.8`, byte-neutro sem nature). Nomes no meta; `drop_names` omite |
| **PROCESSO** | induzido no pré-pass/OBAT a partir dos VALORES, 1 passada O(N), paralelizável (SideOutputs) | `is_numeric` (int/float 1ª aproximação); `cardinality`/`avg_len`/`sample` (enum vs high-card, gabarito); `cadence`; `min_len`; segmentação OBAT; composição HCC | induzido → **deduzido sem custo** (C2 str-default) OU **`:tipo` só na divergência** (C1, pendente). HCC não escreve tipo — produz o body que a fase pós-HCC rotula |
| **PÓS-HCC** | decidido DEPOIS de ter os bytes na mão — só existe pós-HCC | `min(tcf, raw, v2b, split)` por coluna (`multi/core.py:177-197`, consagrado); **bN** (camada V2-L); Formato A (reusa ref-stream do HCC) vs B | pós-HCC → **marcador-de-modo por-coluna** (char-prefixo `!`/`@`/`%`; bN = novo char). Magic sobe a `#TCF.7 M` sse `used_v2` |

## 3. bN é um IRMÃO bit-packed do dict (V2-B) — não uma categoria nova

Correção-chave do crítico. `@` (V2-B/dict) e bN fazem **a mesma coisa**, diferindo só no **radix do índice**:

| | domínio | índice por linha | competem por |
|---|---|---|---|
| **V2-B `@`** (weldado) | tabela de únicos (base-94) | índice **base-94** (char-level, ~1 byte) | colunas de baixa-cardinalidade |
| **bN** (projetado) | domínio embutido = referência | índice em **`w` bits** (bit-level) | **as MESMAS** colunas |

- Ambos produzem **domínio + stream de índices**; a razão `8/w` do bN vem de bit-packar os índices vs o
  ~1 byte/índice do dict — **não** de comprimir os `tcf_bytes` serializados do HCC.
- **Fonte dos índices**: no **Formato A**, bN reusa o **stream de refs que o HCC já emite** (`*N|^k` →
  `^1`=índice 0, `^2`=índice 1…) como os índices; não re-deriva. Isso é o "associar após o HCC" do owner.
- Por isso **competem pelo MESMO `min()`** e pelas MESMAS colunas — e por isso o **brotli colapsa** bN sobre
  V2-B: é a mesma informação (domínio+índices), só num radix mais denso; o entropy-coder geral chega perto
  dos dois. bN só ganha líquido quando NÃO há brotli a jusante (H-TYPE-03).

> Implicação de implementação: `_bN_encode` recebe **domínio + sequência de índices** (do ref-stream do HCC,
> ou re-derivada de `vals`), **nunca** `best_body` (que pode carregar bytes de dict/split se eles venceram).

## 4. Os DOIS contratos de header (não confundir)

O crítico apontou que eu estava fundindo dois codecs distintos. São separados:

### (a) multi-col FLAT `#TCF.7 M` (produção, `multi/core.py`)
Marcador = **char-PREFIXO de 1 char** no par do meta; `:` **já é reservado** ao sufixo `:id` de nature.
```
#TCF.7 M
<s1>=nome,@<s2>=sexo,%colD          @ = dict/v2b · % = split · ! = raw · (sem prefixo) = tcf
```
- Seleção por `min(tcf,raw,v2b,split)` pós-HCC (`:177-197`), zero-regressão por construção.
- Decoder ramifica por **prefixo** (`:328-383`), self-describing, sem flag global.
- Name-guard (`:128`) rejeita nomes iniciados por `!@%`.
- **bN aqui** = mais um **char-prefixo** (ex. `#`/`&`), **não** um sufixo `:b<w>` (que colidiria com o `:id`
  de nature). Ex. projetado: `#TCF.7 M\n<s1>=nome,#<s2>=sexo` (`#`=bN).

### (b) hierárquico TCF.8H (protótipo, `codec.py` do EXP-015)
Marcador = **sufixo** no par do colchete-meta: `col:size`, `:tipo` na divergência (`idade:4i`), `col:b<w>`.
Codec **separado** do multi-col; `:` é o portador de tipo aqui (não há `:id` de nature no mesmo slot).

**Não vender um portador `:` unificado.** Cada linha do checklist C1-C5 pertence a UM dos dois codecs.

## 5. Como bN encaixa (H-TYPE-04, projetado) — o "quase pronto no contrato"

No **multi-col flat**, o mecanismo já existe; bN é aditivo. Faltam **4 pontos** (nenhum é mudança de arquitetura):
1. `_bN_encode(dominio, indices) -> bytes | None` (None se não aplica ou RT não fecha). Recebe **domínio +
   índices** (§3), não `best_body`.
2. Um ramo no loop do `min()`: `if bN is not None and len(bN) < len(best_body): best_mode='bN'`.
3. Um **char de marcador** novo (ex. `#`/`&`) registrado em 3 lugares: prefix map (`:222`), switch do decode
   (`:328-336`) com `_decode_bN`, e o name-guard (`:128`).
4. `_decode_bN` byte-idêntico.

**Gate (H-TYPE-03)**: como sob brotli o ganho some, o candidato bN deve ser **opt-in** por um flag de
"saída terminal" — não default — pra não ser escolhido em pipelines com re-compressão a jusante (onde só
agregaria opacidade). Byte-canonical preservado no caminho default/legado (`fallback=False` → `#TCF.6`).

## 6. O que está pronto no header vs aberto (por codec)

**Pronto / em código (multi-col)**: mecanismo de char-prefixo por-coluna (`!`/`@`/`%`); seleção `min()`
zero-regressão; decoder ramifica por prefixo; sufixo `:id` de nature (`#TCF.8`) já materializa "tipo
declarado na entrada", byte-neutro sem nature; modos v2 sobem o magic só quando usados. Indução no pré-pass
(is_numeric/cardinality/sample) já paralelizável via SideOutputs.

**Pronto (hierárquico TCF.8H)**: `col:size` inline (C1), `:` como portador; str-default (C2).

**Aberto**:
- **bN**: char de marcador não alocado; par `_bN_encode`/`_decode_bN` não existe; formalizar que recebe
  domínio+índices (não `best_body`); gate "saída terminal"; welding gated (N<5, A-revalidar).
- **Canal de ENTRADA de tipos declarados** (int/float/hex-subspec, enum/bool) não existe além das 3 natures
  — falta desenhar como tipos declarados-pelo-produtor viajam out-of-band + header.
- **`:tipo` na divergência** (C1, TCF.8H): pendente (H-TYPE-01, não em código); medir o custo da folha
  DFS-última tipada perder a última-sem-size.
- **hex-default** nos sizes (C4): by-choice, aberto (T-OPT-INFERENCE).
- **Precedência entre as 3 fases**: validar que entrada (declarado) × processo (induzido) × pós-HCC
  (representação) não conflitam pra mesma coluna — ordem de precedência a definir.

## 7. Fecho (por partes)

O fio único: **`:tipo`, hex-default, nature, e bN são o mesmo espectro de specs**, regidos por round-trip
(H-TYPE-00); o que muda é **quando** cada um é conhecido (entrada/processo/pós-HCC), o que decide se é
**declarado** (marcador escrito), **deduzido** (sem custo / tag na colisão), ou **escolhido por `min()`**
(marcador-de-modo). bN, sendo pós-HCC e irmão do dict, **encaixa no mecanismo por-coluna que o header já
tem** — o "quase pronto" do owner. O próximo passo por-partes: (i) alocar o char + par enc/dec do bN atrás
do gate terminal, OU (ii) fechar antes o `:tipo`/hex do TCF.8H (contrato hierárquico), OU (iii) desenhar o
canal de ENTRADA de tipos declarados. Nenhum exige tocar `src/tcf` ainda.

**Protótipo do (i)**: [2026-07-07-2138-bn-candidato-min-prototipo](../2026-07-07-2138-bn-candidato-min-prototipo/result.md)
— o par `bn_encode`/`bn_decode` roda como candidato do `min()` com marcador char-prefixo `#`, RT-OK (mecanismo
prova; margem-vs-V2-B não, ver caveat do lab).

## 8. Direção: bN default sob PERFIL DE COMPRESSÃO (H-TYPE-05, owner — ver depois)

Reenquadramento do owner: em vez de bN **opt-in gated**, ele poderia ser **default** (após validar) com
**opt-OUT** sob um **perfil de compressão agrupado** — `--compress simple`/`low`/`terminal`/… — que bundla o
tradeoff **explicabilidade↔bytes** numa alça só (igual níveis do gzip/zstd/Parquet, melhor que N flags soltos).
O "bN criptografa um pouco" (body de bits opaco) é justamente o que o perfil administra.

Duas tensões que o perfil precisa acomodar (registradas, a fechar depois):
1. **bN só net-ganha TERMINAL** (colapso sob brotli, H-TYPE-03) → o default tem de amarrar no **intent
   terminal**, não ser blanket. O próprio `--compress` codifica isso: `simple`=textual, `terminal`/`max`=bN.
2. **Explicabilidade é pilar, mas a barca já saiu um pouco**: o **V2-B (dict base-94) já é default** e já é
   semi-opaco → bN **continua** essa tendência, não a **quebra** (grau: bN = bits crus, mais opaco que a
   tabela-dict-textual do V2-B). Argumento a favor do default, com ressalva de grau.

Desenho emergente (ilustrativo, não decidido): `simple` (textual puro, bN off) · `default` (V2-B on, bN
off/só-terminal) · `terminal`/`max` (bN on, packing binário). O knob = eixo de **opacidade + intent-terminal**.
`aberta`, ver depois. (H-TYPE-05 no [roadmap](roadmap-hipoteses.md).)

**Cross-links**: [tipos-como-specs.md](tipos-como-specs.md) · [roadmap H-TYPE-*](roadmap-hipoteses.md) ·
[checklist do header TCF.8H](tcf8h-header-checklist.md) ·
[T-OPT-INFERENCE](../../../../tickets/T-OPT-INFERENCE.md) · ADR-0018 (V2-L) / ADR-0025 (V2-B).

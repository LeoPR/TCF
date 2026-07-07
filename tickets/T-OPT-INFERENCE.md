---
title: T-OPT-INFERENCE — Otimizações por INFERÊNCIA (valor deduzido, não escrito) — 1º item: base HEX dos sizes
status: open
priority: P2
created: 2026-07-05
updated: 2026-07-07
blocked-by: []
related:
  - tickets/T-FMT-TCF8H-HEADER.md
  - experiments/lab/dirty/notas/tcf8h-header-checklist.md
  - experiments/lab/clean/EXP-015-tcf-hierarquico-csv-json/
  - experiments/lab/dirty/notas/tcf8h-proximas-ideias.md
---

# T-OPT-INFERENCE — otimizações por inferência/dedução

**[dispositivo]** Classe de otimizações **separada** das decisões estruturais do cabeçalho
([T-FMT-TCF8H-HEADER](T-FMT-TCF8H-HEADER.md)): itens onde o valor **não é escrito**, e sim **deduzido**
(por convenção, por dedução do próprio dado, ou por comando externo). Trade central: **bytes × auto-descrição**.
O ticket do header só prevê a EXISTÊNCIA (ex.: que os sizes têm uma base); a decisão/inferência mora aqui.

## Framework unificado — specs induzidas (owner 2026-07-06)

Reframe do owner: **tipo, base numérica (hex) e natures são a MESMA coisa — specs no mesmo espectro**, do
mínimo (`string`/`int`/`bool`) ao rico (CPF/datetime). Cada spec:
- justifica-se por **COMPRESSÃO ou ACELERAÇÃO** (senão fica `string`, não spec);
- **induz-se com segurança ⟺ round-trip** (o valor reverte pela spec) — regra universal que resolve o
  self-description de TODAS (hex/tipo/nature) de uma vez;
- é **proposta pelo gabarito** (1ª amostra, `analyze_column.sample`) e **confirmada pelo round-trip** em todas.

O **Item 1 (hex)** abaixo é uma **sub-spec numérica** (a base do número) sob essa regra. Análise medida:
nota [tipos-como-specs](../experiments/lab/dirty/notas/tipos-como-specs.md) + lab
[`2026-07-06-2310-tipos-como-specs`](../experiments/lab/dirty/2026-07-06-2310-tipos-como-specs/result.md).
Achado a lembrar: em TCF **textual** a compressão de tipo é modesta (bool ~6B flat/dict); o forte é
**aceleração** + o espaço **binário** (bool-bitmap V2-L). Não superestimar compressão de tipo em texto.

## Item 1 — base HEX dos byte-sizes (a discussão do owner)

**Fato (medido, EXP-015 `05-header-condicoes.txt`)**: `len(hex(s)) ≤ len(str(s))` SEMPRE — hex nunca perde
bytes; ganha em `s∈[10,15]∪[100,255]∪[256,4095]…` (fronteiras 16ᵏ vs 10ᵏ).

**O problema de auto-descrição** (owner): sem marcador, "10" é 10 (dec) OU 16 (hex) — o arquivo não se
explica. **Resolução proposta (owner)**: **HEX é o DEFAULT** (convenção fixa) → "10" é sempre 16, o arquivo
se auto-explica **por convenção**, sem marcador. O **decimal** é opt-in só por **comando externo**
(out-of-band) → nesse modo o arquivo NÃO é auto-descritivo (byte-mínimo, contrato pré-acordado).

**Dedução (rede de segurança, quando a base não é fixada por comando)**:
1. **Letra [a-f] presente** num size → **inequivocamente HEX** (decimal não tem letras).
2. **Quebra na expansão** → se interpretar como decimal e o byte-split NÃO fechar (sizes não cobrem o
   body / caem no meio de um valor), então é HEX (validação por consistência).
3. **Ambíguo** (all-digit, ambas as bases dão split válido) → cai no **default HEX**.

**Crítica (a favor)**:
- Os sizes são **metadados de máquina**, não dado do usuário → o custo de legibilidade é baixo ("quem lê
  os números entende hex", owner). O pilar explicabilidade sofre pouco no size (≠ nos valores).
- Hex-default **resolve** a ambiguidade que o próprio owner levantou (convenção fixa = auto-descrição).
- A dedução por letra é O(1) e robusta; a base é propriedade **do arquivo** (não mistura dec/hex no mesmo).

**Crítica (cautelas)**:
- Modo decimal-por-comando **quebra a auto-descrição** — só usar sob contrato (ex.: O-FMT-14 derivável).
- A dedução "quebra-na-expansão" custa uma tentativa dec→hex no decode; **com hex-default não precisa**
  (assume hex direto). Só relevante se algum modo legado escrever decimal sem marcar.
- Consistência: **um arquivo, uma base** (não misturar).

**Decisão (a fechar)**: HEX-default; decimal só por comando externo; dedução como fallback. → gate de formato.

## Item 2 — enum/bool por largura de bits (família `bN`) — CORRIGIDO 2026-07-07

**Fato (medido, corrigido)**: k valores distintos → w bits/valor (`b`≤2/`b2`≤4/`b4`≤16/`b8`≤256), domínio
embutido = referência. Contra o baseline CORRETO (V2-B, `fallback=True`, ADR-0025, já weldado — não "raw
HCC"), razão teórica limpa `8/w` pré-brotli (12 colunas reais adult/tpch/receita).

**Achado que muda o escopo**: sob brotli q11, o ganho colapsa pra 1.01×-1.33× (praticamente zero em alguns
casos) — o brotli já acha a entropia que V2-B deixou; o bit-pack não adiciona muito além disso. Confirma
empiricamente o caveat de H-REF-05 (2026-06-19, qualitativo até então). **Escopo honesto**: só vale como
TCF representação **terminal** (sem re-compressão a jusante) — mesmo nicho que V2-L já declara (não
compete com gzip/brotli/zstd). NÃO é welding candidate nesta forma (N<5 fontes reais + gate brotli
reprovado). Ver [H-TYPE-02](../experiments/lab/dirty/notas/roadmap-hipoteses.md),
[tipos-como-specs.md](../experiments/lab/dirty/notas/tipos-como-specs.md) (seção "CONSOLIDAÇÃO E CORREÇÃO
2026-07-07"), labs
[2026-07-06-2354-spec-bin-motor](../experiments/lab/dirty/2026-07-06-2354-spec-bin-motor/result.md),
[2026-07-07-0028-spec-bitwidth-bN](../experiments/lab/dirty/2026-07-07-0028-spec-bitwidth-bN/result.md).

## Itens futuros (outras inferências)

- Cardinalidade/kind/rows deduzidos (já no header via colchete — P5/P7).
- Tipos deduzidos (str default; `:tipo` só quando diverge).
- Nomes deduzidos/omitidos (drop_names) quando anônimo.
- (a telemetria sugestiva de ORDEM vive em T-FLOW-ENCODE-STRATEGIES-TELEMETRY — é inferência de forma, não de valor.)

## Critério de aceite (item 1)

- [ ] Convenção **HEX-default** para sizes no TCF.8H documentada; decimal só via comando externo.
- [ ] Dedução (letra→hex; expansão-break→hex; ambíguo→default-hex) especificada.
- [ ] Medir a economia real (hex vs dec) em árvores reais (quando sizes caem nas faixas beneficiadas).
- [ ] (se weldar) gate real-world + baselines.

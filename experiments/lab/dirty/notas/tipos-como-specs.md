# Tipos como specs — o espectro único (reframe do owner, 2026-07-06) [probatório→conceitual]

**Origem**: owner 2026-07-06, sobre o resultado dos tipos (Ciclos 1a/1b). Lab que mede:
[`2026-07-06-2310-tipos-como-specs/`](../2026-07-06-2310-tipos-como-specs/result.md).
Amarra: [H-TYPE-01](roadmap-hipoteses.md), [T-OPT-INFERENCE](../../../../tickets/T-OPT-INFERENCE.md),
natures (ADR-0015), [checklist C1/C2/C4](tcf8h-header-checklist.md).

## A tese

**Tipo não é um bolt-on — é a ponta mínima do MESMO espectro de specs** que já inclui as natures
(CPF/CNPJ/datetime). Um primitivo (`string`/`int`/`float`/`bool`/`null`) é uma **spec ultra-minimalista
induzida**. Do mínimo ao rico: `string` (fallback) → `int`/`float`/`bool` → `nature` (CPF, datetime, …).
No código isso já existe nas duas pontas: `natures.templated_checked.TemplatedCheckedSpec` (rica) e
`column_features.analyze_column` (`is_numeric`, `cardinality`, `sample`) que **induz** a ponta mínima.

## Toda spec se justifica por COMPRESSÃO ou ACELERAÇÃO

Uma spec só vale a pena se dá pelo menos um dos dois:
- **Compressão**: o body encolhe (template, delta, dict, bitmap).
- **Aceleração**: o decode não precisa deduzir (parse/typing conhecido) + habilita acesso lazy/tipado.

Se não dá nenhum → não spec (fica `string`). Medido (o número corrigiu a intuição):

| spec | induz de | compressão (medida) | aceleração | round-trip guard |
|---|---|---|---|---|
| **string** | — (default) | não | não (identidade) | — |
| **int** | dígitos, sem ponto | HCC/seq-RLE quando sequencial (1..100: 601→23B); cadence/delta se ligado | parse rápido | `str(int(v))==v` |
| **float** | tem ponto | idem int | parse rápido | `str(float(v))==v` |
| **bool** | domínio {true,false} | **TEXTO: só ~6B flat** (dict-shrink; HCC já referencia os 2 distintos); **bitmap** (1 bit/val) só em **binário V2-L** | mapa direto | `v∈{true,false}` |
| **null** | máscara (Ciclo 1c) | body vazio + def-level | pula célula | — (máscara) |
| **nature** (CPF/CEP/datetime) | template/gabarito | **template + delta** (forte) | validação | round-trip do template |

> **Correção empírica importante**: em TCF **textual**, o bool-spec NÃO economiza ~N (1 bit/valor) — só o
> **dict** encolhe uma vez (~6B), porque o HCC já dedup os 2 valores e guarda N referências idênticas. O ganho
> por-valor do bool é **binário** (bitmap, V2-L/ADR-0018). Em texto o bool vale por **aceleração**. Não
> superestimar a compressão de tipo em texto — o forte é aceleração + o espaço binário.

## Além dos 2 eixos: características ORTOGONAIS (owner 2026-07-06)

Compressão e aceleração são **preditivas** (dizem se vale aplicar). Mas uma spec tem mais eixos ortogonais:

| eixo | o que é | decide |
|---|---|---|
| 1 compressão | body encolhe | vale aplicar? |
| 2 aceleração | decode sem deduzir + acesso tipado | vale aplicar? |
| 3 **autoridade** | mandatório / spec-natural / deduzido | liberdade de canonicalizar |
| 4 **normalizabilidade** | superfície livre vs byte-locked | pode mudar a superfície? |
| 5 **fechamento de domínio** | fechado (enum/bitmap) vs aberto | habilita bitmap/dict |
| 6 **variante** | superfície do mesmo semântico (1/0, t/f, Y/N) | o que guardar p/ RT |
| 7 **reversibilidade** | round-trip | seguro induzir? |
| 8 **validação/sanidade** | nature alerta anomalia (só detecta) | efeito colateral |

**Autoridade** (o ponto do CSV vs typed): no **CSV cru** trata-se como **string/enum** (preserva a superfície
exata, sanidade — `True`/`False` fica como está); se a entrada é **typed/declarada**, o compressor pode
**canonicalizar** (a saída pode sair `true` minúsculo — "vemos o DADO, não a string"). Três classes:
- **mandatório**: tipo declarado na entrada → canonicaliza.
- **spec-natural**: padrão conhecido (bool, datetime, CPF) → **gabarito-da-spec** (template implícito, a
  coluna nem guarda referência: os valores vêm da spec).
- **deduzido**: induzido do dado via round-trip → preserva superfície.

## Estudo empírico: "boolean" nos nossos datasets → é ENUM, não bool

Varredura (lab [`2026-07-06-2332-boolean-spec-datasets`](../2026-07-06-2332-boolean-spec-datasets/result.md),
synthetic + adult/tpch/receita/…): **ZERO `true`/`false`** em dado real. O que existe é **enum-2/3 com
superfície = DADO** (Male/Female, <=50K/>50K, F/O, A/N/R) + `matriz_filial=1|2` (**não** 0/1!). Portanto:
- **o primitivo útil é ENUM/domínio-k** (fechado, pequeno); **boolean (true/false) é a variante semântica,
  rara em tabela**. A spec certa é *enum-k*, com boolean como sub-caso (k=2 semântico).
- **Variante** é um eixo real: `1/0`, `t/f`, `true/false`, `True/False`, `Y/N` são a MESMA spec (bool) com
  superfícies diferentes; `matriz_filial=1|2` mostra que assumir 1/0 corromperia a semântica.
- **Bytes** (adult.sex, N=48842): raw 97KB → textual 49KB (~2×, encurta superfície) → **bitmap 6KB (~16×)**.
  O ganho textual é ∝ encurtamento da superfície; o grande/constante (1 bit/val) é **binário** (V2-L).

**Motor spec_bin** (lab [`2026-07-06-2354-spec-bin-motor`](../2026-07-06-2354-spec-bin-motor/result.md)):
enum-2 sem catálogo via **escape** (os 2 mais comuns = domínio, guardados 1× afixo-comprimidos: `male→fe1`);
corpo = bit-stream com **2 codificações** que o motor escolhe: **RLE** (textual/explicável, mantém a quebra) vence
ordenado/skew; **packed** (binário N/8, V2-L) vence espalhado. **Overlay de exceções** (99% dominantes + raros
null/other → canal esparso, = def-level do 1c). Medido: em **dado real espalhado, packed vence** (adult.sex
16×; 17–21k runs) → o corpo útil de enum real é binário; RLE fica pro ordenado + pela explicabilidade.

**Reuso do HCC + Formato A/B** (lab [`2026-07-07-0016-spec-bin-formato-A-B`](../2026-07-07-0016-spec-bin-formato-A-B/result.md)):
o HCC **já** produz o binário como literais+refs com índices naturais (`*3|male\n*2|fe1\n*2|^1\n*3|^2` →
male=^1=bit0, female=^2=bit1; `*N|^k` = bit-stream em RLE). Logo o `spec_bin` é **camada pós-HCC (V2-L)**, não
substituto: ordenado → HCC-RLE nativo (textual); espalhado → empacota as refs. **Formato A** (literal na 1ª
ocorrência + 2º declarado no 1º byte-escape) reusa o layout do HCC e é **single-pass streaming** (owner
prefere); **Formato B** (2 literais no topo) é 2-passadas. Mesmos bytes.

**Spec primitivo por LARGURA DE BITS `b<w>`** (lab [`2026-07-07-0028-spec-bitwidth-bN`](../2026-07-07-0028-spec-bitwidth-bN/result.md),
owner): generaliza `spec_bin` a enum-k. k distintos → w bits → 8/w linhas/byte: k≤2→**b**(8/byte) ·
k≤4→**b2**(4/byte) · k≤16→**b4**(2/byte) · k≤256→**b8**(1/byte). O spec = `col:b<w>` + a **lista do domínio
embutida = a referência** (índice↔valor); `spec_bin`=`b`. Medido em 12 colunas reais: **bit-pack vence em
todas** (dado espalhado) — b ~16×, b2 ~6-9×, b4 ~2-6× vs raw HCC. **Pesa vs HCC-nativo** (RLE de refs): HCC
ganha ordenado (poucos runs, textual/explicável); bit-pack ganha espalhado (V2-L). O motor escolhe o menor;
header `col:b<w>` textual roteia. Une string→enum-k num só spec primitivo.

## A regra universal de indução: ROUND-TRIP

**Uma spec induz-se com segurança ⟺ o valor faz round-trip por ela** (encode-pela-spec → decode devolve o
original). É zero-config e resolve o self-description (o mesmo problema do hex, do tipo e da nature) de uma vez:

| valor | induz | por quê |
|---|---|---|
| `"30"` | **int** | `str(int("30"))=="30"` ✓ |
| `"01310"` | **string** | `int("01310")=1310` → `"1310"` ≠ `"01310"` (zero à esquerda) ✗ |
| `"4.5"` | **float** | `str(float("4.5"))=="4.5"` ✓ |
| `"4.50"` | **string** | `float("4.50")=4.5` → `"4.5"` ≠ `"4.50"` ✗ |
| `"1e3"` | **string** | `float("1e3")=1000.0` → `"1000.0"` ≠ `"1e3"` ✗ |
| `"true"` | **bool** | `∈ {true,false}` ✓ |
| `"True"` | **string** | JSON é minúsculo; `∉ {true,false}` ✗ |

O que reverte, induz de graça (sem marcador). O que **não** reverte é uma string que *parece* tipada → fica
string, ou leva marcador explícito (a **C-híbrida** do 1b). É o análogo exato do **hex-default**
(T-OPT-INFERENCE) e da **1ª-string-molde do OBAT**.

## Gabarito: a 1ª amostra propõe, o round-trip confirma

`analyze_column.sample` (primeiras 20) = o **gabarito**. A 1ª amostra **propõe** a spec da coluna; o
round-trip em **todas** **confirma** (ou rebaixa pra string). Medido:
- `idades ["30","41",…]` → 1ª propõe int, todas revertem → **coluna int**.
- `ceps ["01310",…]` → 1ª propõe int, mas não reverte → **string** (o guard salva).
- `misto ["30","ana",…]` → 1ª propõe int, `"ana"` quebra → **string**.

= a **C-híbrida (1b) generalizada**: propõe pelo gabarito, confirma pelo round-trip, tag na colisão.

## Consequências (o que isto reorganiza)

1. **Unifica** três coisas que estavam separadas num **só mecanismo**: tipo (1a/1b) + base hex
   (T-OPT-INFERENCE) + natures (ADR-0015). Todas = specs induzidas por gabarito + round-trip; diferem só na
   riqueza. Hex vira uma **sub-spec numérica** (a base do número); CPF vira uma spec-template.
2. **Pipeline**: a indução é um estágio do **pre-pass** já existente — `analyze_column` induz (is_numeric,
   cardinality, sample), `detect_cadence`/HCC comprimem o número. Custo ~zero ("só o que já se calcula",
   SideOutputs). É "colocar no fluxo do mecanismo todo" (owner).
3. **Decisão por spec**: induz quando (comprime OU acelera) E faz round-trip; senão string (+ marcador na
   colisão). O eixo compressão/aceleração diz QUANDO uma spec vale; o round-trip diz SE é segura induzir.
4. **Camadas**: a compressão forte de alguns primitivos (bool→bitmap) é **binária (V2-L)**, não textual — o
   espectro de specs atravessa as duas camadas (header textual roteia; body pode ser binário).

## Aberto / próximo (Ciclo 3)

- Formalizar o registro de specs (primitiva ↔ nature) e o ponto de indução no pre-pass.
- Medir o ganho de **aceleração** (decode tipado vs deduzido) — hoje só a compressão foi medida.
- bool-bitmap na camada binária (V2-L) — quantificar o 1-bit/valor.
- Ligar hex (T-OPT-INFERENCE) como sub-spec numérica sob esta regra única.

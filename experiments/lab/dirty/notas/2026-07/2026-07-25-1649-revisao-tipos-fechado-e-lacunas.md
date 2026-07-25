---
title: Revisão da frente de tipos — o que fechou, o que falta antes de int/float/specs
type: revisao
status: aberta
created: 2026-07-25
related:
  - docs/adr/0034-header-default-100-porcento-single-col.md
  - experiments/lab/dirty/2026-07/2026-07-25/2026-07-25-1630-null-slot0-weldado-medicao/
  - experiments/lab/dirty/notas/2026-07/2026-07-24-2140-levantamento-null-e-tipos.md
  - experiments/lab/dirty/notas/2026-07/2026-07-24-2320-null-como-referencia-induzida-etapas.md
  - experiments/lab/dirty/notas/2026-07/substituicao-indices-especiais-plano.md
---

# Revisão da frente de tipos

Pedido do owner (2026-07-25): revisar o que foi otimizado em cabeçalho / string nativo /
binário-bool, ver **se falta algo nessa mesma veia**, antes de abrir int, float e specs.

Tudo abaixo foi **medido contra o `src/tcf` real**, não listado de memória.

---

## 1. O que FECHOU

| frente | estado | onde |
|---|---|---|
| **cabeçalho** | `#TCF.8` default em 100% dos casos; órfão vira escape explícito (`stamp=False`) | ADR-0034 |
| **string nativo** | flat implícito, sem tag — é o tipo por exclusão | core |
| **string + null** | flat, null = slot 0 pré-alocado (`0`) | 2026-07-25 |
| **vazio `[]`** | `#TCF.8\n` (7 B) em vez de fugir pro `.8H` | weld #2 |
| **bool** | `#TCF.8b`, dois algoritmos (core vs denso `b1`) competindo no FLOOR | weld #4a/#4b |
| **teto de descompressão** | `max_length` (convenção zlib) | 2026-07-24 |

Medido hoje: bool escala muito bem — **−93% a −97%** vs JSON compacto a partir de ~64
elementos.

## 2. As lacunas na MESMA veia (ordenadas por impacto medido)

### 2.1 `bool + null` ainda cai no `.8H` — a mais grave

É exatamente o problema que acabamos de fechar para string, ainda aberto para bool:

| coluna | JSON | TCF hoje | |
|---|---:|---:|---|
| `[true,null]` | 11 | 46 | **+227%** |
| `[true,null,false]` | 17 | 46 | **+171%** |
| 16 elementos c/ null | 85 | 105 | **+24%** |
| 100 elementos c/ null | 526 | 486 | −8% |

Um único null joga a coluna inteira no envelope hierárquico. **O TCF fica 3× maior que o
JSON** no caso pequeno — o oposto do foco declarado.

**Dependência**: o modo denso `b1` é 1 bit = 2 estados; o trio `{null, false, true}` não cabe.
Ou o null força o modo core, ou entra um denso de 2 bits.

### 2.2 `multi-col + null` cai no `.8H`

`{"a": ["x","y"]}` → `.8M`, 13 B. `{"a": ["x",None]}` → `.8H`, 44 B. Mesma classe da 2.1, um
nível acima. A rota que abrimos foi só a do single-col.

### 2.3 `#TCF.8s` é fail-loud — inconsistência do modelo

Verificamos que **todo mecanismo aceita a forma explícita** além da otimizada (RLE, `^N`,
composição, modo, hex). String é a única exceção: seu tipo só existe implícito. `#TCF.8s`
está no registry mas o decode responde *"discriminador 's' desconhecido"*.

Não custa bytes (ninguém precisa emitir), mas é a única quebra do padrão que formalizamos.

### 2.4 Denso do bool só tem `w=1`

`b2`/`b4`/`b8` estão reservados no namespace e dão fail-loud. Conecta direto com a 2.1: o
trio precisaria de 2 bits.

### 2.5 A tensão bool-tag × índice reservado, agora com consequência

Registrada no levantamento §5, sem decisão — mas a 2.1 **força** a decisão, porque os dois
mecanismos numeram de formas diferentes:

- **tag `b` (soldado)**: domínio implícito do denso é `false=0`, `true=1` — bits, espaço
  próprio, separado da tabela de referências.
- **plano de índices reservados**: `null=0`, `true=1`, `false=2` na tabela.

Se `bool+null` entrar no denso com 2 bits, a numeração natural seria `0=null, 1=false,
2=true` — o que **alinharia os dois** e resolveria a tensão em vez de perpetuá-la. É o
caminho que os dois desenhos apontam, mas ninguém decidiu.

### 2.6 Custo do cabeçalho em payload minúsculo (não é bug, é consequência)

| coluna | JSON | TCF | |
|---|---:|---:|---|
| `[true]` | 6 | 13 | **+117%** |
| `[true,false]` | 12 | 14 | +17% |
| 4 bools | 22 | 14 | −36% |

O crossover do bool contra JSON é **~4 elementos**. Abaixo disso o `#TCF.8` (7 B) domina.
É consequência direta do ADR-0034 (header default, custo aceito) — registrado para que a
decisão continue visível, não como pendência.

## 3. O que NÃO é desta veia (a frente seguinte)

- **int / float**: hoje `.8H` com tag `n`. O plano já registra que **número fica na dedução**
  (cardinalidade infinita não cabe em índice reservado) — é outro mecanismo.
- **specs / naturezas**: `#TCF.8 [nome]:id`, já existente e com FLOOR próprio.
- **NaN / ±Inf**: fail-loud por RFC 8259; pertencem ao domínio de folhas (H-HIER-SCALAR-01).
- **ausência (`-`)**: máscara, declarada como forma de trabalho.
- **ordem canônica dos slots reservados**: continua não fixada — pré-requisito de
  determinismo para qualquer especial além do null.

## 4. Recomendação

Fechar **2.1** antes de abrir int/float: é a maior regressão medida contra JSON (+227%), é
simétrica ao que já foi feito para string, e é a única lacuna que **força** a decisão da 2.5
— que por sua vez condiciona todo o resto do framework de índices.

A 2.3 é barata e fecha a coerência do modelo explícito/implícito. A 2.2 é a mesma ideia num
nível acima e pode esperar. A 2.4 vem junto com a 2.1 se o caminho do denso de 2 bits for o
escolhido.

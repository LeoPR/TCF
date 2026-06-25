# 0029 — Estratégia de identificação de versão/formato: semi-implícito + major-externo

**Status**: proposed
**Date**: 2026-06-24
**Deciders**: project owner
**Tags**: format, versioning, self-describing, byte-economy, 1.0, identification

> **proposed.** Decide a POLÍTICA de quem identifica versão/formato de um blob TCF
> (arquivo vs chamada vs externo). Aprovada → guia a implementação do discriminador
> `#TCF.8` (§"Realização"). Refina [ADR-0024](0024-pre-1.0-versioning-git-as-compat.md)
> / [ADR-0028](0028-pre-1.0-versioning-minor-format-coupling-release-cadence.md)
> (eixos de versão) e [ADR-0017](0017-format-spec-v1-frozen.md) (freeze).

## Context and Problem Statement

Quem é responsável por saber **como descomprimir** um blob TCF? Hoje o projeto
mistura duas respostas sem ter decidido de propósito:

- **Multi-col**: self-describing — `#TCF.7 M` / `#TCF.8 M` no arquivo. Decodável sozinho.
- **Single-col**: **órfão** — body puro, ZERO marcador de versão. Decodável só porque
  o decoder **assume** "single-col, formato atual"; a versão é implícita em *qual
  versão da lib você usa* — exatamente o git-as-compat ([ADR-0024](0024-pre-1.0-versioning-git-as-compat.md)).

A tensão: a **filosofia TCF** valoriza textual/inspecionável/explicável (um `.tcf`
deve poder se identificar); o **foco byte-level** (transmissões minúsculas) quer o
blob mínimo/órfão. O trabalho do `#TCF.8` self-describing (natures, [ADR-0027](0027-nature-mark-header-self-describing.md))
+ a extensão pro single-col forçaram a pergunta: **o header `#TCF.N` deve ser
obrigatório, opcional, ou desnecessário (a chamada declara)?**

## Decision Drivers

- **Byte-economia**: o caso comum (single-col simples) não pode pagar header — D1-D9=1523B
  é byte-canonical pinado e deve ficar intacto.
- **Self-description/proveniência**: um blob sem nenhuma identidade vira texto opaco,
  "órfão", dependente de quem o produziu — contra a filosofia "áreas explicáveis".
- **Decodabilidade pós-1.0**: precisa ser possível descomprimir um blob daqui por diante;
  se o header for opcional, algo tem que garantir a interpretação.

## Decision Outcome — semi-implícito, 3 camadas (mais-barato-primeiro)

Identificação em camadas; cada blob usa a mais barata que serve:

1. **Implícito-por-contrato (órfão, 0 bytes)** — o formato **DEFAULT** (single-col,
   **congelado no 1.0**) NÃO leva marcador. Body sem header ≡ "TCF 1.x single-col,
   formato congelado". Caso comum e mais barato.
2. **Semi-implícito (header in-file, opt-in, ~7–12 B)** — quando o blob **DESVIA** do
   default: multi-col, spec/nature, ou (futuro) variante de formato → emite `#TCF.N`
   + flags. Self-describing onde importa. É onde vive o discriminador `#TCF.8`.
3. **Explícito (chamada, 0 bytes no arquivo)** — `encode`/`decode` podem **sempre**
   declarar versão/formato/spec: pra blob órfão, interpretação forçada, ou spec
   out-of-band (`decode(blob, nature=...)`).

### O contrato de identificação

- **Major version = EXTERNO**: você precisa saber que está decodando *TCF 1.x* (vem
  do contexto: extensão `.tcf`, a lib, o protocolo). A lib 1.x sabe ler o formato 1.x.
- **Variações de formato (minor) = IN-FILE**: o header `#TCF.N` marca o desvio.
- **Specs/natures = semi-implícito OU explícito**: header `:spec` quando há (ADR-0027),
  ou `nature=` na chamada.

### O linchpin: congelamento 1.0

A camada 1 (órfão) só é **segura** se o formato do body single-col for **CONGELADO
no 1.0**. Aí um body sem header é inequivocamente decodável pra sempre como "TCF 1.x
single-col". Se um 2.0 futuro mudar o body, blobs 1.x órfãos dependem de a lib saber
"isto é 1.x" (a regra major-externo cobre isso). **Congelar o body single-col no 1.0
é pré-requisito desta política** — sem isso, órfão é arriscado.

## Realização — discriminador `#TCF.8` (camada 2)

O caractere logo após `#TCF.8` discrimina (1 char, dispatch limpo):

| após `#TCF.8` | tipo | header |
|---|---|---|
| `M` | multi | `#TCF.8M<NN[=nome][:spec]>,<...>` (meta na linha do shebang; nome opcional) |
| ` ` (espaço) | single + spec | `#TCF.8 [nome]:spec` (nome opcional) |
| `\n` | single version-stamp (opt-in, sem spec) | `#TCF.8` |

- **Multi perde o espaço antes do `M`** (`#TCF.8 M` → `#TCF.8M`) — necessário pro
  discriminador de 1 char; senão o espaço do multi colidiria com "single". Economiza
  ~2 B/multi (espaço + a quebra de linha do meta separado). Cada coluna = `NN[=nome][:spec]`.
- **`#TCF.8\n` (single sem nada)** = carimbo de versão **opt-in** num single-col plano
  (raro). **NÃO é o default**: single-col plano segue **órfão (body-only)** — camada 1,
  byte-idêntico. Existe só pra quem quiser estampar a versão sem spec/nome.
- `#TCF.7 M` / `#TCF.6 M` (legado) mantêm a forma própria (cada versão de formato é
  auto-contida; o discriminador-por-char é específico do `#TCF.8`).

## Consequences

**Positivas**:
- Caso comum órfão (0 bytes) — byte-neutro preservado (D1-D9 intacto).
- Self-describing onde importa (multi/spec) — proveniência + decodabilidade standalone.
- A chamada pode sempre declarar — flexível pra dados órfãos / out-of-band.
- Alinha filosofia (inspecionável quando relevante) E byte-economia (mínimo no comum).

**Negativas / custos**:
- Blob órfão exige conhecimento EXTERNO de "isto é TCF 1.x" (extensão/lib/protocolo).
- **Compromisso de congelar o body single-col no 1.0** (linchpin) — limita evolução do
  formato single-col pós-1.0 a um major bump.
- Duas formas de multi coexistem (`#TCF.7 M` espaço vs `#TCF.8M` sem) — assimetria por
  versão (aceitável: cada `#TCF.N` é auto-contido).

## Alternatives considered

- **Tudo órfão (sem header nunca; chamada declara sempre)**: mais barato, mas o `.tcf`
  vira texto opaco sem identidade — contra a filosofia "áreas explicáveis". Rejeitado.
- **Tudo self-describing (header em todo blob)**: máxima proveniência, mas quebra o
  byte-neutro do default (header em D1-D9). Rejeitado.
- **Semi-implícito** (esta): o meio que preserva ambos. Escolhido.

## Relation to other ADRs

- [ADR-0017](0017-format-spec-v1-frozen.md) (freeze): esta política DEPENDE de congelar
  o body single-col no 1.0 (estende o freeze do #TCF.6 pro single-col default).
- [ADR-0024](0024-pre-1.0-versioning-git-as-compat.md) (git-as-compat): formaliza o
  "major-externo" — a lib reproduz o formato da sua versão.
- [ADR-0028](0028-pre-1.0-versioning-minor-format-coupling-release-cadence.md) (3 eixos):
  o eixo FORMATO (#TCF.N) é o marcador in-file desta política.
- [ADR-0027](0027-nature-mark-header-self-describing.md) (natures self-describing): caso
  de uso da camada 2 (spec in-file); a camada 3 (explícito) é o `nature=` out-of-band.

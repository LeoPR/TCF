# Plano — Filtros populares modulares via DSL textual + "compilador"

**Data**: 2026-06-16 · **Tipo**: plano/design (não implementa) · owner avalia.
Origem: ideia do owner — filtros como **definições textuais human-friendly** que passam por um
**"compilador"** e integram como natures executáveis/plugáveis ("facilidade visual de construção").

## Revisão crítica (honesta)
- **A ideia se sustenta — e NÃO parte do zero.** `TemplatedCheckedSpec` / `TemplatedPaddedSpec`
  (`src/tcf/natures/`) já são dataclasses frozen **quase-declarativas** (DADOS + uma `check_fn`),
  e o encoder já despacha via `nature`/`nature_per_col` sem `isinstance`. Um "compilador DSL" é
  literalmente um **gerador de instâncias** desses specs — mapeamento 1:1, baixo risco.
- **Onde rende**: tira a fricção de escrever filtro (texto vs dataclass Python); fixa a única
  parte "código" (`check_fn`) numa **biblioteca fechada de algoritmos nomeados** (mod11-cpf,
  mod11-cnpj, luhn, none); e o **round-trip no compile-time** dá a garantia lossless "de graça".
- **Onde é arriscada / over-eng** (vigiar):
  1. Inventar gramática YAML/EBNF verbosa quando 6-7 campos cabem num dict trivial — o risco real
     é o **parser do `template`** (contar Ns, gerar regex, `mask_variants`) virar frágil.
  2. **O ganho de COMPRESSÃO dos filtros-alvo não está caracterizado** — o FILTRO-NUMERO já
     evaporou sob brotli. O compilador facilita produzir specs que **ninguém deveria weldar**.
     → O valor do DSL é **ergonomia/extensibilidade/explicabilidade**, NÃO bytes garantidos.
  3. Lossless de terceiro é garantia **parcial**: round-trip em N amostras pega a maioria dos
     bugs, não 100% dos edge-cases.
- **Veredito**: começar pelo MVP gadget; header-marker e builder visual são fases separadas/opcionais.

## Fluxo end-to-end
1. **DEFINE** — usuário escreve um arquivo declarativo (`cep.yaml`): `name`, `template`,
   `body_length`, `check_length`, `check_algorithm` (nome da biblioteca), opcional
   `padding_slots`/`separator`/`canonical_form`. **Sem código Python.**
2. **COMPILA** — `python -m natures_compiler compile cep.yaml`:
   PARSE (`yaml.safe_load`, zero eval) → VALIDATE (campos; `count(N/D)` no template ==
   body+check; check_algorithm na biblioteca fechada; `sum(padding_slots)==body_length`;
   capacidade `base94^encoded_length >= 10^body_length`) → BUILD (regex + formatter **auto-gerados
   do template**; instancia o dataclass) → **ROUND-TRIP** (N amostras sintéticas; `encode→decode
   ==original` byte-canonical; **rejeita** se falhar, com erro amigável).
3. **REGISTRA** — emite o spec como `.json`/`.py` **fora de `src/tcf`** (output do gadget);
   registry em memória `register_spec(name, spec)` resolve lookup por nome. Core (CPF/CNPJ/IP)
   segue welded em `src/tcf/natures/`.
4. **USA (encode)** — API atual inalterada: `encode(col, nature=SPEC)` / `nature_per_col`.
   Conveniência: `nature_per_col={'col': 'cep'}` (lookup por nome). **Byte de saída idêntico** ao
   de um spec escrito à mão.
5. **USA (decode) HOJE** — **out-of-band**: o caller passa o mesmo spec. Sem ele, decode devolve
   o base-94 cru.
6. **[HEADER, 0.8]** — com H-NAT-MARK-01 o spec-id viaja na meta-line (`...| natures=col:cep`);
   `decode(text)` reconhece sozinho. **É format change `#TCF.7→#TCF.8`** (ADR + backward-compat).

## DSL — exemplo
```yaml
name: cpf
template: NNN.NNN.NNN-DD     # N=dígito do corpo, D=verificador, . - = literais
body_length: 9
check_length: 2
check_algorithm: mod11-cpf  # nome da biblioteca fechada — NUNCA código do usuário
encoded_length: 5           # auto: base94^5 >= 10^9
```
Gera regex + formatter + instancia `TemplatedCheckedSpec` idêntico ao de `templated_checked.py`.
- **CEP** (sem check, reusa `TemplatedPaddedSpec`): `template: NNNNN-NNN / padding_slots: [5,3] / separator: '-' / check_algorithm: none`.
- **Telefone-BR** (máscara variável): `mask_variants: ['(NN) NNNNN-NNNN', '+NN NN NNNNN-NNNN'] / check_algorithm: none`.
- **MAC / data-BR / EAN-13** (este com `check_algorithm: luhn`): idem, declarativos.

## É uma versão de formato?
| coisa | versão? |
|---|---|
| DSL + compilador + registry + builder | **NÃO** — byte de saída idêntico; zero breaking |
| spec-id viajar no header (decode auto) | **SIM** — `#TCF.8` (H-NAT-MARK-01, 0.8) |
| biblioteca de check-fns (`algorithms.py`) | toca `src/tcf/natures/` (encode/decode core a usa) → **precisa aprovação + weld** |

## Plano faseado
| fase | entrega | tier |
|---|---|---|
| **F1 — MVP gadget** | ✅ **FEITO 2026-06-16** — `scripts/natures_compiler/` (PARSE/VALIDATE/BUILD/round-trip + CLI). **Zero src/tcf** (reusa os check-fns do core importando-os; não precisou de `algorithms.py`). Provado por **regenerar CPF/CNPJ/IP do DSL == escritos à mão** (9 testes). **Achado**: CEP (zeros à esquerda) e MAC (hex) **não cabem** no `TemplatedPaddedSpec` → exigem spec novo em src/tcf (futuro). | pré-1.0 |
| **F1.5 — registry** | `SPEC_REGISTRY` + lookup por nome em `nature`/`nature_per_col`. API inalterada (aceita string). Sem versão. | pré-1.0 |
| **F2 — header (H-NAT-MARK-01)** | tag de nature na meta-line; decode auto; `#TCF.8` + ADR + backward-compat. **Só avançar se um filtro tiver ganho ≥15% weighted em 2+ datasets reais.** | 0.8 |
| **F3 — plugins drop-in (H-NAT-MARK-02)** | `natures/` auto-descoberto; namespace contra colisão. | 0.8 |
| **F4 — builder visual + composição** | form/wizard → YAML → preview (chama o **mesmo** compilador); specs compostos (datetime), auto-detecção via schema-builder. | 2.0/pesquisa |

## Riscos (e mitigação)
- **Lossless parcial** (round-trip em amostras ≠ 100%): permitir amostras reais no validate +
  cobrir bordas (min/max, zeros, longos); o fallback literal `_` já preserva RT do não-compressível.
- **Out-of-band até F2**: docs enfáticas + registry; resolve com header (0.8).
- **Over-eng da gramática**: começar com subset mínimo (sem composite/canonical_form); reusar
  Pydantic/JSON-schema na validação; regex liberal validado em runtime.
- **Ganho não caracterizado**: **gate ≥15% weighted em 2+ reais ANTES de weldar** qualquer filtro;
  manter opt-in até lá. (O DSL vale como infra/DX mesmo sem ganho de bytes.)
- **Colisão de spec-id**: registry rejeita duplicata, ou namespace `user:`/`core:`.
- **Acoplamento ao core**: só a biblioteca de check-fns toca `src/tcf` (arquivo pequeno, fechado,
  auditado 1x); o resto do compilador é 100% gadget.

## Recomendação
Começar pela **F1** (pré-1.0, barata): compilador CLI em `scripts/natures_compiler/` gerando
`TemplatedCheckedSpec`/`TemplatedPaddedSpec` a partir de YAML, com biblioteca fechada de check-fns
e **round-trip obrigatório**. Provar a arquitetura num spec **sem check (CEP)** que reusa
`TemplatedPaddedSpec` (caso mais simples). **Não tocar o formato**; **não** construir o builder
visual ainda. Subir pra F2 (header = versão 0.8) só quando existir filtro com ganho **caracterizado**.

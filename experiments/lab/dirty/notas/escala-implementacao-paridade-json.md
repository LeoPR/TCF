---
title: ESCALA DE IMPLEMENTAÇÃO — paridade com o fluxo JSON (do mais barato ao completo)
type: report
status: aberta
created: 2026-07-17
related:
  - experiments/lab/dirty/2026-07-17-0140-paridade-fluxo-json-vs-tcf/ (o critério, medido)
  - experiments/lab/dirty/notas/perfil-json-like-condicoes-parametro.md (as 5 condições de parâmetro)
  - experiments/lab/dirty/notas/json-chave-repetida-levantamento.md
  - experiments/lab/dirty/notas/p4b-levantamento.md (E5)
  - tickets/T-FMT-ESCAPE-COMBINATORIAL-STUDY.md (E6)
  - tickets/T-CODE-TCF8H-JSON-PARITY.md
  - tickets/T-API-BOUNDARY-CONTRACTS.md
---

# Escala de implementação — paridade com o fluxo JSON

**[probatório + recomendação]** Pedido do owner (2026-07-17): fixar o ROI implementando só o que o
JSON consegue fazer num ambiente JSON (`dataset→encode→json→transmite→recebe→json→decode→dataset`
vs o mesmo caminho com TCF); depois avaliar se vale ir além; e **uma escala do mais barato ao
completo, evitando o complexo demais**. Tudo em §1-§2 é medido.

## 1. O critério, executável (E0 — já feito)

```
∀D:   J-RT-TX(D)  ⟹  T-RT(D)
```
"se o caminho JSON faz round-trip **através da transmissão**, o caminho TCF tem de fazer também".

A etapa **TRANSMITE** (encode p/ bytes UTF-8) é o que torna o critério honesto: sem ela o lone
surrogate "passaria" (o escape `\uXXXX` do `ensure_ascii` o esconde) e mediríamos uma paridade que
não existe no fio.

**Placar medido** (lab `2026-07-17-0140`, 26 datasets + 7 raízes):

| veredito | n | significado |
|---|---:|---|
| **PARIDADE** | 14 | os dois caminhos fazem RT — já estamos lá |
| **LACUNA** | **3** | o json (I-JSON-conforme) faz e o TCF não → **é a superfície inteira de implementação** |
| **LACUNA de RAIZ** | **7** | eixo separado (P4b) |
| TCF-ESTRITO | 2 | `±Infinity`: o json só "passa" emitindo token **inválido por RFC 8259 §6** — não é lacuna |
| AMBOS-RECUSAM | 7 | NaN, tuple, chaves não-str, lone surrogate — **o json também falha** |

**A superfície é pequena**: 3 lacunas de dataset (chave `""` · `\n` em valor · chave com `\n`) +
1 decisão de raiz. Todo o resto já é paridade ou é o json fora da norma. Pinado em
`tests/test_json_flow_parity.py` (24 passed + 3 `xfail(strict)` — as lacunas **não fecham em
silêncio**: implementar uma faz o teste dar XPASS e obriga a promovê-la).

**Bônus medido — TCF ⊃ I-JSON num eixo**: inteiros acima de 2^53 fazem RT no TCF; o I-JSON os
proíbe (RFC 7493 §2.2, faixa segura IEEE 754). Capacidade extra que já temos de graça.

## 2. "É problema do Python ou do JSON?" — a pergunta do owner, medida

Provado por **compilação** (`rustc 1.82.0`, o alvo do 1.0):

| condição | Python | Rust | veredito |
|---|---|---|---|
| chave int + chave str no mesmo mapa (o que **fabrica** a duplicata) | `{1:'x','1':'y'}` é legal → `json.dumps` **emite duplicata**, RT perde calado | **erro de compilação** E0308 (`expected i32, found &str`) | **problema do Python** (tipagem dinâmica) — inexprimível em linguagem tipada |
| lone surrogate | `str` aceita; `dumps` escapa; a string não é UTF-8 | `"\u{D800}"` → **erro de compilação**; `char::from_u32(0xD800)` → `None`; `String::from_utf8([ED,A0,80])` → `Err` | **problema do Python** — inexprimível em Rust |
| NaN quebra identidade | `nan != nan` | `f64::NAN == f64::NAN` → `false` (o rustc **avisa**: "incorrect NaN comparison") | **problema do IEEE 754** — universal, não some em lugar nenhum |

→ **2 dos 5 "defeitos" desaparecem por construção no port Rust do 1.0.** A rigidez atual do TCF não
é parochialismo Python: é exatamente o que o sistema de tipos do Rust vai impor de graça. O que
sobra (NaN) é físico (IEEE 754) e só se resolve **representando** (categoria D), nunca tolerando.

## 3. A escala (dois eixos: custo × lacunas fechadas)

Ordenada por **ROI**. "Presa ao json" = níveis E0-E5 (só o que o JSON conforme faz);
E7 = além do json.

| # | item | custo | lacunas | toca wire? | gate | veredito |
|---|---|---|---:|---|---|---|
| **E0** | **critério executável** (parity suite + pinos) | ~0 | mede | não | — | ✅ **FEITO** |
| **E1** | **tipar os 3 erros crus** (`\n` valor → `ValueError` cru; chave int/bool → `TypeError` cru; surrogate → `UnicodeEncodeError` cru) | **baixo** | 0 | **não** (só mensagem) | suíte | **fazer** — puro ganho, sem risco |
| **E2** | **chave vazia `""`** | baixo-médio | **1** | sim (aditivo no meta) | RT + non-reg + adversarial | **fazer** — JSON válido e comum; ver §4 |
| **E3** | **canal SideOutputs no `.8H`** | médio | 0 | **não** (aditivo) | suíte | **fazer** — destrava o *warning* que o owner quer + profiler + schema-tool |
| **E4** | **chave contendo `\n`** | médio | **1** | sim (escape do meta) | RT + adversarial | avaliar — cruza com o estudo do escape |
| **E5** | **raiz generalizada (P4b)** | médio-alto | **7** | sim (discriminador) | contrato + RT das 8 formas | **maior ROI em lacunas** — 7 de uma vez; 5 decisões suas já levantadas |
| **E6** | **`\n` em valor** | **ALTO** | **1** | **sim, no L1** | byte-canônico D1-D9 + real-world | **SEGURAR** — ver §5 |
| **E7** | **além do json** (NaN/Inf tipados, chave não-str tipada) | alto | 0 (superset) | sim (versão) | formato | **estudar depois** |

### Ordem recomendada
**E1 → E3 → E2 → E5** (fecha 8 das 10 lacunas) → reavaliar **E4**; **E6/E7 ficam para estudo**.

E3 antes de E2 porque destrava a observabilidade (SideOutputs) que os próximos usam — e porque é
o pré-requisito do *warning* que você pediu.

## 4. Por que E2 (`chave ""`) não é trivial (e mesmo assim é barato)

Hoje **"nome de campo vazio" é o sentinela de corrupção** do meta (a auditoria P4a o usa para
detectar blob adulterado). Aceitar `""` como nome legítimo exige distinguir *nome vazio válido* de
*ausência de nome* — isto é, um escape/marcador próprio. Bounded (só o meta do `.8H`, não toca o
L1), mas **precisa de estudo-primeiro**: é grama nova, e a lição do escape (`40a7e10`) diz para
testar nome/valor/borda antes de soldar.

## 5. Por que E6 (`\n` em valor) é o "complexo demais" — e o que fazer

O corpo do TCF é **delimitado por LF**: um `\n` dentro de um valor não é um problema do `.8H`, é do
**L1** (`src/tcf/encoder.py`, o núcleo que comprime toda coluna). Fechar isso significa:
escape/quoting no corpo → **muda o byte-canônico de tudo** (D1-D9=1523 B, D17a=300 B,
real-world=89616 B) → re-pinar todos os baselines, rodar o gate real-world, e passar pelo
`T-FMT-ESCAPE-COMBINATORIAL-STUDY` (que você já abriu justamente porque "o escape me incomoda").

É a lacuna mais **cara** e a mais **comum na vida real** (strings multilinha em JSON são triviais).
Recomendação: **segurar** — mas registrar que ela é a única lacuna de nível-1 (I-JSON) que fica
aberta, para não vendermos "paridade JSON" sem asterisco. Quando o estudo do escape rodar, ela
entra junto (mesmo ato, mesmo gate).

## 6. Fronteira honesta (o que NÃO prometer)

Com E1+E2+E3+E5 feitos, a frase correta é: **"paridade com o fluxo JSON, exceto `\n` em valor
(escape, em estudo) e `\n` em nome de chave"** — não "qualquer JSON". P5 (union/tipo-misto) segue
fora. E o que o TCF recusa (NaN/Inf/tuple/chave não-str/surrogate) **não é lacuna**: é o json
saindo da norma ou do próprio modelo — 2 desses casos nem existem em Rust.

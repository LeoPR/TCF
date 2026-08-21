# 2026-08-21-0230 — um `cnpj` só, e o relatório sobre o compacto numérico

Evidência do [ADR-0044](../../../../../../docs/adr/0044-cnpj-um-so-alfanumerico.md).
Duas tarefas: **provar a unificação** e **responder** o que o owner pediu para eu avisar.

> *"a ideia é ter só 'cnpj' mesmo, ou seja nada de ter dois. [...] agora o alfa é padrão, e o
> só numérico pode até ser oportunidade, mas acho que ela será transitória [...] O ideal é ter
> um algoritmo só pro cnpj novo, e só se tiver uma real vantagem e fácil implementação [...]
> aí vc avisa."*

## O relatório: o compacto **fica** — mas não pelo motivo que eu esperava

### Q1 — Não há versão numérica melhor a achar

| domínio do corpo | tamanho | mínimo em base-80 |
|---|---:|---:|
| numérico `10¹²` | 1,00×10¹² | **7** (80⁶ = 2,62×10¹¹ não cabe) |
| alfanumérico `36¹²` | 4,74×10¹⁸ | **10** (80⁹ = 1,34×10¹⁷ não cabe) |

Os dois são **mínimos**. E o dígito verificador **nunca foi gravado** (`check_length=2` é
recomputado no decode) — a redundância de 100% já estava eliminada desde sempre. Não sobra
folga para uma "versão numérica melhor".

### Q2 — Você estava certo: o ganho **é** transitório. Mas o custo é zero.

| fração numérica | com compacto | sem compacto | ganho | larguras emitidas |
|---:|---:|---:|---:|---|
| 1,00 | 17 585 | 24 292 | **+27,61%** | `[7]` |
| 0,90 | 18 266 | 24 303 | +24,84% | `[7, 10]` |
| 0,50 | 20 958 | 24 367 | +13,99% | `[7, 10]` |
| 0,10 | 23 860 | 24 530 | +2,73% | `[7, 10]` |
| 0,00 | 24 454 | 24 455 | **+0,00%** | `[10]` |

Decai a zero exatamente como você previu. **Mas nunca fica negativo** — 0 de 9 frações. A
hipótese de que a largura mista (7 e 10 na mesma coluna) atrapalharia a compressão a jusante
**não se confirma**. Manter o compacto custa zero em qualquer mistura futura.

### Q3 — E o motivo que decide: ele é **load-bearing**, não otimização

```
payload histórico '!)x+z:$' (7 chars)
  com compacto → '01.941.860/0001-92'   OK
  sem compacto → '!)x+z:$'              NÃO LÊ — devolve o payload CRU como valor
```

Sem o caso compacto, um `:cnpj` alfanumérico **não lê o wire de 7 chars já emitido**. E não
falha alto: devolve valor errado. **Corrupção silenciosa** — a classe que este projeto trata
como inaceitável.

**Isso muda a natureza da resposta.** O compacto não fica porque comprime melhor hoje; fica
porque é **o mecanismo que torna "um `cnpj` só" possível**. A compressão (+27,6% → 0%) é o
bônus que decai. Sem ele, a unificação que você pediu quebraria o legado.

### Q4 — Neutralidade provada contra os parâmetros **históricos**

[`diferencial.py`](diferencial.py): reconstrói o `SPEC_CNPJ` de antes (regex numérica,
`encoded_length=7`, formatter decimal) e compara com o unificado no domínio numérico —
**4 011 encodes + 3 505 decodes (3 000 adulterados) = 0 divergências**. CPF intocado: 2 000
valores, 0 divergências.

E o **censo de status** ([`censo_status.py`](censo_status.py)), porque fora do domínio numérico
o rótulo muda — e minha primeira redação não qualificava isso. Corpus de 10 008 valores,
cobrindo de propósito as formas alfanuméricas: **3 classes, todas partindo de
`format_mismatch`** (o catch-all que o spec histórico dava a qualquer valor com letra) —
→ `compressible` (3 017, **única que muda byte, e é a capacidade nova**), → `format_unmasked`
(2 002) e → `check_invalid` (1 984), estas duas byte-idênticas porque ambas caem em literal.
**Nenhum valor numérico diverge.** Roundtrip: 10 008/10 008.

> **O primeiro diferencial que rodei estava errado.** Ele lia `spec.encoded_length` do spec
> *vivo* (já 10) para simular o pré-weld — comparava "algoritmo antigo com parâmetro novo" e
> acusou divergências que eram artefato do próprio script. Um diferencial só vale se os
> parâmetros históricos forem pinados, não lidos do presente.

## Revisão adversarial pós-weld — 25 achados brutos, e o que sobreviveu

O workflow de verificação **morreu no limite de gasto mensal da conta** (24 de 28 agentes
falharam), então os 3 finders rodaram e eu verifiquei os 25 achados **à mão**. O saldo:

**Consertados (regressões minhas, todas reais):**

1. **[alta] Meu recorte apagou 6 testes que deviam sobreviver** — incluindo
   `test_contrato_do_compacto_falha_alto`, que continha as **7 guardas que a revisão do
   ADR-0043 tinha me feito escrever**, e `test_digito_unicode_...`, cujo próprio docstring
   dizia "pinada de propósito". Fatiei de um marcador ao outro sem conferir o que havia no
   meio. Restaurados e apontando para o spec único.
2. **[alta] O rename mecânico `SPEC_CNPJ_ALFA → SPEC_CNPJ` criou tautologias**:
   `assert SPEC_CNPJ.check_fn is SPEC_CNPJ.check_fn` (sempre verdadeiro) e a mesma asserção
   duplicada. Reescrito para afirmar o que importa — que o DV pelo mapeamento novo (ASCII−48)
   bate com o antigo (`int(dígito)`) em todo o domínio numérico.
3. **[média] Guarda que faltava**: `alfabeto_compacto=None` com `encoded_length_compacto=7`
   construía — estado inconsistente esperando alguém confiar nele. Agora falha alto.
4. **[média] Docs**: `api.md` duplicou `SPEC_INT_PAD` no lugar do símbolo removido; dois
   docstrings do core ainda citavam `SPEC_CNPJ_ALFA`; `MAP.md` tinha 2 linhas obsoletas
   afirmando o desenho de dois specs; a linha do `H-15-02` no roadmap ficou com colunas
   trocadas.
5. **[média] Minha afirmação de "0 divergências, inclusive de status" era larga demais** —
   medida num corpus numérico. O censo (§ acima) é a correção.

**Achados reais que NÃO consertei, por decisão:**

- **[alta] `$` nas regex casa antes de quebra de linha final** — um valor terminado em LF
  classifica como `compressible`, o LF é descartado pelo filtro de símbolos, e o RT **perde o
  caractere**. É **pré-existente** (CPF, IP e data-iso têm o mesmo; não veio deste arco) e
  **inalcançável pela API pública** (`tcf.encode` recusa valor com LF em fail-loud, antes da
  nature), mas alcançável por `tcf.natures.encode_value`, que é público.
  Conserto candidato: `$` → `\Z` nas 4 regex. **Toca 4 specs → precisa de aprovação.**
  Registrado como **H-15-07**.
- **[baixa] Incompatibilidade para a frente**: decoder pré-weld lendo wire novo de 10 chars
  devolve o payload cru em silêncio. É o preço de reusar o id, e está declarado no ADR-0044.

**Refutados por execução:** o `registry.get('cnpj')` da DSL resolve para o core (sem
ambiguidade); o overflow do formatter produz o mesmo formato de garbage do pré-weld (só com
payload adulterado); os arquivos de debris no root eram dos próprios agentes e já sumiram.

## O que mudou no código

`SPEC_CNPJ` **é** o alfanumérico (`[0-9A-Z]`, `wire_id="cnpj"`, pleno 10 / compacto 7).
Deixaram de existir: `SPEC_CNPJ_ALFA`, o `wire_id` `cnpja`, e o helper `cnpj_spec_para` — não
há mais escolha a fazer. O registry voltou a **5 specs**.

## Não medido (declarado)

- **A DSL (`scripts/natures_compiler/`) não expressa alfabeto** — só compila o subconjunto
  numérico. O teste de equivalência foi re-pinado para afirmar o que importa (byte a byte no
  domínio numérico) e documentar a limitação. É acessório, não core.
- Volume futuro (H-15-03) e corpus real alfanumérico (H-15-04) seguem abertos.
- Minúscula (H-15-06) segue fora, aguardando `T-FMT-CONTRACT-SIGNATURE`.

## Evidência

30 arquivos em [`inputs/`](inputs/)+[`outputs/`](outputs/), wires com roundtrip, portão
anti-órfão. [`resultado.json`](resultado.json) com Q1–Q4. Asserts duros no `run.py`
(`ganho >= 0` em toda fração; mínimos batem com o spec; o "sem compacto" tem de falhar).

## Conexões

- [ADR-0044](../../../../../../docs/adr/0044-cnpj-um-so-alfanumerico.md) — supersede
  [0042](../../../../../../docs/adr/0042-cnpj-alfanumerico-dois-specs.md) e
  [0043](../../../../../../docs/adr/0043-cnpj-um-so-compacto-por-valor.md)
- Arco: [`2350`](../../2026-08-20/2026-08-20-2350-cnpj-alfanumerico/) ·
  [`0030`](../2026-08-21-0030-cnpj-alfa-controle/) · [`0130`](../2026-08-21-0130-cnpj-um-so-compacto/)

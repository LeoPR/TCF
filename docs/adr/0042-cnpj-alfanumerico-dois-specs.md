# ADR-0042 — CNPJ alfanumérico: dois specs que coexistem, não um que substitui

- **Status**: **aceito — weld H-15-01/02 SOLDADO** (2026-08-21, aprovação "go então").
  Suíte 1285 → **1301**; gates byte-canonical intactos (D17a=300, D1–D9, real-world).
- **Escopo**: `TemplatedCheckedSpec` (alfabeto parametrizável), `SPEC_CNPJ_ALFA` novo,
  registry core nos dois planos, e o helper de escolha `cnpj_spec_para`.
- **Interage com**: ADR-0015 (natures) · ADR-0027 (self-describing no header) ·
  ADR-0041 (spec em dois planos: `name` × `wire_id`) · ADR-0024 (pré-1.0) ·
  ADR-0002 (vértice tríplice) · `T-PENHASCO-INICIO` (a classe do achado do split)
- **Origem**: fato **externo com prazo já vencido** — IN RFB nº 2.229/2024.

---

## Contexto

A **Instrução Normativa RFB nº 2.229/2024** está **vigente desde julho de 2026** (primeira
inscrição alfanumérica em 31/07/2026). As **12 primeiras posições** do CNPJ passam a aceitar
`[0-9A-Z]`; os **2 dígitos verificadores continuam decimais**. Os CNPJ existentes **não
mudam**.

O DV segue **módulo 11 com os mesmos pesos**. Muda só a conversão de caractere para valor:

```
valor = ASCII(c) − 48      '0'→0 … '9'→9   ·   'A'→17 … 'Z'→42
```

Como `'0'` é ASCII 48, **dígito converte para ele mesmo** — a regra nova é *idêntica* à
antiga no domínio numérico. A retrocompatibilidade é **estrutural, não coincidência**
(verificado: 2 000 CNPJ reais da Receita validam sob a regra nova, 0 divergências).

### O que estava quebrado (medido, não suposto)

O `_cnpj_check_fn` já calculava certo — o exemplo publicado `12.ABC.345/01DE-35` fecha com
os pesos que já estavam em `src/tcf`. O que não aceitava letra era a **regex** e os **3
métodos** que assumiam dígito.

E o dano não era na nature, era no **`split`** (lab `2026-08-20-2350`):

| coluna real, n=2000 | bytes | vs raw | mecanismo |
|---|---:|---:|---|
| CNPJ numérico | 23 436 | −38,32% | `%` split |
| alfanumérico realista | 35 064 | −7,72% | core |
| alfanumérico uniforme | 38 012 | **+0,03%** | raw (maior que o texto cru) |

O gate do split segmenta por **dígito × não-dígito**; a letra no corpo cai dentro do que ele
trata como separador. E o controle (lab `2026-08-21-0030`) mostrou que **o split morre em
k=1** — UM valor novo derruba a coluna inteira de −38% para raw. É a classe do
`T-PENHASCO-INICIO`: decisão de pré-passe cria penhasco. **Não é problema "do futuro com
muitos" — é do primeiro.**

## Decisão

### 1. O alfabeto vira parâmetro do spec; a LEI continua sendo ASCII−48

`TemplatedCheckedSpec` ganha `alfabeto: str = "0123456789"`. **Dois mapeamentos convivem e
não se confundem:**

- **LEGAL** — `_valor(c) = ord(c) − 48`, o que o `check_fn` consome. É a IN. Universal:
  para dígito devolve o próprio dígito, para letra devolve a regra nova.
- **DENSO** — o índice no `alfabeto`, base da **gravação**.

### 2. Base 36, não 43

O mapeamento legal tem um **gap** (10–16 = `:;<=>?@`, não são símbolos válidos). Usá-lo como
base gastaria `43¹² = 4,00×10¹⁹ > 80¹⁰` → **11 chars**. O alfabeto denso `0-9A-Z` dá
`36¹² = 4,74×10¹⁸ ≤ 80¹⁰ = 1,07×10¹⁹` → **10 chars**. **1 char por valor** de diferença.

### 3. DOIS specs, e o numérico fica INTOCADO

| spec | `wire_id` | corpo | chars |
|---|---|---|---:|
| `SPEC_CNPJ` (existente, **inalterado**) | `cnpj` | base 10 | **7** |
| `SPEC_CNPJ_ALFA` (novo) | `cnpja` | base 36 | **10** |

**Por que não um só spec alfanumérico**: medido, uma coluna 100% numérica sob o spec
sempre-alfa paga **+38,1%**. Os CNPJ numéricos continuam válidos e sendo emitidos — a IN não
os altera. Taxar todo o legado para acomodar o novo seria a troca errada, e re-pinaria
baselines sem ganho.

### 4. A escolha é do chamador; o helper é first-order e declara seu resíduo

`cnpj_spec_para(vals)` escolhe por **soma de payload** em uma passada. **A regra ingênua
"tem letra → alfa" está errada e foi medida**: erra em 8 de 12 pontos, porque o spec
numérico segue ganhando (pagando literal pelos poucos alfa) até ~1/4 da coluna. A virada tem
forma fechada — `k/n = (E₂−E₁)/(1+L−E₁) = 3/12 = 1/4`.

**Resíduo declarado** (3 sementes × 17 frações × n=2 000, CNPJ real): **41/51 corretos**. Os
10 erros são **sistemáticos**, todos na faixa **22–25%** de alfanuméricos e todos na mesma
direção; pior custo medido **3,15%**; fora da faixa, zero. Quem precisa de exatidão paga dois
encodes — está no docstring.

`encode(col, nature=<spec>)` **nunca** é sobrescrito calado: nada de substituir a declaração
do chamador (o buraco que a ADR-0041 fechou como "mascarada").

## Consequências

**Byte-neutro no legado — provado por diferencial**, não deduzido: os 3 métodos pré-weld
foram reimplantados e comparados contra os novos em **8 036 encodes** e **5 010 decodes**
(dos quais **4 000 payloads adulterados**, incluindo os que estouram a capacidade do corpo):
**0 divergências de byte**.

**Uma única mudança de comportamento**, pinada em teste: `classify_value` trocou
`v.isdigit()` por "todo char no alfabeto". Um valor de **dígitos unicode** (árabico-índicos,
que passam no `isdigit()`) era rotulado `format_unmasked` e agora é `format_mismatch`. **Os
bytes são idênticos** (os dois caem em literal); muda só a telemetria, e o rótulo novo é o
mais fiel.

**O registry cresceu** — vocabulário fechado, nos dois planos: `cnpj-alfa`/`cnpja`. Os testes
que pinam o registry foram re-pinados **de propósito**, para que crescer siga sendo decisão e
não acidente.

**O que este ADR NÃO resolve** (declarado):

- **O `split` continua morrendo em k=1.** Este weld dá a rota da *nature*, que é plana em k;
  não conserta o gate. A decomposição **posicional** (medida: recupera −37,7% no alfanumérico
  e **bate o split até no numérico real, −45,3% contra −38,3%**) é a direção do **grupo** e
  fica para o desenho próprio.
- **Corpus real alfanumérico não existe** (1ª inscrição 31/07/2026). O sintético é *controle*,
  não amostra. A emissão real pode ser mais restrita que o formato (estratégia Serpro tende a
  consoantes; fontes secundárias citam exclusão de `I,O,U,Q,F` — **não confirmado na IN**). O
  spec valida o **formato** `[0-9A-Z]`; emissão restrita só encolhe o subespaço ocupado.
- **CPF não muda** — nada na IN o afeta.

## Alternativas rejeitadas

- **Substituir `SPEC_CNPJ` pelo alfanumérico** — +38,1% em todo o legado, e re-pin de
  baselines sem ganho.
- **ASCII−48 como base da gravação** — 11 chars em vez de 10, por causa do gap.
- **Chooser "tem letra → alfa"** — medido errado em 8 de 12 pontos.
- **Chooser automático dentro do `encode`** — sobrescreveria calado a declaração do chamador.

## Evidência

- Descoberta: [`2026-08-20-2350-cnpj-alfanumerico`](../../experiments/lab/dirty/2026-08/2026-08-20/2026-08-20-2350-cnpj-alfanumerico/)
- Controle: [`2026-08-21-0030-cnpj-alfa-controle`](../../experiments/lab/dirty/2026-08/2026-08-21/2026-08-21-0030-cnpj-alfa-controle/)
- Registro de hipóteses: Pacote 15 (H-15-01..05) em `notas/2026-05/roadmap-hipoteses.md`

**Fontes**: [Receita — CNPJ alfanumérico](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/cnpj-alfanumerico) ·
[Nota Técnica Conjunta 2025.001](https://www.nfe.fazenda.gov.br/PORTal/exibirArquivo.aspx?conteudo=5ZkvIZt10mQ%3D) ·
[Serpro — cálculo do DV](https://www.serpro.gov.br/menu/noticias/videos/calculodvcnpjalfanaumerico.pdf)

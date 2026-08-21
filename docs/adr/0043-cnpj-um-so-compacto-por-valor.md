# ADR-0043 — Um CNPJ só: o numérico vira caso compacto POR VALOR, e o chooser deixa de existir

- **Status**: **aceito — SOLDADO** (2026-08-21, mesma sessão do ADR-0042, por direção
  explícita do owner). Suíte **1306**; gates byte-canonical intactos; diferencial de
  neutralidade re-executado (0 divergências).
- **Refina**: [ADR-0042](0042-cnpj-alfanumerico-dois-specs.md) — mantém as decisões 1–3
  (alfabeto parametrizável, base 36 densa, `SPEC_CNPJ` intocado) e **substitui a decisão 4**
  (o chooser por soma de payload, com seu resíduo de 3,15%).
- **Escopo**: `TemplatedCheckedSpec` (sub-alfabeto compacto opcional), `SPEC_CNPJ_ALFA`
  (ganha o caso compacto), `cnpj_spec_para` (simplificado a quase-trivial).
- **Origem**: direção do owner (2026-08-21), verbatim no Contexto.

---

## Contexto

O ADR-0042 desenhou **dois specs + chooser**: `cnpj` (7 chars) para colunas numéricas,
`cnpja` (10 chars, fixo) para as demais — e o chooser carregava um resíduo sistemático
declarado (41/51, erros na faixa 22–25% de alfanuméricos, pior 3,15%).

O owner derrubou a premissa temporal desse desenho:

> *"o CNPJ numérico ultimamente será apenas pra legado agora [...] em parte é certo dizer que
> ele é estatisticamente pequeno AGORA, mas ele não é estatisticamente pequeno em uma
> distribuição real no tempo, pois no futuro ele se diluirá [...] precisamos firmar um CNPJ
> só, que será alfa e terá que cobrir o numérico [...] o só numérico pode ser um caso
> particular conveniente pra agora mas [...] pode ser que a gente não consiga fazer uma
> heurística que sustente isso por muito tempo [...] se aparecer alguma oportunidade de
> expressá-lo menor (por ser numérico) me parece uma boa ideia."*

O argumento em número: o domínio numérico é `10¹²/36¹² ≈ 2,1×10⁻⁷` do espaço alfanumérico.
Hoje é 100% do cadastro; a partir de jul/2026 só dilui. **Qualquer chooser por coluna
calibrado na fração numérico/alfa tem prazo de validade** — e o resíduo do ADR-0042 já era o
sintoma disso.

## Decisão

### 1. Sub-alfabeto compacto POR VALOR (mecanismo genérico do `TemplatedCheckedSpec`)

Campos novos, opcionais: `alfabeto_compacto: str | None` e `encoded_length_compacto: int`.
Corpo cujos símbolos caibam todos no sub-alfabeto grava em `encoded_length_compacto` chars
(base menor); senão, no alfabeto pleno. **O decode distingue pelo COMPRIMENTO do payload** —
por isso o contrato exige comprimentos distintos (fail-loud no `__post_init__`, junto com
subconjunto-próprio e capacidade).

### 2. No `SPEC_CNPJ_ALFA`: numérico → 7, alfanumérico → 10

```
corpo 100% decimal  → base 10, 7 chars   (10¹²  ≤ 80⁷  = 2,10×10¹³)
corpo com letra     → base 36, 10 chars  (36¹² ≤ 80¹⁰ = 1,07×10¹⁹)
```

E o payload compacto é **byte-idêntico ao do `SPEC_CNPJ`** por construção — os índices do
sub-alfabeto `0..9` **são** os dígitos, o inteiro é o mesmo, a grafia base-80 é a mesma.
Verificado valor a valor em 2 000 CNPJ reais: **2 000/2 000 idênticos**.

**Canonicidade**: corpo decimal SEMPRE sai compacto (determinístico, por valor — o mesmo
valor nunca tem duas grafias emitidas). O corpo numérico gravado em 10 chars decodifica
(decode tolerante, "emissível não-canônico", espelho do modo C) mas nunca é emitido;
baseline nunca pina não-canônico.

### 3. O chooser vira quase-trivial, e o resíduo DESAPARECE

Com o compacto, o payload do unificado é **≤ o do legado em todo valor** (7 = 7 no numérico;
10 < 1+18 do literal no alfanumérico). Só resta decidir o **empate** (coluna 100% numérica):
fica com `SPEC_CNPJ`, cujo header é 1 B menor e é byte-compat com todo wire já emitido.
`cnpj_spec_para` reduz a: "algum valor alfanumérico compressível → `SPEC_CNPJ_ALFA`; senão
`SPEC_CNPJ`".

**Medido na MESMA varredura que reprovou o anterior** (3 sementes × 17 frações × n=2 000
reais): **51/51 contra a verdade** (era 41/51 com resíduo até 3,15%). E a dominação:

| k alfanuméricos em 2000 | legado | unificado | fixo ADR-0042 |
|---:|---:|---:|---:|
| 0 | 17 585 | 17 586 (**+1 B**, só o header) | 24 292 |
| 1 | 17 598 | **17 589** | 24 292 |
| 500 | 25 007 | **19 277** | ~24 320 |
| 2000 | 38 009 | **24 489** | 24 542 |

Pior caso do unificado: **+1 byte**. Ganho sobre o desenho fixo em coluna numérica: **−27,6%**.

### 4. O universo combinatório, confirmado na fonte

**`[0-9A-Z]` — 36 símbolos, todas as 26 letras MAIÚSCULAS, sem exclusões no formato.** A NT
Conjunta 2025.001/XSD (NF-e) valida `[0-9A-Z]{12}[0-9]{2}`. A exclusão de `I,O,U,Q,F` que
circula em fontes secundárias é (se existir) estratégia de **emissão**, não de formato — e
emissão mais restrita só encolhe o subespaço ocupado.

### 5. Minúscula: fica FORA do spec — é classe CONTRATO (H-15-06)

Minúscula **não pertence ao domínio oficial** (maiúscula-only); é variante de
**representação**, e o owner tem razão de que, *como identificador*, caixa é irrelevante.
Mas aceitar minúscula canonizando a saída (`12.abc…` entra, `12.ABC…` sai) **perde o RT
byte-canonical** — a constituição do formato. É exatamente a classe CONTRATO do
`sort_by`/`drop_names`: lossless como identificador, não como string; exige declaração
load-bearing e fail-loud nas pontas.

**Medido o que o contrato compraria**: coluna 100% minúscula hoje = literal (+0,03% vs raw,
byte-RT intacto); sob case-fold = **−35,55%**. Registrado como **H-15-06**, aguardando a
assinatura de contrato (`T-FMT-CONTRACT-SIGNATURE`, 5 perguntas abertas com o owner).
Até lá: minúscula cai em literal — não ganha, nunca corrompe.

## Consequências

- **Nenhum wire pinado muda**: `SPEC_CNPJ` segue byte-intocado (diferencial re-executado:
  8 036 encodes + 5 010 decodes, 0 divergências) e nenhum baseline usa `:cnpja`.
- **`:cnpja` muda de forma nesta mesma sessão** (numérico 10→7). Pré-1.0 (ADR-0024) e o id
  nasceu ontem; nenhum artefato canônico o pina. Os wires dos labs 0030 ficam como registro
  histórico do desenho fixo.
- Dois testes do ADR-0042 foram **re-pinados de propósito** (extremos numéricos agora 7;
  um alfa em 200 numéricos agora vira `cnpja` — e o teste documenta por que o contrário
  era verdade no desenho fixo).
- O mecanismo é **genérico** (qualquer spec com sub-domínio denso pode usá-lo), mas só o
  CNPJ o instancia — sem especulação.

## Alternativas rejeitadas

- **Manter dois specs + chooser** (ADR-0042 §4) — o chooser tinha resíduo sistemático e
  prazo de validade temporal; a escolha em si era o defeito.
- **Só o spec alfa fixo** — taxa o legado em +38,1% enquanto ele for maioria.
- **Prefixo/flag no payload** em vez de comprimento — gastaria 1 char a mais por valor;
  o comprimento já discrimina de graça.
- **Case-fold dentro do spec** — perde byte-RT calado; vai para a classe CONTRATO.

## Evidência

Lab [`2026-08-21-0130-cnpj-um-so-compacto`](../../experiments/lab/dirty/2026-08/2026-08-21/2026-08-21-0130-cnpj-um-so-compacto/)
— G1 paridade 2000/2000 · G2 dominação (asserts duros) · G3 chooser 51/51 · G4 minúscula
medida. Arco completo: labs `2350` (descoberta) e `0030` (controle).

**Fontes**: [NT 2026.004 / NT Conjunta 2025.001 (NF-e)](http://www.nfe.fazenda.gov.br/POrtal/exibirArquivo.aspx?conteudo=2%2FTP%2FAP+Pb4%3D) ·
[Receita — CNPJ alfanumérico](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/cnpj-alfanumerico) ·
[regex de validação `^[0-9A-Z]{12}[0-9]{2}$`](https://ramosdainformatica.com.br/cnpj-alfanumerico-implementacao/)

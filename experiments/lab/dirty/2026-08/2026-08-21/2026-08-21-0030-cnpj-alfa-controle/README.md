# 2026-08-21-0030 — CNPJ alfanumérico: o sintético de controle que decide o desenho

Pedido do owner: *"no momento precisamos de um dataset sintético de controle só pra ver os
comportamentos pra poder tratar isso agora"*. Este lab responde as três perguntas feitas —
até onde as letras atendem, como afeta os cálculos/base, e se letra vira número — e mede o
comportamento de **transição** que decide o tratamento. `src/tcf` **intocado**.

## O padrão do CNPJ (pesquisado) — regionalização e regras exploráveis

**O CNPJ NÃO é regionalizado.** Quem é regionalizado é o **CPF** (o 9º dígito é a região
fiscal da Receita — 10 regiões, 0–9). A raiz do CNPJ é atribuição **sequencial nacional**,
sem código de UF/região embutido. O que o número carrega de estrutura explorável:

| segmento | posições | estrutura real |
|---|---|---|
| **raiz** | 8 | identidade da empresa; alocação sequencial → empresas antigas têm raízes baixas (clustering temporal, não regional) |
| **ordem** | 4 | `0001` = matriz (dominante no cadastro); filiais sequenciais `0002`… |
| **DV** | 2 | **100% redundante** — dedutível do corpo (o critério de redundância, não de byte) |

**Alfanumérico (IN RFB nº 2.229/2024, vigente; 1ª inscrição 31/07/2026)**: as 12 primeiras
posições passam a aceitar `[0-9A-Z]`; os 2 DV **seguem numéricos**. Distinção que importa:

- **VALIDAÇÃO (formato)**: `[0-9A-Z]` — é o que a regra do DV cobre. É o que o spec valida.
- **EMISSÃO (estratégia)**: o Serpro divulgou estratégia tendendo a **consoantes** (~1 trilhão
  de combinações na raiz); fontes secundárias citam exclusão de `I,O,U,Q,F` — **não confirmado
  na IN**. Emissão mais restrita só encolhe o subespaço ocupado (ajuda dict/afixo); nunca
  invalida um valor que a regra do DV aceita. O spec valida o formato, não a estratégia.

## A) "Letra será tratada como número de qualquer forma, não?" — **SIM, duas vezes, por dois mapeamentos**

1. **No DV (o LEGAL, da IN)**: `valor = ASCII(c) − 48` → `'0'..'9'`→0..9, **gap 10–16**
   (`:;<=>?@`, não usados), `'A'..'Z'`→17..42. Mesmos pesos, mesmo módulo 11 — o
   `_cnpj_check_fn` de `src/tcf` **já calcula certo** (exemplo publicado `12.ABC.345/01DE-35`
   confere; extremos `ZZZZZZZZZZZZ`→DV 62, soma máxima 2436, sempre 2 dígitos).
2. **Na gravação (o DENSO, nosso)**: índice `0–35` para a conversão de base.

**E a diferença entre os dois mapeamentos custa 1 char/valor** — a resposta a "muda a
conversão da base":

| domínio do corpo | tamanho | chars base-80 |
|---|---:|---:|
| numérico (hoje) | 10¹² | **7** |
| alfanumérico, base **densa** 0–35 | 36¹² ≈ 4,74×10¹⁸ | **10** |
| alfanumérico, ASCII−48 **como base** (43) | 43¹² ≈ 4,00×10¹⁹ | **11** |

Usar o mapeamento legal como base desperdiçaria o gap: o corpo pagaria 11 em vez de 10
(~5,5% do valor). **Legal → só DV; denso → só base.**

## C) A máquina real RODA o spec alfanumérico — sem tocar `src/tcf`

Subclasse de lab (`AlfaTemplatedCheckedSpec`) re-generalizando **exatamente os 3 métodos**
que hoje assumem `\d` — este é o mapa do weld:

```
classify_value  →  v.isdigit() / c.isdigit() / int(d)
encode_value    →  int(digits_str[:body])            (base 10 implícita)
decode_value    →  str(n).zfill(body) + formatter(list[int] 0-9)
```

`check_fn`/pesos **intactos**. A porta já existe: `encode(col, nature=spec)` +
`decode(w, nature=spec)` out-of-band; o gate de emissão (ADR-0041) aceitou `wire_id="cnpja"`
(gramática ok, sem mascarada — não está no registry core). E o **fail-loud funciona**:
`decode(w)` sem o spec → `ValueError: nature-id desconhecido... forneça o spec out-of-band`.

| caso (n=2000, RT ✓) | bytes | vs raw | header |
|---|---:|---:|---|
| alfa puro, spec alfa | 24 474 | **−35,59%** | `#TCF.8 :cnpja` |
| misto 50/50, spec alfa | 24 382 | −35,84% | `#TCF.8 :cnpja` |
| numérico real, spec alfa | 24 292 | −36,07% | `#TCF.8 :cnpja` |
| **numérico real, spec de HOJE** | **17 585** | **−53,72%** | `#TCF.8 :cnpj` |

**Coexistência**: a mesma coluna numérica custa **+38,1%** sob um spec sempre-alfa. Um id
único taxaria todo o legado (que segue sendo emitido — CNPJs existentes não mudam). Desenho:
**dois `wire_id`** — `cnpj` (7, intocado, byte-compat com wires existentes) e `cnpja` (10,
aceita ambos) — com escolha por coluna no encode (tem letra → `cnpja`; senão `cnpj`).

> Precisão sobre ontem: "a nature não dispara em real" valia para a rota **sem spec** (o
> `.8M` default escolhe split). **Com** o spec fornecido, a nature numérica é o melhor
> mecanismo da coluna real: −53,7% contra −38,3% do split.

## D) A TRANSIÇÃO — o comportamento que decide (base real n=2000 + k alfanuméricos)

| k | `.8M` (default) | mecanismo | nature-alfa | posicional |
|---:|---:|---|---:|---:|
| 0 | 23 436 | **split** | 24 292 | 20 799 |
| **1** | **38 012** | **raw** | 24 292 | 20 845 |
| 3 | 38 012 | raw | 24 293 | 20 956 |
| 20 | 38 012 | raw | 24 296 | 21 724 |
| 200 | 38 012 | raw | 24 291 | 28 325 |
| 1000 | 38 012 | raw | 24 455 | 29 271 |
| 2000 | 38 012 | raw | 24 542 | 29 268 |

(raw ≈ 37 999 B)

1. **O split morre em k=1.** UM CNPJ novo na coluna e o gate 100%-uniforme recusa a coluna
   inteira: −38% → ~0%, instantâneo. **O problema não é "no futuro, com muitos" — é no
   primeiro.** Mesma classe do `T-PENHASCO-INICIO` (decisão de pré-passe cria penhasco).
2. **A nature é plana em k** (~24,3–24,5 KB do início ao fim): é **per-VALUE** — quem não
   casa vira literal, o resto continua ganhando. É o único mecanismo cuja curva não vê a
   transição.
3. **O posicional degrada suave** (20,8 → 29,3 KB): por posição, o alfabeto cresce de 10
   para 36 símbolos onde as letras aparecem — sem penhasco, mas sem imunidade.

> ## ⚑ SOLDADO em 2026-08-21 — este lab virou `src/tcf`
>
> O owner aprovou ("go então") e o weld **H-15-01/02 está em `src/tcf`**, com
> [ADR-0042](../../../../../../docs/adr/0042-cnpj-alfanumerico-dois-specs.md). O que
> era subclasse de lab agora é core:
>
> - `TemplatedCheckedSpec.alfabeto` (parâmetro) + `_valor()` (ASCII−48) + os 3 métodos
>   generalizados; `SPEC_CNPJ_ALFA` (`wire_id="cnpja"`, `encoded_length=10`) no registry;
>   `cnpj_spec_para()` como chooser.
> - **`SPEC_CNPJ` ficou byte-intocado, e isso foi PROVADO por diferencial** contra a
>   implementação pré-weld: 8 036 encodes + 5 010 decodes (4 000 payloads adulterados) =
>   **0 divergência de byte**. Única mudança: um rótulo de telemetria em dígito unicode
>   (`format_unmasked` → `format_mismatch`), bytes idênticos, pinado em teste.
> - Suíte 1285 → **1301**; D17a=300, D1–D9 e real-world verdes; 73 snippets de doc, 0 falhas.
>
> **Correção ao §C deste lab**: a subclasse usava `wire_id="cnpja"` FORA do registry, então
> o `decode` sem spec falhava alto. Agora `cnpja` **está** no registry core — o wire é
> self-describing e `decode(texto)` resolve sozinho. O fail-loud continua valendo para
> qualquer id que não esteja no vocabulário fechado.
>
> **O chooser mudou de desenho depois de medir.** A proposta abaixo dizia "coluna com letra
> → `cnpja`". Isso foi medido e **está errado** (erra 8 de 12 pontos): o numérico segue
> ganhando até ~1/4 da coluna. O `cnpj_spec_para` soldado escolhe por **soma de payload**, e
> o resíduo está declarado (41/51; erros só na faixa 22–25%; pior 3,15%).

## O desenho do tratamento (proposta pro weld — aguarda aprovação)

1. **Generalizar os 3 métodos** do `TemplatedCheckedSpec` para alfabeto por-spec (ou
   subclasse como a deste lab) — `check_fn`/pesos não mudam.
2. **`SPEC_CNPJ_ALFA`** novo: regex `[0-9A-Z]`, `encoded_length=10` (denso 0–35),
   `wire_id="cnpja"`, registrado no registry core (senão o wire não é self-describing).
3. **`SPEC_CNPJ` intocado** — byte-compat com todo wire `:cnpj` existente; baselines não
   re-pinam.
4. **Chooser no encode** (quando `nature=` pedir CNPJ): coluna tem letra no corpo → `cnpja`;
   senão `cnpj`. Custo: uma varredura barata que já existe como padrão na máquina.

## Não medido (declarado)

- **Volume futuro** ("como seria com muitos números") — o owner deixou explícito que é o
  passo seguinte, com os databases existentes + sintético em volume. Este lab é o controle.
- **Corpus real alfanumérico** — não existe (1ª inscrição 31/07/2026). O sintético alfa é
  uniforme sobre `[0-9A-Z]` = **controle**, não amostra; quando a emissão real (consoantes?)
  aparecer nos dados da Receita, medir de novo.
- O interior do wire da nature (24,3 KB ≈ 22 KB de payloads + ~2,3 KB) não foi dissecado.
- Interação nature×`.8M` multi-col (`nature_per_col`) não medida aqui.

## Evidência

62 arquivos em [`inputs/`](inputs/)+[`outputs/`](outputs/) — todo wire com roundtrip; portão
anti-órfão por conjuntos. [`resultado.json`](resultado.json) com as 4 partes.

## Conexões

- Lab de ontem (descoberta): [`2026-08-20-2350-cnpj-alfanumerico`](../../2026-08-20/2026-08-20-2350-cnpj-alfanumerico/)
- Gate do split por separador: [H-13-04](../../2026-08-20/2026-08-20-2300-h-13-04-template-declarado/) ·
  penhasco de pré-passe: `T-PENHASCO-INICIO` (STATUS)
- Porta `nature=`/out-of-band: ADR-0027/0041, `T-API-BOUNDARY-CONTRACTS`
- `src/tcf/natures/templated_checked.py` (os 3 métodos do mapa do weld)

**Fontes**: [Receita — CNPJ alfanumérico](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/cnpj-alfanumerico) ·
[Nota Técnica Conjunta 2025.001 (NF-e)](https://www.nfe.fazenda.gov.br/PORTal/exibirArquivo.aspx?conteudo=5ZkvIZt10mQ%3D) ·
[Serpro — cálculo do DV](https://www.serpro.gov.br/menu/noticias/videos/calculodvcnpjalfanaumerico.pdf) ·
[cnpj.ws — algoritmo/exemplo](https://docs.cnpj.ws/blog/cnpj-alfanumerico) ·
[CNN — 9º dígito do CPF (região fiscal)](https://www.cnnbrasil.com.br/nacional/saiba-o-que-diz-o-numero-do-seu-cpf/) ·
[estrutura raiz/ordem/matriz](https://juniorcontador.com.br/cnpj/)

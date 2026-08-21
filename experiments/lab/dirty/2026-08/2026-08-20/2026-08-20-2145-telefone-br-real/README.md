# 2026-08-20-2145 — telefone BR real (Receita): a lacuna fechada

> **Estado: VERIFICADO** (workflow `wf_66f663cb`, 9 agentes, 5 alegações → 2 confirmadas —
> e as duas são lacunas **fechadas**, não defeitos). Os 5 totais reproduzem **byte a byte**
> em re-coleta independente; no escopo de **wire completo** (header cobrado) as conclusões
> não mudam (F1−F0 cai para **+20 B / +0,010%**; F3 −29,95%; F4 −30,11%). Detalhe em
> §Verificação.

## O que este lab fecha

A lacuna declarada **duas vezes** (levantamento `0900`, lab `1200`): o "telefone real" era
o `c_phone` do TPC-H (dbgen), não telefone brasileiro. O dado BR real (`ddd_1`/`telefone_1`
da Receita Federal, perfil `enderecos`) estava pronto e nunca tinha sido medido.

## Coleta e mix

Shaper, `ShapeRequest(volume=20000, seed=42, stratify_by="uf")` — **o mesmo request do lab
1200** (padronização). Mix: SP 29,6% · MG 10,5% · RJ 7,9% · PR 7,3% · RS 6,0% · SC 5,9%.

Comparações no **subconjunto limpo** (ddd 2 díg + fone 8 díg = **99,06%**); o sujo é medido
à parte, não escondido.

## Q3 / M4 — o dado sujo real (alimenta o H-13-03)

**187/20 000 = 0,94%**, nas formas: `fone:1` (88 — o dígito `0` solto), `ddd:1,fone:1` (54),
ambos vazios (28), `ddd:4` (11), `fone:7` (5). **Não há fone de 9 dígitos na base** — a
Receita registra fixo/8.

É a taxa que o *throttling* do prefetch (H-13-03 §4) usaria.

> **CORRIGIDO 2026-08-20** (achado no lab `2300`, H-13-04). Eu tinha escrito que *"o gate
> 100%-uniforme recusaria a coluna INTEIRA por causa de 1%"*. **Falso** — o gate do split
> olha os **separadores**, não a **largura** dos dígitos:
>
> ```
> '(47) 99813942'  template=('(', ') ', '')  campos=['47','99813942']
> '(0) 0'          template=('(', ') ', '')  campos=['0','0']       ← MESMO template
> ```
>
> O sujo **passa** no gate; `_struct_split_encode` aplica normalmente numa coluna que o
> contém. Quem sofre com largura variável é a **nature** (b85 de largura fixa) — e é ela
> que precisa do `ndig` explícito, como o próprio §Verificação já apontou. O gate e a
> nature têm critérios **diferentes**, e eu tinha misturado os dois.

## As cinco formas (n=19 813; fone 97,1% distinto, ddd 73 distintos)

| forma | bytes | B/par | vs F0 | modos |
|---|--:|--:|--:|---|
| **F0 duas colunas (como a Receita entrega)** | **198 425** | 10,01 | 0,0% | `ddd:dict, fone:raw` |
| F1 mascarada `(DD) FFFFFFFF` | 198 456 | 10,02 | **+0,0%** | `tel:split` |
| F2 concatenada 10 dígitos | 217 942 | 11,00 | **+9,8%** | `tel:raw` |
| **F3 grupo + nature b85 no fone** | **138 986** | 7,01 | **−30,0%** | `ddd:dict, fone85:raw` |
| F4 opaco + nature b85 nos 10 díg | 138 690 | 7,00 | −30,1% | `tel85:raw` |

## As três respostas

**Q1 — a nature TRANSFERE, e mais forte.** No `c_phone` (TPC-H) o empacotamento de raiz
valia −24,1%; no BR real vale **−30,0%**. Motivo visível nos modos: o fone é **97,1%
distinto** — `dict` não tem o que colher e o campo vai `raw`; empacotar 8 dígitos → 5 chars
é ganho quase puro (−37,5% teórico no campo; −30% no par com o ddd junto).

**Q2 — a origem já é grupo, e a máscara é EQUIVALENTE a ele.** F0 (duas colunas) e F1
(mascarada) diferem **31 B em 198 mil** (0,016%): o `split` recupera da máscara exatamente
a estrutura de origem. Isso é a tese do grupo (labs 1600/1800) **validada em dado real
espontâneo** — a Receita entrega o "grupo" pronto, e custa o mesmo que a forma mascarada que
o split desmonta. Já **concatenar sem máscara (F2) destrói estrutura: +9,8%** — coerente com
o D0 do CEP.

**Q3 — acima.**

E um contraste que fecha o quadro: **F3 ≈ F4** (0,2% de diferença). Com nature, agrupar ou
não agrupar dá no mesmo *aqui* — porque ambos os campos acabam `raw` e o custo é o mesmo.
O grupo importa quando **algum campo tem cardinalidade baixa** (a regra do lab 1500); o ddd
tem, mas vale pouco byte (2 díg × dict ≈ já era pequeno).

## A nature candidata (mock)

`b85_fixo`: dígitos → int → base-85 de **largura fixa** (charset ASCII 33–126 sem `\`),
bijetiva (`assert` de ida-e-volta na carga completa antes de medir). 8 díg → 5 chars;
10 díg → 6 chars. É a mesma família do candidato do levantamento `0900` — **candidata, não
soldada**; um spec real precisa de `wire_id` (ADR-0041) e de decisão de alfabeto.

## Não medido (declarado)

- Uma seed, um volume. CPU não medida.
- A nature no **subconjunto sujo** (fallback `_` por valor) não foi medida — a taxa é 0,94%,
  e o custo do fallback nesse 1% fica para o lab clean.
- `ddd_2`/`telefone_2` existem na fonte e **não** entraram no perfil `enderecos`.
- A tabela inteira (o ganho dilui entre as 12 colunas) — mesma ressalva do CEP.

## Evidência

7 wires + 7 roundtrips + 7 metas em `outputs/` (por estratégia/coluna), portão de
completude no `main()`. `resultado.json` com mix, sujo e estratégias.

## Conexões

- Lacuna declarada: [`0900`](../../../notas/2026-08/2026-08-17-0900-o-que-falta-pro-8-e-cep-telefone.md) ·
  [`1200`](../../2026-08-17/2026-08-17-1200-cep-real-receita/)
- A regra do grupo: [`1500`](../../2026-08-17/2026-08-17-1500-split-didatico/) ·
  [`1800`](../../2026-08-17/2026-08-17-1800-o-que-de-fato-falta/)
- M4/throttling: [`notas/2026-08-17-2400`](../../../notas/2026-08/2026-08-17-2400-h-13-03-encode-streaming.md)

---

## Verificação (workflow `wf_66f663cb`)

**Os números se sustentam** — re-coleta independente, mesmos request/filtros: os 5 totais
batem byte a byte; os 7 `meta.json` têm `bytes_corpo == bytes_reportados` com RT; e no
escopo **wire completo** (a família de erro "custo estrutural de graça", caçada de
propósito) as conclusões são as mesmas: F0=198 448, F1=198 468 (**+20 B**), F3 −29,95%,
F4 −30,11%.

**Q1 sobrevive com ressalva de redação**: o −24,1% do `0900` era nature sobre **split**; o
−30,0% daqui é sobre F0 — mas como F1(split) ≈ F0 (0,016%), as bases são comparáveis e a
transferência é legítima. A ressalva: *"fica mais forte" é fato DESTES datasets*, não
propriedade da nature — a magnitude segue a estrutura do campo (c_phone de 15 chars com
pontuação vs 8 dígitos puros). **Não generalizar o −30% como número da classe.**

**Lacunas fechadas pela própria verificação:**
- **(a) o fallback no sujo é benigno**: `_` por valor custa ~3,0 B/valor sujo →
  **+0,50%** na coluna da nature com os 20 000 completos (119 472 vs 118 877 B).
- **(b) os −30% são teto prático**: a alternativa barata (fone em duas colunas) dá no
  máximo **−9,8%** (corte 2+6; o 4+4 dá −6,5%), sem padrão de prefixo pro `dict`
  (4 465 prefixos distintos, top = 0,95%). E 5 chars é o **piso aritmético** do
  printable-85: `log85(10^8) = 4,15`.

### O achado novo — colisão de largura no b85 (defeito latente do mock)

**`'12345678'` (8 díg) e `'012345678'` (9 díg) codificam para o MESMO `'!5)a8'`.** O meu
assert de bijetividade passou **por sorte do dado** — a Receita é fixo/8, não há coluna
mista. Numa coluna com 8 e 9 dígitos misturados (celular BR real!), o mock **perderia dado
calado**. Um spec de verdade precisa de **`ndig` explícito por coluna ou recusa de coluna
mista** — mesma família do guard de canonicidade do `ipad`.

### O que falta pro spec real (consolidado)

(i) `ndig` explícito ou recusa de mista (o achado acima) · (ii) alfabeto validado contra
os marcadores do wire em **todos** os modos (aqui o raw saiu sem escape nenhum — provado
para raw, **assumido** para dict/split/header) · (iii) `wire_id` (ADR-0041) + fallback `_`
(já dimensionado: +0,50%) · (iv) mais seeds/volumes e a tabela inteira antes de qualquer
número de release.

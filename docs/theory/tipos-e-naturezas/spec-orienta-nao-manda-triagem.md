# Spec orienta, não manda: a triagem: o que já temos · `.8` · `.9` · `2.0`

**Data**: 2026-08-09
**Tipo**: documento de decisão (triagem de arquitetura)
**Origem**: direção do owner ao fechar o estudo de data, *"a ideia do mês é
exemplificativa, não mandatória (…) tem pedaços de specs que podem ser orientados a
segmentar de forma mais inteligente (…) generalidades indo pro código do núcleo (ou
perto), e especificidade como spec apenas dando dicas: 'se a data é assim, veja se dá
pra usar o ano ou o mês ou o dia com delta, e se não der, fallback' (…) o corpus dita
comportamentos para deixar default; ter o mecanismo pra situações hipotéticas, por
sintético"*
**Evidência**: EXP-017 (clean, 27 casos + caçada adversarial de 4 lentes) ·
labs dirty `1853`/`2228`/`1943` · [`duas-similaridades`](../comparacao/duas-similaridades-igualdade-e-proximidade.md)
**Conecta com**: `T-SPEC-PARSE-X-ALVO` · `T-NATURE-CANDIDATO-BN` · ADR-0040 ·
[`tipos-o-caminho-do-dado-ate-o-tcf.md`](tipos-o-caminho-do-dado-ate-o-tcf.md)

---

## 1. A tese, e por que ela acabou de ganhar evidência

Hoje o spec **manda**: `SPEC_DATA_ISO.encode_value` devolve *o* payload (ordinal-dia).
Um alvo fixo. A proposta do owner: o spec **orienta**, declara os *eixos* plausíveis do
tipo ("dia, mês, ano, com delta") e o núcleo faz o resto com a mecânica que já tem
(materializar candidatos, `min()`, fallback pela válvula).

A caçada adversarial do EXP-017 produziu o argumento empírico decisivo, sem querer:

| regime realista | melhor alvo FIXO | o eixo certo |
|---|---|---|
| série mensal limpa | mês×31+dia (95%) | mês |
| folha (último/5º dia útil) | **NEGATIVO nos 3 alvos** | **dia ÚTIL** (recupera 99,0%) |
| vencimento c/ ajuste de fim de semana | 1,6× | nenhum dos testados |
| agregado mensal derivado de dado real | 1,8–9,8× | mês |
| fato transacional cru | ordinal-dia | dia |

**Nenhum conjunto fixo de alvos cobre.** Cada regime pede um eixo, e regimes novos
(dia-útil!) aparecem assim que se olha dado realista. Um spec que *manda* precisa de um
alvo novo soldado por regime; um spec que *orienta* ganha o eixo novo como mais um
candidato da mesma mecânica. É a diferença entre N welds e 1.

## 2. As três regras de decisão do owner (registradas)

1. **O corpus dita o default; o sintético justifica a existência.** Mensal não aparece
   nas colunas de fato cruas → nenhum eixo mensal vira default privilegiado; mas o
   mecanismo pode existir como candidato (custo = mais código, não menos desempenho,
   com a ressalva honesta de CPU do §5).
2. **Generalidade vai pro núcleo (ou perto); especificidade fica no spec como dica.**
3. **Win-win vira default; trade-off = um default + a melhor versão por qualidade.**
   (memória `feedback_default_mais_variantes_por_qualidade`)

## 3. O que JÁ temos (inventário honesto)

| peça | onde | papel na arquitetura "orienta" |
|---|---|---|
| `min()` de candidatos | rota flat, multi-col, tipado | **é o motor**: candidato entra, nunca substitui |
| delta uniforme `*N+d\|` · per-run (ADR-0016) · **periódico** `*N~…\|` (ADR-0040) | `hcc_seqrle.py` | a aritmética que qualquer eixo produz, já genérica |
| válvula per-valor + slot 0 (None) | natures | o fallback automático que a dica pressupõe |
| hint de cadência → OBAT shape (ADR-0011) | pre-pass | **precedente direto de "orientação"** já soldado |
| specs com alvo fixo (CPF/CNPJ/IP/data-iso) | registry | o "manda" de hoje, vira caso particular do "orienta" (1 eixo) |
| split estrutural `%` (ADR-0026) | multi-col | segmentação genérica por template, a "dica de corte" sem semântica |
| bN de domínio · polaridade | rota flat | a rota plena que o candidato da nature ainda não usa |
| telemetria (`SideOutputs`) | transversal | onde a dica pode reportar "tentei eixo X, perdeu" |

O que **não** temos: (a) specs com >1 eixo; (b) a rota plena no candidato da nature;
(c) eixos não-calendário (dia-útil); (d) nós de proximidade no OBAT (a raiz, 2.0).

## 4. A triagem

### `.8`: completude/correção (pouco, e já identificado)

| item | por quê é `.8` | estado |
|---|---|---|
| **`T-NATURE-CANDIDATO-BN`**: candidato da nature pela rota plena | é CORREÇÃO da invariante (o candidato existe manco); mediana ~5,7% real, máx 11,9% (CPF); a rota plena é **nunca-pior por construção** (stress 8000 colunas, 0 violações), weld simples | **aguarda aprovação** |
| **`T-MAX-PERIODO-31`**: teto do periódico | acabamento do ADR-0040: 24 exclui os períodos naturais de calendário (28–31) | 1 linha; **aguarda aprovação** |
| nada mais | o `.8` fecha com specs-que-mandam; data já é spec e funciona; RT/válvula cobrem a completude | n/a |

### `.9`: o estudo "orienta" (é aqui que a ideia vive)

| item | o quê | evidência que já existe |
|---|---|---|
| **`T-SPEC-PARSE-X-ALVO`** reformulado | a forma madura da direção: spec = parse + **dicas de eixos** + válvula; núcleo = materializa candidatos dos eixos + `min()` + gates | critério atingido (2 grafias × 3 alvos medidos); a fatoração dissolve "N specs" em "1 spec, N eixos" |
| eixos de data como dicas opt-in | dia (soldado) · mês (A4/A2f, condicionado a corpus de agregado) · **dia-útil** (novo, da caçada: 99% na folha) · ano | EXP-017 + variantes realistas |
| **`T-GATES-ANTES`** como pré-requisito | cada eixo é um encode a mais; o FLOOR já é 58% do encode, sem gates baratos, "orientar" explode CPU | bateria `2228`: candidato sem-dedup custa +84–93% |
| `T-PENHASCO-INICIO` | `analyze_column(sample_size=20)` + Regra 2: **6×–95×** decidido pela posição da 1ª exceção; e o penhasco de n do ordinal (0,3%→18,7% entre n=3850–3900), instabilidades de pré-passe | caçada (2 lentes independentes) |
| `T-CANDIDATO-SEM-DEDUP` · `T-SPLIT-SINGLE-COL` | os encaixes estruturais já medidos (variantes, não defaults) | bateria `2228` |

### `2.0`: a raiz

| item | por quê 2.0 |
|---|---|
| **`T-OBAT-NOS-PROXIMIDADE`** | proximidade-como-NÓ dentro do OBAT (a "vontade de fazer logo" do owner), muda o motor, GATE total |
| Patricia (`H-TH-02`/`H-PERF-04`) | o índice que não degenera em prefixo comum (1 bucket/100% em data ISO) |
| dicas de segmentação DENTRO do motor | o spec orientando o próprio OBAT/HCC onde cortar (`ano\|mês\|dia` como fronteiras de token), é o "orienta" completo, e toca o núcleo profundo |

## 5. As ressalvas que a triagem carrega (pra não virar slogan)

- **"Sem custo real" não é literal**: cada eixo materializado custa CPU no caminho
  quente. A resposta é arquitetural (gates baratos por dica + `T-GATES-ANTES`), não
  negacional. O corpus dita quais eixos nem são tentados por default.
- **O ganho sintético é O(n) e frágil ao jitter** (20× em n=600 → 1,1× com ±2 dias).
  A dica barata protege: eixo mensal só é tentado se o pre-scan vê dia-do-mês
  quase-constante, que é exatamente o tipo de gate que "orientar" permite e "mandar" não.
- **Guard de re-emissão é lei** (4ª ocorrência: Unicode digits no YM). Todo eixo novo
  nasce com ele.

## 6. Resumo executável

O `.8` não muda de rumo: fecha com specs-que-mandam + as duas correções aprováveis.
O `.9` ganha um organizador: **"spec orienta" é o guarda-chuva que unifica**
`T-SPEC-PARSE-X-ALVO`, os eixos de data, os gates e os encaixes estruturais, com o
argumento empírico (folha/dia-útil) de que orientar escala onde mandar não. O `2.0`
continua dono da raiz (nós de proximidade, Patricia, segmentação no motor).

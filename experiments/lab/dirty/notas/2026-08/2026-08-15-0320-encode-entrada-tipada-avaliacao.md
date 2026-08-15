# O encode pode sustentar a entrada tipada? — ciclo de avaliação

**2026-08-15** · pedido do owner, depois do lab do decode direto ao tipo.

> *"veja se o encode pode sustentar isso também pela entrada… o decode é menos arriscado do meu
> ponto de vista depois de ver os testes, mas o encode é mais arriscado porque, apesar de ser
> uma boa ideia: por um lado a lib de transformação já funciona pra vários formatos, por outro
> **deixa a responsabilidade no TCF de ficar validando date/datetime de muitos formatos**. E é
> um risco — logo deixar a entrada mais **encaixotada** e deixar a responsabilidade do
> desenvolvedor em trabalhar o dataset antes pode dar mais tranquilidade."*

**Tipo**: [probatório] avaliação. Nenhum lab novo, nenhum weld, `src/tcf` intocado.

---

## 1. A assimetria: "objeto nativo" e "muitos formatos" são **opostos** em risco

A preocupação junta duas coisas que se subtraem. Medido:

| entrada | grafias a validar | pode ser inválida? | precisa de parse? | custo |
|---|---:|---|---|---:|
| **objeto `date`** | **0** | **não — por construção** | **não** | `toordinal()` = **123 ns** |
| string canônica (hoje) | 1 | sim | sim | `fromisoformat`+guard = **1230 ns** |
| string livre | **N** | sim | sim | N caminhos de validação |

**O objeto não pode ser inválido** — o construtor já recusou:

```
dt.date(2026, 13, 2) -> ValueError: month must be in 1..12
dt.date(2026,  2,30) -> ValueError: day is out of range for month
dt.date(0,     1, 1) -> ValueError: year 0 is out of range
```

**A validação já aconteceu na fronteira anterior** — quem construiu o objeto pagou. E o
caminho do objeto **pula o parse e o guard**: é **10× mais barato** que o da string canônica
que o TCF já aceita hoje.

**Conclusão da §1**: aceitar objeto é **menos arriscado que o que o TCF já faz**. Aceitar
string livre é o risco que você descreveu — e continua devendo ser vetado.

## 2. Onde você está certo, e a medição confirma

- **Aceitar muitas grafias de string é risco real.** Cada grafia é uma classe de bug de
  canonicidade (o guard de re-emissão existe por isso, com 4 bugs históricos). **Continua
  vetado** — nada aqui propõe afrouxar.
- **O decode é mesmo menos arriscado.** Ele não valida nada: só entrega o objeto que já ia
  construir. Confirmado no lab `…-0200`.
- **"Encaixotar a entrada" está certo — para STRING.** A recomendação de manual continua sendo
  a resposta para quem entrega texto.

## 3. Onde a medição discorda: deixar com o dev **não é mais seguro** no datetime

O achado prático mais forte deste ciclo:

| tipo | `str(obj)` | `obj.isoformat()` | iguais? |
|---|---|---|---|
| `date` | `2026-03-02` | `2026-03-02` | **sim** |
| **`datetime`** | `2026-03-02 08:26:00` | `2026-03-02T08:26:00` | **NÃO** |
| `datetime` c/ micro | `…08:26:00.500000` | `…T08:26:00.500000` | **NÃO** |
| `time` | `08:26:00` | `08:26:00` | sim |

**O dev que usar `str()` ou f-string num `datetime` entrega a grafia com espaço sem saber que
escolheu.** Ele não errou por descuido — errou porque a linguagem tem dois defaults e não
avisa qual.

Ou seja: exigir que o dev normalize **exige que ele saiba dessa divergência**. Deixar com ele
não é mais seguro — é **mais silencioso**. Se o TCF aceitar o objeto, ele escolhe a grafia
canônica e **o dev não pode errar**.

E note a inversão: o **`date` é o caso mais seguro** para aceitar objeto (não há ambiguidade —
os dois defaults coincidem), e o **`datetime` é o que mais ganha** (porque é onde o dev erra).

## 4. O desenho de menor risco — e ele não muda o wire

Hoje o encode **recusa** objeto (`HierarchicalError: valor escalar de tipo não suportado`, e
com `nature=` a mensagem é *"kwargs `['nature']` só valem no flat de STRING"*).

Há dois desenhos possíveis, e o risco entre eles é muito diferente:

### Desenho A — **normalização na porta** (o de menor risco)

O objeto vira a grafia canônica **uma vez**, na entrada, e daí o fluxo é **o de hoje, intacto**.

Medido: o wire sai **byte-idêntico** ao de hoje (26 B, `#TCF.8 :dt`, `True`), e o RT fecha.

- **sem tag nova** — não toca o `T-TIPOS-CONFORTO-MAP`
- **sem grafia nova** no wire
- **sem validação nova**: `isoformat()` não pode falhar num objeto válido
- custo: a normalização é **1,7% do encode**. Quem paga não muda o total — **muda de bolso**

### Desenho B — tipo nativo com tag própria

Exigiria tag no índice 6, cai no `T-TIPOS-CONFORTO-MAP` (⛔ bloqueado em você), e **não é
necessário para o ganho**. Fora de escopo.

## 5. Os riscos honestos do desenho A (que não devem ser suprimidos)

1. **O port para outra linguagem.** Aceitar objeto exige que cada host conheça o tipo de data
   *da sua* linguagem — e em Rust o `chrono` é lib **externa**, não stdlib. Isso é inflação de
   núcleo real. Mitigação: é a mesma classe do kwarg de saída que você já aceitou, e é
   **droppable** — host que não implementa, não aceita objeto e nada quebra.
2. **Coluna mista** (`[date, date, "2026-1-1"]`) precisa de política declarada. O precedente
   existe: o **CONTRATO UNIÃO** do ADR-0039. Mas precisa ser dito, não presumido.
3. **O dispatch**: hoje `_tipo_single_col` reconhece bool/int/float/str. O próprio comentário
   do código diz que a extensão é *"uma LINHA aqui, não um bloco novo"* — mas é `src/tcf`, e
   depende da sua aprovação.
4. **O RT muda de contrato quando entra objeto** (tipo+valor, não grafia). Não é novidade
   estrutural — é o que int/float/bool já fazem —, mas é contrato novo para a família data.

## 6. Resposta direta às suas duas perguntas

**"O encode pode sustentar isso pela entrada?"** — Sim, e com **menos risco que hoje**, desde
que "tipada" signifique **objeto nativo**, não string livre. O objeto dispensa o parse e o
guard que a string canônica de hoje já paga.

**"É exagerado o meu receio?"** — Não, e ele está certo **para o alvo errado**. O risco que
você nomeou existe inteiro em "aceitar N grafias de string", e nada aqui propõe isso. Ele
**não existe** em "aceitar objeto" — lá a superfície de validação é zero.

## 7. Sobre *"se o datetime der certo, a gente revisa novamente o date"*

A medição sugere a ordem **inversa**, e vale registrar:

- o **`date` é o caso trivialmente seguro** (`str()` ≡ `isoformat()`, zero ambiguidade) —
  seria o piloto natural;
- o **`datetime` é o que mais ganha**, mas é onde a ambiguidade de grafia mora.

Se for para pilotar, pilotar no `date` mede o mecanismo sem a variável da grafia. Mas isso é
sugestão de ordem, não de escopo — a decisão é sua.

## Conexões

lab [`…-0200-decode-direto-ao-tipo`](../../2026-08/2026-08-15/2026-08-15-0200-decode-direto-ao-tipo/) ·
`T-DECODE-SAIDA-TIPADA` (o irmão, pela saída) · `T-TIPOS-CONFORTO-MAP` (⛔ owner; **não** é
tocado pelo desenho A) · ADR-0039 (CONTRATO UNIÃO) · `T-DATA-TIPADA-NATIVA` ·
`docs/how-to/normalizar-data-antes-do-tcf.md` (a regra da string, que **não muda**)

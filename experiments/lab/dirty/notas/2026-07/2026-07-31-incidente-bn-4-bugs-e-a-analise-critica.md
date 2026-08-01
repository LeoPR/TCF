# Incidente 2026-07-31 — 4 bugs no weld bN (ADR-0036) e a análise crítica

> *"faça o registro dessas descobertas pra não ficarem só na prosa de chat, isso fere a
> rastreabilidade. Faça a análise crítica, registre de acordo para prosseguir depois."*

Procede. Este documento existe porque os achados abaixo estavam só em mensagens de chat, e
mensagem de chat não é registro.

**Resumo**: uma auditoria adversarial rodada sobre uma **proposta** (`T-BN-TIPADO`) achou
**14 hipóteses**, das quais **4 eram bugs reais no código já soldado** do ADR-0036 — um deles
de corrupção silenciosa. Todos corrigidos, todos com teste. Suíte 1042 → **1061 passed**;
gates inalterados.

---

## 1. O que a auditoria achou, e o veredito de cada um

14 achados brutos, todos com `reproduzido=true`. **Eu triei cada um rodando código** — não
aceitei nenhum de segunda mão. O resultado do orquestrador veio **truncado** e eu inicialmente
só vi 2; a triagem completa só aconteceu depois de ler o `journal.jsonl` direto.

| # | achado | veredito | ação |
|---|---|---|---|
| **1, 4, 7, 12** | `_grafa` não é injetiva — `\0` (dado) colide com o escape de `"0"` | **CONFIRMADO — corrupção silenciosa** | corrigido + teste |
| **3, 6, 8, 13** | cabeçalho aceita família infinita de grafias (`int(x,16)` cru) | **CONFIRMADO** | corrigido + teste |
| **5** | string vazia como **último** valor do domínio quebra o RT | **CONFIRMADO** | corrigido + teste |
| **10** | linha extra depois do bloco de bits é ignorada calada | **CONFIRMADO** | corrigido + teste |
| **2** | `decode_bn` não valida `n` contra o payload (truncamento) | **REFUTADO** | `bitpack.unpack_w` já falha alto |
| **11** | b64 sem `validate=True` aceita char fora do alfabeto | **REFUTADO** | é rejeitado (por padding), mas a mensagem é ruim |
| **9** | tag `s` criaria segunda grafia do bN | **N/A** | era sobre a proposta, não sobre o soldado |
| **14** | denso `b1` emite padding `=`, bN não — 1-2 B mortos | **ANOTAR** | inconsistência real; ticket `T-DENSO-PADDING` |

Quatro dos oito grupos eram **o mesmo bug visto por lentes diferentes** — o que é sinal de
que a redundância das lentes funcionou, não de que havia 14 problemas.

---

## 2. Os quatro bugs, em detalhe

### 2.1 `_grafa` não era injetiva — CORRUPÇÃO SILENCIOSA

```
_grafa("0")   ->  \0
_grafa("\0")  ->  \0        ← mesma saída, valores DIFERENTES
```

`encode(["\0", "x"] * 30)` devolvia `["0", "x", …]` — **sem exceção**, pela API pública, com
`list[str]` trivial.

**Contra-prova que estabelece a culpa**: `encode(mesma_coluna, stamp=False)` (rota core, sem
candidato bN) preservava. Era **regressão do weld**, não limitação do formato.

**Causa**: quem escapa tem de escapar **também o próprio char de escape**. Escapei `"0"` e
deixei passar o `\` que já vinha no dado.

**Correção**: `escapa o \ inicial E o 0 solitário; nada mais`, com teste de injetividade e de
inversa exata.

### 2.2 Cabeçalho não-canônico — família infinita de grafias

`int(x, 16)` aceita zero à esquerda, maiúscula, underscore (PEP 515), prefixo `0x` e sinal;
`str.isdigit()` aceita dígito Unicode. Todos decodificavam igual ao canônico `#TCF.8B2c8`:

```
#TCF.8B20c8   #TCF.8B2C8   #TCF.8B2c_8   #TCF.8B20xc8   #TCF.8B2+c8   #TCF.8B٢c8
```

**O agravante**: o irmão no **mesmo índice 7** (modo denso) já rejeitava tudo isso desde
sempre, e `test_typed_singlecol.py::test_grafia_nao_canonica_fail_loud` já travava o
invariante — *"duas grafias, mesmo valor, violaria S1.2"*.

**Correção**: re-formata e compara, exatamente como o irmão faz.

### 2.3 String vazia como último valor do domínio

`bloco.rstrip("\n")` comia **todos** os `\n` finais, mas o corpo canônico termina em
**exatamente um**. `["a","b",""]` perdia o terceiro valor; o `decode` estourava com *"índice 2
fora do domínio de 2 valores"*.

Falhava **alto**, então não é corrupção — mas é **RT quebrado pela API pública**, que é
igualmente inaceitável.

**Correção**: `[:-1]` em vez de `rstrip("\n")`.

### 2.4 Conteúdo depois do bloco de bits, ignorado calado

Linha extra após o b64 era descartada em silêncio. **O irmão no mesmo índice 7 falha alto na
mesma sonda.** Silêncio ali esconde wire concatenado, truncado ou editado à mão.

**Correção**: fail-loud, como o irmão.

---

## 3. Análise crítica — o que estes bugs dizem sobre o processo

### 3.1 A assimetria de escape apareceu 5 vezes. Isso não é azar.

| # | onde | quando |
|---|---|---|
| 1 | weld do slot nulo — `^0` devolvia o último nó declarado | 2026-07-25 |
| 2 | lab `2126` — a string `"0"` virando `None` | 2026-07-26 |
| 3 | lab `1608` — domínio grafando null como `0` cru | 2026-07-27 |
| 4 | lab `2231` — `_le_grafia` tirando qualquer `\` inicial | 2026-07-27 |
| 5 | **weld ADR-0036** — `_grafa` não injetiva | 2026-07-27 |

**O padrão**: toda vez que introduzi uma grafia nova ao lado do slot nulo, errei o par
escapar/desescapar — ora de menos, ora de mais.

**Crítica dura**: no #4 eu escrevi o invariante *"desfazer exatamente o que fez, nem mais"* e
o registrei no ADR. No #5, dias depois, errei na **direção oposta** — escapei de menos.
Escrever o invariante como frase não impediu a recorrência. **A frase não é o controle; o
teste é.**

**O que muda a partir daqui**: qualquer função de grafia nova entra com **teste de
injetividade** (`len(set(map(grafa, vals))) == len(vals)`) e **teste de inversa exata**
(`le(grafa(v)) == v`) desde o primeiro commit. Os dois existem hoje em
`test_dominio_bn.py::TestGrafiaInjetiva` e custam 6 linhas.

### 3.2 O invariante de canonicidade existia, era testado, e não foi aplicado ao módulo novo

`test_typed_singlecol.py::test_grafia_nao_canonica_fail_loud` travava exatamente isso no
índice 7. Eu **acrescentei um modo no mesmo slot** sem ir ver o que o vizinho exigia.

**Crítica**: o guia de encaixe do `.9` que escrevi manda consultar o mapa antes de soldar —
e eu consultei o mapa de **onde encaixar**, não o de **que invariantes o vizinho já
garante**. São coisas diferentes, e faltou a segunda.

**O que muda**: ao acrescentar valor a um namespace existente (discriminador, modo, tag), a
checklist passa a incluir *"quais testes cobrem os vizinhos deste slot, e eles valem para o
novo?"*. Barato: é um `grep` pelo slot.

### 3.3 Os quatro bugs sobreviveram a 32 testes meus. Por quê?

`test_dominio_bn.py` tinha `test_valor_que_ja_traz_backslash` (`\temp` — passa) e
`test_zero_como_dado_nao_vira_null` (`"0"` × `None` — passa). **A interseção dos dois — `\0` —
era exatamente o buraco.**

**Crítica**: testei os eixos separadamente e não o **produto**. É a mesma classe de erro do
`str-zero-*` no lab `2126`, onde as colunas críticas existiam mas **recusavam**, e eu só
percebi porque a auditoria apontou.

**O que muda**: para grafia, testar o **produto cartesiano** dos chars especiais, não a lista.
São poucos chars (`\`, `0`, o marcador, vazio) — a combinatória é trivial e pega a interseção.

### 3.4 A auditoria adversarial se pagou — mas quase falhei em usá-la

O resultado veio **truncado** e eu inicialmente reportei 2 achados quando havia 14. Só a
leitura do `journal.jsonl` revelou os outros 5 não-triados, **dois dos quais eram bugs
reais**.

**Crítica**: aceitar o sumário do orquestrador é o mesmo erro de aceitar resultado de agente
sem verificar. Já tinha acontecido em 2026-07-26, quando a fase de refutação morreu por limite
de gasto e o orquestrador marcou tudo como "descartado" — o que era **falso**, elas não foram
refutadas, não foram verificadas.

**O que muda**: o `journal.jsonl` é a fonte, o sumário é conveniência. **Sempre ler o journal
antes de reportar.**

### 3.5 O acerto que vale registrar

O FLOOR nunca-pior segurou: **nenhum baseline moveu** em nenhuma das correções. E o `min()`
externo continuou absorvendo o caso patológico. A arquitetura de "mais um candidato" provou
ser resiliente a bug no candidato — o pior que aconteceu foi um wire ilegível, nunca um wire
menor-e-errado que vencesse o `min()`.

Isso é argumento **a favor** de continuar entrando por FLOOR em vez de por substituição.

---

## 4. Estado após as correções

| | |
|---|---|
| suíte | **1061 passed, 3 skipped** (era 1042) |
| gates | **D1-D9 1545 · D17a 300 · real-world 89430** — inalterados |
| `test_dominio_bn.py` | 32 → **58 testes** |
| classes novas de teste | `TestGrafiaInjetiva`, `TestCanonicidadeDoCabecalho`, `TestStringVaziaNoDominio`, `TestNadaDepoisDosBits` |

Commits: `e87cdb5` (bugs 1 e 2), `654c0ac` (correção do exemplo no ADR), e este.

---

## 5. O que fica pendente por causa deste incidente

| ticket | o quê |
|---|---|
| **`T-DENSO-PADDING`** | o denso `b1` emite base64 **com** padding `=`, o bN **sem**. 1-2 B mortos em ~2/3 dos wires densos. O padding é deduzível de `n` e `w`; a inconsistência é do lado antigo, não do novo |
| **`T-BN-B64-VALIDATE`** | b64 inválido é rejeitado, mas com `binascii.Error: Incorrect padding` em vez de mensagem de nível TCF. Cosmético, mas o resto do formato é fail-loud com mensagem própria |
| **`T-GRAFIA-CHECKLIST`** | transformar §3.1 e §3.2 em checklist executável (teste de injetividade + varredura de invariantes do slot vizinho) |

E o **`T-BN-TIPADO` continua NÃO soldado**. A auditoria era sobre ele; o que ela achou estava
no weld anterior. A proposta segue com o ganho provado no lab
`2026-07-28-0829` (−6015 B em 12 de 13 colunas, RT 28/28) e **agora entraria sobre base
corrigida** — o que é um argumento a mais para ela ser a próxima.

Nota relevante para a decisão: pelas tags `b`/`n` o bug 2.1 era **inalcançável** (domínio só
tem `true`/`false`/dígitos). Quem o alcançava era a rota **flat**, já soldada. Ou seja, o
`T-BN-TIPADO` não teria introduzido o bug — mas teria **promovido `decode_bn` a load-bearing
de uma segunda rota** com ele dentro.

---

## Rastro

- decisão e escopo: [`docs/adr/0036`](../../../../../docs/adr/0036-bn-de-dominio-cardinalidade-baixa.md) §"Dois bugs corrigidos"
- ganho do `T-BN-TIPADO`: `experiments/lab/dirty/2026-07/2026-07-28/2026-07-28-0829-bn-tipado-ganho-medido/`
- evidência do weld original: `experiments/lab/dirty/2026-07/2026-07-27/{1608,1647,2211,2231,2247}`
- tickets vivos: bloco no topo do [`STATUS.md`](../../../../../STATUS.md)
- transcrição da auditoria: `subagents/workflows/wf_bfeae270-107/journal.jsonl` (14 achados)

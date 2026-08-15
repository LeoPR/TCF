# Resultado — o processo de compressão do date, com todos os candidatos no mesmo `min()`

6 transformações × 14 regimes, formato fixo (`YYYY-MM-DD`), **0 falhas** de RT — cada
transformação validada pela própria inversa. Orienta, não fecha.

---

## 1. Antes dos números: uma correção ao que a tabela mostra

A coluna "perda-hoje" do `run.py` diz **14 de 14**. **Isso está inflado**, e a causa é minha:
em 7 regimes o vencedor é o **próprio `ordinal`** (22 B) contra o `spec` de hoje (26 B) — e a
diferença de **4 bytes é exatamente o carimbo `:dt`** no header, não uma transformação melhor.
Isso é o `T-SPEC-SEM-CARIMBO`, que já existe, não achado deste lab.

**A régua honesta é transformação contra transformação** — tudo contra o `ordinal`, que é o
que está welded:

| regime | ordinal (welded) | melhor candidato | ganho REAL | quem ganha |
|---|---:|---:|---:|---|
| **esparsa-ordenada** | 3854 | **605** | **84,3%** | **`delta2`** |
| **mensal-faltas** | 2278 | **453** | **80,1%** | `delta` |
| **agrupada** | 167 | **41** | 75,4%¹ | `componentes` |
| **cíclica** | 957 | **351** | **63,3%** | `delta` |
| **mensal-dia1** | 654 | **337** | **48,5%** | `delta` |
| **esparsa-desordenada** | 4468 | **2434** | **45,5%** | `componentes` |
| úteis-feriado | 305 | 292 | 4,3% | `ordinal-rel` |
| diária · semanal · quinzenal · úteis · trimestral · descendente · suja | — | — | **0%** | `ordinal` já é o melhor |

¹ contra o **núcleo** (64 B) o ganho é 35,9% — o ordinal é ruim nesse regime.

**Seis regimes ganham de verdade com transformação nova. Oito já estão no ótimo.**

---

## 2. O buraco que era o motivo do lab: **delta-of-delta tem nicho próprio**

Nunca havia sido medido neste projeto. E ele **vence onde nem o ordinal nem o delta alcançam**:

| regime | núcleo | ordinal | delta | **delta2** |
|---|---:|---:|---:|---:|
| esparsa-ordenada | 6637 | 3854 | 772 | **605** |

Faz sentido mecanicamente: numa série com saltos **irregulares mas crescentes**, a 1ª diferença
ainda é irregular (1..40), enquanto a **2ª oscila em torno de zero** — e alfabeto pequeno em
torno de zero é o que o núcleo come bem.

É um regime real (eventos esparsos ordenados por data — log, auditoria, histórico), e é
exatamente onde o `T-DATA-ALVO-DELTA` registrava que sobrava trabalho (*"sobram pro
delta-coluna: espalhado-ordenado (644)"*). **O delta2 faz 605.**

---

## 3. A partição que emerge — e ela é limpa

Cada transformação tem um domínio, e eles quase não se sobrepõem:

| transformação | ganha quando | regimes |
|---|---|---|
| **`ordinal`** (welded) | há **progressão regular** — o seq-RLE pega | diária, semanal, quinzenal, úteis, trimestral, descendente, suja |
| **`delta`** | a progressão **quebra**, mas o alfabeto de saltos é pequeno | mensal-dia1, mensal-faltas, cíclica |
| **`delta2`** | os saltos são **irregulares e crescentes** | esparsa-ordenada |
| **`componentes`** | a **ordem some** ou o valor repete | esparsa-desordenada, agrupada |

E o simétrico vale: cada uma é **péssima** fora do seu domínio — `componentes` faz 1835 B na
diária (contra 22 do ordinal); `delta` faz 227 nos úteis (contra 30). **Não há candidato
dominante**, e é por isso que a resposta é o `min()`, não a escolha.

---

## 4. O que isto diz sobre "o processo de compressão"

**O ordinal welded está certo como default** — ele vence ou empata em 8 de 14 regimes, e é o
mais geral. O que falta não é substituí-lo: é **ter os outros como candidatos do mesmo `min()`**.

Hoje a rota single-col tem: núcleo (com seq-RLE e periódico dentro), spec ordinal, e bN. Não
tem delta, delta2 nem componentes. Nos seis regimes acima, **o candidato que ganharia não é
construído** — é a mesma classe que o projeto já nomeou três vezes (*"o candidato existe e a
rota não o consulta"*).

E há uma diferença importante em relação às ocorrências anteriores: **delta, delta2 e
componentes não existem em lugar nenhum** — não é rota que falta consultar, é candidato que
falta existir. O `T-DATA-ALVO-DELTA` já pedia isso e está *"aguardando decisão de design do
owner (protocolo da nature: transform de coluna)"*.

**A pergunta de design que o lab devolve**: o protocolo de nature é per-valor
(`encode_value(v)`), e por isso só consegue emitir o ordinal. Delta, delta2 e componentes
**vêem os vizinhos** — precisam de um protocolo de **coluna**. É a decisão que destrava os
seis regimes.

---

## 5. Ressalvas honestas

- **Tudo sintético.** Os regimes são os que o projeto já catalogou, mas os ganhos aqui são de
  laboratório. O precedente é duro: o `T-DATA-ALVO-MENSAL` deu **95% em sintético e 0,0% em
  real**, porque o corpus não tem cadência mensal. **Os 80% do `mensal-faltas` estão sob o
  mesmo risco** — e o `T-CORPUS-DATA-MENSAL` continua bloqueado.
- **Os regimes esparsos e cíclicos, esses, existem no corpus** (`T-CANDIDATO-SEM-DEDUP` mediu
  cíclica real; `esparsa` aparece nas colunas de data do TPC-H). Esses ganhos têm mais chance
  de sobreviver.
- **O `componentes` deste lab não é o `split` do formato** — é a mesma ideia numa lista só,
  para caber no single-col. O split real é multi-col embutido, não streama por linha, e custa
  +47–54% de CPU.
- **CPU não foi medida aqui.** Transformação de coluna é passe extra sobre os dados; o
  `T-CANDIDATO-SEM-DEDUP` mediu +84–93% de encode para um candidato análogo. **Um `min()` com
  seis candidatos custa tempo**, e isso precisa entrar na conta antes de qualquer weld.

## 6. O que orienta

1. **Delta-of-delta merece entrar no registry** — tem nicho próprio e medido, e era o único
   candidato clássico de série temporal que o projeto não tinha tocado.
2. **A decisão de design que destrava tudo é o protocolo de transformação de COLUNA** — sem
   ele, delta/delta2/componentes não podem existir como specs.
3. **O ordinal continua o default certo.** Nada aqui o desafia: ele ganha ou empata em 8 de 14.
4. **Antes de qualquer weld**: medir CPU do `min()` ampliado, e buscar os regimes ganhadores em
   dado real (os esparsos e cíclicos têm chance; o mensal está bloqueado por corpus).

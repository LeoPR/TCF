# Dúvidas levantadas pelo baseline de performance (2026-07-22)

**Parecer posterior**: [política de baseline dividida por cadência](2026-07-22-0156-baseline-perf-parecer.md).
As dúvidas abaixo permanecem como registro do achado original; o parecer avalia as alternativas sem
alterar o instrumento ou o core.

**Contexto**: a primeira tentativa de rodar o baseline real (`bench_perf.runner`, escala
cheia) foi **morta em 84/132 após ~2h26min**. O run expôs questões de desenho do
processo que precisam ser resolvidas **antes** de re-rodar. Registro aqui pra a
re-arquitetura ter checklist — nenhuma está resolvida ainda.

Processo em si (probes/pivot/synth/layers/compress/manifest/calibrador/comparador +
os 11 vetores) está **completo e commitado**; as dúvidas são sobre COMO RODAR o
baseline, não sobre o instrumento.

---

## D1 — As células B4 (concorrência) em escala cheia dominam o run

**Observado**: cada medição de encode das células B4 leva **10-46 s** (o `serial+tN`
spawna K subprocessos × reps; o tier roda tudo **n=5-7 vezes**). ~16 células assim =
a maior parte das 2,5h.

**Dúvida**: vale medir concorrência em escala cheia com reps completos? O achado
(interno = prejuízo líquido, spawn domina; teste escala sem contenção) é
**invariante de escala** — o custo de spawn não depende do tamanho do dado. Rodar
n=5× a 20k linhas não parece acrescentar sobre o que o smoke já mostrou.

**Candidatos de resolução**: (a) B4 em escala reduzida DECLARADA; (b) B4 com n menor
(a concorrência não precisa de percentil fino); (c) tirar B4 do baseline recorrente e
medir 1×, à parte, como caracterização (não como referência comparável).

---

## D2 — Run longo (2,5h+) × deriva térmica = baseline provavelmente suspeito

**Observado**: os smokes já saíam `TERMICAMENTE SUSPEITO` (drift 1,12-1,14) em runs de
minutos. Um run de horas quase certamente estoura o limiar (1,10) — e aí a referência
não vale (o calibrador reprova).

**Dúvida**: qual a **duração-alvo** de um baseline pra ficar dentro do piso de ruído?
A comparação `.8`-vs-`.9` exige similaridade estatística; um baseline suspeito não é
comparável.

**Candidatos**: (a) baseline curto (< ~20 min) minimiza a janela de deriva; (b)
rodar em blocos independentes, cada um curto, com o calibrador por bloco; (c) exigir
máquina quieta (AC, energia alto-desempenho, sem carga) como pré-condição do S0.

---

## D3 — O tier (n adaptativo) multiplica o custo das células que já conhecemos

**Observado**: o tier roda células lentas n=5-7×. Pra células cujo comportamento já
está caracterizado (B4), isso é custo sem informação nova.

**Dúvida**: o baseline recorrente (comparável ao `.9`) precisa dos MESMOS n de uma
caracterização exploratória? Talvez o baseline queira n menor nas células caras (só
o suficiente pra o comparador), e as caras-e-já-entendidas fiquem fora do loop.

---

## D4 — Matriz congelada (R2) × reduzir escala de B4

**Observado**: `cases.json` é dado congelado (regra R2 — o `.9` consome o MESMO
arquivo). Reduzir a escala de B4 muda a matriz.

**Dúvida**: como reconciliar "matriz congelada" com "B4 mais barato"? A escala é
COORDENADA (entra no `case_id`), então mudar a escala de B4 muda os `case_id` — e o
join `.8`↔`.9` continua válido DESDE QUE as duas rodadas usem a mesma matriz nova.
Ou seja: re-congelar a matriz UMA vez (antes do baseline definitivo) é aceitável; o
que não pode é `.8` e `.9` usarem matrizes diferentes.

**Candidatos**: (a) re-gerar `cases.json` com B4 em escala menor e re-congelar; (b)
separar a matriz em "núcleo recorrente" (comparável, barato) e "caracterização"
(caro, 1×, fora do join).

---

## D5 — Baseline único vs split (rápido cheio + lento reduzido)

**Dúvida de arquitetura** que amarra D1-D4: o baseline deve ser UM run, ou SPLIT?
- **Núcleo recorrente** (caminhos, escala moderada, camadas, compressão, `.8H`,
  typed, candidate/column, accel) — escala cheia onde é barato, é o que o `.9` compara
  toda vez. Curto o bastante pra ficar sob o piso de ruído.
- **Caracterização** (B4 concorrência em escala cheia, R6e5 gigante) — caro, rodado
  1× à parte, registrado como observação, NÃO no loop de comparação.

Isso responde D1, D2 e D3 de uma vez, ao custo de D4 (re-congelar a matriz em duas
faixas). Parece o caminho, mas é decisão de desenho — não implementado.

---

## D6 — Pendentes de infra ainda abertos

- `process-tree` (memória da árvore de processos) precisa de `psutil` — hoje 2 células
  pendentes. Adicionar `psutil` (dependência de dev do harness, não do TCF) ou deixar
  como limitação declarada?
- Células-régua B0 (pins/sondas/sentinela) — são infra do manifesto/calibrador, não
  célula de dado. Representá-las como "medidas" (tempo do `validate_pins`) ou tirá-las
  da matriz e deixá-las só no cabeçalho do run?

---

## Estado (não decidido)

Nada acima está resolvido. A re-arquitetura do baseline (provável: D5 split +
re-congelar matriz em duas faixas, D2 máquina-quieta como pré-condição) depende da
palavra do owner. O instrumento está pronto; a POLÍTICA DE EXECUÇÃO é o que falta
fechar.

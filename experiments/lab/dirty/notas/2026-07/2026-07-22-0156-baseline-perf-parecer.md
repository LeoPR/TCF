# Parecer sobre a política do baseline de performance

**Força**: recomendação para decisão do owner. Não altera o instrumento, a matriz ou o core.

**Fontes avaliadas**: `../scripts/bench_perf/cases.json`, `cases.py`, `runner.py`,
`probes.py`, `calibrators.py`, `manifest.py`, `compare.py`, o smoke persistido em
`experiments/results/perf-baseline/` e as [seis dúvidas do primeiro run](2026-07-22-0142-baseline-perf-duvidas.md).

## Veredito

O run interrompido em 84/132 não demonstra um blocker de performance do TCF. Ele demonstra que
uma **matriz de caracterização** foi executada como se fosse um **baseline recorrente único**.
O instrumento mede superfícies úteis, mas a política atual mistura três atos com cadências
diferentes:

1. regressão recorrente, que precisa ser curta e comparável;
2. caracterização de escala/concorrência, que pode ser cara e rara;
3. validação do próprio instrumento, que pertence ao envelope do run.

**Recomendação**: adotar um baseline dividido por papel, preservando uma matriz-mestra de casos e
versionando separadamente o plano de execução. Não reduzir B4 e concluir que concorrência é
invariante de escala: o custo de spawn tem parcela fixa, mas contenção, memória e amortização do
trabalho variam com a carga.

## O que os achados sustentam

- B4 concentra 16 casos. Cada caso de paralelismo interno mede o encode solicitado e uma referência
  serial; cada uma dessas medições passa pelo tier adaptativo. Casos de concorrência do teste ainda
  criam processos e fazem três encodes por worker. O custo observado é consequência esperada dessa
  composição, não evidência de defeito no runner ou no TCF.
- O smoke já separa sinais fortes: em `R=200`, `p2/p4/p8` ficou aproximadamente em 0,53-0,62 s por
  ponto, enquanto `serial+t2/t4/t8` ficou em 0,035-0,041 s. Esses números caracterizam o protocolo
  reduzido; não autorizam extrapolar o speedup ou a contenção para 20 mil linhas.
- O comparador só junta `case_id` e tempos. Hoje ele não prova que os dois lados usaram o mesmo
  número de amostras, tier, ordem ou política de execução. Mudar apenas a repetição sem registrar o
  protocolo pode produzir um join sintaticamente válido e cientificamente desigual.
- O runner persiste o JSONL somente depois de todos os casos. Por isso, um run morto após 2h26 não
  deixa as 84 medições como artefato retomável. Antes de outra rodada longa, persistência incremental
  é mais importante que qualquer ajuste fino de amostragem.
- O limiar térmico de 1,10 é uma guarda útil, mas os smokes em 1,12-1,14 mostram que “máquina quieta”
  é pré-condição, não solução. Um run monolítico de horas associa posição na matriz a estado térmico.

## Desenho recomendado

### 1. Manter uma matriz-mestra e congelar planos

Manter `cases.json` como catálogo das coordenadas semânticas. Adicionar planos versionados que
contenham:

- lista ordenada ou seed de ordem dos `case_id` participantes;
- tier/repetições e warmup por família;
- duração máxima do bloco e frequência da sentinela;
- dependências opcionais exigidas;
- hash da matriz-mestra e versão do protocolo.

O manifesto de cada run deve carregar o hash do plano. O comparador deve abortar quando matriz,
plano ou protocolo divergirem. Isso resolve D4 sem reescrever coordenadas: **pertencer a uma
cadência não é uma dimensão do dado medido**.

### 2. Separar duas cadências

**Núcleo recorrente**: casos representativos e baratos de caminhos, camadas, compressão,
hierarquia, tipos, candidates/columns e acelerador. Excluir do ciclo frequente B4 em escala cheia e
os extremos como `R6e5`. Executar em blocos curtos, cada qual com calibradores, sentinela inicial e
final e aceite térmico próprio.

**Campanha de caracterização**: B4 em escala representativa, `R6e5` e memória da árvore de
processos. Rodar uma vez para o `.8` e repetir no `.9` quando uma mudança tocar concorrência,
memória, multiprocessamento ou em um marco de release. A campanha continua comparável, mas não
penaliza cada ciclo de desenvolvimento.

Para B4, usar um tier explícito de baixa repetição, declarado como comparabilidade fraca e MDE alto,
é preferível a reduzir silenciosamente a escala. Se a decisão depender de uma diferença pequena,
abre-se uma medição focal com mais amostras; não se aumenta toda a matriz por antecipação.

### 3. Tratar B0 como envelope

Pins, sondas, calibradores e sentinelas validam o run; não são workloads de produto. Devem aparecer
no resumo do run, com status próprio, mas fora da contagem de casos comparáveis. Isso evita registros
`pendente` artificiais e deixa claro quando a infraestrutura, e não o TCF, invalidou uma rodada.

### 4. Tornar runs longos retomáveis

Persistir cada registro assim que for concluído, com escrita atômica ou JSONL append + flush. Na
retomada, aceitar somente registros cujo hash de matriz, plano, código e ambiente coincida; caso
contrário, iniciar novo artefato. O resumo final deve distinguir `completo`, `interrompido` e
`termicamente-reprovado`.

### 5. Isolar memória multiprocesso

`psutil` pode ser dependência opcional de desenvolvimento do harness, nunca do pacote TCF. As duas
células `process-tree` pertencem à campanha de caracterização e ficam `não-medidas` quando a sonda
não estiver instalada; isso não bloqueia o núcleo recorrente.

## Ordem de execução sugerida

1. Persistência incremental e estado de retomada.
2. Esquema do plano + hash no manifesto + recusa de protocolo desigual no comparador.
3. Classificação dos casos entre núcleo recorrente e campanha, sem apagar a matriz-mestra.
4. Baseline `.8` do núcleo em blocos; aceitar apenas blocos abaixo do limiar térmico.
5. Campanha `.8` separada, com B4 na escala representativa e tier explícito.
6. `process-tree` depois da sonda opcional; não segurar os demais resultados por essa ausência.

## Critérios que podem refutar este parecer

- Se B4, com tier explícito baixo, ainda impedir blocos termicamente válidos, subdividir por dataset
  e eixo (`internal`, `test`, `interaction`) antes de reduzir a escala.
- Se a variância de B4 tornar o MDE declarado incapaz de separar as decisões relevantes, aumentar
  amostras apenas nas células inconclusivas.
- Se o núcleo recorrente ainda ultrapassar a janela térmica observável, mover os próximos casos mais
  caros para a campanha com base no tempo medido, não no nome do bloco.
- Se calibradores e sentinelas não explicarem a variação entre blocos aceitos, a normalização atual
  não sustenta claims `.8` versus `.9`; nesse caso, exigir replicações em dias/blocos independentes.

## Decisão solicitada ao owner

Adotar ou vetar o **split por cadência com matriz-mestra preservada**. Se adotado, a implementação
deve mudar somente o harness `scripts/bench_perf/`; nenhuma otimização de `src/tcf/` é justificada
pelo run interrompido.
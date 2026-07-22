# Diagnóstico do baseline: fases 1–3 e entrega do `.8`

**Escopo**: avaliação dos commits `4e08aef` (fase 1), `24d2bda` (fase 2), do instrumento
vigente e do desenho proposto para a fase 3. Este parecer trata da confiabilidade da evidência de
fechamento do `.8`; otimização, revisão de algoritmo e exploração de performance pertencem à `.9`.

## Síntese

As fases 1 e 2 seguiram uma direção útil e proporcional ao problema observado. A fase 1 impede que
uma execução interrompida perca todo o trabalho e separa infraestrutura de casos comparáveis. A
fase 2 impede comparação por célula quando `tier` ou número de amostras divergem e detecta matriz
diferente. Nada nesses commits indica regressão do TCF ou necessidade de alterar `src/tcf/`.

O ponto a corrigir antes de aceitar uma referência do `.8` é simples: algumas condições chamadas
de inválidas ainda são apenas avisos. Em teste dirigido, matriz divergente e candidato
`termicamente-reprovado` produziram veredictos e terminaram com código `0`; o autoteste de um run
termicamente reprovado também imprimiu `PASSOU`. A fase 3 deve fechar esse contrato e congelar uma
referência curta, reproduzível e suficiente. Não precisa transformar o closeout em nova pesquisa.

## Fase 1 — persistência, retomada e envelope

### Importância alta — manter

- **Persistência incremental e `--resume`** resolvem diretamente a perda das 84 medições da
  execução interrompida. Validar Git e matriz antes de retomar evita misturar código ou casos
  diferentes no mesmo artefato.
- **B0 fora dos comparáveis** é conceitualmente correto: calibradores, sentinelas e gates não são
  workloads de produto e não devem contaminar os veredictos de performance.

### Importância alta — ajustar no aceite da fase 3

- O resumo usa `completo` quando existe quantidade suficiente de registros, não quando todos os
  casos obrigatórios são aceitáveis. Um plano pode terminar com `pendente`, `rejeitado` ou
  `rt-quebrado` e ainda parecer completo. A fase 3 deve declarar os status permitidos por caso:
  caso obrigatório só aceita `ok`; caso opcional pode aceitar `não-medido`/`pendente` com motivo;
  `rt-quebrado` e `erro` sempre invalidam o bloco.
- O processo hoje retorna falha somente para status `erro`. Para evidência do `.8`, também deve
  retornar falha quando houver `rt-quebrado`, ausência de caso obrigatório, bloco incompleto ou
  reprovação térmica.
- A retomada entre sessões combina registros antigos com calibradores e drift apenas da sessão
  final. Isso já está reconhecido no resumo. A fase 3 não deve tentar fabricar um único aceite
  térmico para esse conjunto: cada bloco/sessão recebe seu próprio resumo e aceite.

### Importância média — esclarecer, sem reabrir B0

Os oito casos B0 agora retornam `envelope` antes de executar. Portanto, os três “pins” não validam
bytes e a “sonda” não testa heap/RSS nesse caminho. Não é necessário recolocá-los no benchmark: os
pins canônicos e o round-trip já têm gates próprios. Para o closeout, basta registrar no índice da
fase 3 o commit e o resultado dos testes de regressão/real-world executados separadamente. O nome
“envelope” não deve ser interpretado como se esses oito casos tivessem realizado tais gates.

## Fase 2 — guarda do comparador

### Importância alta — manter

- Recusar por célula `tier` ou `n` diferentes é uma política conservadora adequada. Reamostrar os
  vetores crus pode ser estudado depois; não agrega valor ao fechamento do `.8`.
- Conferir o hash da matriz antes do join é necessário e está no nível certo: o custo de SHA-256
  sobre esse arquivo é irrelevante para a duração do benchmark.

### Importância alta — corrigir antes do baseline aceito

O comparador precisa **falhar fechado**. Se matriz ou plano divergir, se faltar resumo, se um run
estiver parcial/termicamente reprovado ou se a intenção dos runs for diferente, ele deve:

1. não emitir `MELHOR`, `PIOR`, `IGUAL` ou `RUIDO`;
2. devolver código de saída não zero;
3. listar a causa de forma objetiva.

Avisar e continuar é útil durante desenvolvimento, mas não serve como guarda da evidência. O
autoteste também deve falhar quando o próprio run não for aceito, mesmo que os arquivos sejam
idênticos.

### Importância média — teste mínimo

Não há testes em `tests/` para as fases 1 e 2. Antes da rodada definitiva, valem poucos testes de
contrato, sem ampliar a suíte em excesso:

- retomada compatível continua; Git/matriz/plano divergente aborta;
- linha final truncada falha com mensagem ou é descartada explicitamente;
- `rt-quebrado`/obrigatório ausente invalidam o bloco;
- matriz/plano/status inválido fazem o comparador retornar não zero;
- comparação do mesmo artefato aceito continua retornando zero.

## Fase 3 — recomendação de execução

### 1. Preservar a matriz-mestra e adicionar planos

Não dividir nem regenerar `cases.json`. Criar planos versionados é suficiente e mantém o histórico:

- `núcleo`: casos baratos e representativos usados como referência recorrente;
- `campanha`: B4 em escala representativa, extremos como `R6e5` e memória multiprocesso;
- `smoke`: validação rápida do instrumento, sem valor probatório de performance.

Cada plano deve declarar `plan_id`, lista/ordem de `case_id`, tier ou política de repetição,
frequência de sentinela, status obrigatórios/opcionais e versão do protocolo. O manifesto registra
o hash completo do plano e o comparador exige o mesmo hash e a mesma intenção nos dois lados.

### 2. Fazer de cada bloco a unidade de validade

Cada bloco deve ter arquivo e resumo próprios, com calibradores e sentinela inicial/final. Um índice
da rodada apenas aponta para os blocos e seus estados; não combina drift de sessões diferentes. Se
um bloco for reprovado termicamente, repete-se somente aquele bloco.

Não é preciso adivinhar agora uma duração universal de 20 minutos. Começar com blocos curtos e
mover um caso para a campanha quando ele dominar o tempo é suficiente. A decisão deve usar o tempo
observado, não uma teoria sobre o nome do bloco.

### 3. Congelar primeiro o núcleo do `.8`

O artefato de maior valor para a entrega é um baseline do núcleo que:

- venha de commit limpo e identificado;
- use o ambiente que representa a distribuição, com acelerador Cython ativo quando o caso estiver
  rotulado `cython`;
- tenha todos os casos obrigatórios `ok`, round-trip preservado e blocos termicamente aceitos;
- carregue hashes da matriz e do plano;
- seja acompanhado pelos gates canônicos do `.8` e pelo smoke de instalação/uso do pacote.

Os smokes observados foram gerados com árvore suja e `cython_accel: false`; são adequados para
testar o harness, não para virar referência de performance da distribuição. O runner deve abortar,
em vez de apenas avisar, quando uma rodada probatória estiver suja ou quando o modo real do
acelerador divergir do vetor declarado.

### 4. Tratar a campanha como complemento, não como trava automática

B4 e os extremos continuam valiosos para deixar uma fotografia do `.8`, principalmente para a
comparação futura com `.9`. Use escala representativa e poucas repetições declaradas, com MDE alto;
se uma célula ficar inconclusiva, refine apenas essa célula.

A campanha cara não precisa bloquear a publicação do `.8` se o núcleo, os gates de correção, a
documentação, a wheel e o clean-room smoke estiverem fechados. Ela só vira gate se revelar quebra
de round-trip, instalação/uso ou afirmação pública incorreta — os critérios de preempção já adotados
no closeout.

## Ordem sugerida por significância

1. **Alta** — fazer o comparador falhar fechado para matriz/plano/status inválido.
2. **Alta** — definir aceite por plano: obrigatórios, opcionais e status que invalidam o bloco.
3. **Alta** — versionar plano e registrar seu hash/intenção no manifesto.
4. **Alta** — rodar o núcleo em blocos independentes, em commit limpo e no modo Cython declarado.
5. **Alta** — anexar os gates canônicos e o smoke de distribuição; não presumir que B0 os executou.
6. **Média** — adicionar os poucos testes de contrato das fases 1 e 2.
7. **Média** — rodar a campanha cara uma vez como fotografia para a `.9`, sem otimizar o `.8` a
   partir dela.

## Notas de ROI pequeno — registrar e seguir

- Recuperação automática de uma última linha JSONL truncada; fail-loud já basta para o `.8`.
- Trocar SHA-256 por xxHash/BLAKE3; o hash atual é one-shot e não está na hot path.
- Usar hashes completos em cada registro em vez dos 12 caracteres já acompanhados pelo manifesto;
  melhora defesa teórica, sem efeito prático no closeout.
- Instalar `psutil` para as duas células `process-tree`; pode ficar opcional na campanha.
- Reamostrar vetores para comparar tiers diferentes, refinar percentis ou normalização térmica.
- Lazy input, streaming, revisão de OBAT/HCC, paralelismo e mudanças de algoritmo/formato.

Esses itens podem ser revisitados na `.9` ou perto do 1.0. Nenhum deles justifica atrasar a entrega
do `.8` depois que o baseline do núcleo e os gates de release estiverem aceitos.
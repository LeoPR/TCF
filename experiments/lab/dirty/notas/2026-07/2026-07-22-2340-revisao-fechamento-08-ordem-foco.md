# Revisão do fechamento do `.8` e ordem de foco [probatório]

**Data**: 2026-07-22 23:40. **Corte avaliado**: `b0e3bf1`.
**Natureza**: parecer consolidado para releitura. As direções atribuídas ao owner são
dispositivas; as conclusões técnicas e a ordem abaixo são recomendações probatórias e não
substituem ADRs, tickets ou código.

## Regra de leitura usada nesta revisão

Esta revisão lê a literatura do estado atual para o passado:

1. decisão mais recente do owner;
2. código e testes vigentes;
3. ADR aceito e ticket dispositivo, já consideradas erratas posteriores;
4. relatório probatório mais recente;
5. artefato histórico apenas como proveniência.

Um registro antigo não volta a ser conclusão só porque ainda contém uma frase ou campo que foi
superado. Quando o histórico precisa permanecer intacto, a correção deve aparecer como errata ou
bloco de supersessão na entrada atual, de forma que ferramentas e revisores não promovam a camada
antiga a estado vigente.

Fontes recentes que controlam este parecer:

- [baseline first-order](2026-07-22-2207-baseline-perf-08-first-order.md);
- [direções pós-baseline](2026-07-22-2225-direcoes-pos-baseline-discutir-depois.md);
- [inventário de funcionalidades](2026-07-22-2230-funcionalidades-08-3-tiers.md);
- [plano de pré-faxina](2026-07-22-2235-prefaxina-08-plano.md);
- [STATUS](../../../../../STATUS.md) e
  [T-REL-08-CLOSEOUT](../../../../../tickets/T-REL-08-CLOSEOUT.md), subordinados às
  decisões e erratas posteriores quando seus blocos de 12/07 divergem delas.

## Síntese corrigida

O núcleo `.8` não apresenta falha funcional geral observada: a suíte completa passou com
`861 passed, 3 skipped`, e os recortes de hierarchy, view, paralelismo e gates canônicos também
estão verdes. Isso não significa que a superfície esteja pronta para release.

Há quatro trabalhos pré-`.9`:

1. retirar a falsa porta pública `encode_hierarchical` e concluir a API única `encode`/`decode`;
2. revisar natures como linguagem estrutural de códigos, começando por CNPJ e generalizando o
   gabarito de CPF para CPF/CNPJ/IP e futuros códigos;
3. fechar as bordas funcionais e a fotografia first-order de `view`, sem expandir seu escopo;
4. reconciliar documentação e só então testar o protótipo completo em clean room.

O `.9` continua reservado para otimização algorítmica, paralelismo, memória e simplificação sobre
uma base já organizada. API e desacoplamento que sabemos estar errados não devem atravessar essa
fronteira.

## 1. Performance: baseline aceito, sem nova rodada térmica

### Estado correto

O rótulo `termicamente-reprovado` veio de um gate binário intra-run que se mostrou inadequado para
o propósito da medição. A avaliação atual usa o que a literatura pede para esta pergunta:
invocações independentes e variabilidade entre runs. O piloto B1 em sete invocações obteve CV
entre-runs mediano de 3% e máximo de 5%, suficiente para ordem de grandeza e localização de pontos
quentes no protótipo `.8`.

Portanto:

- o baseline first-order está **aceito para seu propósito declarado**;
- não há ação de rerun motivada pelo antigo gate térmico;
- não se deve usar o campo histórico para desqualificar a evidência atual;
- o baseline não promete precisão de poucos pontos percentuais nem comparação cross-machine sem
  calibradores.

O achado vigente permanece: crescimento puro por linhas aproximadamente linear e concentração do
problema no canto extremo `R x C`, que é entrada para otimização na `.9`.

### Higiene ainda necessária

Há uma inconsistência mecânica: o manifesto bruto ainda contém `status:
termicamente-reprovado`, enquanto o README e o parecer vigente aceitam a rodada pela análise
entre invocações; o comparador fail-closed ainda interpreta apenas o campo antigo.

Isto não pede novo benchmark. Pede tornar a adjudicação atual legível por humanos e ferramentas:

1. preservar o valor bruto como resultado do gate antigo, sem apagar a proveniência;
2. registrar uma adjudicação explícita, por exemplo `accepted-first-order`, com propósito,
   critério, referências e decisão do owner;
3. fazer o comparador consumir a adjudicação vigente, mantendo o fail-closed para ausência de
   decisão ou incompatibilidade de protocolo;
4. explicar no README do snapshot que `runner_thermal_status` não é o status metodológico final.

Isso encerra a contradição sem reescrever medição nem ressuscitar o gate refutado.

## 2. API: remoção obrigatória antes da `.9`

### Diagnóstico

`encode_hierarchical` não é uma segunda API de produto. É uma porta de implementação que vazou.
Sua presença pública força o caller a conhecer a organização interna exatamente onde `decode` já
faz roteamento pelo wire. O contrato desejado para dados é:

```python
blob = encode(data, ...)
data = decode(blob)
```

Não cabe deprecar ou carregar essa porta até a `.9`. O pacote ainda é pré-1.0, a exposição foi
identificada como erro e a correção é requisito de organização da `.8`.

### Precedência proposta para `encode`

A regra conservadora é preservar os dois domínios flat byte-canônicos e enviar o restante do
domínio hierárquico aceito para `.8H`:

| entrada | rota default | motivo |
|---|---|---|
| `list[str]` não vazia | single flat órfão | preserva API e bytes existentes |
| `dict[str, list[str]]` retangular, com ao menos uma linha | multi `#TCF.8M` | preserva tabela, `view` e bytes existentes |
| `[]`, `{}`, objeto com escalares/objetos, `list[dict]`, arrays tipados ou ragged aceitos pelo `.8H` | `#TCF.8H` | preserva tipo e estrutura |
| entrada fora dos domínios declarados | fail-loud na fronteira | não stringificar estrutura por acidente |

Há duas ambiguidades reais a congelar em teste:

- `list[int|bool|None]` hoje pode ser stringificada pelo flat, mas a rota coerente com tipos é
  `.8H`; a mudança precisa ser declarada como correção de contrato pré-1.0;
- um `dict[str, list[str]]` retangular também pode ser lido como objeto cujos campos são arrays.
  A precedência flat preserva compatibilidade e o `decode` devolve a mesma forma Python. Se houver
  necessidade comprovada de forçar o layout, ela deve ser um modo de `encode`, não outra função.

### Trabalho completo da migração

1. Escrever primeiro uma tabela de dispatch com casos positivos, ambíguos e inválidos.
2. Fazer `encode` rotear para um helper hierárquico privado.
3. Unificar `side_outputs=` no caminho hierárquico; eliminar a porta separada
   `encode_hierarchical_so`.
4. Definir quais kwargs valem em cada layout. Knob flat recebido por `.8H` deve falhar alto ou ter
   semântica documentada, nunca ser ignorado silenciosamente.
5. Manter natures de folha no mesmo `encode`, com paths documentados.
6. Remover `encode_hierarchical` de `tcf.__all__`, do namespace público e da implementação como
   nome sem underscore. Não manter alias de compatibilidade.
7. Migrar toda a suíte e os labs vivos para `encode`; os testes em massa de hierarchy passam a
   provar o caminho público real.
8. Atualizar o contrato de API pinado e a documentação no mesmo conjunto de mudanças.

Arquivos que obrigatoriamente participam da reconciliação:

- `src/tcf/__init__.py`, `encoder.py` e `hierarchical.py`;
- `tests/test_regression_v1_baseline.py` e suites hierárquicas;
- ADR-0033, `docs/reference/json-equivalence.md` e README EN/PT;
- tickets de weld/paridade que ainda nomeiam a função de suporte como API.

O wire `.8H` e sua capacidade não são reabertos. O que muda é a porta de entrada.

## 3. Natures: RT funcional não equivale a fechamento estrutural

### Estado correto

CPF/CNPJ/IP estão funcionais no sentido mínimo:

- encode/decode preservam round-trip no domínio declarado;
- o marcador self-describing funciona quando a nature vence;
- o FLOOR escolhe o menor blob e impede regressão operacional contra o baseline.

Isso não prova que a representação do código seja estruturalmente adequada nem que a análise de
compressão esteja encerrada. O FLOOR é um chão de segurança; ele não é o teto do spec.

O número antigo `+7339 B` descreve a forma absoluta do CNPJ competindo mal com a estrutura
inter-linha. Depois do FLOOR, ele não descreve o resultado público escolhido. Também não deve ser
convertido na conclusão oposta de que o modelo atual está bom: ele é evidência de que a forma
absoluta perde informação compressível de ordem, subcampo e cadência.

Hipótese a testar: CNPJ deve ser tratado como composição de subcódigos e transformação de coluna,
não apenas como valor isolado convertido para uma base densa. A mesma lente deve ser aplicada a
CPF, IP e qualquer futuro código estruturado.

### Lab obrigatório de revisão estrutural

Abrir um dirty lab novo, sem tocar o core, obedecendo ao layout canônico
`inputs/`, `intermediates/`, `outputs/`, `README.md`, `result.md`, `run.py` e
`datasets-provenance.md`.

Objeto primário: CNPJ real da Receita já existente em `Z:/tcf-data/`. Controles: CPF nos regimes
disponíveis e IP, sempre rotulando sintéticos como dados construídos para a hipótese. Não baixar
dado novo para repetir infraestrutura existente.

Matriz mínima por natureza:

| eixo | variações mínimas |
|---|---|
| ordem | fonte, embaralhada com seeds, agrupada/clusterizada |
| escala | amostra pequena, média e população disponível quando viável |
| forma | sem spec, spec absoluto atual, derive-only, split de campos, delta do corpo, delta por campo, forma mista |
| unidade | por valor stateless e por coluna stateful |
| escolha | candidato forçado para diagnóstico e competição total pelo blob |
| evidência | bytes total/header/body, modo vencedor, tempo, memória, apply-rate e RT |

Cada célula deve produzir artefato `.tcf` e round-trip diffável. Bytes só entram no relatório se
o RT correspondente passou. Resultados por coluna servem para diagnóstico; a decisão usa o blob
completo, incluindo header e identidade do spec.

### Checklist generalizado de uma nature de código

O gabarito do CPF deve virar checklist explícito para todas as natures:

1. léxico: máscara, alfabeto, largura fixa/variável e zeros significativos;
2. segmentação: campos e subcódigos posicionais;
3. validação: algoritmo e escopo dos dígitos verificadores;
4. derivação: informação reconstruível que não precisa viajar;
5. distribuição por campo: cardinalidade, skew e entropia;
6. estrutura inter-linha: ordem, delta, cadência, agrupamento e repetição;
7. candidatos físicos: raw, base-N, dict, split, delta e composição;
8. estado: transformação por valor versus transformação por coluna;
9. inversa: ordem exata de reconstrução, fail-loud e propriedade de RT;
10. aplicabilidade: quando não usar, custo do marcador e competição pelo blob completo;
11. validade ecológica: real versus sintético, com viés declarado;
12. custo: encode/decode e memória, não apenas bytes.

### Linguagem/compilador como saída arquitetural

O compilador atual é útil, mas modela apenas um DSL flat e stateless: template, corpo, check-fn
nomeada e base absoluta. Ele não expressa segmentação semântica, alternativas físicas, estado de
coluna, delta, ordem de inversão ou escolha competitiva.

A consolidação pré-`.9` deve definir uma IR declarativa de spec com pelo menos:

- template e campos nomeados com largura/alfabeto;
- regra de validação e campos deriváveis;
- preservação explícita de zeros;
- transformações candidatas por campo e pela coluna;
- dependências e ordem da inversa;
- requisitos de estado/ordenação;
- política de fallback/competição;
- identidade/versão do spec no wire ou contrato externo;
- geração de property tests de RT no compile-time.

O lab deve primeiro provar quais primitivas são necessárias. Só depois o compilador é ampliado.
A `.9` pode otimizar a execução dessas primitivas, mas não deve começar tendo de inventar a
linguagem e desfazer acoplamento ao mesmo tempo.

### Saída esperada do lab

- classificação do CNPJ atual: o que é funcional, o que é limitação da forma e o que é bug;
- comparação honesta das formas em ordem e desordem;
- conjunto mínimo de primitivas que generaliza CPF/CNPJ/IP;
- IR/DSL proposta e lacunas do compilador atual;
- decisão separada entre o que precisa entrar na organização da `.8` e o que é otimização da `.9`;
- nenhuma claim `confirmada-empirica` sem cumprir o gate de evidência do projeto.

## 4. View, paralelismo e teste em massa

### Paralelismo

Pode ser fechado como correto no domínio flat atual:

- serial e paralelo produzem bytes idênticos;
- round-trip está coberto;
- resultados e `SideOutputs.per_col` voltam à ordem original;
- workers explícitos, caps por número de colunas e fallback serial estão pinados.

Não há sinal para reabrir a implementação na `.8`. Tuning de workers, orçamento global do host,
porção serial e paralelismo intra-coluna pertencem à `.9`.

Depois da API unificada, basta repetir a matriz pública representativa e incluir `parallel=2` no
clean room. O caminho `.8H` não deve prometer paralelismo enquanto não o implementar.

### View

L1-L4 podem fechar funcionalmente dentro do contrato atual `#TCF.8M`. Não ampliar para `.8H`,
single, SQL, joins ou QueryPlan durante o closeout.

Faltam dois fechamentos pequenos:

1. testes negativos explícitos de `view` contra single órfão/stamped, `.8H` e discriminador
   desconhecido, alinhados ao texto da referência;
2. fotografia first-order própria, porque o baseline atual mede encode e não mede consultas.

O baseline de view deve comparar correção com `decode` e medir ao menos `count`, `select`,
`where`, agregação e group-count nos modos raw/dict/split/tcf, registrando latência e bytes
materializados. L5 permanece experimental. Essa fotografia prepara a `.9`; não é convite para
otimizar durante a `.8`.

### Massa

Não há ROI em repetir toda a campanha hierárquica pela função antiga. Após o novo dispatch,
reexecutar o corpus existente pela única porta pública `encode` é necessário e suficiente para
provar que a migração não perdeu capacidade.

A massa adicional útil fica concentrada em:

- lab de natures, onde ordem e população são parte da hipótese;
- uma tabela real larga para serial versus `parallel=2/4/8`, se ainda for desejada confirmação
  populacional do ambiente;
- clean room do artefato final.

## 5. Documentação: errata imediata e F6 final

O estado atual tem afirmações contraditórias que já causam retrabalho. Não é adequado esperar o
release para sinalizar tudo, mas também não convém reescrever documentação pública duas vezes.

### Passada A: supersessão imediata, pequena

Adicionar blocos curtos no topo das fontes vivas:

- baseline: decisão entre-runs supersede o gate térmico intra-run;
- CNPJ: `+7339 B` é resultado da forma absoluta pré-FLOOR, não do resultado público atual, e a
  modelagem estrutural está sob revisão;
- API: remoção de `encode_hierarchical` é bloqueador pré-`.9`;
- versão: metadata e READMEs já estão em `0.8.0/#TCF.8`; não repetir o snapshot stale do survey.

Alvos prioritários: `STATUS.md`, `T-REL-08-CLOSEOUT`, `T-QA-8`, `T-SPEC-STATUS-08`, o survey de
22/07 e o README do snapshot de performance. Artefatos históricos permanecem intactos e passam a
apontar para a errata atual.

### Passada B: F6 depois do protótipo completo

Após API e decisão do lab:

- README EN/PT usam apenas `encode`/`decode` para dados flat e hierárquicos;
- ADR-0033 recebe emenda que distingue wire/capacidade da porta interna removida;
- referência de equivalência JSON e exemplos migram para `encode`;
- docs de natures separam RT, FLOOR e qualidade estrutural, sem claim ampla de ganho;
- referência de `view` explicita apenas `#TCF.8M` e seus erros de fronteira;
- CHANGELOG descreve a superfície final realmente embarcada.

## 6. Clean room do protótipo completo

O smoke antigo é pré-verificação, não gate final. O teste deve ocorrer somente depois da API, da
decisão de natures, dos testes de view e da documentação F6.

### Artefatos

- construir sdist e wheel a partir de árvore limpa e commit candidato;
- instalar cada artefato em venv novo, fora do repositório, sem `-e`;
- provar por `tcf.__file__` que o import vem do ambiente instalado;
- testar fallback puro e acelerador Cython quando o artefato/plataforma o oferecer;
- inspecionar o conteúdo do wheel/sdist e metadata/versionamento.

### Matriz de caminho feliz

| caminho | prova mínima |
|---|---|
| single flat | órfão, stamped, nature que vence/perde, RT |
| multi flat | raw/dict/split/tcf, serial e `parallel=2`, bytes idênticos, RT |
| hierarchy | dataset, objeto, array, raiz vazia/generalizada, tipos/null/ragged, nature, SideOutputs |
| API | somente `encode`/`decode` como portas de codec; `encode_hierarchical` ausente |
| view | connect/select/filter/aggregate em `.8M`; rejeição explícita dos demais wires |
| Cython | pure/compiled byte-equivalentes nos gates existentes |
| pacote | versão, README/metadata e imports correspondem ao candidato |

O smoke deve executar a suíte de contrato instalada ou um script versionado que reutilize os
mesmos vetores. Comandos avulsos não bastam como evidência de release.

## Ordem recomendada de foco

| ordem | trabalho | gate de saída |
|---:|---|---|
| **0** | persistir este parecer | decisões e divergências reunidas para releitura |
| **1** | errata curta nas fontes vivas | nenhuma leitura atual promove gate térmico, caveat CNPJ ou API antiga a conclusão vigente |
| **2** | fechar contrato de dispatch e remover `encode_hierarchical` | todos os caminhos usam `encode`; API, testes e ADR coerentes; gates flat byte-verdes |
| **3** | executar lab estrutural de natures e desenhar IR/DSL | CNPJ revisto, checklist generalizado e fronteira `.8`/`.9` decidida com RT |
| **4** | fechar `view` e validação focal de paralelismo/massa | bordas pinadas, baseline first-order de query e corpus hierarchy pela API real |
| **5** | F6 documental final | README EN/PT, referências, tickets, ADR e CHANGELOG descrevem o mesmo protótipo |
| **6** | build + clean room completo | wheel/sdist instaláveis; matriz de caminho feliz verde fora do repo |
| **7** | suíte final + gates canônicos + decisão do owner | candidato `.8` pronto para tag, sem commit/tag/push automático |
| **8** | abrir `.9` | somente otimização, paralelismo, memória e simplificação sobre contratos já limpos |

## Fechamentos e bloqueios resultantes

### Pode ser considerado fechado

- baseline de encode `.8` como fotografia first-order aceita;
- capacidade semântica/wire do `.8H`;
- correção funcional do paralelismo flat;
- RT operacional das natures atuais e proteção never-worse do FLOOR;
- versão de projeto `0.8.0/#TCF.8` já aplicada no repositório.

### Continua bloqueando a passagem para `.9`

- API única ainda não implementada;
- lab/contrato estrutural de natures ainda não concluído;
- fronteiras e baseline first-order de `view` ainda não fechados;
- documentação viva ainda contraditória;
- clean room ainda baseado em protótipo anterior.

### Não deve sequestrar o closeout

- nova rodada do baseline motivada pelo gate térmico superado;
- suporte de `view` a `.8H`, SQL ou QueryPlan;
- tuning de workers e paralelismo intra-coluna;
- otimização OBAT/HCC do canto `R x C`;
- hardening amplo de blob deliberadamente corrompido;
- expansão indiscriminada de catálogo de specs antes da linguagem e de dados adequados.

## Decisões que precisam de confirmação antes de tocar `src/tcf`

1. precedência flat exata no dispatch automático, especialmente `list` tipada e
   `dict[str, list[str]]` ambíguo;
2. nome e semântica de eventual modo de layout dentro de `encode`;
3. comportamento fail-loud de kwargs sem sentido para `.8H`;
4. fronteira da IR/DSL de natures que deve estar consolidada na `.8`, deixando apenas execução
   otimizada para a `.9`.

Esta nota não autoriza edição do core por si só. A execução de cada mudança em `src/tcf/` continua
dependendo de aprovação explícita e dos gates definidos em `AGENTS.md`.
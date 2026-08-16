# STATUS — TCF (compendio sempre-atualizado)

> ## 🎯 ESCALA DE VERIFICAÇÃO (decisão de processo, 2026-08-07)
>
> **E0** ingênuo · **E1** round-trip · **E2** assimetria · **E3** fail-loud barato ·
> **E4** canonicidade · **E5** adulteração ("homem no meio").
>
> **`.8` = E1/E2 obrigatórios + E3 (custa zero) + E4 quando trivial. `.9` = E4
> sistemático + E5 opt-in.** Evidência: **4 dos 6 bugs catastróficos do ciclo eram
> E1/E2** — os únicos alcançáveis por `encode→decode`. Orçamento de auditoria vai pra
> round-trip e assimetria, não pra wire escrito à mão. Ressalva do próprio `malloc`:
> ele não pré-verifica, mas devolve `NULL` — E3 fica no `.8` porque falhar CORRETAMENTE
> custa zero no caminho feliz.
>
> Detalhe + classificação das 17 checagens do bN:
> [`escala-de-verificacao-e-fechamento-do-bn`](experiments/lab/dirty/notas/2026-08/2026-08-07-escala-de-verificacao-e-fechamento-do-bn.md).

> ## 🔖 PENDENTES NOMEADOS — não deixar cair no esquecimento
>
> Tickets criados pelos welds de 2026-07-26/27. **Nenhum é bloqueante; todos são ganho
> medido esperando encaixe.** Detalhe em ADR-0036 §aberto e no
> [guia de encaixe pro `.9`](experiments/lab/dirty/notas/2026-07/2026-07-27-guia-de-encaixe-para-o-dot9.md).
>
> | ticket | ganho medido | por que ainda não |
> |---|---|---|
> | ~~`T-BN-TIPADO`~~ | **SOLDADO 2026-08-07** | `#TCF.8nB<w><n>` — a MESMA forma do `#TCF.8bB` (ADR-0039), não grafia nova. Medido n=200: `int` 0/1 **608→55 B**, `int` 0..3 **604→93 B**, `float` **612→59 B**. O decode reescreve o cabeçalho e DELEGA ao `decode_bn`, herdando todas as checagens. De quebra fechou a canonicidade da GRAFIA numérica (5 famílias colidiam: `01`/`1.50`/`+1`/`1e3`/`1_0`) no `_cast_tipo`, que serve as DUAS rotas. Suite 1192. |
> | **`T-BN-LOTE`** | ~1 B/coluna | falta so' o opt-in de EMISSAO; o modo `C` já é decodável. **Não é decisão em aberto** (owner 2026-08-07): os dois modos existem, `B` é stream-friendly e é o default, `C` só quando declarado. Forma mínima `encode(data, bn_modo="C")`, ou cair de um perfil (`T-PERFIS-MACRO`) — um knob por mecanismo não escala |
> | **`T-UM-CAMINHO-SO`** | explica **4 tickets abertos** de uma vez; sem numero proprio (e' causa, nao sintoma) | direcao do owner 2026-08-12: *"o single-col e' so' uma convencao humana; no codigo ele tem que ser algo perto de um multi-column que tem apenas uma coluna — o codigo e' o mesmo pra um ou mais"*. EVIDENCIA desta rodada: as 4 divergencias achadas tem a MESMA forma (capacidade existe num caminho e nao no outro) — bN no `min()` (single tem, `.8M` nao: 13,8%), split `%` (`.8M` tem, single nao: -35/-63%), `view` lazy (abre `.8M`, recusa as 11 formas nao-M), rota plena no candidato da nature (~5,7%). Quatro tickets, quatro classes aparentes, UMA causa: dois caminhos de codigo, entao cada mecanismo novo precisa ser soldado DUAS vezes e na pratica e' soldado uma. Explica por que a classe 'o candidato existe e a rota nao consulta' ja' reincidiu 5x. NAO e' unificar a API (as duas formas de chamada ficam) nem o formato (single-col congela no 1.0, ADR-0030) — e' o caminho INTERNO de decisao. **SEQUENCIAMENTO (owner): depois dos tipos** — o ciclo atual fixa UMA coluna; multi-col e hierarquia vem depois. Nota: `2026-08-12-single-col-e-multi-col-de-uma` |
> | **`T-BN-MULTICOL`** | **13,8% na mesa em dataset real** (adult: soma de single-col c/ bN = 2.784 B vs .8M = 3.231) | MEDIDO 2026-08-12 (colateral da pesquisa de pulsos): o `min()` por coluna do `_encode_multi` NAO consulta o bN — **5a ocorrencia** da classe 'o candidato existe e a rota nao consulta' (T-BN-TIPADO, FLOOR-da-nature, T-SPLIT-SINGLE-COL, T-NATURE-CANDIDATO-BN, e agora o .8M). bN como 5o candidato do min() por coluna; classe floor-never-worse que o projeto solda em `.8`. RESTRICAO do view (mesma pesquisa): marcador de modo novo no meta = **pontuacao, nunca letra** (`B178=col` e' HEX-PARSEADO CALADO pelo _parse_meta) + solda simetrica _parse_meta+view |
> | **`T-BN-LARGURA-VARIAVEL`** | slots desperdiçados em `k` = 3, 5, 6, 7 | largura fixa arredonda pra cima |
> | **`T-BN-GZIP`** | — | o gzip encolhe muito o ganho do bN (medido no estudo multi-col) |
> | **`T-POLARIDADE-FUSE`** | 1 varredura a menos, **byte-neutro** | fundir no laço que `_escape_lit` já roda |
> | **`T-GATES-ANTES`** | CPU, **byte-neutro** | avaliar gates C1-C7 antes de materializar candidatos |
> | **`T-SEQRLE-INCREMENTAL`** | CPU, **byte-neutro** | janela de 2 em vez de re-varredura |
> | **`T-SPEC-L0L1`** | detecção automática de spec | **muda byte**; CPU piloto |
> | **`T-FEATURES-STREAM`** | perfil parcial em `k=20` | destrava decisão precoce |
> | **`T-OBAT-TRIGRAMA`** | CPU | bucket por `min_len` em vez de 3 fixo |
> | **`T-B64-TOLERANTE`** | recuperacao com prova | `on_noncanonical='error'\|'warn'` no `decode`, default `error`; SO' para extensao / padding a mais / bits mortos sujos — as 3 classes onde o valor recuperado e' PROVADAMENTE o mesmo. Soldar so' se houver caso de uso real de recuperacao de arquivo |
> | **`T-B64-BITS-MORTOS`** | trocar O(n) por O(1) | a re-codificacao custa ~0,17%; checar so' os bits mortos do ultimo char da' a MESMA garantia em O(1). So' vale se o custo um dia importar — medido em `2026-08-06-2250` |
> | **`T-GRAFIA-CHECKLIST`** | previne a 6a recorrencia | a assimetria escapar/desescapar ja' apareceu **5 vezes**; a frase no ADR nao impediu — o teste impede |
> | **`T-DENSO-PADDING`** | 1-2 B em ~2/3 dos wires densos | os densos `b1` e `b2` emitem padding `=`, o bN nao; o padding e' deduzivel de `n` e `w` (vale pros dois modos, ADR-0037) |
> | **`T-FLOAT-SLOTS`** | NaN/±Inf hoje é fail-loud | falta fixar a **ordem canônica dos slots reservados**. Precedente fixado p/ bool (ADR-0037): **null=0, valores na ordem de declaração do tipo** |
> | **`T-TIPADO-LEGIVEL-PARAM`** | legibilidade/inspeção (custa bytes) | opt-in de grafia legível (nomes no wire tipado); o DECODE já aceita nomes (ADR-0038) — falta só o plumbing de encoder (kwarg/`PipelineConfig`) |
> | **`T-MISTO-RLE-B64-SINGLE`** | ganho desconhecido | misto RLE+b64 no single-col tipado. CAVEAT: segmentação mista DERRUBADA no multi-col denso (0/18 real-world, bloco DECISÃO PENDENTE abaixo) — contexto diferente, mas medir real-world primeiro; serialização mais complexa |
> | **`T-FORCAR-MECANISMO-PARAM`** | heurística/experimento | forçar mecanismo (RLE/b64/refs) via params — demanda explícita do owner; destrava medição de candidatos sem depender do FLOOR |
> | **`T-TIPOS-CONFORTO-MAP`** | tipos de formulário como slots internos (ex. masc/fem = 14/15) | preparado em `src/tcf/tipos_internos.py` (fonte única, byte-neutro); o DESIGN do mapa (externo × config; alocação de índices) é decisão do owner — sem isso, nenhum tipo novo |
> | **`T-FLOOR-MULTIVETOR`** | evita troca ruim; **byte-quase-neutro** | o `min()` decide so' por BYTE. Medido 2026-08-07: a polaridade ganha **-1 B** e custa **+25 a +42% de CPU de decode** (+5,5% de memoria), sinal firme em 4 rodadas intercaladas — e o criterio de hoje nao consegue nem VER isso. Minimo viavel: desempate entre candidatos dentro de uma margem de bytes (ex. <=0,5%) pelo vetor mais barato. Lab `2026-08-07-2055` |
> | **`T-ONLINE-NESS-BENCH`** | vetor que nao existe | `bench_perf` mede wall/cpu/heap/rss e **nada** de streaming (nenhum grep por `first_byte`/`streaming` acha). Medido: core = 0,1-0,3% do fio pro 1o valor mas **100% pro ultimo**; bN modo B = 2,1-7,0% **constante em j**; modo C = **100% sempre**. O metodo de truncamento do lab e' barato e usa o decoder real. Lab `2026-08-07-2055` |
> | **`T-DECIMAL-HARD-RECUSADO`** | dinheiro perde o tipo hoje | `Decimal` e' fail-loud no `.8H` (`valor escalar de tipo nao suportado: Decimal`), junto com `date`. E' o tipo que existe PRA NAO virar float; mandar como string joga fora a informacao de que era decimal. Registrado agora **so' pra a decisao de data nao fechar de um jeito que nao sirva pra dinheiro** — nao e' pra fazer junto |
> | **`T-DATA-TIPADA-NATIVA`** | destrava `date`/`datetime` na API | HOJE e' FAIL-LOUD: `encode([datetime.date(...)])` -> `HierarchicalError: valor escalar de tipo nao suportado: date`. Entao o ramo "data entra tipada" NAO EXISTE — o lazy e' o unico caminho, nao uma escolha entre dois. Quando existir tera' uma decisao que o lazy nao tem: QUAL GRAFIA emitir na volta (um `date` nativo nao traz formato). Irmao do schema previo. **INVENTARIO COMPLETO DA PORTA, medido 2026-08-15** (`hierarchical.py:163-179`, `_scalar_type`): ENTRAM exatamente 4 tipos — `str`->`s`, `int`/`float`->`n`, `bool`->`b`. **FAIL-LOUD: `date`, `datetime`, `time`, `Decimal`, `bytes`.** Ou seja a porta aceita exatamente os escalares do JSON, nem um a mais. **LACUNA DE REGISTRO ACHADA 2026-08-15**: `datetime.time` estava **sem ticket nenhum** — `date`/`datetime` estao aqui, `Decimal` esta' no `T-DECIMAL-HARD-RECUSADO`, mas o `time` nativo nao aparecia em lugar nenhum do STATUS, apesar de o `T-HORA-SPEC` ja' ter fechado o lado da GRAFIA (`HH:MM` como string, lab `2026-08-14-2230-fechamento-hora`). Fica registrado AQUI, com os irmaos: e' a MESMA porta e a MESMA decisao de grafia-na-volta. `bytes` fica fora de proposito (nao e' escalar de tabela textual; se um dia entrar e' outra discussao, nao esta) |
> | ~~`T-DATA-LAZY-ISO`~~ | **SOLDADO 2026-08-08** | `SPEC_DATA_ISO` no registry (`#TCF.8 :data-iso`). Detecta por `date.fromisoformat` + guard de re-emissao; alvo = ordinal DECIMAL (o `*N+M|` do seq-RLE). Medido n=600: `mensal` **6338->33 B (-99,5%)**, `diario` 414->32 (-92,3%), `espalhado` -17,1%; e **RECUSA** em `agrupado`/`k12`, onde o OBAT ja' resolve e o spec pioraria. De quebra: (a) o FLOOR da nature passou a comparar contra o baseline REAL (incluia so' o core, nao o bN — CPF k=2 saia 198 B com nature vs 61 sem); (b) `None` nas QUATRO natures estourava `TypeError` cru. Suite 1199 |
> | **`T-NATURE-STRICT`** | **−61% do encode**; risco de bytes assumido por quem pede | flag que AFIRMA a grafia: falha alto se o valor nao casar, E dispensa montar o baseline do FLOOR (medido: o baseline custa 58% do encode; 66.635 -> 25.821 us, mesmos bytes). Risco medido: ate **4,2x pior** onde o FLOOR recusaria (`k12-ciclado`). E' a origem HARD DECLARADA sem precisar do tipo nativo. EM ABERTO: sao dois eixos num flag so' (falhar x nao-comparar) — decidir se e' 1 parametro ou 2. Nota `2026-08-08-onus-do-fluxo-total` |
> | **`T-SPEC-PARSE-X-ALVO`** | "8 specs" vira "1 spec, 8 parsers" | separar o PARSE do ALVO no spec: N grafias -> data canonica -> N alvos, com o `min()` escolhendo o alvo por regime (medido: nenhum alvo ganha sempre — delta-dias 5/8, ordinal-denso 2/8, iso 1/8). Dissolve o atrito "CPF tem 1 grafia, data tem muitas". **CRITERIO ATINGIDO 2026-08-09** (lab `1853`): ja' sao DUAS grafias (`YYYY-MM-DD`, `YYYY-MM`) e TRES alvos medidos (ordinal-dia, mes-geral A4, mes-fim A2f) com payloads compartilhados — 2x3 fatoravel. Decidir junto com o `T-DATA-ALVO-MENSAL` |
> | **`T-DATA-ALVO-DELTA`** | delta-coluna: **2-11x** onde o ciclo nao e' exato; robusto a ruido | **MEDIDO 2026-08-09** (lab `0042-data-alvo-delta`, RT 12/12): transform de coluna `[1o ordinal, depois deltas; invalido → _literal]` compoe com o core inteiro — alfabeto pequeno cai no bN (`mensal` 1085→349, `quinzenal` 3951→349, `espalhado-ordenado` 4059→644), feriado vira SIMBOLO e nao quebra (345-353 B sob todo ruido testado). COMPLEMENTAR ao periodico (cada um ganha onde o outro nao alcanca; juntos sob FLOOR cobrem tudo). PRESSUPOE `T-NATURE-CANDIDATO-BN`. Aguarda decisao de design do owner (protocolo da nature: transform de coluna). O irmao `T-SEQRLE-PERIODICO` foi SOLDADO (ADR-0040) e cobre o ciclo EXATO; e o `T-DATA-ALVO-MENSAL` (lab `1853`) tirou o caso mensal deste ticket (31-33 B per-valor vs 349 do delta-coluna). SOBRAM pro delta-coluna: espalhado-ordenado (644) e ciclo-quebrado (345 vs 677) — urgencia caiu de novo. **MEDICAO CONJUNTA 2026-08-15** (lab `2026-08-15-0400-date-processo-de-compressao`, a pedido do owner: *"fazer o MINIMO pra sustentar o ponto de vista de compressao — ve o formato mais comum e se sustenta nele pra ver o processo de compressao primeiro"*; formato FIXO, I/O fora de escopo). **6 transformacoes x 14 regimes no MESMO `min()`, 0 falhas** (cada uma validada pela propria inversa) — ate' aqui **cada transformacao tinha sido medida contra o ordinal, nunca todas juntas**. **A PARTICAO E LIMPA e nenhum candidato domina**: `ordinal` (welded) ganha ou empata em **8 de 14** — onde ha PROGRESSAO REGULAR (diaria, semanal, quinzenal, uteis, trimestral, descendente, suja); `delta` ganha onde a progressao **QUEBRA** — `mensal-faltas` 2278->**453 (80,1%)**, `ciclica` 957->**351 (63,3%)**, `mensal-dia1` 654->**337 (48,5%)**; **`delta2` (2a diferenca, H-DA-12, NUNCA medida antes)** ganha onde os saltos sao irregulares MAS crescentes — `esparsa-ordenada` 3854->**605 (84,3%)**, batendo tambem o delta (772); e `componentes` ganha onde a **ORDEM SOME** — `esparsa-desordenada` 4468->**2434 (45,5%)** e `agrupada` (nucleo 64 -> **41**). Cada uma e **pessima fora do seu dominio** (`componentes` faz 1835 B na diaria contra 22 do ordinal; `delta` faz 227 nos uteis contra 30) — por isso a resposta e o `min()`, nao a escolha. **CORRECAO DE UM NUMERO MEU**: a tabela do runner diz *14 de 14 regimes ganham*, e **esta inflado** — em 7 deles o vencedor e o proprio `ordinal` contra o `spec`, e os 4 B de diferenca sao **o carimbo `:dt`** (`T-SPEC-SEM-CARIMBO`), nao transformacao. A regua honesta (transformacao x transformacao) e **6 de 14**. **A DECISAO DE DESIGN QUE DESTRAVA**: delta/delta2/componentes **veem os vizinhos**, e o protocolo de nature e per-valor (`encode_value(v)`) — por isso so o ordinal cabe hoje. E o **protocolo de transformacao de COLUNA** que este ticket ja pedia, e ele destrava os 6 regimes de uma vez. **RESSALVA DURA**: tudo sintetico, e o precedente e o `T-DATA-ALVO-MENSAL` (95% sintetico -> **0,0% real**); os 80% do `mensal-faltas` correm o mesmo risco. Os que tem chance de sobreviver ao real sao **ciclica** (ja medida em coluna real pelo `T-CANDIDATO-SEM-DEDUP`) e **esparsa** (existe no TPC-H e no br-identidades). E **CPU nao foi medida** — um `min()` de 6 candidatos custa tempo (o analogo mediu +84-93%). **AS DUAS RESSALVAS FORAM FECHADAS 2026-08-15** (lab `0530-date-real-e-cpu`, 8 colunas do corpus, 24 medicoes, 0 falhas de RT): (1) **`componentes` vence em 7 de 8 colunas** com **51,9-55,1%** sobre o ordinal welded — estavel a ordem E a amostragem (6170 B constantes); (2) **`delta` vence na unica coluna real ja ORDENADA** (`football-date`, ND=100%): **71,0%** sobre o ordinal em ordem fisica, 73,2% sobre o spec de hoje — deixa de ser caso hipotetico; (3) **o `delta2` NAO venceu uma unica vez nas 24 medicoes** — o precedente do `T-DATA-ALVO-MENSAL` SE REPETIU (95% sintetico -> 0,0% real), agora com o delta-of-delta: registrar como candidato conhecido, **nao usar como motivo**; (4) **CPU do `min()` de 6: +47,7% a +86,1%** (dev-run, 2 rodadas) — DENTRO da faixa que o projeto ja pagou por UM candidato, logo **nao e' proibitivo**; a objecao real e' que **4 dos 6 candidatos nunca vencem** (um `min()` de tres — `ordinal`, `componentes`, `delta` — cobre as 8 colunas). **DOIS ACHADOS DE METODO** que valem alem do date: (a) **entropia e' o comparador ERRADO** — H de ordem zero preve `delta` onde o byte medido da' `componentes` por 1,6x, porque o nucleo e' texto-com-dicionario e nao codificador de entropia (§RT aplicada a escolha de transformacao); (b) **o passo espalhado NAO e' amostra quando o eixo le vizinhos** — em `lineitem` (ordenada por `l_orderkey`) o `v[::300]` mediu \|delta\| mediano **710** contra **50** da coluna inteira, porque pula sempre pra outro pedido; qualquer eixo que leia adjacencia precisa de **par contiguo** |
> | ~~`T-SEQRLE-PERIODICO`~~ | **SOLDADO 2026-08-09** (ADR-0040, suite 1238) | `*N~d1,...,dp\|template` — o delta CICLA entre linhas. Ideia do owner, anterior a esta rodada. **O ciclo paga UMA vez**: 600 dias uteis = `*600~1,3,1,1,1\|\739617` (1590 → **40 B** com o spec de data), n=6000 → **41 B** (**O(1) em n** — cresce so' o contador), ids nao-data 1959 → **32 B** (nivel CORE, sem nature nenhuma). Terceiro candidato do MESMO `min()`; **D1-D9 = 1545 e real-world = 89430 byte-IDENTICOS**; 39 testes novos. **DUAS cacadas adversariais, SETE defeitos** — e DOIS foram criados pelos proprios consertos: (1) teto de memoria nao cobria o marcador novo; (2) detector O(n²) = 13,8 s em n=2400; (3) FLOOR invertia o desempate e reescrevia wire SEM periodicidade; (4) telemetria `seq_rle_runs` zerava CALADA em wire byte-identico ao do core (regressao de canal publico, nenhum teste pegava); (5) pad com cauda morta = nao-injetivo; (6) **o gate do (5) virou amplificador** — 48,8 KB → 126,87 s (16.881x) e 22 B → 85 MB, porque validava proporcional ao que o WIRE declara ANTES de validar; (7) `compact_body` por fragmento SEM piso ressuscitava marcador que o core recusou, e a POLARIDADE cobrava (corpo −9 B embarcando wire +19 B, 963 regressoes em 28.985 casos). Sintaxe `~` reversivel pre-1.0. Gerou `T-FLOOR-POS-POLARIDADE` |
> | **`T-NATURE-CANDIDATO-BN`** | **mediana 6,7% em dado REAL** (ate' 7,5%; 12.582 B em 12 colunas) — e vale p/ QUALQUER nature | **MEDIDO EM DADO REAL 2026-08-09** (EXP-017 clean, corpus de Z:): o candidato interno da nature sai de `_encode_column` — **so' o corpo do core**, SEM polaridade (ADR-0035) e SEM bN (ADR-0036) — enquanto a rota flat normal aplica os dois. TPC-H `o_orderdate` 13521 -> 12612 B; `br data_cadastro` 21366 -> 20101; football 16241 -> 15021. **Nao e' de data**: CPF real 19467 -> 18095 (1372 B, 7,0%). O sintetico anterior media 19/70/298 B e subestimava em uma ordem de grandeza. RECALIBRADO pela cacada (4 lentes): mediana **~5,7%** no corpus amplo (nao 6,7% — aquele era subconjunto), max **11,9%** (`socio_cpf`); total corrigido 10.453 B em 10 colunas DISTINTAS (2 eram duplicatas de input); a lacuna **varia com n** (mesma coluna: 6,4% em n=200 -> 0,24% em n=15000); em dado real e' quase toda POLARIDADE (22/26), o bN so' aparece em low-card sintetico. Os 'negativos' eram ARTEFATO de metrica (lacuna so' e' interpretavel quando a nature VENCE o FLOOR). E o conserto SIMPLIFICOU: **a rota plena e' nunca-pior por construcao** (o FLOOR da polaridade devolve sufixo vazio quando nao paga; stress 8000 colunas, 0 violacoes) — trocar o corpo do candidato pela rota plena, mantendo o FLOOR nature-vs-baseline que ja' existe. Aguarda aprovacao (mexe em src/tcf) |
> | **`T-DATA-ALVO-MENSAL`** | mensal **679→31 B** (21,9x); faltas **2799→41** (68x); fecho **655→31**; YYYY-MM **826→31** | direcao do owner 2026-08-09 ("olhar pelo mes, o incremento fica melhor"), MEDIDA no lab `1853-data-alvo-mensal`: alvos per-valor com valvula (MESMO protocolo do SPEC_DATA_ISO, zero mudanca de core) transformam constancia-de-dia em uniformidade-de-delta que o M10+ADR-0040 ja comem. Estrutura que os numeros revelam: **A4 `mes*31+dia`** e' o alvo geral SEM convencao (cobre dia-01/15/misto por 33-36 B, perde so' 2 B do otimo); **A2f fim-de-mes** e' a unica convencao que paga (31 vs 745 do A4 no fecho contabil); **A3 YYYYMM morre** (legibilidade custa a aritmetica — virada +89 quebra runs); **YM** = spec irmao p/ grafia `YYYY-MM` (uma grafia de re-emissao por tag, senao RT quebra). Controle diario: floor protege (A1 segue vencendo). **DECISAO do owner 2026-08-09: data E' SPEC mesmo** ("e nao caracteristica so' de multicolumn nem nada") — per-valor, valendo no single-col; NAO vira feature de rota. Resta escolher a forma (specs irmaos A4+A2f+YM vs fatorar parse-x-alvo). **EXP-017 CLEAN 2026-08-09 — NAO FECHA EM DADO REAL**: ganho mediano **0,0%** em 14 colunas reais contra **95%** nos sinteticos mensais. O motivo NAO e' o mecanismo, e' o CORPUS: nenhuma coluna real disponivel tem cadencia mensal (TPC-H, br-identidades, football, retail, receita = todas diarias/transacionais). O regime-alvo **nao esta representado** no que temos. Sinteticos seguem verdes (33-48 B contra 655-2799), nunca-pior 26/26, PINs fixados. CONSEQUENCIA: o weld dos alvos mensais fica **CONDICIONADO a corpus real com cadencia mensal** (competencia/vencimento/faturamento) — sem ele, nao ha' gate a bater. A bateria multi-vetor do lab `2228` vale para o REGIME, nao para o corpus atual. **CACADA ADVERSARIAL (4 lentes)**: o 95% sintetico e' O(n) e fragil (n=12 PERDE; jitter +-2 dias -> 1,1x; 15 variantes realistas -> mediana 13,6%); o regime mensal E' alcancavel como AGREGADO derivado do corpus (1,8-9,8x); e folha de pagamento fica NEGATIVA nos 3 alvos mas um 4o eixo **dia-UTIL** recupera 99% — o argumento medido do **spec-orienta-nao-manda** (triagem em docs/theory/spec-orienta-nao-manda-triagem.md): eixos como DICAS opt-in do `.9`, nao alvos mandatorios |
> | **`T-PENHASCO-INICIO`** | **6x-95x decidido pela POSICAO da 1a excecao** da coluna | achado da cacada adversarial do EXP-017 (2 lentes independentes): (a) UMA sujeira numa coluna de 600 meses custa 4073 B se cair no indice <20 e 43 B se cair no >=20 — fronteira bate com `analyze_column(sample_size=20)` + Regra 2 do `auto_cadence` ('todas as primeiras 20 strings sao numericas'); atinge o ordinal SOLDADO igual (4308 vs 666 B) — fragilidade de NUCLEO, nao de alvo; (b) mesma classe: o candidato ordinal cai num penhasco de n (0,3% em n=3000 -> **18,7% em n=4000**, fronteira n=3850-3900). Decisoes de pre-passe criam penhascos que o FLOOR nao ve. `.9`; caso pinado no EXP-017 (`valv-sujeira-no-inicio`) |
> | **`T-CORPUS-DATA-MENSAL`** | destrava o gate do `T-DATA-ALVO-MENSAL` | achado do EXP-017 (2026-08-09): o corpus de `Z:/tcf-data/` tem **10 colunas de data reais** (TPC-H x5, br-identidades x2, receita, retail, football) e **NENHUMA com cadencia mensal** — todas diarias/transacionais. Sem corpus do regime, o alvo mensal nao tem gate a bater (mede 0,0% real contra 95% sintetico). Regimes procurados: **competencia** (folha, faturamento mensal), **vencimento** (parcelas, assinaturas, contratos), **fecho contabil** (dia = ultimo do mes). Anexo ao `project_dataset_coverage_map`. NAO baixar sem decisao do owner |
> | **`T-OBAT-NOS-PROXIMIDADE`** | a RAIZ do H-SIM-DUPLA-01; **alvo 2.0, vontade de fazer LOGO** | diagnostico do owner 2026-08-09 (confirmando o lab `1943`): *"nao desenvolvi porque a parte da proximidade dentro do OBAT nao foi feita — os nos so' fazem comparacao de IGUALDADE; se tiver similaridade [proxima como delta] ele nao cria nos para o HCC desenvolver depois"*. Ou seja: proximidade-como-NO' (o no' delta que o detector de composicao poderia desenvolver) e' lacuna de nascenca do OBAT, nao do fluxo. Owner: **"deixe registrado a vontade de fazer logo, apesar disso parecer mesmo melhor pro 2.0"**. Ate' la', os paliativos sao os encaixes E1/E2 (tickets abaixo) e os SPECS (que escolhem dominio onde a aritmetica sobrevive). Irma da H-TH-02 (Patricia) e da familia comparacoes-nao-literais (2026-05-11). **REFORCO 2026-08-09 (EXP-017)**: a lacuna de rota da nature (`T-NATURE-CANDIDATO-BN`, 6,7% em dado real) mostra que hoje ate' os PALIATIVOS estao pela metade — o candidato semantico nem passa pela rota que os mecanismos cegos usam. Ordem sensata: fechar a rota (barato, ja' medido) ANTES de atacar a raiz no 2.0 |
> | **`T-CANDIDATO-SEM-DEDUP`** | teto ~20x nas colunas que CICLAM (mes 423->~35 B; dia 523->~35) | achado estrutural 2026-08-09 (lab `1943-fluxo-igualdade-x-proximidade`, direcao do owner): o nucleo tem DUAS nocoes de similaridade — IGUALDADE (dedup `^N`/bN/dict) e PROXIMIDADE (seq-RLE uniforme/periodico) — e elas **nao competem no mesmo `min()`**. A igualdade roda DENTRO do OBAT/HCC, antes; a proximidade le' o que sobrou. Medido: a leitura aritmetica morre na linha **k** (1a repeticao aciona o dedup) — coluna `01..12` ciclica tem 1a referencia `^N` na linha 12, **11 deltas legiveis** e 0 runs periodicos (423 B), enquanto a MESMA aritmetica sem repeticao (k=600) faz 20 B. O candidato aritmetico nunca e' CONSTRUIDO, entao o FLOOR nao pode escolhe-lo. **BATERIA MULTI-VETOR 2026-08-09** (lab `2228`): bytes 10x nos ciclicos (423->42, 321->30, 4024->43); candidato custa **+84-93% do encode**; mem ~igual; online igual (mesma gramatica — SONDA PROVOU que o corpo sem-dedup ja' DECODIFICA hoje, e' encoder-only). VEREDITO pela regra do owner: **VARIANTE** (perfil `compacto`/flag), promocao a default condicionada ao `T-GATES-ANTES` baratear o caminho; gate natural = so' coluna toda-digito. Corolario registrado: parte do ganho dos SPECS e' o nucleo compensando escolha propria (o alvo devolve k grande, onde a aritmetica sobrevive) |
> | **`T-DECODE-SAIDA-TIPADA`** (NOVO 2026-08-15, proposta do owner) | o decode entrega o OBJETO nativo em vez da string — **17,5-19,3% do decode completo**, com o wire IDENTICO | direcao do owner: *"no decode ele sai de string e vai passar por uma funcao de date/datetime de qualquer forma... e' mais barato se fizer isso ja' na primeira vez: `datetime comprimido` -> decode(alguns formatos) -> date que o cliente quer. Use o barato/nativo; padronizar antes; nao quero que vire um datatransform portatil; cuidado pra nao inflar o nucleo"*. **O FATO DE CODIGO QUE SUSTENTA**: `data_iso.py:107` = `fromordinal(int(payload)).isoformat()` — **o objeto ja' existe no meio do decode e e' jogado fora** ao serializar; o cliente entao re-parseia a mesma string. **MEDIDO** (lab `experiments/lab/dirty/2026-08/2026-08-15/2026-08-15-0200-decode-direto-ao-tipo`, prototipo de **9 linhas**, `src/` intocado, 0 falhas): rota-hoje (decode->str + cliente re-parse) vs rota-direta (decode_value devolve `date`): **17,5%** (n=2000) e **19,3%** (n=500) do decode COMPLETO; o caso n=200 deu -5,9% e e' **ruido declarado** de dev-run (a rota direta faz estritamente menos trabalho). **PRECEDENTES, todos ja' decididos**: (1) o decode JA' transforma — `decoder.py::_cast_tipo` converte string->int/float/bool DENTRO do decode, soldado (a proposta estende aos specs de grafia, opt-in); (2) a uniao na saida (`['date','str']` quando ha' literal) e' o **CONTRATO UNIAO do ADR-0039** herdado pronto; (3) o RT-objeto e' o plano 5 da formulacao do owner (tipo+valor+resolucao), com o modo string continuando DEFAULT e contrato byte-exato. **MECANICA DESCOBERTA**: o registry tem precedencia na resolucao do `:id` (`decoder.py:73-77`) — o spec out-of-band so' e' usado quando o id NAO resolve; e `decode_value -> str` e' **convencao, nao checagem** (um decode que devolve objeto atravessa a rota sem erro) — a tubulacao ja' nao se importa, o que torna o kwarg barato. **O DESENHO REGISTRADO (sem weld)**: `decode(w, nature=SPEC, saida="date")` — kwarg da **API do host**, wire **byte-identico**, cada host entrega o objeto nativo DELE (Rust: `chrono::NaiveDate`), host que nao implementa fica na string (**droppable**). **A LINHA VERMELHA**: o parametro escolhe o **TIPO** de saida, **nunca uma grafia** — `ordinal -> "31/01/2026"` e' o datatransform que o owner vetou. **E O ENCODE NAO MUDA**: objeto `date` na entrada segue recusado; a regra do date (string pre-formatada por manual) vale, por preferencia explicita do owner. **AVALIACAO DA ENTRADA 2026-08-15** (`experiments/lab/dirty/notas/2026-08/2026-08-15-0320-encode-entrada-tipada-avaliacao.md`, a pedido do owner: *"o decode e' menos arriscado depois de ver os testes, mas o encode e' mais arriscado porque deixa a responsabilidade no TCF de ficar validando date/datetime de MUITOS FORMATOS"*): **a preocupacao junta duas coisas que se SUBTRAEM**. Medido — **objeto `date`: 0 grafias a validar, NAO PODE ser invalido por construcao** (o construtor ja' recusa mes 13, 30/fev, ano 0), **zero parse**, `toordinal()` = **123 ns**; **string canonica (o que o TCF ja' aceita HOJE)**: 1 grafia, pode ser invalida, `fromisoformat`+guard = **1230 ns**; **string livre**: N grafias — **e' esse o risco que o owner nomeou, e ele continua vetado**. Ou seja **aceitar OBJETO e' MENOS arriscado que o que o TCF ja' faz** (10x mais barato, e a validacao ja' aconteceu na fronteira anterior). **O ACHADO QUE CONTRARIA 'deixar com o dev e' mais seguro'**: para `date`, `str()` ≡ `isoformat()`; para **`datetime` DIVERGEM** (`str()` da' ESPACO, `isoformat()` da' `T`) — **o dev que usar `str()` ou f-string entrega a grafia com espaco SEM SABER que escolheu**. Exigir que ele normalize exige que ele saiba dessa divergencia; deixar com ele nao e' mais seguro, e' **mais silencioso**. **O DESENHO DE MENOR RISCO (A): normalizacao na PORTA** — o objeto vira a grafia canonica UMA vez na entrada e daí o fluxo e' o de hoje; medido: wire **BYTE-IDENTICO** (26 B, `#TCF.8 :dt`), **sem tag nova** (nao toca o `T-TIPOS-CONFORTO-MAP`), sem validacao nova (`isoformat()` nao falha em objeto valido), e a normalizacao custa **1,7% do encode** — quem paga nao muda o total, **muda de bolso**. O desenho B (tipo nativo com tag) cai no `T-TIPOS-CONFORTO-MAP` e **nao e' necessario para o ganho**. **RISCOS HONESTOS DO A**: (1) no port, o "nativo" varia — em Rust o `chrono` e' lib EXTERNA (mitigacao: droppable, como o kwarg de saida); (2) coluna MISTA precisa de politica declarada (precedente: CONTRATO UNIAO do ADR-0039); (3) o dispatch (`_tipo_single_col`) precisaria de **uma linha** — e o proprio comentario do codigo diz que e' assim que se estende —, mas e' `src/tcf` e depende de aprovacao; (4) o RT muda de contrato quando entra objeto (tipo+valor), como int/float/bool ja' fazem. **SOBRE A ORDEM DO PILOTO**: a medicao sugere o INVERSO do que o owner propos — o **`date` e' o caso trivialmente seguro** (`str()` ≡ `isoformat()`, zero ambiguidade) e seria o piloto natural; o **`datetime` e' o que mais GANHA**, mas e' onde a ambiguidade mora. Sugestao de ordem, nao de escopo. |
> | **`T-OBAT-COME-O-SEQRLE`** (NOVO 2026-08-15) | um mecanismo do nucleo **inutiliza** o outro, e a diferenca e' **4x** | achado no prototipo do spec de datetime (`experiments/lab/dirty/2026-08/2026-08-15/2026-08-15-0130-spec-datetime-receita-do-padrao`). Numa progressao aritmetica pura (n=2000, passo fixo), **quem age depende de quantos digitos ficam INVARIANTES no prefixo** — nao da magnitude: 11 digitos com passo 300 -> **79 B** (`!639081*8*2760`, o OBAT fatorou o numero em afixos); os MESMOS 11 digitos com passo 30000 -> **32 B** (`*2000+30000|\63908182760`, o seq-RLE agiu); 9-10 digitos com passo 300 -> 28-29 B (seq-RLE). Mecanismo: o `find_escape_digit_runs` (`hcc_seqrle.py`) opera sobre a linha **ja' tokenizada**; se o OBAT extraiu o prefixo comum como afixo, o seq-RLE ve 3 runs pequenos com deltas mistos em vez de 1 corrida grande, e recusa. **Nao ha' teto hard-coded** — e' interacao de pipeline. **CONSEQUENCIA PRATICA**: todo spec que emite inteiro deve escolher a MENOR representacao possivel, nao por bytes brutos, mas para nao dar prefixo longo ao OBAT. O `data_iso` esta' a salvo por sorte (ordinal de 6 digitos); um spec de datetime com ordinal de 11 digitos perderia **3x**. Mesma classe do *binarizar destroi a estrutura* (fechamento da hora), agora entre dois mecanismos do proprio nucleo |
> | **`T-RLE-COUNT-ZERO`** (NOVO 2026-08-14) | wire aceito-em-silencio no CORE: `*0\|` declara e NAO emite — o "RLE fantasma" existe por acidente | **VERIFICADO A MAO** (arvore limpa, `src/` intocado): `decode('#TCF.8\n*0\|abc\ndef\n^1\n')` devolve `['def','abc']` — o `abc` e' declarado, nunca emitido, e depois referenciado por `^1`. Tambem `decode('#TCF.8\n*0\|abc\n')` -> `[]` (1 linha no corpo, 0 elementos) e `*-1\|` (count NEGATIVO) idem. Mecanismo: `syntax.py:968` declara INCONDICIONALMENTE e so' `syntax.py:974` escala a emissao por `count`; **nao ha' guarda `count >= 1`** (`syntax.py:926-935`). Popula as DUAS tabelas (nos e fragmentos OBAT). **O encoder canonico nunca emite** (verificado em 7 formas de entrada) -> mesma classe dos 4 bugs corrigidos em `dominio_bn.py`. **A INCONSISTENCIA que faz disto um ticket**: o mesmo padrao e' **fail-loud no bN** — `dominio_bn.py:288-292` levanta `ValueError` se um slot do dominio nao e' referenciado (*"o encoder nunca emite slot sobrando"*, achado da varredura 2026-08-07) — e **silencioso no corpo do core**. Independe de querermos ou nao o RLE intra-valor: ou o core ganha a mesma guarda, ou a porta se abre COM CONTRATO. Descoberto ao avaliar a proposta de "RLE fantasma" do owner, que pedia exatamente esta construcao. **LAB (a evidencia, 4 wires escritos A MAO em `inputs/`, fluxo invertido)**: `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-2010-rle-intra-valor-medida`. Nota: `experiments/lab/dirty/notas/2026-08/2026-08-14-2010-rle-intra-valor.md` |
> | **`T-DATETIME-TIPO`** | o menos avaliado, e o de **maior retorno estrutural** (split = 7,13x) | aberto 2026-08-14 pela correcao do owner (datetime fica no `.8`). **Falta TUDO**: caracterizar nos 5 eixos, decidir se e' spec proprio ou COMPOSICAO (data + hora), e declarar a peculiaridade de ser **COMPOSTO** — e' o unico tipo cuja melhor resposta hoje **nao e' um spec**, e sim o SPLIT estrutural: medido em `online-retail.InvoiceDate` (3000 linhas, 304 datas x 603 horas), 61.856 B em single-col contra **8.675 B** em multi-col, onde o `_best_of` escolhe `split` sozinho. Bate epoch-como-inteiro (26.887 B) e separar-a-mao (17.559 B). Liga direto com o `T-SPLIT-SINGLE-COL`. Nota: `experiments/lab/dirty/notas/2026-08/2026-08-14-0430-fechar-todos-os-tipos-no-08.md`. **1o LAB 2026-08-15** (`experiments/lab/dirty/2026-08/2026-08-15/2026-08-15-0020-datetime-grafias-regimes-mecanismos`, 13 grafias x 8 regimes x 9 mecanismos isolados, 2000 linhas cada, **0 falhas**) — ate' aqui os 4 numeros do datetime (61.856/26.887/17.559/8.675) eram **ad-hoc de uma nota, sem lab**. **(1) A GRAFIA quase nao importa PARA O SPLIT**: pt-BR, ISO-com-T e SQL-com-espaco dao os **mesmos 842 B** (de 40 KB raw) — ele le' a ESTRUTURA, nao a convencao. **(2) DUAS GRAFIAS MATAM O SPLIT, por razoes diferentes**: `YYYYMMDDHHMMSS` (compacta) e' **1 grupo de digitos** e o gate exige >=2 campos — quem economiza 5 chars na origem **perde 235 B** por 2000 linhas no formato; e `MM/DD/YYYY hh:mm:ss AM/PM` falha porque o template exige as partes nao-digito IDENTICAS e **`AM` != `PM`** (unica grafia em que o `core` vence). A ISO BASICA (`YYYYMMDDTHHMMSS`) se salva pelo `T` (2 grupos), mas fica 15% pior que a estendida. **(3) NENHUMA TRANSFORMACAO DOMINA — cada uma serve um REGIME**: no batimento de 5 min o `epoch-s` da' **58 B contra 3275 do split (56x)**, porque epoch de batimento e' progressao aritmetica e o seq-RLE a esmaga (mesma lei do `data-iso` e do ordinal de hora: *deixar a aritmetica visivel vale mais que empacotar*); mas no log de alta cardinalidade o mesmo `epoch-s` da' **10818**, pior que o split (3519). **(4) O NUCLEO INFLA num regime**: `esparso-multi-ano` -> **43957 B para entrada de 39999 = +9,9%**, porque a rota single-col **nao tem `raw` no `min()`** (o multi tem) — caso medido em que o resultado e' **pior que nao fazer nada**; e' o `T-UM-CAMINHO-SO` com consequencia dura. **(5) O `campos-6` NAO e' competidor** (descarta a grafia; RT contra o dict) — e' o **PISO** do split, e a diferenca e' **28 B CONSTANTES**, o custo do template: o split ja' opera a 28 B do proprio piso, **nao ha' gordura ali**. **SPEC PROTOTIPADO 2026-08-15** (`experiments/lab/dirty/2026-08/2026-08-15/2026-08-15-0130-spec-datetime-receita-do-padrao`, decisao do owner: *"o datetime entra no mesmo esquema do date e do time — sao PRE-FORMATADOS; formatos variantes viram STRING; so' seguir a receita de padrao"* — isso elimina o problema das 13 grafias). **A RESTRICAO QUE DECIDE O DESENHO**: o contrato de nature e' `encode_value(v) -> (payload, status)` — **um valor, um payload**; um spec **nao pode** partir a coluna em campos (isso e' o `split`, multi-col). Logo a unica pergunta e' QUAL INTEIRO emitir. **RESULTADO: ganha em 7 de 8 regimes** (14,3% a **99,8%**) e nunca perde (no embaralhado o FLOOR recusa e devolve o nucleo). `epoch` vence em 5, `ordinal` em 1 (o regime do corpus), `par` em 1 (log) — **nenhum domina**. **O PAYLOAD NAO SE ESCOLHE POR 'MENOS DIGITOS'**, e sim por **quantos digitos ficam INVARIANTES**: com prefixo longo o **OBAT fatora o numero e o seq-RLE perde a corrida** — mesma progressao, 11 digitos com passo 300 da' 79 B (`!639081*8*2760`), com passo 30000 da' **32 B** (`*2000+30000|\63908182760`); e' por isso que `epoch` (desde 1970) bate `ordinal` (desde o ano 1) por **3x** no batimento (34 vs 104 B). **O SEPARADOR**: errar custa **ZERO** — o wire com o spec errado e' **byte-identico** ao sem-spec (o FLOOR descarta), simetrico nas duas direcoes. **E O ARGUMENTO DE NORMA NAO TRANSFERE**: nenhuma das duas grafias de 19 chars e' RFC 3339, porque `full-time = partial-time time-offset` torna o offset **obrigatorio** — `2026-03-02T08:26:00` e' ISO 8601 *local date-time*, nao RFC 3339; logo o criterio que elegeu o `YYYY-MM-DD` do `data_iso` **nao vale aqui**. **E O CORPUS NAO VOTA**: o espaco do `InvoiceDate` foi FABRICADO por `setup_online_retail.py:109-110` (pandas re-emitindo `datetime64` via `str()`); a origem e' `M/D/YYYY HH:MM`. Sobra: o `T` tem a norma (ISO 8601 removeu a omissao em 2019; TOML so' admite `T` em local-date-time), o espaco tem os BANCOS (SQLite/PG/MySQL/SQLServer-121), e o Python **se divide** (`str(dt)` -> espaco, `dt.isoformat()` -> `T`; para `date` coincidem, para datetime nao). Como o custo e' simetrico e sem regressao, o caminho barato e' **separador como campo do spec, duas instancias congeladas e dois `wire_id`** — errar passa a custar **1 byte de id**. **AS 13 BORDAS, todas com RT ok**: a irma com `T` e' pega pela **RE-EMISSAO** (tem 19 chars, passa a largura) e o pt-BR pelo **PARSE** (tambem 19 chars) — **a peculiaridade que o datetime tem e a data nao: as duas canonicas concorrentes tem o MESMO comprimento**, entao o gate barato nao as separa. **CICLO DE AVALIACAO 2026-08-15 — OS 5 PLANOS** (`experiments/lab/dirty/notas/2026-08/2026-08-15-0230-datetime-os-cinco-planos.md`, a pedido do owner ANTES de novo lab): eu colapsava dois planos que sao independentes — *o que o DATASET entrega* e *o que o DECODE promete*. **MEDIDO: o TCF RECUSA `datetime`/`date`/`time` hoje** (`HierarchicalError: valor escalar de tipo nao suportado`); os 4 tipos que entram sao **exatamente os escalares do JSON** (str/int/float/bool) — confirmacao empirica da observacao do owner de que *nao ha' tipo nativo de relogio*. Logo o plano *"devolver um datetime sem compromisso com a entrada"* **nao existe nem em potencial**: o tipo nem entra. **A PREMISSA DE VELOCIDADE DO OWNER SE CONFIRMA**: `datetime.fromisoformat` = **1,48x** o `date.fromisoformat` e **61x mais barato** que o `strptime` (220 vs 13.541 ns). **MAS O CARO NAO E' O PARSE, E' O GUARD**: a re-emissao (`d.isoformat(sep) != v`) custa **2056 ns = 4,6x o parse** — no `data_iso` ela era barata. Uma **regex compilada** faz a mesma triagem por **871 ns (2,4x menos)** e recusa corretamente `T`, `_`, week-date e `HH:MM`. **E O PRECO DE 'ACEITAR OS FORMATOS QUE TIVER'**: o `fromisoformat` aceita **16 de 20** grafias testadas (inclusive `_`, `x` e TAB como separador, e week-date), mas devolver UMA canonica faz sobreviver ao RT byte-exato so' **3 de 16** (saida espaco) ou **1 de 16** (saida `T`). Aceitar generosamente e devolver canonico **destroi o RT byte-exato**. **E 'mesma resolucao' NAO VEM DE GRACA**: `2026-03-02 08:26`, `...08:26:00` e `2026-03-02` colapsam no MESMO objeto, e `microsecond=0` nao distingue *sem fracao* de `.000000` — a resolucao teria de VIAJAR. **A ESTRUTURA REPENSADA — 3 caminhos, e o plano 2 decide qual**: **(A)** dataset entrega `str` canonica -> compromisso e' a GRAFIA, RT byte-exato — **existe hoje, e' o `data_iso` aplicado, cabe no `.8` sem decisao de formato**; **(B)** entrega `int` (timestamp) -> ja' funciona, tag `n`, **spec nenhum necessario** (e o lab mediu: batimento 58 B contra 19.786 do texto) — merece **uma linha no manual, nao codigo**; **(C)** entrega objeto `datetime` -> compromisso e' tipo+valor+RESOLUCAO — **nao existe**, exige tag nova e cai no `T-TIPOS-CONFORTO-MAP` (bloqueado no owner); detalhe barato: a resolucao pode viajar no proprio `wire_id` (`:dtm` seg, `:dtmm` min, `:dtmu` micro), que ja' viaja e ja' e' fail-loud. **O FECHO**: *aceitar os formatos que tiver* e *RT byte-exato* sao **incompativeis no caminho A** e **compativeis no C** — porque la' o compromisso deixa de ser a grafia. **2o CICLO — A DINAMICA RECUPERADA (owner: *"ja' foi discutida muitas vezes no bool, no bN e inclusive no date; ja' esta' decidido, bem entendido e inclusive FEITO; o datetime basta seguir a mesma logica; o `date` ja' esta' welded"*)**. Ele esta' certo e **o erro foi de metodo**: eu tratei como pergunta aberta o que ja' esta' soldado. **A DINAMICA, recuperada**: o guard do `data_iso` **E' LITERALMENTE a funcao de emissao do `decode_value` do proprio spec** — `data_iso.py:92` (`if d.isoformat() != v`) e `data_iso.py:107` (`return _FROM_ORD(int(payload)).isoformat()`) sao **a mesma chamada**. Logo a regra nao e' *"aceite o que a lib re-emite"*, e sim **"aceite exatamente o que o SEU decode devolve"** — o mesmo que a ADR-0036 diz como *"`_le_grafia` desfaz exatamente `_grafa`, nem mais"* e *"recusar o que o encoder canonico nunca produz"*. Status normativo: **"guard de re-emissao e' lei; todo eixo novo nasce com ele"** (5 aplicacoes soldadas, 4 bugs historicos). **ISSO DISSOLVE A PERGUNTA DO SEPARADOR**: nao e' decisao de norma, e' **consequencia de qual decode se escreve** — decode com `sep=' '` faz o guard aceitar o espaco; com `sep='T'`, o `T`. **Dois decodes ⇒ DOIS SPECS IRMAOS**, exatamente o que o `data_iso` ja' declara (*"outras grafias sao specs nomeados irmaos — precedente CPF/CNPJ, um objeto por grafia"*). CPF e CNPJ nao competem por "qual e' o canonico". E o lab ja' mediu que isso custa **1 byte de id**. **E 'O TCF RECUSA DATETIME' NAO E' OBSTACULO** — foi o meu erro mais direto: ele **recusa `date` tambem**, e o `data-iso` esta' **welded e funcionando**, porque o date **entra como STRING**. O caminho A nao e' limitacao a contornar: e' **a dinamica escolhida, exercida e soldada**. O caminho C (objeto nativo) **nunca foi a rota do date**, logo nunca foi a pergunta. **E 'ACEITAR OS FORMATOS QUE TIVER'**, dentro da dinamica, nao e' *aceite tudo*: e' *a lib nativa e' barata o bastante para ser o leitor* (confirmado: 1,48x o do date, contra **90x** do `strptime`); o conjunto aceito segue sendo o que o guard deixa passar. **E A MINHA SUGESTAO DE REGEX FICA RETIRADA**: pela lei, o guard TEM de ser o emissor do decode — regex so' seria legitima se **provadamente equivalente**, e nao esta' provado; os 2056 ns/valor sao o que a lei cobra. **NAO HA' PERGUNTA PENDENTE PARA O OWNER** — havia uma pergunta minha, que a dinamica ja' respondia. |
> | **`T-FLOAT-SPEC`** | **8,0% agregado** em 12 colunas reais — nao paga um spec novo agora | AVALIADO 2026-08-14 a pedido do owner. **NAO PRECISOU DE LITERATURA**: o corpus tem **30 colunas FLOAT reais** (online-retail, tpch-sf001/sf01, wine-quality — o extrator do int filtrava `REAL` de proposito), e elas ja' cobrem quase todas as variacoes previstas: **float com `1.`** (`l_quantity`=`17.0`, `CustomerID`=`17850.0`, 2000/2000 com 1 casa), **casas variadas** (`UnitPrice` {1:139, 2:1861}; `chlorides` {1:15, 2:219, 3:1766}), **entre 0 e 1** (`l_discount` 0.00-0.10, `density` 0.9978), **formatados** (`density` {3:146, 4:1082, 5:755}). **+1 variacao NAO prevista**: `alcohol` traz {13:4, 14:2} — seis valores como `10.0333333333333` (medias sujas do dataset), 1,3% do texto em 0,3% dos valores. **CANDIDATOS MEDIDOS** (todos generalizacoes do que ja' existe): ESCALA (`float -> int x 10^k`, ideia do ordinal) vence em **8 de 12**; SPLIT (ADR-0026) vence em **4**; **ESCALA+PAD NAO ACRESCENTA NADA** — empatou com a escala pura nas 12, porque depois de escalar a largura ja' fica uniforme e o `int_pad_para` corretamente devolve `None`: **o `IntPadSpec` soldado hoje NAO e' reaproveitavel para float**, ao contrario do que eu esperava. **AGREGADO 78.782 -> 72.504 B = 8,0%**; melhor caso individual **1,16x** — outra ordem de grandeza contra o int (mediana 1,72x) e a data (414 -> 26 B). **A PRECISAO SUJA QUEBRA A ESCALA**: em `wine.alcohol` os 6 valores de 13-14 casas impedem escala exata e a coluna inteira perde o candidato — um spec precisaria de fallback literal por valor (o Protocol ja' preve), mas ai a coluna deixa de ter escala unica. **CORRECAO DE CRITERIO (owner, 2026-08-14)**: *"a gente ainda vai ter que ver os tipos datetime, time e float ainda no .8 pra fechar, mesmo que alguns sinteticos... seria interessante fechar todos os tipos primeiro ate' pra ver se o fluxo de spec esta' padronizado e cada um tem suas peculiaridades declaradas, quanto mais coisa em comum melhor"*. **EU RECOMENDEI `.9` POR ROI DE BYTES — errado, e e' a REPETICAO do erro que o owner ja' corrigira** (*"vc pensa muito em compressao, eu penso em fluxo que funciona"*). O criterio do `.8` e' ESTRUTURA: **um tipo nao fecha porque compensa, fecha porque foi VERIFICADO**. Float FICA NO `.8`. O que falta nao e' ganho — e' rodar os 5 eixos de conformidade e **DECLARAR AS PECULIARIDADES**: a precisao suja que quebra a escala (`wine.alcohol`) e o fato de o `IntPadSpec` NAO ser reaproveitavel aqui. **FECHADO 2026-08-14** (`2026-08-14-1616-fechamento-float`: 12 bordas + 5 colunas reais nos 5 eixos, **0 falhas**). **CONFORME EM TUDO**: dispatch (uma linha, tag `n`), candidatos (o MESMO `min()` — RLE, seq-RLE, polaridade `n!`/`n!!` e **bN de dominio** `nB77d0`, o mesmo bN de bool/int/string), API (`nature=` processado + FLOOR recusa, `min_len=` aceito — **a porta que o weld de hoje abriu funciona p/ float tambem**; antes eram ValueError), wire (tag no 6, sufixos no 7) e RT. **6 PECULIARIDADES DECLARADAS**: (1) e' a metade flutuante de uma **tag-UNIAO** — `n` e' `int|float` (o `number` do JSON) e o tipo concreto vem da **GRAFIA**, por elemento (`[1,2.5,3]` volta `['int','float','int']`); nenhum outro tipo compartilha tag; (2) **`-0.0` e' distinto de `0.0` e `==` NAO DETECTA** — o wire preserva (`-*!0.0`) mas so' `math.copysign` prova: qualquer teste de RT de float com `==` e' cego pra isso; (3) NaN e ±Inf **recusados fail-loud** (fora do JSON, RFC 8259); (4) a **precisao suja quebra a ESCALA, nao o RT** — `10.0333333333333` impede escala exata e a coluna perde o candidato, mas o round-trip fica perfeito; (5) o **`IntPadSpec` NAO e' reaproveitavel** (verificado `False` nas 5 colunas reais); (6) a grafia canonica e' a do Python (`1e-05`, `1e+20`), imposta pelo guard de re-emissao. **BORDAS**: max-float, subnormal `5e-324`, cientifica nas duas direcoes, uniao int+float e slot nulo TODAS atravessam com RT ok; NaN/+Inf/-Inf recusados. Lab: `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-1616-fechamento-float`. O spec de escala fica ADIADO COM RAZAO ESCRITA — que e' diferente de adiado sem caracterizar. Nota: `experiments/lab/dirty/notas/2026-08/2026-08-14-0430-fechar-todos-os-tipos-no-08.md`. **SINTETICOS**: como o real cobre quase tudo, so' serviriam p/ os regimes AUSENTES (notacao cientifica `1e-5`, negativos com decimal, precisao alta uniforme 16+ casas). Nota: `experiments/lab/dirty/notas/2026-08/2026-08-14-0400-avaliacao-float.md`. **ADENDO 2026-08-14 (pesquisa de literatura, pedido do owner)**: a razao "precisao suja INVIABILIZA a escala" esta' ENFRAQUECIDA — o estado da arte lossless (**ALP**, SIGMOD 2024, adotado no DuckDB) faz exatamente escala decimal-como-inteiro **com EXCECOES por-valor** (patching): escala o vetor e guarda os poucos que nao fecham em grafia plena, em vez de derrubar a coluna inteira. Quando o spec de escala for reaberto, o desenho de referencia e' **escala-com-excecoes**, nao tudo-ou-nada. E a ideia lossless-alterada do owner (`0.333333333333` -> fracao `1/3…12`) virou **H-FLOAT-GRAFIA-01** (lossless, SEM gate — diferente do Pacote 10). **CONSOLIDADO DO CICLO: `docs/theory/float-e-variantes-consolidado.md`** (fonte unica — o que fecha, os dois planos de variante, o parametro de tolerancia, o aviso obrigatorio, a fila, e o registro das constantes notorias). Nota: `experiments/lab/dirty/notas/2026-08/2026-08-14-1739-loss-e-lossless-alterado-pesquisa.md`. **LAB RODADO 2026-08-14** (`experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-1745-grafia-fracional-e-escala-com-excecoes`, 7 sinteticos + 8 bordas + 5 colunas reais, 4 mecanismos, **0 falhas** no RT estrito). **(1) A ESCALA PURA FALHA DE DUAS MANEIRAS, nao de uma** — eu so' tinha articulado a recusa (nenhum k serve; `wine.alcohol`). A segunda e' **PIOR QUE NADA**: um k serve, mas e' enorme, e o candidato INFLA (`owner-sujo` 79 vs 53; `money-com-terco` **188 vs 124** — UM valor sujo em 20 forca k=12 e multiplica a coluna inteira por 10^12). O modo 2 nao aparece como falha: o mecanismo devolve candidato valido e o FLOOR so' nao o usa porque perde. A escala COM EXCECOES resolve os dois — em `wine.alcohol`, onde a pura RECUSA, ela escala em k=1 com **14 excecoes em 2000** e tira **109 B (-3,8%)**. **(2) O NUCLEO JA' TEM O MECANISMO** (levantamento verificado em codigo): `MARKER_LITERAL = '_'` (`natures/templated_checked.py:38`), identico nas 4 natures, desambiguado por EXCLUSAO DE ALFABETO (nao escape); e **`int_pad.py:73-74` (`length_wrong`) e' literalmente o patching do ALP** — o valor que nao cabe vira literal SOZINHO, sem alargar nem recusar a coluna. `int_pad.py:75-78` ja' faz canonicidade por re-emissao. **Nao falta mecanismo, falta a GRAFIA economica da excecao**; medido, o `_` custa 11 B em 14 excecoes. **(3) A GRAFIA FRACIONAL e' solida e quase nao tem onde morar**: 126/126 dizimas fecham byte-a-byte e a re-emissao AUTO-PROTEGE (recusa `2.718281828`, `0.30000000000000004`, `12.3456789`), mas no real sao **9 conversoes em 2000** numa coluna e **ZERO** nas outras 4 — a varredura do corpus explica: `wine.alcohol` e' a **UNICA** coluna com dizima do corpus INTEIRO (9 bancos, 186 colunas, 31 float; nas outras 30, valores com >=10 casas = **zero**). O par de contra-prova isolou a causa do ganho: em `dizima-uniforme` sao 3 B (o RLE ja' resolvia), em `dizima-variada` sao **66 B (-41%)** — o ganho e' de haver dizimas DISTINTAS, nao de grafia curta. **(4) TRES DEFEITOS MEUS, ACHADOS PELO PROPRIO LAB**, todos da familia *mecanismo que nao verifica engana*: epsilon na escala (`<1e-9`) aceita `0.30000000000000004` em k=1 e devolve `0.3` — **lossless que perde calado**; a tag-UNIAO quebra a escala (apaga o tipo, e a excecao int COLIDE com escalado); e sem GUARDA DE MAIORIA o `k=0` "vence" marcando 1716/2000 como excecao, mas em k=0 nao ha' escala — quem decide os bytes ali e' o bN de dominio. |
> | **`T-HORA-SPEC`** | **1,03x** no unico dado real — nao se justifica agora | AVALIADO 2026-08-14 a pedido do owner (*"poderiamos ver a parte de spec de hora, sem data. avalie"*). **(1) Hora quase nao existe no corpus**: varrendo todos os bancos de `Z:`, UMA coluna tem hora e ela e' DATETIME (`online-retail.InvoiceDate`), nao hora pura. **(2) A transformacao hora->segundos rende POUCO em real**: 15.022 -> 14.563 B = **1,03x** (a hora como texto ja' e' bem comprimida pelo OBAT — os `:` sao afixo e os digitos se repetem). Em regimes REGULARES rende muito (batimento 15min ciclico **2,00x**; batimento 1min ordenado **9,05x**) — mas esses sao telemetria/logs, que existem no mundo e NAO neste corpus. **(3) DIFERENCA ESTRUTURAL vs data**: o ordinal do `data-iso` e' ABSOLUTO e monotonico (dias desde 0001-01-01, cresce sem voltar); a hora e' **CICLICA** — volta a zero todo dia, e o seq-RLE ve um salto negativo a cada meia-noite (medido: corpo `*96+900|\\00000`, 96 passos = 1 dia, depois re-ancora). So' e' monotona DENTRO de um dia. **(4) O caso real e' datetime, e a resposta JA' EXISTE** — ver o `T-SPLIT-SINGLE-COL` ao lado. **FECHADA 2026-08-14** (lab `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-2230-fechamento-hora`: 7 regimes sinteticos + 9 bordas + 1 coluna real + a ciclicidade medida em 4 escalas, **0 falhas**). **CONFORME NOS 5 EIXOS**: dispatch (chega como STRING — a hora NAO e' tipo nativo, e' da familia *spec sobre string* como data/cpf/ip), candidatos (o MESMO `min()`: literal, polaridade `!`/`!!` e **bN de dominio** `B7c0` — o mesmo bN de bool/int/float/string), API (`min_len=` aceito, `nature=` processado com FLOOR), wire (sem tag; disc no indice 6) e RT (19/19). **COMUNIDADE MAXIMA**: a hora nao tem caminho proprio em lugar nenhum do nucleo. **A PECULIARIDADE REGISTRADA ESTAVA INVERTIDA**: eu escrevi que a ciclicidade ATRAPALHA (o seq-RLE ve salto negativo a meia-noite) — certo sobre o seq-RLE, **errado sobre o resultado**. Medido, mesmo batimento de 15min: 2 dias **-29,3%**, 3 dias **-46,4%**, 7 dias **-73,0%** do ciclico contra o absoluto. **Ciclar e' REPETIR**: o que o seq-RLE perde o **dedup** ganha (96 distintos em 672 linhas -> `#TCF.8B7c0`). A peculiaridade correta e' que a ciclicidade **troca um mecanismo por outro, e o `min()` faz a troca sozinho** — e' a distincao igualdade x proximidade ja' nomeada no projeto. **O ORDINAL E' COMPLEMENTAR, NAO SUBSTITUTO**: segundos-desde-meia-noite ganha **94,4%** a 1 dia (progressao aritmetica perfeita -> seq-RLE, 751->42 B) e so' **6,9%** a 7 dias (o wrap quebra a progressao). Um spec que emitisse ordinal SEMPRE seria pior que o nucleo na maioria dos dias. **7 PECULIARIDADES DECLARADAS**, com 3 proprias so' dela: (4) tem **grafia valida-na-norma e irrepresentavel-no-pivo** — `24:00:00` e' ISO legal (removido em 2019, REINTRODUZIDO em Amd 1:2022), proibido em RFC 3339, fora de `0..86399`, e o Python recusa; nenhum outro tipo fechado tem isso; (5) **nao pode validar leap second sozinha** — `23:59:60` so' e' legitimo em 30/06 ou 31/12, e uma coluna de hora **nao tem a data**; (6) **a deteccao e' minada de falsos positivos** (varredura de 102 colunas): `0..86399` pega **44 colunas** que nao sao hora (`wine.pH`, `adult.age`, `l_discount`), `HHMMSS` pega chaves (`o_orderkey`, `fnlwgt`), e `AM`/`PM` por substring pega **`uf_sigla='AM'` — o Amazonas**. **CORPUS (full-scan, 102 colunas)**: hora pura **NAO EXISTE**; a unica parte-hora e' o `InvoiceDate` com **segundo constante `00`**, 774 distintos, 97,61% em 08-18h, sem sabado, e **95,71% de repeticao adjacente** (o `*N|` ja' cobre). O banco que traria hora de verdade (`beijing-pm25.db`) esta' com **0 bytes**. **BORDAS**: as 9 atravessam byte-a-byte porque o nucleo trata hora como string e **nao a interpreta** — um SPEC e' que teria de recusar `24:00`, `:60`, `-00:00` e offsets sub-minuto (sem volta) e tratar separador/fracao/offset como **flag de coluna**, nao grafia por celula. O spec fica **ADIADO COM RAZAO ESCRITA E NUMERO**. **ADENDO 2026-08-14 (pergunta do owner: *"talvez se ele tiver uma forma binarizada propria para o espaco de numeros dele"*)**: medido no lab `2026-08-14-2320-hora-binarizada-pelo-tipo` — a binarizacao pelo ESPACO DO TIPO (17 bits, dominio nao viaja) **tem nicho, e o nicho comeca exatamente onde o `bN` acaba** (`MAX_W=8` = 256 distintos, um limite de NAMESPACE do header, nao de compressao). Na coluna real (k=564): **-46,5%**. Mas **binarizar DESTROI a estrutura** — onde ha' progressao o ordinal DECIMAL vence 77x a 114x. Registrada como **H-DENSE-MODE-03** com 3 condicoes medidas (k>256 E irregular E leitura terminal). Este mecanismo REABRE o tipo por via nova, sem invalidar o fechamento. **SE virar spec um dia**: desenho irmao do `data-iso` (segundos desde meia-noite, auto-contido, sem parametro), com a ressalva da ciclicidade, e id na familia `dt*` ja' reservada no ADR-0041 — nao em prefixo novo. Nota: `experiments/lab/dirty/notas/2026-08/2026-08-14-0330-avaliacao-spec-de-hora.md` |
> | **`T-SPLIT-SINGLE-COL`** | **7,13x num datetime REAL** (61.856 -> 8.675 B) — o melhor numero que este ticket ja' teve; e **TERCEIRA avaliacao seguida a convergir nele** (data 1,35-2,7x; datetime 7,13x; float vence em 4 de 12 colunas). E' o item de maior retorno da fila **e nao precisa de spec nenhum**; +mensal 1085->700 B, uteis 2454->903 B | **EVIDENCIA NOVA 2026-08-14** (avaliacao de spec de hora): o `InvoiceDate` do online-retail (3000 linhas espalhadas, 304 datas x 603 horas) custa **61.856 B em single-col** e **8.675 B em multi-col de UMA coluna**, onde o `_best_of` escolhe `split` SOZINHO — **7,13x**, sem spec, sem parametro, sem nada novo. Bate as alternativas todas: epoch como um inteiro da' 26.887 B (2,30x) e separar a mao (data c/ spec `dt` + hora em segundos) da' 17.559 B (3,52x). E' a mesma classe 'o candidato existe e a rota nao consulta'. Nota: `experiments/lab/dirty/notas/2026-08/2026-08-14-0330-avaliacao-spec-de-hora.md`. o split estrutural (ADR-0026, marcador `%`) **ja' corta `ano\|mes\|dia`** e ja' esta' soldado — mas e' candidato so' do multi-col (`min(tcf, raw, dict, split)`); a rota **single-col flat NAO o consulta**. Medido (lab `1943`): no multi-col o split VENCE nas colunas mensal e uteis (`#TCF.8M%dt`), e no diario perde (e faz bem — 820 vs 414). **RESSALVA DE ORDEM — MEDIDA 2026-08-15** (lab `2026-08-15-0020-datetime-grafias-regimes-mecanismos`, par de contra-prova: os MESMOS 2000 instantes, mesma cardinalidade, **so' a ORDEM muda**): **o split VIVE da ordem**. Ordenado 842 B; embaralhado **6331 B = +651,9%** — ele passa de MELHOR candidato a PIOR que todos, e o vencedor vira o `dict` (2864). O `core` tambem cai (+160,9%). **Os UNICOS imunes sao `bN` (+0,3%) e `dict` (+0,4%)** — os de IGUALDADE pura; tudo que explora vizinhanca (OBAT, HCC, seq-RLE, split) desaba quando a vizinhanca some. E' a distincao *igualdade x proximidade* aparecendo como propriedade de ROBUSTEZ. **CONSEQUENCIA PARA O 7,13x**: ele foi medido na `InvoiceDate`, que e' **100% nao-decrescente com 95,71% de repeticao adjacente** — logo boa parte daquele numero e' credito da ORDENACAO, nao do split. O ticket nao cai, mas a regua honesta passa a ser *"o split rende X EM COLUNA ORDENADA"*, e qualquer promocao a default teria de consultar a ordem (o `min()` ja' faz isso sozinho). **Terceira ocorrencia da classe "o candidato existe e a rota nao o consulta"** (antes: `T-BN-TIPADO` e o FLOOR da nature que nao via o bN). **BATERIA MULTI-VETOR 2026-08-09** (lab `2228`): alem do custo de CPU (+47-54% SEMPRE, mesmo quando perde), o corpo do split e' um **multi-col EMBUTIDO** (blocos por coluna-campo) — **NAO streama por linha**. Classe do modo C (ADR-0036): decodavel, nao-emitido-por-default, opt-in. VEREDITO: **VARIANTE/perfil** (`compacto`/`lote`), nao default |
> | **`H-TH-02` / `H-PERF-04` (Patricia)** | o indice NAO indexa em coluna de data | evidencia NOVA 2026-08-09 (lab `1943` S1): o indice do OBAT e' hash de **trigrama** (ADR-0009), nao Patricia. Em `diario ISO` e `uteis ISO` da' **1 bucket com 100% dos unicos** (todo `2026-...` cai em `202`) — o indice vira lista e o "achar o melhor pedaco" vira O(n) por string. A `H-PERF-04` foi adiada dizendo exatamente "precisaria Patricia trie (out of scope agora)"; a medicao de hoje e' evidencia a favor de reabrir. Unico dos tres encaixes que muda COMO os pedacos sao achados, nao QUAIS candidatos competem |
> | **`T-DATAISO-GUARD-SEM-TESTE`** (NOVO 2026-08-15) | a UNICA classe que depende do guard de re-emissao do `data_iso` **nao esta' pinada em teste nenhum** | achado no levantamento da receita (frente 1). O `classify_value` do `data_iso` tem 3 gates: largura (barato), parse, e **re-emissao**. A classe **exclusiva** do terceiro e' a week-date estendida `YYYY-Www-D` — ela tem **exatamente 10 chars**, entao e' **invisivel ao gate de largura**, e o `fromisoformat` a aceita desde 3.11 (`2021-W01-1` -> `2021-01-04`). Medido: **735 formas validas** so' nos anos 2021 e 2026. **O teste existente (`test_natures.py:597-608`) pina `20191204`** — que tem 8 chars e o **gate de LARGURA ja' recusaria**. Ou seja: o guard que a docstring chama de load-bearing nao tem cobertura propria. Barato de corrigir (1 caso), e vale para qualquer spec novo que replique a receita |
> | **`T-DATA-GRAFIAS-IRMAS`** | **2 de 10 colunas reais de data nao sao pegas** (o spec nem se aplica) | medido no lab de inspecao 2026-08-13 (`2026-08-13-1650-inspecao-data-estado-atual`): das 12 colunas de data do corpus (10 distintas — **CONTAGEM CORRIGIDA 2026-08-15**: esse "10" e' o tamanho da lista `FONTES` do EXP-017 (`extrai.py:37-51`), que e' uma **SELECAO**, nao o inventario; ela conta `orderdate` duas vezes (sf001 e sf01 com offset) e **OMITE as 3 colunas de `lineitem` do `sf01`**. Varredura por VALOR: **13 colunas fisicas**, **9 identidades independentes** — as 4 do `tpch-sf001` sao prefixo do `tpch-sf01`, como o proprio EXP-017 ja registrava p/ `orderdate`. Nao muda nenhuma conclusao medida), o `data-iso` venceu em 9 com -24,8% agregado — mas nas 3 restantes a apply-rate e' **0%** (`length_wrong` em 3000/3000): elas nao sao `YYYY-MM-DD`. Grafias observadas em dado REAL: `receita-data-inicio` = **`YYYYMMDD`** (8 chars, compacta) e `retail-invoicedate` = **`YYYY-MM-DD HH:MM:SS`** (19 chars, datetime). O FLOOR se comportou certo (recusou, wire byte-identico ao core) — o buraco e' de COBERTURA, nao de competicao. O mapa de ids do ADR-0041 ja' reserva `dtm` p/ datetime; **`YYYYMMDD` compacta NAO tem id reservado**. Precedente CPF/CNPJ: uma grafia = um spec irmao, nao um adivinhador de formato (`data_iso.py` e' explicito sobre isso). Nao decidido — informacao pro mapa |
> | **`T-MAX-PERIODO-31`** | **ENQUADRAMENTO SOB REVISAO 2026-08-13** — o teto nao devia sair do calendario | **O ALERTA DO OWNER (2026-08-13) BATE AQUI**: `MAX_PERIODO = 24` esta' documentado no codigo como *"Cobre mensal (12) e quinzenal-ano (24)"* — justificativa de CALENDARIO para um mecanismo GENERICO (o comentario ao lado cita "ids por turno `10,10,10,50`"). Este ticket pede 31 *"porque dia-do-mes"* e a inspecao de 2026-08-13 quase pediu 48 *"porque bissexto"*: a escalada 12->24->31->48 e' o sintoma de derivar do DOMINIO. O teto REAL e' orcamento de DETECCAO (o detector e' O(n*P)) — mesmo eixo da latencia, que o owner apontou como o real. Reformular como *qual P cabe no orcamento de tempo do encode*, com o FLOOR decidindo se paga; so' entao decidir o numero. Ver `2026-08-13-1740-latencia-como-eixo`. **EVIDENCIA VISUAL** (lab de inspecao `2026-08-13-1650`, caso `a5-primeiro-do-mes-240`): 240 datas do dia 1 de cada mes saem em **9 marcadores** de periodo 12 re-ancorando a cada 48 linhas — `*26~31,28,31,...|` depois `*48~31,30,31,...|` TRES VEZES IDENTICOS. O ciclo verdadeiro do calendario e' **48** (4 anos, por causa do bissexto) e o teto 24 o exclui; os 3 marcadores repetidos seriam UM so'. 323 B contra 455 do core (ganho modesto onde o mecanismo daria muito mais). Wire inspecionavel em `intermediates/a5-primeiro-do-mes-240.anatomia.txt` | o teto `MAX_PERIODO=24` do detector periodico (ADR-0040) exclui os periodos NATURAIS de calendario 28/29/30/31 (medido no lab `2228`). Subir pra 31 custa +7 iteracoes no laco O(n*P). Weld de 1 linha; **aguarda aprovacao** |
> | **`T-SPEC-SEM-CARIMBO`** | **32 -> 15 B** na transmissao (o header inteiro sai do fio) | decisao 4 do ADR-0041, tirada do escopo do weld A por decisao do owner (2026-08-13): e' CAPACIDADE NOVA, nao rename. Aplicar o spec e NAO mandar o id junto, obrigando a outra ponta a declarar (contrato-nas-pontas aplicado ao spec). **As duas pontas tem de ir juntas**: hoje `encode(vals, nature=SPEC, stamp=False)` carimba assim mesmo (o `stamp=False` e' ignorado na rota da nature) e `decode(corpo_sem_tag, nature=SPEC)` devolve o PAYLOAD CRU (o parametro so' age quando ja' ha' tag) — emissao sozinha produziria wire que a propria API nao le'. **NAO e' o `stamp=False`**: aquele tira o header inteiro (orfao), este tira so' o `:id`; sao eixos distintos e combinaveis. Preco aceito: sem o id o wire fica indistinguivel de uma coluna de inteiros — casa com a assinatura-de-contrato fail-loud da direcao de contrato externalizado. Desenho fechado no ADR-0041 §4; falta so' o weld |
> | **`T-SPEC-IMPOSTOR`** | **corrupcao CALADA emissivel hoje** (200 valores deslocados 1000 dias, zero excecao) | achado da cacada do weld A (2026-08-13) e **reproduzido IDENTICO no commit anterior — PRE-EXISTENTE, nao regressao**. Um duck-type que se declara com a identidade do core (`name` E `wire_id` iguais) mas transforma DIFERENTE vence o FLOOR, carimba `:dt`, e o decode resolve pelo registry -> aplica o spec CORE. A fronteira de confianca da emissao e' o `name` (registry-first no decode), e ela e' pre-weld. **Por que nao foi fechado no weld A**: apertar exige DECIDIR entre (a) quebrar o clone funcional compilado de `.dsl` pelo gadget (que legitimamente se chama `cpf`) ou (b) verificar equivalencia por AMOSTRAGEM contra o spec do registry na porta do encode (k valores, custo ~0 perto da transformacao que ja' roda; pega divergencia sistematica, que e' como impostor e clone-bugado se manifestam; NAO e' prova total). Desenho (b) e' o candidato. O weld A ESTREITOU o buraco: de 'coincidir o name' para 'coincidir name E wire_id' — `replace(SPEC_CPF, name='custom')` (que herda o wire_id) agora e' recusado. PINADO em `TestLacunaImpostorDuckType` (o teste falha quando o ticket fechar) |
> | ~~`T-NOME-SPEC-CURTO`~~ | **SOLDADO 2026-08-13** (weld A ADR-0041, suite 1239 → **1247**) | MEDIDO 2026-08-10: nao ha' formalizacao nenhuma do nome de spec (`name: str`, sem limite/validacao/grafia; o ADR-0027 fixou ONDE a tag mora, nunca COMO se escreve). 3 dos 4 specs ja' cabem em 8 chars (`ip`/`cpf`/`cnpj`); **so' `data-iso` destoa**, e e' o unico com hifen (1 B que nao informa). Custo por payload: n=12 -> 19,1%; n=600 -> **28,1%**; `dtiso` deixaria o wire **9,4% menor**. Bate direto na diretriz de payload minusculo (O-FMT-15/16). **PESQUISA PROFUNDA 2026-08-12** (nota `2026-08-12-tres-frentes-onde-atacar`): o id viaja em TRES gramaticas de wire com parses DIVERGENTES (single=primeiro `:`, multi=ultimo, .8H=ate' `,]}` — nome `a:b` quebra em multi e passa em .8H); ZERO validacao (nome com `,` explode como 'referencia a fragmento inexistente' — erro ENGANOSO); e o achado forte: **o comprimento do id FLIPA o FLOOR** — em N=11-15 diarias a nature PERDE com `data-iso` (47 B) e VENCE com `dt`/`d` (43-44): o nome longo SUPRIME a propria nature no payload minusculo. `dtiso` captura 2 flips; `dt`/`d` capturam 5. PROPOSTA FECHADA: ADR com regra `^[a-z][a-z0-9]{0,7}$` + validacao FAIL-LOUD em 2 pontos (registro + emissao); **minusculas-only e' decisao carregada** — reserva MAIUSCULA/pontuacao pros sufixos de rota que o T-NATURE-CANDIDATO-BN pode trazer pra MESMA linha (desarma o conflito lexicalmente); tabela de reserva de ids (1 char = 26 slots; terceiros = prefixo `x`). MIGRACAO LIBERADA: baselines NAO re-pinam (zero nature nos suites), wire velho falha loud, e a valvula runtime ja' existe (`decode(w, nature=dataclasses.replace(SPEC, name='data-iso'))`, decoder.py:71). De carona: registry gadget nao semeia data-iso (gap); view.py:156 usa decode_value cru (None-slot). **ADR-0041 ESCRITO (proposto) 2026-08-12** — o enquadramento MUDOU pela correcao do owner: nome-legivel x id-curto nao sao ALTERNATIVAS, sao PLANOS distintos (codigo x dado x contrato), e o desenho pede os dois. O ADR fixa 4 decisoes: (1) tres planos separados; (2) regra `^[a-z][a-z0-9]{0,7}$` fail-loud no registro E na emissao (minusculas-only reserva MAIUSCULA/pontuacao pros sufixos de rota); (3) a resolucao compara **`wire_id`**, nao `name` — obrigatorio, senao o rename QUEBRA o out-of-band (medido: `decode(wire ':dt', nature=SPEC_DATA_ISO)` -> erro de divergencia); (4) modo SEM-CARIMBO (aplica o spec e nao manda o id junto: **32 -> 15 B**), que hoje esta' quebrado nas DUAS pontas (`stamp=False` e' ignorado na rota da nature; `decode(corpo_sem_tag, nature=)` devolve payload cru) e e' parametro NOVO, nao o `stamp=False`. PRECEDENCIA no decode: ja' soldada e mantida (dado vence; funcao ESTENDE o registry; divergencia = fail-loud); o `force` fica pra estudo. O mapa de ids (`dt` + familia `dt*` + `x*` p/ terceiros) e' **escolha revisavel ate' o 1.0** — a ESTRUTURA e' o que congela. **AS 4 DECISOES FORAM TOMADAS pelo owner (2026-08-13), uma a uma**: (1) DOIS campos; (2) regra RESTRITIVA `^[a-z][a-z0-9]{0,7}$`; (3) resolucao ESTRITA (so' o wire_id vigente — os 14 wires historicos falham alto e se leem out-of-band, coerente com ADR-0024); (4) o modo sem-carimbo SAIU do escopo e virou `T-SPEC-SEM-CARIMBO`. **CORRECAO medida no caminho**: a justificativa 'minusculas-only e' necessidade tecnica' NAO se sustentava — `DT`/`8d`/`ab_c`/`x-y` fazem RT hoje; varrendo os 33 chars de pontuacao so' `,` e `:` quebram. A regra restritiva ficou por CONVENCAO (previsibilidade + espaco de prefixo + imunidade a separador futuro), nao por necessidade — e o ADR foi corrigido. **WELD A SOLDADO 2026-08-13** (aprovacao 'pode soldar'): campo `wire_id` nos 3 dataclasses (fallback name; data-iso = `dt`); `_register` atomico montando os 2 planos (SPEC_REGISTRY por name INTACTO + _WIRE_REGISTRY por wire_id); validacao de emissao NA PORTA do encode (a rota .8H tem try/except que cairia pro piso CALADO se a validacao fosse interna — pin: as 3 rotas recusam); resolucao estrita por wire_id; gadget semeado com data-iso. **ACHADO DO WELD — a MASCARADA**: `replace(SPEC_CPF, name='custom-cpf')` HERDA wire_id='cpf' — emitiria `:cpf` e o decode resolveria o spec CORE, corrupcao CALADA (buraco NOVO dos 2 planos; pre-weld id=name, nao existia). Fechado na porta: wire_id do registry exige name IGUAL ao do dono (check por NAME de proposito — clone .dsl do gadget chamado 'cpf' passa, fronteira pre-weld preservada; igualdade de dataclass nao serve, regex/callables comparam por identidade). PINS: flip do FLOOR N=10 core / N=11-12 `:dt` (o rename DESTRAVA a nature no payload minusculo); 11 grafias recusadas x 3 rotas; registro atomico; wire historico falha alto + valvula `replace(wire_id='data-iso')` le + divergencia fail-loud; telemetria no plano do CODIGO. Baselines byte-pinned NAO re-pinaram (verificado, zero nature nos suites). Falta da familia: `T-SPEC-SEM-CARIMBO` (ticket proprio) |
> | **`T-LAZY-BYPASS-ARITMETICO`** | filtro de data em **O(1) no tamanho do run**, hoje O(n) | MEDIDO 2026-08-10: o `tcf.view` ja' filtra data (`where(ano==2025)` -> 365 linhas, `where(mes==03)` -> 93, com `select` cruzando coluna), mas **materializa 100%** — decodifica tudo e filtra depois. As NOTAS do `view.py` (L3, 2026-06-16) concluiram que agregar runs no modo-tcf NAO era separavel porque OBAT+HCC entrelacam, e que havia **0 colunas "clean-numeric"** no corpus. **O SPEC CRIOU essa condicao**: coluna de data com spec vira corpo de **UMA linha** (`*900+1\|;9617`; uteis: `*900~1,3,1,1,1\|`). Payload ordinal e' MONOTONICO -> filtro de data = intervalo aritmetico -> `count`/`where`/`min`/`max` em duas divisoes, sem expandir. GENERALIZA p/ qualquer spec de alvo inteiro monotonico (contrapartida de leitura do "spec orienta"). **PESQUISA 2026-08-12**: (1) **BUG real e silencioso no view soldado, emissivel HOJE**: coluna nature que vence em modo dict (`#TCF.8M@1a9=dt:data-iso,@v`) responde where/group_count pelo PAYLOAD ordinal — `where('dt','2025-06-20')` = 0 onde a verdade e' 133, SEM erro (pior classe); **FIX SOLDADO 2026-08-12** (aprovacao do owner): a causa-raiz era DOIS CAMINHOS de reversao, um so' revertia — agora ha' fonte unica `LazyTCF._reverte_nature`, usada por `_col` E por `_dict_parts` (reverte nos K unicos, laziness intacta). De carona, o `_col` passou a usar o WRAPPER DE MODULO em vez do metodo cru do spec (trata o slot nulo, como o decoder ja' fazia). Teste de regressao `test_lazy_tcf8_nature_em_modo_dict_reverte_no_where_e_group` — verificado que FALHA com o fix removido. Suite 1238 -> **1239**. (2) **single-col no view e' DISPATCH-ONLY** (~20-25 linhas): LazyTCF montado a mao sobre `#TCF.8 :data-iso` roda RT/where/sum perfeito **inclusive wire PULSADO 2x300** (paridade por construcao via _decode_column) — o caso de stream do owner, e onde as frentes view+pulso se ENCONTRAM sem tocar formato. (3) bypass aritmetico MEDIDO: `ano=2025` num run de spec = **12us vs 12.285us (1000x), 0 B materializados**, indices identicos, compoe com sum via Filtered(parent,idx). (4) o view acompanhou o ADR-0040 (`*N~`) sem mexer em nada — paridade por construcao, registrar como propriedade. Caminho: fix bug [.8] -> dispatch single-col [.8] -> `entre=(lo,hi)` em 3 camadas + bypass [.9]. **O LADO `.8H` MEDIDO 2026-08-15** (lab `0800-view-e-colunas-tipadas`, 10 formas de wire x tabela 5000x5 x 3 variantes, 0 falhas de RT) — este ticket cobria o single-col; o `.8H` nunca tinha sido medido, **e e' la' que a tabela TIPADA mora**: (1) **o view abre 2 de 10 formas, so' as `.8M`** — recusa as 7 single-col E o `.8H` inteiro, todas com a mesma mensagem (`view.py:68`); (2) **a causa nao esta' no view**: `_tabela_flat` (`encoder.py:134-147`) termina em `all(isinstance(x,str) ...)`, entao **UM valor nao-`str` em qualquer coluna manda a tabela inteira pro `.8H`** — e a docstring registra que e' deliberado (parecer 2340 §2). Logo *"view p/ coluna tipada"* NAO e' lacuna do view, e' consequencia do DISPATCH um nivel acima; (3) **o preco medido**: mesma tabela retangular = 76.803 B em `.8M` contra **154.521 B** em `.8H` (**+101,2%**), e a pergunta `data>=2020` custa 18,7 ms pela view (tocando **19,9%** do blob) contra 99,4 ms de decode completo do `.8H` (**5,3x**, dev-run) — a tabela tipada paga DUAS vezes: dobro de bytes e perda do acesso parcial; (4) **PAR DE CONTRA-PROVA que troca o culpado**: forcar `.8H` SEM tipar nada custa **+78.134 B** e tipar 2 colunas DENTRO do `.8H` custa **-416 B** — **tipar e' de graca, o que custa e' o ENVELOPE**. A frase intuitiva "tipar dobra o tamanho" esta' errada. **DUAS SAIDAS**: (a) gramatica de tipo no `.8M` + rotear tabela retangular tipada pra la' — a view alcanca **sem tocar na view**, e resolve os +101,7% junto; (b) ensinar a view a ler `.8H` — resolve o acesso, NAO resolve os bytes. A (a) e' o mesmo movimento do `T-UM-CAMINHO-SO` |
> | **`T-VIEW-PRED-POSICIONAL`** (NOVO 2026-08-15) | **resposta de consulta ERRADA, sem erro** — `where` posicional devolve 0 | achado colateral do lab `0800-view-e-colunas-tipadas`. A assinatura e' `where(col, value=None, *, pred=None)`; passar o predicado POSICIONALMENTE e' sintaticamente valido e cai no ramo `v == value`. Como uma string nunca e' igual a uma funcao, o filtro casa **zero linhas** e devolve um `Filtered` vazio — **o predicado nunca chega a ser chamado** (verificado com acumulador: n=0). MEDIDO: `where('data', lambda x: x>='2020-01-01').count()` = **0** onde a verdade e' **2675**; com `pred=` da' 2675. Mesma familia do `T-NATURE-IGNORADA-CALADA` (a API aceita e nao faz o que foi pedido, calada) mas **PIOR**: la' o wire sai certo e so' a expectativa quebra, **aqui a resposta da consulta e' errada**. Fecha com um `raise` de uma linha (`callable` em `value` -> `TypeError` dizendo que e' `pred=`). BARATO e INDEPENDENTE — nao espera decisao nenhuma. Evidencia de que morde: **eu cai nela escrevendo o lab do proprio view** |
> | **`T-POLARIDADE-COME-NOME`** (NOVO 2026-08-16) | **RT QUEBRADO CALADO** — o dado sai do round-trip diferente do que entrou, sem warning | **A PIOR CLASSE DO PROJETO**, achado no mapeamento de M/H e reproduzido em lab (`1330-polaridade-come-nome-de-coluna`). `decode(encode({"obs.": [5 valores]}))` devolve a chave **`"obs"`**; com pontuacao DOBRADA (`"obs.."`) **os VALORES tambem corrompem**. MECANISMO (verificado): a polaridade e' camada de BORDA, *"a PRIMEIRA coisa do decode"* (`decoder.py:150-161`), e roda `_separa_sufixo_polaridade(line1[6:])` — no `.8M` esse `line1[6:]` e' `M<meta>`, e o fim do meta e' o **NOME DA ULTIMA COLUNA** (forma `min_header` omite o size da ultima, `multi/core.py:413-414`). A polaridade nao conhece a gramatica do `.8M`: ve `Mobs.`, separa `('Mobs','.')`, e o parser recebe coluna chamada `obs`. ALCANCE MEDIDO (64 nomes = `string.punctuation` x {1,2} repeticoes, 26 valores fixos): **`.8M` 48/64 = 75,0% RT falso** (24 perdem so' a chave, **24 corrompem chave E valores**); **`.8H` 38/64 = 59,4%**, mesmo mecanismo — o `.8H` **NAO e' controle**; **0 warnings em todo o sweep**. Escapam 16, os que terminam em `* , : = \ ^ | ~`. **CONTRA-PROVA que isola a causa**: a MESMA coluna com uma SEGUNDA ao lado da **64/64 RT ok** — com 2+ colunas o meta ganha `,`/`=`, o nome deixa de ser o fim da linha 1, e a polaridade nao o alcanca. **O defeito e' da COLUNA UNICA**. **POR QUE A SUITE NAO PEGOU**: o gatilho e' o MODO que vence o `min()`, porque o modo poe ou nao um prefixo antes do nome — n=3 sai `#TCF.8M!obs.` (modo raw, prefixo `!`) e o RT FECHA; n>=5 sai `#TCF.8Mobs.` (modo tcf, prefixo vazio) e QUEBRA. **Qualquer teste de RT com coluna pequena passa.** E' a 6a recorrencia da familia do `T-GRAFIA-CHECKLIST` (*"a frase no ADR nao impediu — o teste e' que impede"*), e a PRIMEIRA **entre camadas** em vez de dentro de uma. Nomes reais que caem: `obs.` `qtd.` `valor_r$` `medida(m)` `id#` — `.` final e' comum em export de planilha. **NAO CONSERTADO** (src/tcf intocado): exige aprovacao e decidir onde cortar — escapar o nome contra o alfabeto da polaridade no emissor, ou ensinar a polaridade a nao agir quando o disc e' `M`/`H`. Nao varrido: Unicode, `drop_names=True`, 3+ colunas |
> | **`T-8H-UM-CANDIDATO-SO`** (NOVO 2026-08-16) | **99,986% do overhead do `.8H` em tabela retangular tem UMA causa so'** | medido no mapeamento de M/H e **reverificado a mao**. adult-census n=2000, 15 colunas, RT True nos tres: `.8M` **41.925 B** · `.8H` **76.949 B** (+83,5%) · `.8M(fallback=False)` **76.944 B**. O residual `.8H - .8M(nf)` e' **5 B (0,0065%)**, e **os corpos sao byte-IDENTICOS** (76.717 B nos dois). Ou seja: **o conjunto de CANDIDATOS explica 35.019 de 35.024 B**. Os 5 B restantes sao so' grafia do size no meta (56 digitos decimais no `.8H` contra 51 hex no `.8M`). CAUSA no codigo: `hierarchical.py:502` comprime cada coluna com `_encode_col(..., stamp=False)`, e `encoder.py:461-466` faz `if stamp is False: return body` — **return ANTECIPADO**, antes do bloco que monta os candidatos bN (`encoder.py:479-492`). O `.8H` nao *escolhe mal* entre candidatos: **ele nunca chega ao `min()`**. A exclusao esta' DECLARADA no proprio codigo (`encoder.py:474-475`: *"orfao (`stamp=False`) nao tem cabecalho onde declarar"*) — e' fronteira conhecida, motivada por falta de lugar no wire pra anunciar o modo, nao esquecimento. **CORRIGE O ENQUADRAMENTO ANTERIOR**: o lab `0800` atribuiu os +101,7% ao "envelope `.8H`" — esta' certo que nao e' a tipagem (tipar custou -416 B), mas **o "envelope" e' especificamente o candidato unico**, nao mascara/meta/framing. **RESSALVA**: o refutador adversarial deste achado NAO RODOU (morreu no limite de gasto); a decomposicao foi reverificada a mao e replica byte-exato, mas o teste de dado desalinhado (outra cardinalidade, com nulls, outro n) **nao foi feito** |
> | **`T-META-COLISAO-NOME-POSICIONAL`** (NOVO 2026-08-16) | decode de wire estrangeiro **PERDE COLUNA CALADA** quando nome explicito colide com posicional | reproduzido no lab `1450-ordem-de-colunas-no-M` (bloco 3b, fluxo invertido): wire a mao `#TCF.8M!3,!3=0,!fim` — coluna ANONIMA na posicao 0 (decoda `'0'`) + coluna NOMEADA `"0"` -> as duas viram a chave `'0'`, o dict SOBRESCREVE, **header declara 3 colunas e o decode devolve 2**; os valores da anonima somem sem warning. Os cheques do BUG-05 nao pegam (bytes e n_rows fecham). O ENCODE nao emite essa forma (chaves de dict sao unicas; `''` tem guard proprio em `multi/core.py:316-326`) — e' so' decode-de-wire-estrangeiro, mas a regua do proprio BUG-05 ("integridade deduzida de graca") cobre: **`len(result) == len(pares do header)` e' 1 linha de fail-loud** em `_decode_multi_impl`. Mexe em src, aguarda aprovacao. Nota-mae §4.4 |
> | **REGISTRO — mapa de estagios e soldas do `.8M`** (2026-08-16, a pedido do owner: maleabilidade p/ cache/buffer/paralelo/stream + "TCF como linguagem") | nota `2026-08-16-1510-estagios-e-soldas-do-M.md` + labs `1450` (ordem) e `1400` (header) | **SAUDE: suite completa 1260 passed / 3 skipped** pos-welds de single-col; header integro (invariante de fronteira por assert em todas as permutacoes). **ENCODE em 5 estagios** (E1 valida+stringify / E2 corpo core POR COLUNA — ja' paralelo e byte-identico / E3 candidatos `_best_of` / E4 FLOOR da nature / E5 emissao) e **DECODE em 7** (D0 polaridade..D6 integridade). **4 SOLDAS nomeadas**: (1) **dois IDIOMAS pra mesma ideia** — single-col e' lista+`min()` (`encoder.py:549-600`), `.8M` e' cadeia de ifs (`_best_of`, `core.py:420-434`); unificar o idioma e' o "resumir o multi-col" mais barato e e' pre-requisito do `T-UM-CAMINHO-SO`; (2) **o FLOOR serializa o blob INTEIRO 2x por spec** (`core.py:473-475`) — correto (never-worse global) mas funde decisao com emissao; delta local byte-equivalente e' candidato `.9` com contra-prova obrigatoria; (3) **`_serialize` e' CLOSURE** dentro de `_encode_multi` (`core.py:398-418`) — o leitor `_parse_meta` e' enderecavel, o emissor nao; pro objetivo-linguagem o par emissor/leitor da gramatica tem de ser nomeado; (4) **D6 nao confere `len(result)==len(pares)`** -> `T-META-COLISAO-NOME-POSICIONAL`. **PRONTIDAO dos vetores**: paralelo de encode EXISTE (E2); paralelo de decode NAO existe mas e' SO' orquestracao (offsets todos deduziveis do header — **o header e' o unico coldstart**, formulacao do owner confirmada no codigo); stream de DECODE possivel HOJE (menos a ultima coluna; `min_header=False` remove ate' essa); stream de ENCODE segue bloqueado por sizes-antes-do-body (V2-J, defer 2.0 ja' decidido); memoria: encode materializa tudo (`T-GATES-ANTES` ataca metade). **ORDEM DE COLUNAS (lab `1450`, 4 predicoes declaradas, 0 falhas)**: corpos INDEPENDENTES — RT em qualquer permutacao, corpo por coluna byte-identico, variacao total de **3 B** (so' a escolha da ULTIMA: economiza `len(size_hex)+1`); p/ anonimas **a ordem E' o nome** (reordenar troca os donos CALADO — drop_names exige contrato de ordem fora do fio); a "burla" do owner (posicao como NOME explicito) **ja' e' representavel**: indices canonicos como nomes custam **1,9 B/coluna** e a coluna movida fica achavel por nome em qualquer posicao fisica — nao precisa de formato novo, so' do guard da colisao. **A prova de que os estagios sao reais**: o `view` ja' compoe D2+D3+D4 por fora do decode. Tabela de algoritmos nomeados p/ port (OBAT/HCC/seq-RLE/polaridade/bN/denso/dict-V2B/split/natures/FLOOR/gramatica-do-meta) na nota §6 — alimenta `.9`-legibilidade e o 1.0-Rust |
> | **`T-INT-CONFORMIDADE-DE-FLUXO`** | o int ja' herda **5 de 7** algoritmos; falta padronizar o que o bool tem | ciclo de analise 2026-08-14 (direcao do owner: *"o fluxo tem que ser generalizado... ter codigo exclusivo pros tipos deixa o codigo engessado... precisamos que isso seja uma OTIMIZACAO, nao um padrao do tcf... como mesmo o bool respeita o fluxo, entao e' justo pensar no int tambem"*). **A GENERALIZACAO JA' ESTA' FEITA** e escrita: a docstring de `_tipo_single_col` (`encoder.py:98-112`) diz *"antes so' o bool tinha ramo; generalizado p/ que cada tipo novo seja uma LINHA aqui, nao um bloco novo no encode"* — e e' isso: `return 'b', lambda v: RENDER_B[v]` e `return 'n', str`. **OS 3 PLANOS do owner mapeados no codigo** (e' o ADR-0041 aplicado a tipos): CORE (OBAT/HCC/seq-RLE/polaridade/bN — **nao ve tipo nenhum**, so' linhas de texto); API (`nature=`/`nature_per_col=` — **e' onde esta' o buraco**, so' aceita string); WIRE (a tag do indice 7 + `:id`). **O BOOL RESPEITA O FLUXO — VERIFICADO**: o encode tipado e' UM `min()` de candidatos (`encoder.py:549-600`) = core + polaridade + bN (todos os tipos EXCETO bool) + denso b1/b2 (SO' bool). O bool nao tem rota propria, tem **um candidato a mais**, e a razao esta' escrita no codigo (*'bool NAO entra [no bN]: o denso tem dominio IMPLICITO e vence por construcao'*). **O INT JA' HERDA, MEDIDO**: seq-RLE (23 B), RLE (17 B), bN de dominio tipado (`#TCF.8nB3258`), polaridade (`#TCF.8n!!`), OBAT (`#TCF.8n!`) — **5 de 7**. Falta: denso (exclusivo do bool) e pre-transformacao (spec). **TRIAGEM .8 x .9 pelo criterio do owner** (*'otimizacao, nao padrao'*): **.8 = estrutura** (muda o que e' EXPRESSAVEL) — spec na rota tipada como mais um `candidatos.append`, tag+spec convivendo no `.8H` (exige gramatica nova de meta; apagar o check faria coluna int voltar STRING sem erro), e fechar o `T-NATURE-IGNORADA-CALADA`; **.9 = atalho** (so' muda desempenho do que ja' e' expressavel) — denso para int (o `pack_w` de `bitpack.py` ja' e' parametrizado por largura) e auto-deteccao dos gatilhos. **O OFFPAD SAIU DE CENA 2026-08-14** — e a decisao A/B/C que estava pendente DESAPARECEU. Veio da observacao do owner (*"eu penso que tem int embutido no date, o que faz sentido em parte"*), que esta' certa: o `data-iso` converte ISO -> **ordinal**, que E' um inteiro, e E' um offset. O projeto ja' resolve offset de DUAS formas e **as duas fazem a informacao viajar**: o `data-iso` por BASE CONVENCIONADA (a epoca 0001-01-01, que os dois lados conhecem) e o seq-RLE por ANCORA EMITIDA (`*600+1|\\739617`). O OFFPAD era a unica que nao fazia nem uma coisa nem outra — dai o defeito de medicao. **E MEDIDO: ele nao e' necessario em caso nenhum**: onde ganhava por LARGURA VARIAVEL o PAD da' o mesmo (1..600: 26 B; passo 7: 27 B) e e' auto-contido; onde ganhava por BASE ALTA o problema era **fragmentacao do OBAT**, e so' ajustar `min_len` resolve MELHOR e **sem spec nenhum** — epoch 40 -> **27 B** (ml=12), base-alta 37 -> **26 B**, gigante 46 -> **35 B** (ml=20), com wire limpo `#TCF.8\n*600+60|\\1750000000` (a ancora ESTA' no wire). Sobram **2 alvos, ambos AUTO-CONTIDOS** (PAD e B94) + o `min_len`, que nem e' spec. **De carona, tentacao descartada com medida**: e se o ordinal do date fosse base-94? **2196 B contra 22 B** — a base densa DESTROI a progressao; densidade e aritmetica sao antagonicas, e a docstring do `data_iso` ja' dizia. Nota: `experiments/lab/dirty/notas/2026-08/2026-08-14-0210-offpad-detalhado-e-o-int-no-date.md`. ~~PONTO DELICADO~~: o `OFFPAD` e' o maior ganho mas e' PARAMETRIZADO — 3 caminhos: (A) so' specs auto-contidos no .8 (PAD e B94 sao; OFFPAD espera o meta estendido) — mantem o .8 minimo; (B) o parametro viaja no header agora (extensao de formato no .8); (C) o parametrizado vive so' no contrato-nas-pontas (`T-SPEC-SEM-CARIMBO`). **LAB FEITO 2026-08-14** (`2026-08-14-0032-conformidade-de-fluxo-por-tipo`, 4 tipos x 5 regimes x 3 rotas, **0 falhas**, RT comparado por `type()`): **O FLUXO E' CONFORME** — int, float e str sao **IDENTICOS** nos 5 regimes (constante->RLE, duas-classes->bN, com-nulo->core, progressao->seq-RLE, baixa-card->bN); muda a TAG, nao o MECANISMO. **A unica divergencia e' o bool**, e e' a justificada: onde os outros usam bN ele usa o DENSO, com a razao escrita em `encoder.py:566` (*'bool NAO entra [no bN]: o denso tem dominio IMPLICITO e vence por construcao'*) — nao e' rota propria, e' UM CANDIDATO A MAIS no mesmo `min()`. **RT preserva tipo em 12 de 12** combinacoes (inclui None no meio, float em coluna de int, 2^63). **A PECA QUE FALTA**: `nature=` recusado em coluna tipada nas 3 rotas — e' o 'entra int, spec int, devolve int'. **A ASSIMETRIA QUE SOBRA**: `nature_per_col=` em single-col e' RECUSADO COM MENSAGEM para string e **silenciosamente sem efeito** para tipado — mesma chamada sem sentido, dois tratamentos. **ACHADO DE CARONA**: a rota `.8H` **nao reporta `nature_apply`** (lacuna de INSTRUMENTACAO, nao de funcionalidade — verificado: ela processa a nature, wire 1841->1826 B, header ganha `:cpf`, RT ok). **LISTA DO QUE SOLDAR p/ padronizar o int**: (1) spec na rota tipada [.8, estrutura] — mais um `candidatos.append`, como o bool fez; (2) fechar a assimetria do `nature_per_col` em single tipado [.8, barato]; (3) telemetria de nature no `.8H` [.8, byte-neutro]; (4) denso para int [.9, atalho] — o `pack_w` de `bitpack.py` ja' e' parametrizado por largura. Os itens 1-3 nao mudam um byte de quem nao usa spec. **METODO — 3 CORRECOES DO PROPRIO INSTRUMENTO antes do lab valer**, todas do mesmo erro (tomar 'wire identico' como prova de 'parametro ignorado', quando pode ser o FLOOR recusando): 1a usou spec que nao mordia os dados; 2a usou spec que mordia mas o FLOOR podia recusar; 3a adotou telemetria e o `.8H` apareceu como falso-positivo — **verificado a mao ANTES de virar reporte**. Criterio final combina os dois sinais e esta' documentado em `_vered()`. NAO houve verificacao adversarial externa — foi auto-correcao. Lab: `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-0032-conformidade-de-fluxo-por-tipo` | Nota: `experiments/lab/dirty/notas/2026-08/2026-08-14-0100-tipos-como-fluxo-nao-como-ramo.md` |
> | **`T-NATURE-IGNORADA-CALADA`** | o usuario pede spec e recebe outra coisa **sem aviso**, em 3 situacoes — **+1 INVERSA achada 2026-08-14** | VERIFICADO A MAO 2026-08-13/14 (investigacao de 4 lentes sobre a rota tipada). O portao principal e' fail-loud (`encode([1,2,3], nature=SPEC)` -> ValueError), mas AO LADO dele: (1) **`nature_per_col=` na rota TIPADA e' aceito e DESCARTADO CALADO** — `encode([1,2,3])` e `encode([1,2,3], nature_per_col={'x':SPEC})` dao wire **byte-identico**; causa: o rejeitador em `encoder.py:349` esta' condicionado a `_lista_flat`, FALSO p/ lista tipada; (2) **mesma classe no multi-col**: `nature_per_col={'ZZZ':SPEC}` com coluna INEXISTENTE e' descartado calado (`encoder.py:625-633`, `if name in data`); (3) **`decode(wire_tipado, nature=SPEC)` e' ignorado calado** — `decode(encode([738886,738887]), nature=SPEC_DATA_ISO)` devolve os inteiros; causa: `decoder.py:175-176` roteia p/ `_decode_typed` antes de qualquer tratamento de nature, e `_decode_typed` nem recebe o parametro (no disc `''` o ignorar e' DOCUMENTADO e justificado pelo FLOOR; aqui nao ha' justificativa registrada). **A SITUACAO (3) ENCOLHEU — RESOLVIDA COMO COMPORTAMENTO pelo weld EXP-018, verificado a mao 2026-08-15**: `_decode_typed` **agora RECEBE** `nature` (`decoder.py:176-178`, com o comentario do weld) e o USA quando o header tipado carrega `:id` (`decoder.py:415-421`). Quando o header NAO tem `:id` (`resto == ''`, `decoder.py:423`) ele continua ignorando — e **isso e' CORRETO**, pela MESMA razao pos-FLOOR do stamp/orfao (`decoder.py:236-240`): sem `:id` o wire significa DEFINITIVAMENTE valores originais, e aplicar o spec ali corromperia. Sonda 2026-08-15: `decode(encode([738886,738887]), nature=SPEC_DATA_ISO)` -> `[738886, 738887]`, que e' a resposta certa. **O QUE SOBRA DA (3) e' so' a LACUNA DE DOCUMENTACAO** — o ramo `resto == ''` nao tem o comentario que o ramo do stamp tem. Ticket agora e' **3 situacoes + 1 lacuna de comentario**, nao 4 bugs. **AS (1) E (2) CONTINUAM ABERTAS, re-medidas 2026-08-15**: `encode(ints)` e `encode(ints, nature_per_col={'x':SPEC})` seguem byte-identicos, e coluna inexistente segue aceita sem erro. **A (4) e' DEPENDENTE DE n** (re-medida 2026-08-15 com `SPEC_CPF` sobre horas `HH:MM`): n=16 o FLOOR recusa (124=124 B), n=48 carimba e vence (368->357 B), n=96 carimba e vence (792->671 B), n=200 o FLOOR recusa de novo (1792=1792 B) — nao e' monotonica, entao o gate que a fechar tem de ser por APPLY-RATE (0% aqui), nao por tamanho. **Nenhum corrompe dado** — o wire esta' certo; o que quebra e' a expectativa, e o projeto invoca 'nunca ignorar calado' como regra. Barato de fechar e INDEPENDE do spec de int. Nota: `experiments/lab/dirty/notas/2026-08/2026-08-14-0010-onde-o-spec-encaixa-na-rota-tipada.md` | **4a SITUACAO (a INVERSA, achada no fechamento da hora, `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-2230-fechamento-hora`)**: nas 3 anteriores o usuario PEDE spec e nao recebe; nesta ele passa um spec **irrelevante** e o formato **o ADOTA e o CARIMBA no wire**. Medido: `encode(horas_HH:MM, nature=SPEC_CPF)` -> o CPF aplica em **0% dos valores** (`by_status={'length_wrong': 96}`, `apply_rate: 0.0`) e **mesmo assim VENCE o FLOOR** — 831 B sem nature contra **773 B com**, e o header sai `#TCF.8 :cpf` **numa coluna de horas**, com `used: True`. Mecanismo: todo valor vira `_HH:MM`, e o prefixo `_` uniforme da' ao OBAT um **afixo compartilhado** que ele fatora — o candidato fica menor por um motivo que **nao tem nada a ver com a semantica do spec**. O RT fecha (nao e' corrupcao), mas o `:id` e' justamente o campo self-describing que um leitor usa pra saber o que a coluna E' — logo e' **metadado falso**. Mesma familia do artefato do `_` ja' visto no lab `2026-08-14-1745` (M3b). Guarda obvia a considerar: o FLOOR nao pergunta se o spec **fez alguma coisa** (`compressible > 0`).
> | **`T-META-NAO-DECLARA-MODO`** | 3 metadados de coluna **sem lugar** no meta do `.8M` — e cada tipo novo pode somar mais | VERIFICADO 2026-08-13 (contra-argumento a' ordem, aceito com ressalva). **A DEFASAGEM E' CRONOLOGICA E MEDIDA**: multi-col e' de mai/jun (ADR-0004/0013/0023) e hierarquico de 09-jul (ADR-0031/0032); as CINCO otimizacoes de coluna seguintes sao TODAS posteriores — polaridade **single-col** (ADR-0035, 26-jul; o titulo diz single-col), bN de dominio (0036, 27-jul), denso b2 (0037, 31-jul), indice core tipado (0038, 01-ago), lazytype bool (0039, 01-ago). Confirma o owner: *"eles estao comecando a ficar obsoletos... podem ate' estar funcionando, mas deve estar perdendo caracteristicas que tinhamos otimizado"*. **O REQUISITO CONCRETO**: o meta do `.8M` so' declara `!`raw/`@`dict/`%`split + `<size>=<nome>:<spec>`, e o `size` e' em BYTES. Os modos novos carregam metadado que NAO cabe: denso `#TCF.8b1258` = largura de bit + contagem de VALORES; bN `#TCF.8B2258` = largura do indice + contagem; polaridade `#TCF.8!!` = o char eleito. Propagar exige **estender o meta** — mudanca de FORMATO, nao de codigo. **PROPOSTA (barata, nao e' 'testar M/H')**: a cada tipo fechado, registrar em uma linha *o que este modo precisa declarar, e cabe no meta de hoje?*. Custo de minutos; evita que a extensao do meta seja projetada as cegas no fim, sobre um conjunto so' entao conhecido. O lab de INT ja' somou o 4o caso: PAD precisa da largura, OFFPAD da largura E da base, B94 dos digitos |
> | **`T-8H-SEM-SPEC-OUT-OF-BAND`** | spec de terceiro nao e' legivel em `.8H`; single e multi aceitam | MEDIDO 2026-08-13 (ciclo da ordem): `decode_hierarchical(tcf_text)` **nao recebe spec** (`hierarchical.py:843`), entao um spec fora do registry core produz wire `.8H` que a propria API nao le' — erro *'nature-id desconhecido no header single-col: ...'*. Single (`nature=`) e multi (`nature_per_col=`) aceitam normalmente. PRE-EXISTENTE (a auditoria de streaming ja' verificou identico no commit anterior) e so' afeta spec de TERCEIRO — specs welded no registry atravessam as tres rotas (`data-iso` ja' faz). Ciclo: `experiments/lab/dirty/notas/2026-08/2026-08-13-2115-ciclo-ordem-coluna-antes-de-MH.md` |
> | **`T-BAIXA-CARD-EM-TABELA`** | **5x a 12,8x** — a coluna perde o proprio mecanismo ao entrar em tabela | MEDIDO 2026-08-13 (levantamento de proximo-tipo). A MESMA coluna, sozinha x dentro de tabela: **bool nativo 12,79x no `.8M` e 12,67x no `.8H`** (112 B sozinho -> 1433 B); bool-string 5,01x / 10,73x; categoria k=5 1,87x / 5,12x. Data (1,08x), inteiro (0,97x) e texto (1,00x) atravessam INCOLUMES — o problema e' especifico de **baixa cardinalidade**. Causa: o bool sozinho vira bitpack denso (`#TCF.8b1`) e a rota multi/hierarquica **nao consulta esse candidato** — 6a ocorrencia da classe 'o candidato existe e a rota nao consulta'. **TABELA REALISTA** (cadastro, 10 colunas x 2000 linhas, 5 flags bool = o formato de qualquer sistema): 41.760 B, dos quais as 5 flags custam **12.428 B** (contra 1.740 B sozinhas, 7,1x) e `uf` (k=6) custa 5.854 B (contra 1.031 B, 5,7x); soma dos excedentes marginais = **47% da tabela** (indicativo — soma de marginais nao e' exatamente decomponivel; o padrao por coluna e' que e' inequivoco). **NAO exige mecanismo novo**: o denso/bN ja' esta' soldado e testado. ENGLOBA e SUPERA o `T-BN-MULTICOL` (que registrava 13,8% e nao cobria bool nativo nem categoria). **RECOMENDACAO REVISADA 2026-08-13** (ciclo pedido pelo owner): eu havia sugerido isto como PROXIMO item, por ROI de bytes — **estava errado**. O owner: *"se mexer em M/H agora, e depois mexer nos numeros e algo alterar, pode ser que impacte em revisao do M/H novamente... vc pensa muito em compressao, eu penso em fluxo que funciona. se atender apenas uma coluna, o resto e' consequencia nao?"*. VERIFICADO: os candidatos do single e do multi sao QUASE DISJUNTOS (single: core polarizado + bN + tipado/denso + nature; multi `_best_of`: `_encode_column` cru + raw + dict `@` + split `%` + nature). O multi NAO esta' mal feito — ele tem candidatos proprios que o single nao tem (categoria k=5: core cru 1742 B, mas na tabela 639 B, porque o `dict` entra). Levar o denso pro multi **AUMENTARIA a solda dupla**: o mesmo candidato em dois lugares, e todo tipo novo registrado duas vezes — exatamente o retrabalho que o owner quis evitar. Este ticket NAO e' item de M/H: e' SINTOMA da solda dupla e some junto com o `T-UM-CAMINHO-SO`, que ja' estava na ordem certa (depois dos tipos). Ciclo: `experiments/lab/dirty/notas/2026-08/2026-08-13-2115-ciclo-ordem-coluna-antes-de-MH.md`. Nota: `experiments/lab/dirty/notas/2026-08/2026-08-13-2030-proximo-tipo-e-ordem-por-roi.md` |
> | **`T-NUMERO-SPEC`** | **1,9x a 3,0x** nos regimes de progressao e largura fixa | levantamento 2026-08-13, resposta a *"podemos olhar para os numeros, comecando com algum como inteiro"*. Numero JA' e' tipo nativo (`stype='n'`) mas **nao tem pre-transformacao nenhuma** — vira string e passa pelo core; a rota tipada custa **1 byte A MAIS** que a string, sem ganhar nada. DUAS alavancas medidas, ambas com precedente SOLDADO: **(a) largura variavel quebra o marcador aritmetico** — `1..600` sai como TRES marcadores (`*9+1|1` + `*90+1|10` + `*501+1|100`, 36 B) porque o run quebra em 9->10 e 99->100; com zero-pad vira UM marcador (19 B, **1,9x**); passo 7: 48 -> 20 B (**2,4x**). E' o mesmo fenomeno que a docstring do `data_iso` descreve p/ ISO, e o `TemplatedPaddedSpec` (IP) **ja' usa padding zero-leading exatamente pra ativar o seq-RLE**. **(b) aleatorio de largura fixa nao ganha nada hoje** (600 ids de 6 digitos = 4.209 B contra ~4.200 crus); o `TemplatedCheckedSpec` (CPF) ja' faz 11 digitos -> 5 chars BASE94, mesma ideia daria ~2,3x. **ONDE NAO COMPENSA** (medido, importante p/ o FLOOR): moeda em centavos rende so' 1,17x e o padding PIORA (0,82x); negativos com offset 1,06x e o padding piora. As alavancas valem p/ PROGRESSAO e LARGURA FIXA, nao p/ numero em geral. Caso `epoch`/timestamp sozinho vale **3,0x**. **TESE 'O RESTO E' CONSEQUENCIA' VALIDADA 2026-08-13**: prototipei um spec de inteiro sintetico (12 linhas, zero-pad) e apliquei nas TRES rotas **sem tocar em M nem H** — single 36 -> 28 B (1,29x) e multi 655 -> 644 B, emitindo `#TCF.8Mf=n:xint,@x`. O tipo entra UMA vez e a rota composta o carrega. (O `.8H` falhou, mas por outro motivo: nao aceita spec OUT-OF-BAND — `T-8H-SEM-SPEC-OUT-OF-BAND`; spec do REGISTRY atravessa os tres, o `data-iso` ja' faz.) **Confirma a ordem do owner**: fechar o tipo primeiro, e M/H vem de graca. **LAB FEITO 2026-08-13** (`2026-08-13-2258-int-spec-faz-sentido`, ritual classico, 16 casos sinteticos controlados, **0 falhas de RT, 16 pins verdes**): SIM, um spec de inteiro faz sentido — mas em TRES REGIMES NOMEAVEIS, com gatilho detectavel na coluna antes de encodar, e **nenhuma ideia nova** (os 3 alvos sao tecnicas ja' soldadas, generalizadas): **PAD** (zero-pad p/ largura fixa, do `TemplatedPaddedSpec`/IP) rende 1,38x (1..600: 36 -> 26 B) a 1,78x (passo 7: 48 -> 27 B); **OFFPAD** (offset p/ o minimo, ideia do ordinal do `data-iso`) rende **2,79x** no epoch (81 -> 29 B) e **2,50x** em base alta 1e9+i (65 -> 26 B); **B94** (base-94 densa, do `TemplatedCheckedSpec`/CPF) rende 1,31x em ids de 6 digitos (4209 -> 3217 B) e **1,52x** em 11 digitos (7209 -> 4730 B). **9 dos 16 casos sao RECUSA CORRETA** — e' metade do valor do lab: largura ja' fixa (22 B), baixa cardinalidade (bN ja' cobre), quase-constante (RLE), negativos (offset+pad PIORA 0,89x), sujeira 10% (literal quebra o run E paga marcador), largura mista sem progressao, e a ARMADILHA `zeros-a-esquerda` (`000001` NAO e' o inteiro 1 — recusado pelo mesmo guard de canonicidade por re-emissao que o `data-iso` introduziu). **4 PINS CORRIGIDOS**: eu esperava spec em descendente/negativos/sujo/misto e veio core nos 4 — a expectativa era minha, o FLOOR estava certo. **CORPUS REAL MEDIDO 2026-08-14** (`2026-08-14-0112-gatilhos-int-em-corpus-real`: 39 colunas numericas descobertas AUTOMATICAMENTE nos hubs de Z: — escolher a dedo seria montar o corpus p/ a resposta —, 2 ordens, 78 medicoes, 0 falhas). **AGREGADO: 245.094 -> 217.670 B = 11,2% menor**; em **18 das 39 ninguem bate o core**. **QUEM GANHA E QUANTO** (a contagem bruta enganava): **PAD** vence com ganho REAL em 21, **mediana 1,72x, max 2,73x, ZERO empates** — quando ganha, ganha de verdade (maiores: `o_orderkey` 123->45 B); **B94** vence em 22 mas **mediana so' 1,14x** e **33 vitorias sao de <=1 byte** (o `min()` escolhendo por desempate) — marginal neste perfil; **`min_len` NAO GANHA EM NENHUMA** (0 ganho real, 2 empates). **SEGUNDA REVERSAO MINHA**: em 2026-08-14 eu invertera a recomendacao dizendo que o `min_len` 'resolve 3 dos 5 casos e resolve melhor' — **neste corpus ele nao ganha nada**. A explicacao importa: os 3 casos em que brilhava (epoch, base alta 1e9+i, 2^63+i) sao regimes que ESTE corpus nao tem (sao chaves, quantidades e ids). Enunciado honesto: nao e' 'o min_len nao serve', e' **'neste perfil de dado ele nao aparece'**. **MEUS GATILHOS ESTAO MAL CALIBRADOS — achado sobre o DESENHO**: `gat_PAD` disparou 11x e acertou 9 (bom); `gat_B94` disparou **2x** mas o B94 venceu **28x** (subestima grosseiramente — ele comprime qualquer largura fixa, com ou sem progressao); `gat_min_len` disparou 1x e acertou 0. Logo **a auto-deteccao que propus p/ o `.9` nao funcionaria como esta'** — ou recalibrar contra este corpus, ou deixar o FLOOR decidir sozinho, que e' o que ele ja' faz bem. **ACHADO DE CARONA**: `encode([1,2,3], min_len=12)` -> `ValueError: kwargs ['min_len'] so' valem no flat de STRING` — **a rota tipada e' fechada para os DOIS mecanismos que o int precisa** (spec e tuning do nucleo), nao so' p/ o spec. **PROTOTIPO CLEAN FEITO (EXP-018) 2026-08-14**: `IntPadSpec` escrito como o codigo que iria p/ `src/tcf/natures/int_pad.py` + prototipo da ABERTURA da rota tipada. **18 casos (8 sinteticos + 10 reais congelados), 0 falhas, TODOS os pins verdes, suite do repo intacta em 1252**. O spec vence em **6**, mediana **1,79x**, max **2,80x** (`o_orderkey` 123 -> 44 B). **RECUSA nos outros 12** — incluindo **6 colunas REAIS escolhidas justamente p/ isso** (negativos, k baixo, largura uniforme, chave repetida, sem progressao) — e nesses o wire e' **byte-identico** ao de hoje: **nunca-pior provado caso a caso**, nao por argumento. **7 PROVAS por caso**: RT estrito COM TIPO (`type(x) is type(y)` — em Python `True == 1` e `1 == 1.0`, comparar so' valor mascararia), RT do alvo isolado, RT em ARQUIVO diffavel, NUNCA-PIOR, determinismo, o artefato E' o wire, e o nucleo nao regride (baseline gravado). **1 PIN CORRIGIDO na rodada**: `l_orderkey` — eu esperava spec e veio core; a coluna e' monotona mas tem TRES passos distintos, e repeticao quebra a progressao. **Licao: monotonia NAO basta**, o gatilho precisa de progressao limpa. **O WELD, LOCALIZADO** (nao estimado): `encoder.py:539` (spec depois do `render`), `encoder.py:549-600` (um `candidatos.append`), `decoder.py:410-411` (spec antes do `_cast_tipo`), registry com `wire_id='ipad'`. A diferenca entre o prototipo e o destino e' de UMA LINHA (aqui o spec vai out-of-band no decode porque `ipad` nao esta' no registry). **Lab: `experiments/lab/clean/EXP-018-int-pad-e-rota-tipada`. **SOLDADO 2026-08-14** (aprovacao 'pode soldar'): `src/tcf/natures/int_pad.py` (`IntPadSpec` + `int_pad_para` p/ dimensionar) + `SPEC_INT_PAD` no registry nos DOIS planos (`int-pad` / `ipad`) + **A PORTA TIPADA ABERTA**: `nature=` e `min_len=` deixaram de ser recusados na rota tipada; o spec entra como **mais um `candidatos.append` no MESMO `min()`** — como o bool ja' faz com o denso, sem rota nova — e o decode reverte o spec ANTES do `_cast_tipo`, porque ele opera sobre a GRAFIA e o cast so' entao devolve o tipo (inverter daria `int('_lixo')`). O `_decode_typed` passou a RECEBER `nature` — antes nem recebia, e spec out-of-band era ignorado CALADO ali (buraco da auditoria, fechado). **Wire**: `#TCF.8n :ipad\n*600+1|\\001`, e o decode **resolve sozinho pelo registry** (auto-contido: a largura e' o comprimento das linhas do corpo). **8 testes novos** (`TestIntPadSpecWeld`): ganha onde a largura varia; decode sem out-of-band; NUNCA-PIOR em 5 regimes de recusa; slot nulo atravessa; guard de canonicidade (`'007'` != `7`, com RT byte-exato do literal); `int_pad_para` recusa o que nao ha' o que padear; `min_len` na rota tipada; registry nos 2 planos. **Suite 1252 -> 1260**, gates byte-canonical VERDES, e o EXP-018 re-roda contra o codigo soldado com 0 falhas e os mesmos 18 pins. Um re-pin: `test_resolve_nature_id`. **PONTA SOLTA FECHADA 2026-08-14** (lembrete do owner: *"para nao ficar inventando nomes do nada, lembre da regra sobre o spec e o tamanho... 'ipad' e' interessante, mas podemos revisar ate' o 1.0"*): o `ipad` foi soldado mas **nao estava no mapa de ids do ADR-0041**, que e' o lugar canonico onde eles vivem e sao revisaveis — agora esta'. E ao registrar apareceu uma **colisao de FAMILIA**: o `ipad` cumpre a regra (`^[a-z][a-z0-9]{0,7}$`, 4 chars), mas o mapa usa **prefixo de familia de proposito** (`dt`/`dtm`/`dtbr`/`dtym`/`dtmes`/`dtfim` sao todos data, e a §2 do ADR lista 'familia por prefixo' como uma das 3 coisas que a regra restritiva compra) — e **`ip` ja' e' IPv4**. Lado a lado, `ip` e `ipad` parecem irmaos e nao sao. **PROPOSTA REGISTRADA, NAO APLICADA**: familia `n…` p/ numerico — **`npad`** em vez de `ipad` (e `nb94` se o base-94 vier), porque `n` ja' e' a **tag da rota tipada** (`#TCF.8n`, o `number` do JSON): o wire viraria `#TCF.8n :npad`, a tag dizendo *e' numero* e o id dizendo *qual transformacao*. Custo da troca HOJE: uma string em `natures/int_pad.py`, um re-pin e a linha do mapa; **depois do 1.0 e' format change**. Aguarda decisao do owner.** ~~RECOMENDACAO~~: o **PAD e' o alvo que vale** (1,72x em real, gatilho calibrado, auto-contido); o B94 e' marginal aqui mas nao descartavel (1,52x em ids de 11 digitos no lab sintetico); o `min_len` espera corpus com timestamps; e abrir a rota tipada e' **pre-requisito dos tres**. **VIES DECLARADO**: 25 das 39 colunas sao TPC-H (gerador de benchmark, muitas chaves sequenciais densas) — **favorece o PAD**; as de origem independente sao 14. O lab sustenta a ORDEM RELATIVA e a calibracao, nao os absolutos como previsao universal. Lab: `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-0112-gatilhos-int-em-corpus-real`. ~~FALTA~~: (1) medir a FREQUENCIA dos 3 gatilhos em corpus REAL (o corpus dita o default — mesma regra que valeu p/ data; o lab e' sintetico POR ESCOLHA, p/ isolar mecanismo); (2) decidir um-alvo-com-parametro x tres-specs-irmaos (precedente CPF/CNPJ e' um objeto por grafia, mas aqui a grafia e' a mesma e muda a ESTRATEGIA); (3) **como o parametro viaja** — PAD precisa da largura, OFFPAD da largura E da base, B94 dos digitos de origem; hoje vive no objeto do spec (out-of-band). **E' a MESMA CLASSE do requisito de meta do M/H** (`T-META-NAO-DECLARA-MODO`). **CORRECAO DO OWNER 2026-08-13 — o lab das 22h58 mediu inteiro SO' COM FONTE STRING**: *"porque os numeros estao como string em tudo? o json tem que colocar numeros como numeros, lembra da tipagem? [...] se o dado era int [...] ele entra int, o spec e' int, o tcf trata internamente como int, e devolve int. fizemos isso com data, com bool, e' a historia do semantico tipo"* — e depois: *"o caso de entrada string e spec int TAMBEM e' valido, mas o lab so' tem isso"*. NAO ha' primario/secundario: sao DOIS EIXOS. **LAB DA MATRIZ** (`2026-08-13-2326-int-tipagem-x-spec`, 14 regimes x 4 celulas, 0 falhas, RT comparado com TIPO — `type(x) is type(y)`, porque em Python `True == 1` e `1 == 1.0` e a comparacao ingenua mascararia o defeito). **3 ACHADOS**: (1) a rota tipada custa **+1 byte em TODOS os 14 regimes** (o disc `n`) e **nao entrega otimizacao nenhuma** — ela preserva o tipo (int/None/2^63 conferidos) mas converte p/ string e entrega ao mesmo nucleo; (2) **a celula `int+spec` NAO E' EXPRESSAVEL EM NENHUMA DAS 3 ROTAS** — single: *kwargs ['nature'] so' valem no flat de STRING*; multi: *nature so' aplica a coluna scalar-string*; .8H: *e' coluna TIPADA (number/bool), nao string*. Spec e tipagem sao dois mundos que nao se tocam, e o **bool ja' faz o que falta ao int** (`[True,False]` -> `#TCF.8b\n\\2\n\\1`, pela tabela congelada de `tipos_internos.py` — isso E' um spec semantico embutido na rota tipada, o modelo pronto); (3) **os dois eixos dao respostas DIFERENTES** — em ids aleatorios o eixo INT ganha mais (6 dig: 3017 vs 3217; 11 dig: 4217 vs 4730) porque, partindo de int, a transformacao nao precisa preservar grafia de origem (nao ha' `'007'` p/ distinguir de `7`); em `faixa-0-100` SO' o eixo int ganha (1044 vs 1110). Logo um spec p/ fonte string e um p/ fonte int **nao sao o mesmo objeto com um cast na frente**: o contrato de RT e' outro (grafia x valor). O FLOOR recusaria em 6 dos 14 (onde o nucleo ja' resolve). **DOIS ERROS MEUS na rodada, corrigidos e comentados no run.py**: filtrei os `None` da simulacao (inflava — `com-nulos` aparecia 186 B, honesto e' 247 onde o spec PERDE) e converti a volta com `int()` (quebra em coluna mista int+float; o certo e' restaurar `type(origem)`). **3o ERRO, PEGO PELO OWNER 2026-08-13** — ele abriu `outputs/gigante-64bit.str-spec.tcf` e estranhou: *"parece que quebrou... o numero e' gigante mas o conteudo nao parece fazer sentido. sera' que o teste de RT deu errado?"*. O RT NAO deu errado; a MEDICAO e' que estava. O wire era `#TCF.8 :xioff\n*600+1|\\000` — **26 B para 600 numeros de 19 digitos**, porque o OFFPAD subtraiu a base e o corpo virou `000..599`; **a base de 19 digitos NAO esta' no wire**, vivia no objeto do spec que eu passava no decode. PROVA: o MESMO wire devolve `['9223372036854775808']` com `base=2**63` e `['0']` com `base=0`, **sem erro nenhum**. **ACHADO DE DESIGN que isso revelou — spec AUTO-CONTIDO x PARAMETRIZADO**: `PAD` (a largura e' visivel no corpo expandido) e `B94` (`int(b94)` da' o numero; zeros a' esquerda ja' sao recusados como nao-canonicos) sao **auto-contidos** — o id no header basta, e e' a classe de TODOS os specs ja' soldados (`data-iso`/`cpf`/`cnpj`/`ip`: o ordinal de data e' ABSOLUTO, nao relativo, por isso `#TCF.8 :dt\n*600+1|\\739617` tem 26 B sem nada out-of-band). Ja' o `OFFPAD` e' **parametrizado**: a base e' informacao PERDIDA, nao deduzivel — e isso **quebra o self-describing do ADR-0027** (o decode nao resolve sozinho pelo registry). Nao inviabiliza, mas muda o que ele e': ou o parametro viaja no header (extensao de formato) ou o contrato vive nas pontas (`T-SPEC-SEM-CARIMBO`). **NUMEROS CORRIGIDOS** (custo do parametro somado): epoch 29 -> **40 B** (ganho 2,79x -> **2,03x**), base-alta 26 -> **37 B** (2,50x -> **1,76x**), gigante-64bit 26 -> **46 B** (3,15x -> **1,78x**). PAD e B94 NAO mudam. **ONDE O SPEC ENCAIXA — INVESTIGADO 2026-08-13/14** (4 lentes + verificacao, achados re-verificados a mao): **encode** = o spec depois do `render` em `encoder.py:539` (o `render` da familia `n` e' literalmente a builtin `str`); **FLOOR** = um `candidatos.append` em `encoder.py:549-600`, o spec compete como toda nature; **decode** = o spec antes do `_cast_tipo` em `decoder.py:410-411`; **header** = `#TCF.8n [nome]:id`, slot do indice 7 **verificado livre** (ocupados hoje: `''`, `!`/`!!`, `B`, `1`, `2`, `4`, `8`). **CORRECAO A UMA AFIRMACAO MINHA**: eu disse que a rota tipada *'custa 1 byte e nao entrega nada'* — ERRADO. A tag seleciona a FAMILIA DE CAST: o mesmo corpo `\\1` devolve `[1]` int sob `#TCF.8n`, `[False]` bool sob `#TCF.8b`, `['1']` str sob `#TCF.8s`. O byte E' o produto. O correto e' mais estreito: entrega o CAST, nao entrega OTIMIZACAO. Assimetria que importa p/ o desenho: na familia `n` (uniao int|float, o `number` do JSON) o tipo concreto e' re-derivado da GRAFIA por elemento (`encode([1,2.0])` volta `['int','float']`) — e um spec de int mexe justamente nessa grafia; ja' na familia `b` a grafia e' indice de slot congelado e a TAG e' o unico portador. **O `.8H` NAO E' 'APAGAR UM CHECK'** (achado que evita erro caro): a gramatica do meta e' MUTUAMENTE EXCLUSIVA entre tag de tipo e id de nature — encode emite `f'{csz}:{nat_id}'` SEM stype quando ha' nature (`hierarchical.py:602-605`) e o decode, havendo id, empilha com **`stype` hardcoded `'s'`** (`:806-813`). Apagar o check de `:476-479` faria uma coluna INT voltar STRING SEM ERRO — exatamente a falha que o owner reclama. No `.8H`, spec+tipo exige **gramatica nova de meta** (soma ao `T-META-NAO-DECLARA-MODO`). Nota: `experiments/lab/dirty/notas/2026-08/2026-08-14-0010-onde-o-spec-encaixa-na-rota-tipada.md`. **LICAO DE METODO**: medir um spec parametrizado sem contabilizar o parametro e' medir um wire que ninguem consegue ler — o auto-contido tem de ser a unidade de comparacao. Lab: `2026-08-13-2326-int-tipagem-x-spec` | Nota: `experiments/lab/dirty/notas/2026-08/2026-08-13-2030-proximo-tipo-e-ordem-por-roi.md` |
> | **`T-MIN-LEN-CANDIDATO`** | 22% das colunas ganham SEM spec, mas so' **1-5%** COM spec | MEDIDO 2026-08-13. O `min_len` e' escolhido por heuristica ANTES de encodar (`auto_min_len.py`) e **nao compete** — mesma classe do 'candidato nao consultado'. Varrendo 101 colunas, uma grade de 4 bate o auto em 22 (9,1% do corpus). **MAS a checagem contra os specs desinfla o numero**: nas 10 colunas de data reais o ganho cai de 1,19-1,39x (sem spec) p/ **~1,00x** (com spec); no CNPJ, de 1,14x p/ 1,05x. Onde ha' spec, ele ja' colhe quase tudo. O que sobra de verdade: **3,0x em timestamp** (que nao tem spec) e 1-5% em texto/CNPJ. Custo: 4,1x de CPU p/ grade de 4. **REVERSAO 2026-08-14 — SUGESTAO ANTERIOR INVERTIDA POR MEDICAO**: eu havia recomendado NAO abrir agora, por redundancia com o spec de numero. **Errado**: medido, o `min_len` resolve **3 dos 5** casos de int e resolve MELHOR que o spec (epoch 27 B contra 40 do OFFPAD auto-contido; base-alta 26 contra 37; gigante 35 contra 46), e **sem spec nenhum**. Ele nao e' redundante — e' **COMPLEMENTAR**: cobre 'progressao + base alta / digitos que nao informam' (fragmentacao do OBAT), enquanto o PAD cobre 'progressao + largura variavel' e o B94 cobre 'sem progressao + largura fixa'. Cada um num regime distinto. Nota: `experiments/lab/dirty/notas/2026-08/2026-08-14-0210-offpad-detalhado-e-o-int-no-date.md`. ~~SUGESTAO ANTERIOR~~: NAO abrir agora — a maior parte do que pegaria e' o que o `T-NUMERO-SPEC` resolveria melhor (o caso epoch e' numerico); fazer os dois seria trabalho duplicado. Reavaliar DEPOIS, com grade de 1-2. Nota: `experiments/lab/dirty/notas/2026-08/2026-08-13-2030-proximo-tipo-e-ordem-por-roi.md` |
> | **`T-CONCAT-CORROMPE-CALADO`** | **299 de 600 valores errados, ZERO excecao** | VERIFICADO A MAO 2026-08-13 (auditoria de streaming): na rota CORE, `decode(cabecalho + corpo_A + corpo_B)` com corpos encodados INDEPENDENTEMENTE devolve dado errado SEM erro. Causa: as refs sao indices posicionais na tabela ACUMULADA de fragmentos (`composicional/syntax.py:836-839`) e a gramatica NAO tem marcador de reset — o pulso 2 sempre fala do dicionario do pulso 1. Nas outras rotas e' fail-loud (bN: 'conteudo apos o bloco de bits'); so' a core cala. **E' a armadilha exata de quem for implementar pulsos**: a intuicao 'encoda pedaco 1, encoda pedaco 2, concatena' produz corrupcao silenciosa. CORTAR um wire PRONTO e' seguro (verificado: 600 e-mails em prefixos de linha dao 1/10/100/600 valores, todos corretos); CONCATENAR wires independentes nao. Sao operacoes opostas e parecem a mesma. Nota: `experiments/lab/dirty/notas/2026-08/2026-08-13-1900-auditoria-streaming-do-nucleo.md` |
> | **`T-BUDGET-DE-BUSCA`** | o unico freio do nucleo e' um contador FIXO de 99, **ja' saturado** | VERIFICADO 2026-08-13 (`composicional/syntax.py:522`): `if len(iter_traces) >= 99: break` e' o unico limite de busca em todo o `src/tcf` — `grep` por time/perf_counter/deadline/timeout/budget/elapsed da' **ZERO** ocorrencias. Colunas de texto livre BATEM no teto exato, e soltar p/ 200 **ENCOLHE** o wire 0,71% e 1,09% (deixando compressao na mesa hoje). No outro sentido, 1 alias em vez de 99 custa **+0,68% a +4,43%** de bytes e devolve **5,8x a 8,8x** de tempo, RT verde — e' o "risco de nao conseguir melhores comparacoes" que o owner antecipou, agora QUANTIFICADO. `PipelineConfig` e' o lugar pronto p/ o knob. LIGA direto com a regua de latencia do `T-PULSO-SINGLE-COL`: e' aqui que um deadline entraria no encode. Nota: `experiments/lab/dirty/notas/2026-08/2026-08-13-1900-auditoria-streaming-do-nucleo.md` |
> | ~~`T-SIDEOUTPUTS-OVERHEAD`~~ | **SOLDADO 2026-08-13** — telemetria virou OPT-IN; **3,9% a 31,1%** do encode devolvidos, wire BYTE-IDENTICO (suite 1249 -> 1252) | VERIFICADO POR LEITURA 2026-08-13 (`composicional/syntax.py:762-777`): `build_trace` e `build_rede` sao chamados INCONDICIONALMENTE no encode do HCC, mesmo sem `side_outputs`. Custo exclusivo medido: 4,2% / 3,7% / 7,3% em colunas reais e **17,1%** numa cadeia true/false. **Contradiz o contrato escrito** em `side_outputs.py:10-12` ('overhead zero'). **SOLDADO 2026-08-13** (pedido do owner: *"gostaria de ver um fix"*): `Syntax.coletar_trace` (default False) + o encoder liga com `syn.coletar_trace = side is not None`. **MEDIDO CONTRA O COMMIT ANTERIOR** (`git archive HEAD src` num dir separado, 2 rodadas x 9 encodes de cada lado, comparando o MINIMO): true/false **12,6%**, categoria k5 **9,0%**, codigo **3,9%**, e-mail **24,1%**, texto livre **31,1%**. Byte-identico em todas (sha conferido nas 4 execucoes). **ERRO DE MEDICAO no caminho, corrigido**: a 1a tentativa simulou o 'antes' por monkeypatch do `__init__` — mas o encoder SOBRESCREVE `coletar_trace` logo apos instanciar, entao os dois lados mediam a mesma coisa e o resultado (ganho negativo, profiling 0,0%) era ruido puro. So' o A/B contra o codigo real vale. 3 testes novos em `test_side_outputs.py::TestTraceOptIn`: spy provando que `build_trace`/`build_rede` NAO sao chamados sem `side_outputs` (e SAO com), telemetria intacta, byte-identico. A docstring de `side_outputs.py` tambem foi corrigida — ela dizia 'overhead zero' e no mesmo parenteses admitia que os logs eram gerados e descartados |
> | **`T-DECODE-PREFIXO`** | o WIRE permite prefixo; o `decode()` recusa 100% deles | auditoria 2026-08-13. Um leitor de prefixo escrito A MAO (header -> dominio ate' `=` -> grupos b64 completos -> bits) entrega valores CORRETOS de prefixos que o `decode()` publico rejeita (1o valor com 33% do fio; 60 valores corretos com 50%). Quem recusa e' `valida_payload_b64`, que exige `len(raw) == ceil(n*w/8)` EXATO (`composicional/dominio_bn.py:182-187`, usada pelas 3 rotas densas) — guarda contra wire adulterado, e e' exatamente o que impede consumo parcial ('90% do que chegou' e' indistinguivel de 'truncado'). **O criterio do owner ('so' falha se tiver algo no final') descreve corretamente o WIRE e incorretamente o CODIGO**: nenhuma rota emitida hoje tem trailer. Um modo de leitura PARCIAL ao lado do canonico e' mudanca de DECODER, zero mudanca de formato. **PROTOTIPO EXECUTAVEL 2026-08-13** (`experiments/lab/dirty/2026-08/2026-08-13/2026-08-13-1820-entrega-incremental-do-nucleo/prototipo_leitor_prefixo.py`, fora do `src/tcf`): le' prefixos das rotas densas e entrega os valores que ja' dao pra saber. Medido nas 3 rotas, onde o `decode()` publico recusa **100%** dos cortes: bool 3-ciclo e bool aleatorio entregam **96/264/432/528** valores (a 25/50/75/90% do fio) e categoria k=3 entrega **72/252/420/528** — **todos corretos**. ACHADO do prototipo: o dominio do bN e' **CORE-COMPRIMIDO**, nao literal (num caso medido sai `ativo`/`in1`/`pendente`, onde `in1` = 'in' + ref ao fragmento 1 = 'inativo' — um digito NU, sem `*` nem `^`). A 1a versao leu literal e devolveu valor ERRADO em silencio; corrigida usando o decodificador do core pro dominio. **Logo o bN tem DUAS camadas** e um leitor parcial dele precisa do core — a rota densa `b1` (dominio implicito) e' a facil. O prototipo NAO e' candidato a weld (nao valida integridade, nao cobre todas as rotas): serve pra enquadrar a decisao, que e' `.9`/`2.0`. **PRECEDENTE JA' SOLDADO** (`encoder.py:484-489`): o modo bN `C` e' ~1 B MENOR e foi recusado por nao streamar — "trocar streaming por 1 byte, calado, seria a decisao errada tomada pelo criterio errado". Nota: `experiments/lab/dirty/notas/2026-08/2026-08-13-1900-auditoria-streaming-do-nucleo.md` |
> | **`T-GRANULARIDADE-DE-ENTREGA`** | **de 1 a 5 pontos de entrega** no MESMO wire, conforme o mecanismo; e a implementacao para na fronteira de LINHA | modelo do owner (2026-08-13): *"o decode fica coletando e descomprimindo de acordo com a demanda. Ele so' falha se tiver algo no final"*. MEDIDO (`2026-08-13-1820-entrega-incremental-do-nucleo`, 9 casos, 0 falhas): o wire e' encodado UMA vez e entregue em prefixos de linhas integras — custo em bytes ZERO. **O criterio do owner e' satisfeito pelo FORMATO**: nada fica no final — no bN de dominio o dicionario vem NA FRENTE (`true`/`false` antes dos indices) e as referencias apontam PRA TRAS (`^1`). O que limita e' a IMPLEMENTACAO: o decode corta em fronteira de LINHA, e dentro de uma linha densa e' tudo-ou-nada. **Granularidade por mecanismo**: RLE por bloco = muitos pontos (bool em blocos entrega 200/400/600, de graca — a afirmacao do owner CONFIRMADA aqui); OBAT por afixo = varios (texto 1/2/10/100/600); bN de dominio = **1** (bool aleatorio e categoria k=5 so' respondem no fim); seq-RLE = **1** (data+spec: 600 valores em 26 B e UMA linha). **A TENSAO**: granularidade e compressao sao antagonicas — quem comprime por contexto GLOBAL colapsa em 1 linha e perde a progressividade; e' o mesmo achado do lab das 17h40 pelo outro angulo (la', re-emitir custa 16,46x justo p/ quem comprime bem). PROXIMO PASSO natural: entrega DENTRO da linha densa do bN (os indices sao POSICIONAIS, entao um prefixo deveria render valores) — levaria bool aleatorio de 1 para ~N pontos. Falta auditar (A) parar a busca por tempo e (B) dicionario congelado entre entregas: sao do ENCODER, nao observaveis pela API publica |
> | **`T-PULSO-SINGLE-COL`** | **REENQUADRADO 2026-08-13**: o eixo e' LATENCIA, nao pulso-de-data; a fatia sai de `[piso, teto]` MEDIDOS | **CORRECAO DE ENQUADRAMENTO (owner, 2026-08-13)**: *"a questao do periodo e' acessorio para relacionar com a latencia... a rigor o que existe e' tentar responder por slices de tempo, ou menor latencia. e isso vale pra virtualmente qualquer tipo... nao e' so' pegar a data e picotar... ela tem que derivar da latencia"*. O registro anterior fazia o INVERSO (corte alinhado ao periodo) e fechava com "um modo de baixa latencia nao pode cortar em qualquer lugar" — **REFUTADO** no lab `2026-08-13-1740-latencia-como-eixo`: dias uteis (periodo 5) cortados em TODOS os tamanhos de 1 a 40 = **40 de 40 legais**, RT em todos (1,2,3,7,11,13,17,23,37 fora de fase inclusive). As restricoes do `*N~...|` (2p+1 valores, pad rotacionado) sao de UMA GRAFIA, nao do modo de latencia — quando o corte nao cabe, o FLOOR escolhe outra grafia. **A REGUA CERTA, medida**: (1) o custo de fatiar NAO e' propriedade da data — a MESMA coluna custa 2,69x sem spec e 16,46x com spec, e `inteiro-sequencial` (sem spec, sem periodo) custa 14,40x; o que governa e' **de onde vem a compressao** — ganho GLOBAL (progressao) morre no corte (14-18x), ganho LOCAL (afixo/dicionario/por-valor) se reconstroi em cada fatia (1,9-8,4x), sem ganho e' de graca (1,01x). (2) **PISO** = menor fatia que mantem o mecanismo ligado — p/ data diaria c/ spec sao **100 valores** (de 100 a 600 o wire custa 26 B CONSTANTES; em 90 o marcador desliga e o B/valor salta 2,5x); o piso sai do FLOOR, nao do periodo nem do calendario. (3) **TETO** = quantos valores cabem no deadline: 200 ms valem de **1.425** (data uteis c/ spec) a **13.428** (categoria k=5) valores — fator 9x entre tipos. (4) A fatia vive em `[piso, teto]`; p/ data diaria em 200 ms = **[100, 2051]**. E ha' um CHAO honesto: o piso de 100 custa 9,75 ms, entao abaixo disso o intervalo fica VAZIO — nao da' pra atender sem desligar o mecanismo. Falta p/ fechar o desenho: throughput probatorio (`bench_perf`, nao a ordem de grandeza deste lab). MEDIDO 2026-08-10: **o wire JA' ACEITA pulsos** — `*300+1\|X` + `*300+1\|Y` decodifica identico a `*600+1\|`; RT verificado em 1/2/4/6/12/60 pulsos. Falta so' o encoder ter o ponto de decisao "parar e emitir". **O bloqueio do V2-J (ADR-0018) e' de OUTRA rota**: `# size=name,...` e' multi-col; o single-col flat com spec nao tem sizes no header, entao o caso do owner (stream de datas, coluna unica) **nao esta' bloqueado pelo formato** — o registro atual nao fazia essa distincao. RESTRICOES NOVAS do periodico: (a) o pad do 2o pulso **rotaciona por `corte mod p`** (corte multiplo do periodo mantem; fora de fase exige rotacionar, e a rotacao tem de seguir canonica sob o guard do ADR-0040); (b) **pulso periodico tem minimo de `2p+1` valores** (o guard exige 2 ciclos) — com p=5 um pulso de 7 e' ILEGAL. Um modo de baixa latencia **nao pode cortar em qualquer lugar**. **PESQUISA 2026-08-12 — as decisoes de ESTRUTURA**: matriz de 48 colunas reais: pulsaveis HOJE = spec/flat/tipado-core (`#TCF.8n` e' fato novo); NAO-pulsaveis = tudo com n/w/size no header (denso/bN/bB/.8H/.8M — count-no-fim = format change 2.0). Custo do modo-pulso na flat: **+4,73%** no corpus real, 2/3 = forfeit de bN (ate +262% em categorica) -> o perfil roteia POR COLUNA. **O CONFLITO com o T-NATURE-CANDIDATO-BN se resolve pela via (b) com custo ZERO no regime de pulso** (medido: em serie monotonica o FLOOR da polaridade recusa o sufixo sozinho; bN nunca vence o corpo transformado) -> CONSTRAINT no weld: polaridade/bN na rota spec CONDICIONADOS a perfil batch, nunca min() incondicional. Trailer-no-fim REPROVADO (mataria streaming de decode — a algebra 17x do modo C). **Leniencia nao-contratada descoberta**: commit precoce de sufixo corrompe SILENCIOSO (`ab!cd`->`abcd`), mas o parser aceita escape `\!` nao-emitido — fechar OU contratar (decide se a via sufixo-precoce existe; tem prazo). CANONICIDADE: pulsado = **'emissivel nao-canonico'** (espelho do modo C), SEM flag de header — re-encode canonicaliza (verificado byte-igual); gate: baseline nunca pinna saida pulsada. Fase do periodico: 100% estado de encoder, ZERO formato. Multi-col por coluna: +6,4%/+28,8% -> 2.0 (fica como TETO) |
> | **`T-FLOOR-POS-POLARIDADE`** | o FLOOR mede a grandeza errada | achado da 2a cacada adversarial (2026-08-09, lab `0042`): o `min()` do HCC decide pelo **corpo canonico** (`hcc_seqrle.py:329`), mas o que embarca no wire e' `polariza(corpo)` (`encoder.py:456`) — e o ganho da polaridade e' proporcional ao numero de corridas `\digito`, que a compactacao DESTROI. Medido: um corpo **9 B menor** embarcando wire **19 B maior**. Vale pro core de HOJE, nao so' pro periodico (que so' tornou visivel). Conserto por construcao seria comparar `len(polariza(c))` no `min()` — mas isso faz o HCC conhecer a camada de borda (violacao de camada), entao a alternativa e' FLOOR na granularidade certa. Vizinho do `T-FLOOR-MULTIVETOR`. **MEDIDO 2026-08-13** (critica aos parens): nao e' hipotese — **6 inversoes em 77 colunas REAIS (7,8%), 4 delas FORA do empate**; pior caso `online-retail/UnitPrice` 349 -> 356 B (**perde 7 B = 2,0%**), `tpch/l_quantity` 2 B, `wine-quality/chlorides` 2 B. **E' o unico ticket com perda medida no wire que SAI HOJE**, sem depender de weld pendente. ABSORVE o porem do 'desempate por ordem de argumento': as inversoes no empate sao o mesmo fenomeno (o `min()` decide no corpo canonico; o empate e' onde a grandeza final diverge) — pinar o desempate trata o sintoma, medir a grandeza que embarca e' a cura; fazer os dois na mesma mexida. **SUBIU na fila** |
> | **`T-PERFIS-MACRO`** | ergonomia; sem byte novo | perfis declarativos (`stream`/`lote`/`rapido`/`memoria`/`compacto`/`auto`) em vez de um knob por mecanismo — `encode()` ja' tem 13 params e o `PipelineConfig` ja' e' o precedente de agrupador. `auto` TEM de ser o default e o comportamento de hoje, senao os baselines byte-exatos morrem. DEPENDE do `T-FLOOR-MULTIVETOR`: enquanto o `min()` so' enxerga byte, perfil nao tem em que mandar. Nomes a decidir. Esboco: nota `2026-08-07-flags-modo-bn-e-perfis-macro` |
> | **`T-ERRO-SET-ORDEM`** | reprodutibilidade, **byte-neutro no wire** | achado no EXP-016: `HierarchicalError` interpola um `set` cru (`tipos escalares MISTOS {'b', 'n'}`) e o repr varia com `PYTHONHASHSEED` — a mensagem muda de rodada pra rodada. Não afeta encode/decode, mas quebra diff de evidência e teste de mensagem. Fix: `sorted()` na interpolação. O lab normaliza no lado dele enquanto isso |
> | **`T-LAZYTYPE-OUTROS`** | o padrão lazy nos outros tipos/specs | bool já é a **referência soldada** (ADR-0039, weld 2026-08-01); resta testar `n` (int/float + extras, ex. `"N/A"` em coluna numérica) e **revisar as natures/SPEC sob a lente unificada** (hoje caem no literal; cair no slot declarado?) — memorizado por direção do owner 2026-08-01 |
> | **`T-MODO-JSON-IMITADOR`** | interop consciente com ecossistema json | param hipotético: TCF **alerta** como o json alertaria (nunca arruma); régua **medida** no lab `2026-08-01-0309` (29 casos: json-lib ALTERA em 0 casos que o TCF aceita — o conjunto de alertas ganha corpo com lazytype + cross-ecossistema); catálogo de alertas no `result.md` §2; sem flag, TCF faz tudo que pode; ambíguos "fogem" pro comportamento json |
> | **`BUG-CHAVE-VAZIA-POSICIONAL`** | o ÚNICO caso onde o TCF **altera** | `{"":[…]}` → `{"0":[…]}` com warning (rota flat/multi trata `""` como anônima); `.8H` já preserva via escape. Opções no [ticket](tickets/BUG-CHAVE-VAZIA-POSICIONAL.md) — fail-loud × preservar |


> **▶ PLANO VIGENTE — fechamento bool/binário/bN single-col (2026-08-01).** Fila aprovada:
> 1 `T-BN-B64-VALIDATE` · 2 `T-GRAFIA-CHECKLIST` · 3 `T-DENSO-PADDING` · 4 params de wire
> (`T-BN-LOTE` + `T-TIPADO-LEGIVEL-PARAM` + `T-FORCAR-MECANISMO-PARAM`, 1 superfície) ·
> 5 `T-MISTO-RLE-B64-SINGLE` (estudo real-world primeiro) · 6 revisão de conformidade de
> cabeçalhos (fecho). Decisão do owner no caminho: `BUG-CHAVE-VAZIA-POSICIONAL`.
> Triagem completa (o que fica pra int/float, `.9` e multi-col) e critério de "universo
> fechado": [plano](experiments/lab/dirty/notas/2026-08/2026-08-01-0453-plano-fechamento-bool-bn-single-col.md).

> **✅ WELD — bN de DOMÍNIO no single-col flat (2026-07-27, ADR-0036, suíte 1042 passed).**
> Coluna de cardinalidade baixa gastava ~3 B/linha em `^N`. Com `k` distintos bastam
> **`ceil(log2 k)` bits**: o domínio viaja uma vez (comprimido pelo próprio core) e os índices
> vão empacotados. `['0','1']*100`: **609 → 54 B**.
>
> **Densidade por CARDINALIDADE, não por tipo declarado** — era problema de ROTA: `list[str]`
> nunca chegava ao modo denso, que além disso é bool-**sem-null**.
>
> Duas grafias, escolhidas pelo **transporte**: `B` (domínio primeiro) streama nos dois lados
> e é o **único emitido**; `C` (domínio por último) é ~1 B menor mas **não streama** (17× mais
> buffer numa coluna de 2000 linhas) — fica decodável, com opt-in pendente.
>
> Marcador `=` com escape `\=`, seguro porque **o core nunca emite `\` + char fora de
> `* 0-9 \ ^ ~`**. `null` é mais um slot — o **0**, que já era dele.
>
> **Nenhum baseline moveu** (D1-D9 1545, D17a 300, real-world 89430): nenhuma coluna dos gates
> tem cardinalidade baixa o bastante, o que confirma o FLOOR nunca-pior.
> Evidência: `experiments/lab/dirty/2026-07/2026-07-27/{1608,1647,2211,2231,2247}`.

> **✅ WELD — denso b2 TERNÁRIO: bool com null a 2 bits, domínio IMPLÍCITO (2026-07-31,
> ADR-0037, suíte 1077 passed).** O trio `{null,false,true}` não cabia em 1 bit e caía no
> core (**546 B**, n=200). Mas `null/false/true` são tipos puros do JSON — o domínio é
> conhecido a priori, declará-lo é redundante. Agora `#TCF.8b2<n>`: domínio implícito
> congelado `null=0, false=1, true=2` (símbolo 3 = fail-loud), mesmo `bitpack` do `b1`,
> mais um candidato do mesmo `min()`. **546 → 79 B** (15 B a menos que o bN tipado, que
> declarava o domínio) e **vence inclusive n=3** (14 vs 21 B) — o domínio implícito zera o
> custo fixo. Reais Adult ternário (n=100): 232–250 → 47 B. Bool puro segue no `b1` (FLOOR).
> **Nenhum baseline moveu** (D1-D9 1545, D17a 300, real-world 89430 — gates são rota flat).
> Evidência: `experiments/lab/dirty/2026-07/2026-07-31/2026-07-31-2350-denso-b2-ternario/`.
> O T-BN-TIPADO perdeu a família bool do escopo (denso b2 a cobriu) e SOLDOU os números em 2026-08-07.

> **✅ WELD — índice interno DEFAULT no core tipado bool (2026-08-01, ADR-0038, suíte 1084
> passed).** O null já viajava como `0` cru no core tipado (slot 0 pré-alocado), mas
> `true`/`false` viajavam como NOMES. Agora o render da tag `b` emite **slots congelados** —
> a MESMA tabela do b2 (`null=0, false=1, true=2`) — completando a tabela da ADR-0037 no
> core: `*200|true` (18 B) → `*200|\2` (**16 B**). Run-heavy 30 → **25 B**; reais Adult
> ordenados 27 → **22 B**; **nunca pior em 11 colunas** (nos densos o render nem
> materializa). Caso run-heavy confirmado: o core **vence o b2 nos dois renders** — é o
> nicho que o b2 não cobre. Nomes seguem **decodáveis-não-emitidos** (contrato do modo `C`,
> ADR-0036) — wires legados leem, e o opt-in legível fica pendente
> (`T-TIPADO-LEGIVEL-PARAM`, decode já pronto). Adversidades inertes: polaridade 0 disparos
> (estrutural: ≤2 literais), seq-RLE não dispara em 2 valores, fail-loud 3/3.
> **Nenhum baseline moveu** (gates são rota flat); 1 pin alterado (empate byte-neutro n=2).
> A **família bool fecha ponta a ponta**: b1 · b2 · core-com-slots.
> Evidência: `experiments/lab/dirty/2026-08/2026-08-01/2026-08-01-0037-tipado-bool-indice-default/`.

> **✅ WELD — lazytype bool: cabeça congelada + extras declarados (2026-08-01, ADR-0039,
> suíte 1105 passed).** A união bool+str (true/false/null **com exceções string** —
> "other", " ?") era **fail-loud** (o `.8H` recusa escalar misto) e a única saída era o
> flat-string, que perde o tipo. Agora `#TCF.8bB<w><n>`: cabeça CONGELADA implícita
> `null=0/false=1/true=2` (a MESMA `TABELA_B2` do b2/core — NUNCA se declara;
> redeclaração = fail-loud) + extras str declarados do slot 3 por 1ª aparição, domínio
> comprimido pelo próprio core (disciplina `dominio_bn`). A justificativa decisiva é a
> **armadilha `"true"`**: declarar o domínio completo funde `"true"` str com `True` no
> mesmo slot — perda silenciosa de tipo; a cabeça congelada elimina isso por construção.
> **CONTRATO UNIÃO novo**: 1ª rota que emite lista mista [bool/None/str] por construção
> (decisão do owner — lazy = default; estrito = param futuro, `T-FORCAR-MECANISMO-PARAM`).
> Ganho da cabeça 9–14 B × domínio completo; real Adult `sex`+" ?" (n=100): **50 B** vs
> 64 completo / 61 flat-str; detecção 8/8 borda, 0 FP/FN; gates da fiação 12/12.
> **Nenhum baseline moveu** (a rota só captura ex-fail-loud); 18 testes novos
> (`TestLazyBool`); **pins alterados: nenhum**. Desvios do lab registrados: decode
> dedicado (não reusa `decode_bn` — fundiria a armadilha) + b64 `validate=True`.
> Com este weld, o grupo "TCF ⊃ json" do `T-MODO-JSON-IMITADOR` passa a existir — a
> união que o json-lib aceita e o TCF recusava agora round-tripa.
> Evidência: `experiments/lab/dirty/2026-08/2026-08-01/2026-08-01-0229-lazytype-bool-extras/`
> + `.../2026-08-01-0322-lazybool-fiacao-rota-real/`.

> **✅ WELD — delimitador de POLARIDADE no single-col (2026-07-26, ADR-0035, suíte 1010 passed).**
> O corpo gastava **1 byte por LITERAL** (o `\` de corrida de dígito). Agora marca-se a **troca**
> literal↔referência: **1 byte por TRANSIÇÃO**. E, por estar *entre* as duas corridas, o
> delimitador carrega também a **fronteira** — o ponto que derrubou 3 propostas anteriores
> (labs `0038`/`0200`/`0330`: apagar o escape funde `56` + `\033` em `56033`).
>
> **Camada de BORDA**: `encode` polariza depois do corpo canônico pronto (já com seq-RLE),
> `decode` despolariza antes de tudo. O seq-RLE — que acha o dígito incrementável **pelo
> escape** — só vê corpo canônico dos dois lados, e não foi tocado.
>
> **O char é ELEITO por coluna**, do complemento do alfabeto que ela usa (conflito zero por
> construção, sem escapar o próprio delimitador). `FAIXA` = só **pontuação**: exclusão por
> **classe** porque a auditoria adversarial reproduziu que **dígito** eleito funde com a corrida
> e **letra** eleita colide com o slot do discriminador (`#TCF.8b` de uma coluna de string).
> Cabeçalho: `#TCF.8<tag><sufixo>`, sufixo de 1 char = polaridade `R`, dobrado = `L`.
>
> **FLOOR nunca-pior incluindo o próprio sufixo.** Baselines re-pinados (ADR-0024):
> **D1-D9 1586 → 1545**, **real-world 89637 → 89430**, **D17a 300 intacto** (`.8M` fora do escopo).
> Escopo do weld: single-col stamp + tipado. **Fora**: `.8M`, `.8H`, spec, órfão.
> **Aberto**: delimitador como grafia canônica interna (exigiria o seq-RLE localizar pela
> polaridade). Evidência: `experiments/lab/dirty/2026-07/2026-07-26/{1853,1913,1954,2126}`.

> **⚑ DECISÃO PENDENTE — weld do bN-dense no FLOOR (2026-07-23).** Estudo implicitude/bool/RLE/bN
> fechado com evidência medida e VERIFICADA (10 labs em `experiments/lab/dirty/2026-07/2026-07-23/`,
> nenhuma linha de `src/tcf` tocada). **Estabelecido**: (1) **segmentação misto RLE+b64 DERRUBADA** —
> reality-check em dados reais deu 0/18 vitórias (o regime "misto genuíno" é artefato sintético);
> (2) **bN-dense base64 VENCE o `dict/V2-B` atual** — tabela real adult-census 9 col × 10k:
> **89.902 → 48.224 B = 1,86× menor**; (3) **não existe limiar simples de `k`** (cruzamento
> NÃO-monotônico: bN ganha k≤32, perde k≈64–94, volta a ganhar k≥95 pq base-94 esgota e o dict pula
> p/ 2 chars/símbolo) ⇒ a forma correta é **competir no FLOOR/`min()`**, nunca-pior por construção;
> (4) ressalvas medidas: **gzip encolhe muito o ganho** (0,17×→0,75×) e **N pequeno o anula** (N=5 ≈
> empate) — colide com o foco em payload minúsculo.
>
> **Plano de weld pronto (NÃO executado)**: escopo **multi-col `.8M` apenas** (o `.8H` single-col fica
> fora — não tem ponto de seleção); novo `src/tcf/multi/bn_dense.py` espelhando `dict_v2b.py`; 3 pontos
> de fiação (`_best_of` candidato, `_serialize` prefixo, `_parse_meta` dispatch); marcador **`#`** já
> **RESERVADO** pro bN no [registry de chars](experiments/lab/dirty/notas/2026-07/tcf8-header-char-registry.md)
> (Eixo 2) — não é char novo; largura **exata `ceil(log2 k)`** (a escada {1,2,4,8} desperdiça 33%).
>
> **⛔ FALTA DECIDIR (owner)** — como entrar: **(a)** ligado por padrão + **re-pin de D17a (300B) e
> real-world (89616B) com ADR** (o ganho entra em vigor; há precedente: D17a já foi 307→303→302→300 a
> cada modo novo), ou **(b)** atrás de flag desligado (`fallback_bn=False`) — zero mudança de baseline,
> ganho opt-in, decisão de ligar fica pro `.9`. **D1–D9 (1523B) fica intacto nas duas** (é single-col,
> não passa pelo `min()` multi-col). Evidência: labs `1857` (v2 corrigida), `1832`, `1759`, `1548`.

> **⚑ PASSO 2 — API ÚNICA `encode`/`decode` (2026-07-23, suíte 861 passed).** `encode_hierarchical`
> saiu do público (virou interno `_encode_hierarchical`); **`encode()` rota por TIPO** — flat puro
> (list[str]/dict[str,list[str]] retangular ≥1 linha) fica flat, o resto (list[dict]/objeto/escalar/
> `[]`/`{}`/tipado/ragged/0-linha) vai pro `#TCF.8H`, simétrico ao `decode`. **type-coherent**: preserva
> tipo (`[1,2,3]`→array int; `None` não vira `""`); tipo não-JSON/union→fail-loud. Wire `.8H` INALTERADO
> (só a porta mudou). **Contrato pré-1.0 declarado** (ADR-0024): `encode([])`/`encode({})` viram `.8H`
> (resolve BUG-03); non-str→`.8H` tipado; tuple/bytes→fail-loud. Fonte única da superfície:
> [`docs/reference/api.md`](docs/reference/api.md) · emenda [ADR-0033](docs/adr/0033-hierarchical-codec-weld.md) ·
> plano [parecer 2340 §2](experiments/lab/dirty/notas/2026-07/2026-07-22-2340-revisao-fechamento-08-ordem-foco.md).

> **⚑ ERRATA 2026-07-22 (parecer de fechamento do `.8`, corte b0e3bf1) — controla as leituras abaixo.**
> **(1) baseline perf**: a adjudicação vigente é a análise ENTRE-runs (CV 3%, aceito *first-order*); o
> `status: termicamente-reprovado` no manifesto bruto é o gate intra-run REFUTADO, **não** o status
> metodológico final. **(2) CNPJ**: o `+7339 B` do F4 é a forma ABSOLUTA pré-FLOOR, não o resultado
> público (o FLOOR escolhe o menor blob); a modelagem estrutural da nature está **SOB REVISÃO** (owner
> suspeita de ganho real mascarado por lab). **(3) API**: remover `encode_hierarchical` do público é
> **bloqueador pré-`.9`** (API única `encode`/`decode`). **(4) versão**: metadata/READMEs já em
> `0.8.0/#TCF.8`; o snapshot do survey 22/07 é foto datada, não estado vigente. Ordem de foco e gates:
> [parecer 2340](experiments/lab/dirty/notas/2026-07/2026-07-22-2340-revisao-fechamento-08-ordem-foco.md).

> **⚑ BASELINE DE PERFORMANCE DO `.8` REGISTRADO 2026-07-22.** Processo `bench_perf` (Fase 3
> completa, `da4544a`) rodado como referência first-order pro `.9` — grandeza + pontos quentes,
> **não** precisão (protótipo; extremos → `.9`/`1.0`). Reprodutibilidade validada (piloto B1×7
> pinado: CV entre-runs 3%, Georges 2007). **Achado**: encode é **LINEAR O(n)** no nº de linhas
> (tcf-flat/json-ref/tcf-8h, slope ~1.0); a super-linearidade está só no **canto R×C extremo** —
> `cantoRC-both`=44.6s vs base 595ms = **~75×**, o penhasco do OBAT (índice de trigramas degenera
> com prefixos parecidos). Alvo do `.9` = esse penhasco (escada de prefixo adaptativa P1). Snapshot
> versionado: [`evidencia-0.8/perf-baseline/`](experiments/results/evidencia-0.8/perf-baseline/) ·
> estudo: [`2026-07-22-2207-baseline-perf-08-first-order`](experiments/lab/dirty/notas/2026-07/2026-07-22-2207-baseline-perf-08-first-order.md).

> **⚑ ESTRUTURA DO `.8` COMPLETA 2026-07-17.** P5/union RATIFICADO (fora do `.8`, fronteira
> declarada; msg de fail-loud ENSINA o fallback-string) + 2 bordas de contrato DECIDIDAS:
> **(1)** contagem-de-contêiner-vazio (problema B) = fail-loud que ensina; representação plena =
> registro-'0'/O-FMT-20 (armazenamento, pré-1.0); **(2)** ordem-de-chaves = **schema-order CANÔNICA**
> (o `.8H` é colunar-shredded como Arrow/Parquet; ECMA-404: ordem não é significativa; dict-eq
> sempre preservada). **Não há mais estrutura JSON pendente.** Caminho vira RELEASE (F3/F4/F6/C3) +
> decisão de timing (0.8.0 feature-complete agora vs 0.8.x). Suíte 853 passed. Ponteiro:
> H-P5-STRING-FALLBACK-01 (degradar union→string opt-in, revisar depois).

> **⚑ MARCO 2026-07-17 — J0 PLENO + J1 FECHADOS (funil J0-J2/L/G).** Aprovação "1→2→3" executada:
> **(1)** par R0 fechado no L1 (`e8c8be1`: SEQRLE `..` + BRACKET skip; **byte-neutro** — gates
> D1-D9/D17a/real-world SEM re-pin; **PW3 em POPULAÇÃO INTEIRA**: receita 51.536 raízes/200.000
> estab. RT byte-exato) → **J0 pleno** pela régua do funil; **(2)** P4b raiz generalizada welded
> (`cccf1bb`: `#D`/`#E`/`#O`/`#V`; dataset **0 B idêntico**; decode devolve o TIPO EXATO; defaults
> vetáveis do owner) → **J1 fechado**; **(3)** E3 canal SideOutputs no `.8H` (`3c767d7`:
> `encode_hierarchical_so`, hier_info+per_col, bytes idênticos) → pré-requisito do warning/profiler.
> Antes, no mesmo dia: escape D_json (chave `""`/LF/CR em valor e nome — `da1aa73`+`d72b9eb`) com
> auditoria (~57k RT adversarial). **Suíte 845 passed, 0 xfail de bug** · paridade `LACUNAS = {}`
> = **D_json COMPLETO**. Pausa do marco (funil §4) ANTES de J2/P5. Fontes: ADR-0033 §escape+§P4b ·
> [funil](experiments/lab/dirty/notas/2026-07/2026-07-17-0124-funil-fechamento-json-language.md) ·
> [matriz](experiments/lab/dirty/notas/2026-07/matriz-caminhos-hierarquia-2026-07-17.md) · diário 2026-07-17.

> **⚑ DIREÇÃO 2026-07-16 — JSON completo: capacidade antes da simplificação.** Programa S0–S7
> adotado: DatasetH semântico → IR lógico → representações físicas → decisão de weld. **S0–S3
> executados**, sem tocar `src/tcf`: 20/20 RT, 20/20 álgebras de vínculo, 8/8 fail-loud, 20 wires
> `.tcf` e corpus canônico byte-idêntico. Contraprova: bit `first-child` sem skip perde pai vazio;
> `[0,2,2]` e `[0,1,1]` colidem. Estado científico: confirmação conceitual sintética, não decisão de
> header/wire. Próximo: S4 wires físicos lado a lado → S5 decode/busca/paralelismo → S6 header → S7
> default/fallback e eventual weld. Fontes: [lab S0–S3](experiments/lab/dirty/2026-07/2026-07-16/2026-07-16-1708-dataseth-s0-s3-semantica-vinculos/) ·
> [semântica](tickets/T-STUDY-DATASETH-COMPLETE-SEMANTICS.md) ·
> [vínculos](tickets/T-STUDY-HIERARCHY-LINK-ALGEBRA.md) · [execução](tickets/T-EXP-DATASETH-S0-S3.md) ·
> [checkpoint S4](experiments/lab/dirty/notas/checkpoints/2026-07-16-s0-s3-capacidade-json.md).

> **⚑ DIREÇÃO 2026-07-16 (noite) — contrato externalizado + aceleradores; estrutura-sem-dado.**
> Owner ditou direção (registro pra estudo, NADA é `.8`): (1) TCF **auto-contido por default**,
> modificadores externalizam diretivas de header/schema pra **contrato nas pontas** (por versão,
> assinatura-de-contrato fail-loud) — REVISA materialização-minimal (self-containment = default,
> não invariante); (2) **arquivos de aceleração** droppable (profiler PGO-style via SideOutputs,
> dicas de view, índice); (3) **encode em pulsos** por deadline (~1ms) — a linguagem permite, o
> código não; saída não-canônica → modo de perfil. Sobre o gate P4b: formas vazias são "formatos
> opacos" → **definições**, não compressão; lab estrutura-sem-dado a criar. Registros:
> [contrato-externalizado-e-aceleradores](experiments/lab/dirty/notas/2026-07/contrato-externalizado-e-aceleradores.md) ·
> [estrutura-sem-dado-levantamento](experiments/lab/dirty/notas/2026-07/estrutura-sem-dado-levantamento.md) ·
> 7 hipóteses novas (H-CONTRACT-EXTERN-01 · H-ACCEL-SIDECAR-01 · H-ENCODE-DEADLINE-01 ·
> H-STRUCT-{DEF,AMORT,META,ASDATA}-01) no roadmap. Antes disso, no mesmo dia: lab P4a consertado
> (24 `.tcf`, errata da tabela confundida) + levantamento P4b (`46ac5f3`).

> **⚑ PAUSA 2026-07-16 — P2 revisado; investigação P4 decomposta.** P1, P3a, P3b e P2 estão
> welded. Auditoria P2 válida no caminho normal e endurecida em `268608d`; suíte observada **731
> passed, 2 skipped, 2 xfailed**. Achado residual: metadata com tag desconhecida após size pode ser
> reinterpretada como campo e produzir `[]` silenciosamente; registrar como hardening fail-loud, não
> como falha do encoder. Parecer P4: **P4a count recursivo/array-em-array** primeiro; **P4b raiz
> generalizada** depois, pois altera API e exige envelope/discriminador que preserve tipo e ordem.
> “N-raízes” é termo histórico; JSON tem uma raiz. Nenhum código P4 foi iniciado. Fonte probatória e
> gates: [levantamento P4](experiments/lab/dirty/notas/2026-07/p4-replevel-nroots-levantamento.md). Retomada:
> [checkpoint 2026-07-16](experiments/lab/dirty/notas/checkpoints/2026-07-16-revisao-p2-p4.md).

> **⚑ PAUSA 2026-07-15 — revisão pós-P1 registrada; decisão de null pendente do owner.** P1
> presença/ragged está **WELDADO e fechado** (`bcb6405` + `69db6bc`), com probe real-world amostral e
> suíte vigente **685 passed, 2 skipped, 1 xfailed**. O crash do PW3 foi diagnosticado como bug
> pré-existente do L1 (`BUG-SEQRLE-RANGE-EMPTY-B`), isolado e pinado em `xfail`; não é regressão do P1.
> Revisão crítica não encontrou outra feature de grande ROI pronta que deva passar à frente de null.
> **Opinião registrada, não decisão**: decompor P3 em **P3a null em campo** (baixo custo; usa `0` da
> definition mask) e **P3b null em elemento de array** (máscara alinhada aos elementos); null na raiz
> depende do contrato de P4/N-raízes. NaN/infinitos ficam fora de P3. Próximo ato é o owner decidir
> P3a/P3b; nenhum código de null foi alterado. Checkpoint vigente:
> [`2026-07-15-revisao-null-pos-p1.md`](experiments/lab/dirty/notas/checkpoints/2026-07-15-revisao-null-pos-p1.md).

> **⚑ WELD 2026-07-14 — HIERARQUIA `#TCF.8H` no `src/tcf` (1º incremento, gate verde)**: codec
> hierárquico weldado ADITIVO em 3 camadas (arquitetura do owner:
> [tcf-camadas-arquitetura.md](experiments/lab/dirty/notas/2026-07/tcf-camadas-arquitetura.md)) — L1 compressor
> de coluna REUSADO sem tocar; L2 `src/tcf/hierarchical.py` (NOVO, shredding em blocos + `#count`, header
> sem-espaço ADR-0031); L3 deduções. `decoder.py` roteia `H` (era fail-loud) → `decode_hierarchical`;
> `__init__` exporta `encode_hierarchical` (decode auto-roteia). **Suíte 646 passed, 2 skipped; FLAT
> BYTE-IDÊNTICO** (D1-D9/D17a/real-world pinados). RT-exato nos clássicos de transmissão (cadastro c/ 2
> listas irmãs, pedido aninhado, telemetria, arrays vazios, ambiguidade de chave). **Cobre**: raiz única,
> chaves uniformes, `{}`/`[]` recursivos. **Fail-loud/próximo**: ragged (def-level), tipos/null, N raízes,
> N:N/snowflake. Ticket: [T-CODE-TCF8H-WELD](tickets/T-CODE-TCF8H-WELD.md) (W2/W3 feitos, W5 ADR pendente).

> **⚑ REESCOPO 2026-07-13 — `.8` = feature-complete "1.0" (decisão do owner, vigente sobre o bloco abaixo)**:
> o `.8` deixa de ser "release mínimo, features → `.9`" e passa a ser **o 1.0 com tudo que funciona**;
> `.9` fica **só** limpeza/perf/paralelismo/memória/simplificação/bug-fix-de-borda. Auditoria dos 26
> tickets abertos (workflow 2026-07-13): a superfície **tabular-plana já está feature-complete** (0 features
> prontas-e-que-pagam-o-gate a puxar). Entram no `.8` DUAS expansões de capacidade: **(1) hierarquia
> `#TCF.8H`** ([T-CODE-TCF8H-WELD](tickets/T-CODE-TCF8H-WELD.md), gate de CAPACIDADE — RT-exato em JSON
> aninhado real + non-regressão flat + aprovação `src/tcf`; NÃO ≥15%) e **(2) congelar contratos de borda
> JSON** (null/tipos/ragged/`\n`; [T-API-BOUNDARY-CONTRACTS](tickets/T-API-BOUNDARY-CONTRACTS.md), regate
> pré-1.0 → `.8`). `parked-no-pay` continua parado; perf/refactor segue `.9`. Guia: reescopo no topo do
> [T-REL-08-CLOSEOUT](tickets/T-REL-08-CLOSEOUT.md) + ponte no [ROADMAP](ROADMAP.md).

> **⚑ ESTADO VIGENTE (2026-07-12) + REGRA DE LEITURA** — leia ISTO primeiro:
> - **Formato**: `#TCF.8` e' o DEFAULT ([ADR-0032](docs/adr/0032-tcf8-default-format.md), accepted —
>   multi-col `#TCF.8M`, hex, escaping; legado `.6/.7` CORTADO, git-as-compat). Single-col orfao intacto.
> - **Pacote**: `0.8.0` (bump feito; wheel + clean-room smoke PRE-verificados 2026-07-09; publicacao
>   PyPI apenas apos a fila de fechamento + go explicito do owner —
>   [T-DIST-RELEASE](tickets/T-DIST-RELEASE-0.8.0.md)).
> - **Foco vigente / fila unica por ROI**: [T-REL-08-CLOSEOUT](tickets/T-REL-08-CLOSEOUT.md).
>   FEITOS ate' 2026-07-12: F0 (12/13 bugs, 4 lotes), R0 **BUG-14**, **BUG-15**, F1 (runner
>   `bench_evidencia`), F2 (controle 29/29), **F3 amostral**, **F4-minimo** (9/9 RT nos hubs
>   prontos), **C0** (dedup do core), **FLOOR total-byte** e fronteira de spec customizado.
>   Suite local **634 passed, 2 skipped**; pinos 1523/300/89616 exatos.
> - **R1.5 concluído (redirect do owner, 2026-07-12)**: specs cadastrais, base segura e compilador
>   foram revisados em laboratório; specs do `.8` permanecem CPF/CNPJ/IP (**Opcao A**), `DateSpec`
>   ISO é candidato condicional e clássicos novos → `.9` ([T-SPEC-STATUS-08](tickets/T-SPEC-STATUS-08.md)).
>   **ACHADO F4**: nature CNPJ PIORA a tabela em dado real (+7339B, split→raw) — caveat do F6.
> - **Proximo**: executar F6 (R1.5 registrado: specs cadastrais explorados; DateSpec ISO apenas condicional) →
>   rebuild/clean-room smoke → C3 (go owner). Depois do closeout, F3/F4 populacional
>   pode rodar em janela separada com RT, bytes, custo e paralelismo registrados.
>   Corrupcao/hardening fica 0.8.1/pre-1.0; C1/C2 (rename M8A→HCC + achatar decode) pos-release.
> - **Retomada temporal**:
>   [checkpoint 2026-07-12](experiments/lab/dirty/notas/checkpoints/2026-07-12-revisao-roi-fechamento-08.md)
>   + [diario 2026-07-12](experiments/lab/dirty/notas/diario/2026-07-12.md).
> - **Numeros**: a fonte e' a SUITE (`tests/test_regression_v1_baseline.py`, `test_real_world_snapshots.py`),
>   nao as copias em compendio.
> - **REGRA DE LEITURA da pilha abaixo**: os blocos datados (retificacoes/reconciliacoes/sessoes) sao
>   CAMADAS HISTORICAS empilhadas do mais ANTIGO ao mais novo — em conflito, vence o mais NOVO e, acima
>   de tudo, o DISPOSITIVO (ADRs accepted / codigo / testes). Nao leia o primeiro bloco como o vigente.
>   (Guia completo: secao "Como ler este documento", mais abaixo.)

> **RETIFICACAO DE VERSAO (ADR-0028, 2026-06-24)** — leia os blocos datados abaixo nesta chave:
> o pacote e' `0.<formato>.<release>` (minor = numero do formato; release/patch = entrega DENTRO do
> formato). **O ciclo do lazy + poda de legado = release `0.7.2`** (formato `#TCF.7` inalterado), NAO
> `0.8.0`. **`0.8.0` fica reservado pro `#TCF.8`** (carga "cross-dict" SUPERADA — gate geral falhou
> 2026-06-27; ver reconciliacao 2026-07-08 abaixo: 0.8.0 = release da familia self-describing welded) —
> onde as notas dizem "#TCF.8 -> 0.9",
> leia "#TCF.8 = 0.8.0". "plano 0.8" nos cabecalhos de sessao = ciclo `0.7.2`. Versao do repo segue
> `0.7.1` (PyPI segura; publica `0.7.2` no go do owner). Termos: [vocabulary §Versionamento](docs/vocabulary.md).

> **RECONCILIACAO 2026-07-08 (saneamento; ponte, nao reescrita de historico)** — os blocos datados abaixo
> sao HISTORICOS; onde restatam status/estado, a FONTE-DE-VERDADE e' o dispositivo, nao esta linha:
> - **#TCF.8 (formato) esta' WELDED**, nao "proposed"/"nao implementado": a fonte e'
>   [ADR-0027](docs/adr/0027-nature-mark-header-self-describing.md) (`accepted`, MVP welded 2026-06-24) +
>   [ADR-0029](docs/adr/0029-version-format-identification-semi-implicit.md) (discriminador) + o codigo em
>   `src/tcf/` (`decoder.py`, `multi/core.py`, `natures/`) + `tests/test_natures.py`. Os blocos F2/2026-06-17
>   que dizem "ADR-0027 `proposed`" / "Nao implementado" (linhas ~78-80) e "Pacote 0.8.0 != #TCF.8"
>   (linha ~99) sao PRE-weld — superados por esta chave + pela retificacao 2026-06-24 acima.
> - **Escopo (corrigido 2026-07-08 vs o plano canonico)**: `0.8.0` = RELEASE da familia self-describing
>   `#TCF.8` (natures + discriminador + anonimas + lazy-#TCF.8 — TODOS welded); o release e' ato
>   ADMINISTRATIVO (go do owner), NAO "weldar cross-dict". O **cross-dict (H-GDICT)** foi a carga
>   originalmente prevista pro #TCF.8, mas o **gate GERAL FALHOU** (2026-06-27: 1/5 >=15%, nicho estreito
>   SNAP-like, B3/B4 suspensos; pivo robusto = **H-DICT-HIGHCARD**). Fila: `0.7.2` (lazy) antes.
> - **Fonte do GATE byte-canonical** = os testes (`tests/test_regression_v1_baseline.py` D1-D9=1523B/D17a=303B;
>   `tests/test_real_world_snapshots.py` RW=89616B) — qualquer numero repetido em compendio (CLAUDE.md/STATUS)
>   e' COPIA de conveniencia; o teste e' que mede (principio Strata: apontar, nao duplicar).
> - **Plano CANONICO do .8** = [`tcf8-estrutura-plano.md`](experiments/lab/dirty/notas/2026-06/tcf8-estrutura-plano.md)
>   (fonte unica da familia #TCF.8) + [`specs-capacity-map.md`](experiments/lab/dirty/notas/2026-06/specs-capacity-map.md)
>   (specs/natures, EnumSpec no-go). A [`tcf8-vista-o-que-falta.md`](experiments/lab/dirty/notas/2026-07/tcf8-vista-o-que-falta.md)
>   da sessao 2026-07-06/08 e' subordinada: mapeia como bN/specs/TCF.8H se relacionam (research-track, FORA do release).

> **RECONCILIACAO 2026-07-09 (#TCF.8 = DEFAULT — [ADR-0032](docs/adr/0032-tcf8-default-format.md), accepted)** —
> chave sobre TODOS os blocos datados abaixo que dizem "#TCF.7 default" / "#TCF.6/.7 legado lido" / "D17a=303B":
> - **`#TCF.8M` e' o formato DEFAULT do multi-col** (supersede a regra opt-in-SSE-nature do ADR-0027).
>   Single-col segue **orfao** intocado (D1-D9=1523B e RW=89616B — ADR-0032 nao mexe no single-col).
> - **Legado `#TCF.6`/`#TCF.7` CORTADO de `src/tcf`** (emit E decode): decode fail-loud com dica de git;
>   comparacao historica via `git checkout` OU copias em `legacy-snapshots/` (gitignored). Git-as-compat
>   (ADR-0024): a versao antiga e' ponto de progresso, nao producao — no 1.0 o passado morre no git.
> - **Byte-sizes em HEX** (T-FMT-HEADER-BASE-HEX) + **nomes com separador escapados com `\`**
>   (T-FMT-NAME-ESCAPING) + **discriminador `H`** reservado (ADR-0031, fail-loud, codec no lab).
> - **D17a re-medido = 300B** (#TCF.8M inline hex; 4a re-pin — MEDIR nao calcular; fonte = a suite).
> - **Versao**: pacote vai a `0.8.0` (ADR-0028 aceito); o ciclo `0.7.2` (lazy) foi **ABSORVIDO** no 0.8.0
>   (sem release intermediario). PyPI segura em 0.7.1 ate' publicar completo+estavel (go do owner).
> Detalhe: milestones M1 (flip+corte)/M2 (escaping)/M4 (docs) — ver ADR-0032 + diario 2026-07-09.

> **Versionamento (ADR-0024, 2026-06-14)**: projeto e' **pré-1.0**. Os minors do
> formato (`#TCF.4/.5/.6/.7`) sao iteracoes de dev rumo a um **1.0 solido**, sem
> compat rigida entre eles (git reproduz versoes antigas). O `#TCF.7` = "0.7"
> pré-1.0, **NAO v2.0** (v2.0 = depois). Pacote: `0.7.0` (era "1.0.0", rotulo
> prematuro). Labels "v1.0 frozen"/"v2.0" em ADRs/STATUS antigos: ler nessa chave.
>
> **0.7 e' o DEFAULT do encode** (multi-col): `encode(dict)` -> `#TCF.7` (fallback
> + dicionario V2-B + header minimo, automaticos). Single-col inalterado.
> Baseline D17a re-pinado **322 -> 307 -> 303 B** (V2-B na coluna `categoria`;
> #TCF.6 legado=322, lido pelo decoder + produzivel via `_encode_multi(fallback=
> False, min_header=False)`). D1-D9=1523B (single-col) inalterado. Suite 385 passed.
>
> **Proximo foco (2026-06-14)**: continuar no 0.7 (detalhes de compressao). Revisao
> implicito-vs-explicito + candidatos a knob explicito + detalhes "passaram batido"
> em `experiments/lab/dirty/notas/2026-06/2026-06-14-1947-revisao-implicito-vs-explicito.md`.
> FEITO: knobs explicitos #1-3 (fallback/min_header opt-out, min_len override);
> #5 ordering (O-FMT-02 `sort_by` order-free welded); **V2-B dicionario WELDED**
> ([ADR-0025](docs/adr/0025-v2b-dictionary-categorical-weld.md), `@`, 13.9% weighted);
> **SPLIT ESTRUTURAL WELDED** ([ADR-0026](docs/adr/0026-structural-split-weld.md),
> `%`, 4o candidato do fallback, **19.39% weighted** = maior lever do ciclo:
> decimal/data/datetime/id -> campos -> V2-B). **Pacote 8 (H-HCC dinamico) ADIADO**
> (1.30% teto, cauda longa, risco alto no detector core). **V2-D strip de afixo
> REFUTADO** (subsumido pelo OBAT, 0.11%; sinal real era split estrutural).
> **LOSS ampliado (Pacote 10, 2026-06-14)**: owner ampliou o escopo lossy ("loss e
> PRO TCF FAZER SIM"). Revisao exaustiva de TODAS as vertentes (9 facets + critico,
> workflow) em `experiments/lab/dirty/notas/2026-06/loss-taxonomia.md`. Ideia-chave: loss
> por-linha + LOSSLESS NO AGREGADO (soma; parcelamento) — PoC do maior-resto OK.
> Mais promissora = loss CROSS-COLUNA (`valor=soma(parcelas)`). Decisao de weld
> PENDENTE (owner; cruza a linha lossless, GATE N>=5).
> **FECHAMENTO DO CICLO 0.7 (2026-06-15)**: bytes-core welded (V2-A/B/split +
> header minimo + sort_by). **Higiene de tickets feita**: 3 fases welded fechadas
> (encoder-manager 1+1b, schema-builder 1+2, layered Fase 1) + 3 ja'-prontos
> confirmados (stratify-test, H-PERF-06 T01/T02); **5 parks** v2.0/pos-0.7
> (output-sinks, plan-contract, shaper-hardening, llm-gadget, META-TYPE execucao);
> [ADR-0018](docs/adr/0018-v2-format-roadmap.md) -> `accepted` (referencia do
> roadmap de formato; V2-D refutado). **Decisoes do owner**: o **0.7 permanece
> lossless-puro** — V2-C round e Pacote 10 (loss) viram **roadmap v2.0** (se
> perseguido, cross-coluna primeiro, GATE N>=5); nome PyPI = **`tcf-format`
> RESERVADO** (2026-06-16) — release **`0.7.1`** (pyproject `1.0.0` -> `0.7.1`,
> alinha ADR-0024; o patch e' contador de release, desacoplado do formato `#TCF.7`
> e do comportamento). Build validado via `uv` (`tcf_format-0.7.1.{tar.gz,whl}`).
> Suite 398 passed; D1-D9=1523B / D17a=303B intactos; `src/tcf` so' string de
> versao. Tag `v0.7.1`. Follow-ups adiados: V2-B RLE no stream; release.yml
> (Trusted Publishing). Detalhe: `experiments/lab/dirty/notas/diario/2026-06-15.md`.
>
> **SESSAO 2026-06-16 (pos-0.7, divulgacao + lazy + caracterizacoes)**:
> - **Lazy view gadget** [`scripts/tcf_lazy/`](scripts/tcf_lazy/) — **L1-L5 funcional, 27 testes**:
>   conectar e consultar (`count/sum/min/max/avg` + `where` + group-by) **descomprimindo so' o
>   necessario** (qtd-por-usuario toca **7,9%** do blob). Le `#TCF.7`, **nao-versao**, `src/tcf`
>   intocado. Achados: `*N|` no modo-tcf NAO e' separavel (so' dict/raw); L5 layout = trade-off
>   de compressao. Lab `2026-06-16-lazy-query/` + Pacote 12 (H-QUERY-01).
> - **TCF + brotli vence em ESCALA**: TCF cheio + brotli < csv+brotli em multi-col real (adult
>   −28%); "menos TCF" refutado; ordering codec-dependente (`2026-06-16-staged-and-ordering-brotli/`).
>   EXP-008 refrescado (single-col).
> - **number-nature** caracterizada -> **PARK** (weighted <15% em 2+, some sob brotli).
>   **O-FMT-12** (encode_file/auto-detect CSV) levantado -> **PARK** (input fora-do-core).
> - Criados **[`ROADMAP.md`](ROADMAP.md)** (tiers pre-1.0/2.0/pesquisa) + **[`docs/divulgacao-tcf.md`](docs/divulgacao-tcf.md)**.
>   Filtros modulares (H-NAT-MARK-02) + classificacao "e' versao?" registrados. README propagado.
> - **Pacote `tcf-format 0.7.1` publicado no PyPI**. Suite **425 passed**, 1 xfailed. `src/tcf` intocado.
>
> **SESSAO 2026-06-17 (filtros modulares F1.5/F2 + CEP)**:
> - **F1 + F1.5 FEITOS** (gadget [`scripts/natures_compiler/`](scripts/natures_compiler/)): compilador
>   DSL textual -> spec + registry por nome (cpf/cnpj/ip semeados); **14 testes**; regenera CPF/CNPJ/IP
>   do DSL == a' mao. **Zero `src/tcf`.** Achado: CEP/MAC precisariam spec novo.
> - **CEP + outer-dict pesquisados** -> **nenhuma acao**: o TCF ja' trata CEP (split/OBAT+dict, lossless,
>   zeros preservados); outer-dict subsumido por V2-B+split no caso tabular (nicho = payload minusculo
>   indexando tabela-padrao grande). [pesquisa](experiments/lab/dirty/notas/2026-06/cep-outer-dict-codebook-pesquisa.md).
> - **F2 (H-NAT-MARK-01) — DESIGN FEITO, PARADO em (A)** (decisao owner): nature-id viaja no header
>   (`#TCF.7->#TCF.8`, tag `:` no nome, resolucao core-only, id desconhecido->cru+flag). **Nao implementado**
>   — o magic permanente nao se justifica so' por DX (gate >=15%/2-reais nao bate; registry gadget ja'
>   cobre quase de graca). [ADR-0027 `proposed`](docs/adr/0027-nature-mark-header-self-describing.md) +
>   [design](experiments/lab/dirty/notas/2026-06/f2-nature-mark-header-design.md). **`src/tcf` intocado.**
>
> **SESSAO 2026-06-19 (pre-1.0: cheap-wins fechados + V2-RLE-STREAM + defrag)**:
> - **Cheap-wins fechados**: Tier A (release.yml, [reference de knobs](docs/reference/encode-knobs.md),
>   higiene CI) + CW-4 (docstrings stale em `src/tcf` alinhados, so' docstring) + CW-5 (O-FMT-11
>   subsumido por min_header/name-guard). Ver [ROADMAP](ROADMAP.md) cheap-wins.
> - **V2-RLE-STREAM caracterizado** ([lab](experiments/lab/dirty/old/refuted/2026-06-19-v2rle-stream-caracterizacao/result.md)):
>   fecha o follow-up "V2-B RLE no stream" pendente desde 06-15. **Geral CLOSED-INSUFFICIENT-GAIN**
>   (+1,19% weighted/7 reais, 0/7 >=15%, -1,39% sob brotli). **Nicho textual-puro ABERTO** p/ decisao
>   do owner (low-card skewed, ordem natural: situacao +55%, workclass +22%). Achado: **clusterizado
>   flipa pro tcf-`*N|`** (overlap com o run-RLE de linha). Registry: roadmap-hipoteses Pacote 11-bis;
>   familia RLE em [`rle-familia-estudo.md`](experiments/lab/dirty/notas/2026-06/rle-familia-estudo.md).
>   RLE intra-valor (H-INTRA) ADIADO. **`src/tcf` intocado** (lab-first).
> - **Defrag/Strata**: tickets [T-CLEAN-2](tickets/T-CLEAN-2-strata-defrag.md) (QW feitos + backlog) +
>   [META-STRATA-GOVERNANCE](tickets/META-STRATA-GOVERNANCE.md). Diretiva: sempre cross-reference.
>
> **SESSAO 2026-06-21 (plano 0.8 + lazy endurecido + transmissao + dict/H-REF)**:
> - **Plano 0.8** ([`v08-plano-etapas.md`](experiments/lab/dirty/notas/2026-06/v08-plano-etapas.md)): 0.8 =
>   lazy basico shipado+endurecido + cross dict (se pagar); Q-04 avancado -> 0.9. Pacote 0.8.0 != #TCF.8.
> - **Lazy endurecido (workstream A)**: A1 banco de testes (4 modos + bordas, verde) + A2 fecha bug de
>   dupla contagem em `touched` + A3 otimiza o CAMINHO do algoritmo (count 1->0 decode; redundancia
>   3->1; Python deferido). 381 passed. [lab](experiments/lab/dirty/2026-06/2026-06-19/2026-06-19-lazy-testbank/result.md).
>   `src/tcf` intocado (tudo no gadget). Falta A4 (promover -> `tcf.view`, sob aprovacao) + A5.
> - **Cross dict / referencia**: achado — `^N` ja' e' dict implicito; ideia do owner = dict GLOBAL no
>   header ([H-GDICT-01](experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md)) + familia H-REF
>   ([`dict-referencia-hipoteses.md`](experiments/lab/dirty/notas/2026-06/dict-referencia-hipoteses.md)). Nao caracterizado.
> - **Header linhas-vs-bytes**: row-count REFUTADO (solid-block; ganho ininfimo, perde O(1)/paralelo);
>   base-94 size = O-FMT-18 candidato (so' nicho transmissao-minuscula). [lab](experiments/lab/dirty/old/refuted/2026-06-19-header-rows-vs-bytes/result.md).
> - **Guia de transmissao por API** ([`transmissao-api-onde-tcf-importa.md`](experiments/lab/dirty/notas/2026-06/transmissao-api-onde-tcf-importa.md)):
>   honesto — nicho do TCF ~5-15% (batch/export tabular grande); **teste decisivo pendente**:
>   TCF+brotli vs **NDJSON+brotli** (so' comparamos com CSV+brotli).
> - Checkpoint Strata: [`checkpoints/2026-06-21-avaliacao-documental-strata.md`](experiments/lab/dirty/notas/checkpoints/2026-06-21-avaliacao-documental-strata.md).
>
> **SESSAO 2026-06-21-b (faxina + avaliacao 0.8 + A4)**:
> - **Faxina dirty/docs** (commit 4401046): 17 labs -> `old/welded|refuted`, drift
>   `#TCF.6->#TCF.7` corrigido nos docs de exemplo, snapshots marcados, MAP/diario/historia
>   atualizados, `_wf_*.js` + `out_files/` destrackeados. `src/tcf` intocado.
> - **Avaliacao grounded de prontidao 0.8** (workflow 6 agentes, testes rodados): base solida
>   confirmada (D1-D9=1523B/D17a=303B/RW=89616B verdes); A1-A3 do lazy feitos; gaps = A4/A5/B1/C.
> - **A4 FEITO** ([T-CODE-LAZY-VIEW-PROMOTE](tickets/T-CODE-LAZY-VIEW-PROMOTE.md), owner aprovou
>   o toque): lazy promovido `scripts/tcf_lazy/lazy.py` -> **`src/tcf/view.py`** (camada read-only;
>   `from tcf import view`), shim de compat mantido. Aditivo, **zero regressao byte-canonical**,
>   380 passed. Versao segue 0.7.1 (bump 0.8.0 e' no release, workstream C).
> - **4 tickets 0.8 criados** (rastreabilidade): A4 (closed), A5 [T-DOC-LAZY-REFERENCE],
>   B1 [T-EXP-H-GDICT-01] (segurado ate' A4, feito), C [T-DIST-RELEASE-0.8.0] (blocked).
> - **A completo** (A1-A5): lazy promovido + reference Diataxis ([docs/reference/lazy-view.md]).
> - **Drift de superficie #TCF.6-default corrigido** (commit aa92642): TCF-format.md diagrama/Estado,
>   STATUS visao/foco, docs/README hub -> 0.7. ADRs/codnomes preservados (historico).
> - **B1 caracterizado** ([lab gdict](experiments/lab/dirty/2026-06/2026-06-21/2026-06-21-gdict-caracterizacao/)): 3 tensoes
>   do owner; medicao sintetica + reais. **Correcao metodologica do owner: brotli NAO e' gate** (nem
>   sempre aplicado + incompativel com lazy; [[gzip-e-compressao-externa...]]). Re-medindo TCF-nativo
>   (textual+paralelismo+lazy): **cross-dict GANHA no regime same-domain-refs** (origem/destino, de/para,
>   FK repetida): **−19.2% textual** + lazy le' o dict 1x; PERDE em disjunto/entidade -> **hibrido V2**
>   (dicts por grupo) captura e evita. Veredito de "close" revertido — era artefato do gate-brotli.
> - **B1 PASSA em dado real** (Etapa 5, owner aprovou add datasets; raw em Z:/external, provenance no lab):
>   SNAP ca-GrQc (grafo from/to) **−19.3% textual** (cruza 15% com 2 colunas); OpenFlights (airport
>   src/dest IATA −4.6%, ids −6.6%); lazy cross-col le' o dict 1x. Ganho escala com K/N + nº cols
>   same-domain. → recomendacao **ir pro B2** (#TCF.8 opt-in + hibrido V2 + ADR + GATE).
> - **Filtros/naturezas revisitados** (owner 2026-06-24, [lente](experiments/lab/dirty/notas/2026-06/2026-06-24-0034-filtros-graus-de-entrega.md)):
>   reframe "graus de entrega" (otimizar-formato -> bypass) + 3 tiers de ONDE o dict mora (V2-B in-blob /
>   B1 cross-dict / H-CODEBOOK out-of-blob universal = "dict roubado"). Consolidado: graus 1-2 welded
>   (ADR-0015), enumerated in-blob refutado, spec-dict universal = nicho payload-minusculo NAO-MEDIDO +
>   forward-compat duro; eixo VELOCIDADE = lacuna real.
> - **DECISAO de escopo (owner 2026-06-24)**: **0.8 = lazy (A, feito) + release (C)**; **B2/B3 cross-dict
>   (#TCF.8) + F2/spec-dict/filtros -> 0.9** (B2 paga o #TCF.8 com ganho medido; resto por carona). Proximo:
>   **workstream C** (release 0.8.0). Publicar exige go explicito do owner.

**Snapshot 2026-06-08** (**Schema/quality gadget COMPLETO + incidente
OneDrive recuperado + push remoto**) — resumo desde 06-03. Atualizacoes
posteriores nos blocos **SESSAO** acima (ate' 2026-06-17):

- **Schema/Quality Gadget (T-RECOVER-SCHEMA-MULTI-TABLE) — COMPLETO**, em
  `scripts/schema_gadget/` (auxiliar, ALERT-ONLY, NUNCA arruma, `src/tcf`
  intocado). 4 fases:
  - Fase 1 `fk_detect.py` — FK candidate por overlap de valores + confiança
    graduada (nome+cardinalidade). TPC-H: 9/9 recall, 0 FP em `alta` (d6b5d2e).
  - Fase 3 `sideouts_quality.py` — alertas ZERO-CUSTO (constant, duplicate_key
    single-PK, type_drift fração-numérica). Validação adversarial (workflow 7
    datasets) removeu useless_id (94% ruído em tpch) (9ed66de).
  - Fase 4 `report.py`+`__main__.py` — CLI `python -m schema_gadget
    {list|analyze}` markdown/JSON (484ce9b).
  - Fase 2 `date_check.py` — impossible_date/format_mix/suspicious_date,
    auto-detecta colunas-data. NÃO zero-custo (scan calendário). Validado por
    corrupção controlada (0 FP no real limpo, recall total no corrompido) (88618f8).
  - ~40 testes CI-friendly. Ticket closed-done. T-DATA-3 deixou de bloquear.
- **Incidente OneDrive (2026-06-03→08, ADR-0021)**: OneDrive criou cópias de
  conflito `-DESKTOP-SG30VJF` e reverteu `main` 158 commits (latência local,
  1 máquina, RARO — não sistêmico). RECUPERADO: backup Z: + reset p/ HEAD real
  + limpeza. Nada perdido. Repo VIVE no OneDrive → checar HEAD/`import tcf` no
  início de sessão (memória `reference-onedrive-git-corruption-risk`).
- **Git remoto SADIO**: `origin/main` sincronizado (push fast-forward dos ~45
  commits). Branch-lixo `main-DESKTOP-SG30VJF` removido local e **confirmado
  ausente no remoto** (2026-06-16: `git ls-remote` mostra so' `main` + tag `v0.7.1`).

**Anterior 2026-06-03** (**Datasets BR/CNPJ + H-PERF-06 Cython +
shaper gating + reorg separacao de concerns**). 33 commits desde o bloco
anterior. Resumo:

- **Datasets novos** (referencia leve no git; dados reais regeneraveis em Z:):
  - `ibge-municipios` (5571 municipios BR, geografia real) — commit 29024f7
  - `tpch-sf01` (TPC-H SF=0.1, ~866k linhas, FK OK) — commit 4733f52
  - `br-identidades` (SINTETICO: 500k pessoas CPF + 100k empresas CNPJ,
    geografia IBGE reusada, FK socio_cpf) — commit f5e2fa8
  - `receita-cnpj` (REAL non-PII: 200k estabelecimentos Receita Federal) —
    commit f7ded09. **Nature CNPJ medida em dado real: 64.1% vs M10 108.4%
    = ganho 40.9%** (>> gate 5%). 1a fonte ECOLOGICA de check-digit ->
    **nature CNPJ confirmada-empirica** (confianca Media, falta N>=5 fontes).
  - tpch part/partsupp samples emitidos (T-DATA-4, commit c9b4984)
  - Setup via WebDAV: Receita migrou pra Nextcloud (`/public.php/webdav`);
    `setup_receita_cnpj.py` faz streaming-stop (nao baixa os ~2GB).
- **H-PERF-06-v2** (acelerar HCC `_detect_compositions`, byte-canonical):
  - Fase A: prune top-K + early-term (ADR-0019, commit 8118d7a)
  - Fase B: acelerador **Cython opcional** com fallback pure-Python
    byte-identico (ADR-0020, commit f44f7d3). `src/tcf/_core/detect.pyx`.
    Cumulativo ~2.67x speedup encode (online-retail 20k x 8col).
- **Shaper** (tool auxiliar, NAO TCF-core) cientificamente validado:
  `tests/test_shaper_scientific.py` (10 testes P1-P5: fk_preserving,
  stratify chi2+TVD, join, volume marginal, schema levels). Aprovado p/
  uso <=100k linhas (T-SHAPER-SCIENTIFIC-GATING, commit 004e8b0).
- **Gate real-world** byte-canonical: `tests/test_real_world_snapshots.py`
  (retail Description/StockCode + lineitem l_comment, regime n_tam_est>=3) —
  T-REGRESSION-REAL-WORLD, commit bb321c5. Mudancas em HCC/prune DEVEM passar.
- **Reorg separacao de concerns** (Fases 0-7, commits 5a15538..bb02cff):
  benchmark LLM v0.5 consolidado em `llm-benchmark/` (harness); catalogo
  findings FICA em `docs/findings/` (research compendium); motor v0.5 em
  `old/tcf/` revisto (`LEVELS-REVIEW.md` — niveis L0-L3 desambiguados do
  codigo). README enxuto 332->184 linhas. **src/tcf INTOCADO** (verificado).
- **Bugs ADR-0006/0007** fixados (commit 2b6edc0): separador ref->lit p/
  `,`/`~`; decode preserva string vazia.

**Anterior 2026-05-27** (**Auditoria profunda + fechamento do limbo**:
workflow 6 dimensoes mapeou 197 itens (76 pra repensar). Limbo de hipoteses
nunca concluidas foi fechado empiricamente (lab `2026-05-27-naturezas-reais-uci/`):
naturezas raras/Pacote 7 re-caracterizadas nos UCI — estrutura EXISTE (refutacao
anterior foi dataset errado); novo achado de ponto cego baixa-cardinalidade
(TCF infla colunas curtas ate' 2.3x); fallback identity prototipado (0.8-10.2%,
RT OK). Todos exigem format change → roadmap **v2.0** ([ADR-0018](docs/adr/0018-v2-format-roadmap.md)).
**B-tier resolvido**: H-DA-01 seq-RLE CONFIRMADO forte (beijing -29.5% se removido,
nao marginal). v1.0 segue pronta pra tag (limbo agora caracterizado+decidido, nao esquecido).

**Anterior 2026-05-27** (**Sprint 3 v1.0**: Validation Plan ADR-0017 8/9 +
packaging fix critico (pyproject empacotava old/tcf v0.5) + docs Diataxis. Commit 92fed11.

**Anterior 2026-05-27** (**Sprint 2 v1.0 fechado**: ADR-0017
proposed (freeze format+API em v1.0, 339 linhas com 5+1 enforcement
features); benchmark UCI extension (wine 90.9%, beijing 71.7%, retail
23.7% — **TCF vence 7/9 datasets** acumulados); TCF-format.md ganha
seccao "Versionamento" + Estado v1.0 atualizado. Pendente pra tag
v1.0.0: Validation Plan 10 items em [ADR-0017](docs/adr/0017-format-spec-v1-frozen.md).

**Anterior 2026-05-27** (**Sprint 1 v1.0**: T-DATA-1 3 datasets UCI
baixados + canonical rodado; bug encoder seq-RLE multi-delta `+-1,0`
encontrado e corrigido (decoder rejeitava); suite regressao formal
`tests/test_regression_v1_baseline.py` (21 tests: D1-D9 snapshot + D17a
322B INVARIANT). 259 tests passing. Commit 304f38a.

**Anterior 2026-05-27** (**Consolidacao dirty lab**: 17 labs
pos-canonical movidos pra `experiments/lab/dirty/old/welded/` (10) ou
`old/refuted/` (7). Topo do dirty agora tem **3 labs ativos +
1 baseline-consolidado**. Novo
[`2026-05-27-baseline-consolidado/`](experiments/lab/dirty/2026-05/2026-05-27/2026-05-27-baseline-consolidado/)
com METRICS.md (D1-D9 1523B, D17a 322B INVARIANT), ADRs-INDEX.md
(16 ADRs 0001-0016), lessons-learned.md, run-baseline.py reproduzivel.
MAP.md atualizado. **Source of truth pra comparacoes futuras**.

**Anterior 2026-05-24** (**CHECKPOINT sessao maxima**: 3 ADRs
welded canonical (0014 unified API, 0015 natures, 0016 multi-delta).
14 sub-exps dirty + benchmark consolidado. **TCF vence em 5/6 datasets**
vs csv+brotli. 96 -> 211 tests. Pausa pra retomada — checkpoint em
[`2026-05-24-sessao-maxima-natures-multi-delta.md`](experiments/lab/dirty/notas/checkpoints/2026-05-24-sessao-maxima-natures-multi-delta.md).

**Anterior nesta sessao**: ADR-0016 WELDED — Bug #2 sub-exp 14 fix:
HCC seq-RLE multi-delta `*N+d1,d2,...|template`. M10 markers preserved
pra uniform; CSV format pra mixed. D-IP-subnet 1000 sem nature:
117.51% -> **4.18%** (-96.4%). D1-D9 byte-canonical preservado.
Bug #1 (atom detection) superseded. 19 tests novos.
Suite completa: 211 passed (+19) + 1 pre-existing fail.

**Anterior**: **ADR-0015 WELDED + extensao SPEC_IP**:
`src/tcf/natures/` package canonical com:
- `TemplatedCheckedSpec` + SPEC_CPF + SPEC_CNPJ (CPF -64%)
- `TemplatedPaddedSpec` + SPEC_IP (IP subnet 1000 = **229B / 1.71%** confirmado)
- Protocol uniforme: spec.encode_value/decode_value/classify_value methods
- Polimorfico zero `isinstance` (Strategy pattern, separacao responsabilidades)
- API publica: `encode(values, nature=SPEC_CPF/SPEC_CNPJ/SPEC_IP)` opt-in
- Default sem nature preserva M10 INVARIANT byte-canonical D17a 322B
- 37 tests novos (21 test_natures.py + 16 test_natures_ip.py)
- Suite completa: 192 passed (+37) + 1 pre-existing fail.

**Dirty lab CPF/CNPJ/IP completo + 3 tickets P2/P3
novos registrados**: 14 sub-exps executados. Achados sumarizados:
- Sub-exps 01-09: CPF/CNPJ caracterizacao + variantes B/C + fallback + stats ISO 25012
- Sub-exp 10 debug OBAT/HCC: 6 cases revelaram comportamentos
- Sub-exp 11: hipotese gating ADR-0010 **REFUTADA** (min_len bypass nao muda)
- Sub-exp 12 IP hex variante D: **abandonada** (entre B e C, nunca vence)
- Sub-exp 13 base-aware seq-RLE: **arquitetura validada** (regression OK), mas
  ganho marginal em hex (-94B subnet). H1 partially refutada.
- Sub-exp 14 cross-subnet investigation: **2 bugs reais identificados**:
  (1) M8A nao cria atom secundario; (2) compare_for_seq rejeita multi-run delta
- 3 tickets P2/P3 registrados: T-CODE-HCC-MULTI-DELTA-FIX, 
  T-CODE-HCC-ATOM-DETECTION-REFINE, T-CODE-LAYERED-PIPELINE
- Nota arquitetural funil de camadas + toggles + online adaptive + literatura
  (Frame of Reference, PFOR-DELTA, Gorilla, Dictionary encoding))

**Anterior 2026-05-24**: T-CODE-SCHEMA-BUILDER Fase 1+2 WELDED:
novo `src/tcf/schema.py` com `build_schema(data) -> TableSchema`,
`ColumnSchema` + `TableSchema` dataclasses, `to_dict()` + `to_json()`.
Reaproveita 100% SideOutputs (ColumnFeatures, cadence_info, min_len,
seq_rle_runs, multi_info). Output deterministico. 24/24 tests novos
(`test_schema.py`). Suite: 155 passed (+24) + 1 xfailed + 1 pre-existing
fail. `natures` placeholder vazio pra Fase 3 (META-TYPE-ENCODERS).

**Anterior 2026-05-24**: T-CODE-ENCODER-MANAGER Fase 1b WELDED
work-stealing: refactor `_encode_columns_parallel` pra submit +
as_completed sorted desc por workload. Benchmark: customer 0.83x,
orders 1.23x (4w) / 1.30x (8w). Conclusao: gargalo NAO eh load
imbalance, eh IPC overhead (Windows spawn ~4s + pickling).
Speedup teto realista ~1.3x sem dependencia externa (joblib/Cython).
Byte-canonical preservado. 82 tests OK. Otimizacoes alem adiadas
pra Fase 1c (joblib opcional) ou Fase 4 (streaming chunks).

**Fase 1 anterior 2026-05-24**:
`encode(data, parallel=False|True|N)` via ProcessPoolExecutor.
`_worker_encode_column` picklavel. D17a 322B INVARIANT preservado em
modo parallel. 14/14 tests novos (`test_parallel.py`). SideOutputs
serializado entre workers funciona.

**Sessao 2 anterior 2026-05-24**: O-FMT-14
header desacoplavel/opcional registrado em `futuras-otimizacoes-formato.md`.
Nova nota `naturezas-templated-2026-05-24.md` cataloga sub-naturezas
de T02 Templated (CPF/IP/MAC/telefone/CEP/EAN/IBAN) + T04 Checksummed
(CPF/CNPJ/Luhn) + LR Lossy (FLOAT-PREC/GEO/MONETARY) + CP Composite
(datetime/endereco/money). Hipoteses H-TM-*/H-LR-*/H-CP-* registradas
em roadmap-hipoteses.md secao Pacote 7. META-TYPE-ENCODERS atualizado.
Lab nao iniciado — criterio reabertura: T-DATA-1 download + caracterizacao
em datasets dedicados.

**Sessao 1 anterior 2026-05-24**: API UNIFICADA ADR-0014: `encode(list|dict)`
+ `decode(text)` por dispatch (tipo + shebang). Single = caso particular de
multi com 1 coluna. `SideOutputs` recipiente opcional captura
column_features, cadence_info, OBAT log, HCC trace/rede, seq_rle_runs,
multi_info, per_col. `encode_table`/`decode_table` viram deprecated aliases.
D17a 322B INVARIANT preservado. 117 passed (+21 novos) + 1 xfailed. 4 novos
tickets P2/P3: T-CODE-ENCODER-MANAGER (revive D13 v0.4), T-CODE-PLAN-CONTRACT,
T-CODE-SCHEMA-BUILDER (consume SideOutputs), T-CODE-OUTPUT-SINKS.
TCF-format.md expandido com pipeline ASCII unificado + camadas futuras.)

> **Como ler este documento**: este e' o ponto de entrada
> bibliografico do projeto. Se um sistema novo (humano ou Claude)
> precisar entender **onde estamos agora**, comeca por aqui.
> Sempre atualizar este arquivo ao fechar sub-experimento ou tomar
> decisao estrutural. **Status absoluto**, nao incremental.
>
> **Sistema de discoverability (novo 2026-05-18)**:
> - `CLAUDE.md` raiz — guia pra Claude Code com inventario completo
> - `MAP.md` raiz — wayfinding map
> - `INDEX.md` raiz — auto-gerado por `scripts/index.py`
> - `docs/adr/` — Architecture Decision Records numerados
> - `docs/vocabulary.md` — vocabulario controlado
> - `docs/how-to/audit-memorias-e-documentacao.md` — auditoria periodica
> - `experiments/lab/dirty/notas/checkpoints/` — pausas explicitas
>
> **Checkpoint ativo**:
> [`2026-05-24-sessao-maxima-natures-multi-delta.md`](experiments/lab/dirty/notas/checkpoints/2026-05-24-sessao-maxima-natures-multi-delta.md)
> — 3 ADRs welded canonical (0014/0015/0016); 14 sub-exps; benchmark
> consolidado (TCF vence 5/6); pronto pra retomada
>
> Checkpoint anterior:
> [`2026-05-18-pausa-para-organizar-documentacao.md`](experiments/lab/dirty/notas/checkpoints/2026-05-18-pausa-para-organizar-documentacao.md)

---

## TCF — visao 1 paragrafo

**TCF** (Tabular Compact Format) e' um formato de **compressao de
strings tabulares** (0.7 / `#TCF.7`, pré-1.0 ADR-0024) com pipeline
canonical delta-aware (M10 baseline, ADR-0011) + camadas V2 multi-col
(fallback/dicionario/split/header-minimo, ADR-0022/0023/0025/0026):

- **Pre-pass** — `analyze_column` (ColumnFeatures) + `detect_cadence`
  (regras 1+2, ADR-0008) + `detect_min_len` (heur v3 + gating n>=100,
  ADR-0010)
- **OBAT** (Online Bidirectional Affix Tokenizer) — tokeniza via
  LCP+LCS. `processar_with_hint` (shape-preserve) ou `processar`
  canonical. Em `src/tcf/core/` + `src/tcf/obat_shape.py`.
- **HCC** (Hierarchical Compositional Coding, M8.A + seq-RLE) —
  detector unificado + emit composicional + seq-RLE near-identical
  (`*N+delta|template`). Em `src/tcf/composicional/`.

API publica unificada (ADR-0014): `from tcf import encode, decode, SideOutputs, view`.
- `encode(list)` -> body single-col (sem shebang)
- `encode(dict)` -> multi-col com header `#TCF.8M` (default, ADR-0032; hex + escaping)
- `decode(text)` -> dispatch pelo discriminador (`#TCF.8M`; legado #TCF.6/.7 -> fail-loud, cortado)
- `SideOutputs()` opcional captura features/logs/traces internos
- `view(blob)` -> camada read-only lazy/consultavel (A4)

RT byte-canonical validado em D1-D9 (M10 baseline 1523B, single-col intacto),
D17a multi-col (300B #TCF.8M default, ADR-0032), Adult+TPC-H
single-col 57 cols, 9 tabelas multi-col (Adult + TPC-H tier 1+2, 136k linhas,
-33.02% weighted vs raw, -31.46% vs single concat, RT 9/9).

---

## Foco — snapshot 2026-06-03 (estado vivo: blocos SESSAO no topo + [ROADMAP.md](ROADMAP.md))

> Esta seção é um snapshot datado. O foco corrente está nos blocos **SESSAO**
> no topo deste arquivo (mais recente 2026-06-21: faxina + A4 do plano 0.8) e
> no [ROADMAP.md](ROADMAP.md) (Marco v0.8). Mantida pra rastro.

Pré-1.0 (ADR-0024 supersede o "v1.0 frozen" do ADR-0017): formato `#TCF.7`
default, `#TCF.6` legado. Snapshot 2026-06-03: datasets BR/CNPJ adicionados,
nature CNPJ confirmada-empirica em dado real, H-PERF-06 Cython welded, shaper
validado, reorg de separacao de concerns completa (Fases 0-7). **`src/tcf/`
intocado** em toda a reorg/datasets.

### Historico — Ciclo 2026-05-21/22 (Revalidacao + H-DA-11 fechado)

- **2026-05-21 Pacote 2** (escape deduction H-ED-01..04): CLOSED-INSUFFICIENT-GAIN
  (real-world max 1.13% << criterio 5%). Primeiro ticket YAML frontmatter
  validou metodologia. Aprendizado: sintetico "digit-dominant" nao
  generaliza pra real-world.

- **2026-05-21 Revisao conceitual** de hipoteses confirmada-empirica:
  classificadas A/B/C por evidencia real-world. Lab dirty `2026-05-21-revalidacao-categoria-B/`
  + ticket T-REVAL-H-DA-01-06-10.

- **2026-05-21 T-REVAL Categoria B**: CLOSED-COMPLETED-WITH-SURPRISES
  - H-DA-06 SUBSUMIDA em H-DA-09b-v2 (cobertura 87.5% real-world)
  - H-DA-01 MARGINAL real-world (1.36%, 16.3x reducao vs sint)
  - **H-DA-10 CONFIRMADA INESPERADAMENTE** (9.92% weighted)
  - Nova H-DA-11 decorrente

- **2026-05-22 T-EXP-H-DA-11**: CLOSED-CANONICAL-WELDED (ADR-0010)
  - Heuristica v3 (decision tree shallow em avg_len + card + is_numeric)
  - Gating n_threshold=100 preserva M9 baseline 1615B EXATO
  - **Adult+TPC-H ganho 9.87% weighted real-world**
  - `src/tcf/auto_min_len.py` (novo) + `src/tcf/encoder.py` modificado
  - RT 100%: D1-D9 9/9 + real-world 57/57

- **2026-05-22 T-CODE-H-DA-11c**: CLOSED-REFACTOR-COMPLETED (zero-risk)
  - Novo `src/tcf/column_features.py` (ColumnFeatures + analyze_column)
  - Refator `src/tcf/auto_min_len.py` com APIs from_features + wrapper
  - Output IDENTICO ao pre-refactor (1615B + 9.87% + RT 100%)
  - Prepara terreno pra T02-T07 + weld futuro de detect_cadence canonical

- **2026-05-22 T-CODE-PACOTE1-WELD-CANONICAL**: CLOSED (ADR-0011)
  - Pipeline canonical delta-aware completo welded em src/tcf
  - Novos modulos: `auto_cadence.py`, `obat_shape.py`, `composicional/hcc_seqrle.py`
  - `encoder.py` + `decoder.py` modificados (pipeline + HCCSeqRLE.decode)
  - **D1-D9 baseline mudou: M9=1615B → M10=1523B (-92B, -5.70%)**
  - **Real-world ganho 11.73% weighted** (vs M9 puro 1,008,003B → 889,714B)
  - RT 100%: 9/9 + 20/20 sint + 57/57 real-world

- **2026-05-22 T-REVAL-H-DA-07**: CLOSED-CONFIRMED-REAL-WORLD
  - Shape-preserve gating funciona: 62/66 cols sem mudanca
  - 2 wins enormes: c_name -98.19%, D9 -48.03%
  - 2 losses pequenas: l_extendedprice +0.65%, c_acctbal +0.20%
  - Real-world weighted: -0.46% (ganho marginal)
  - Categoria B residual fechada

- **2026-05-23 T-EXP-H-PERF-05d**: CLOSED-VALIDATED-WITH-BYTE-DIVERGENCE
  - Fase 1 profile GO (rebuild=46% _dc, 0.3% lines/iter)
  - Fase 2 prototype IncrementalSyntax: 37/41 byte-canonical OK
  - 4 divergencias em datetime TPC-H (+62B / 80kB = 0.08%)
  - Causa: ordem Counter difere (rebuild vs incremental)
  - Welding adiado (fix byte-canonical complexo OU aceitar M11)
  - Pacote 4 permanece fechado-parcial; ADR-0009 OBAT continua win principal

- **2026-05-23 Reflexao naturezas numericas**:
  - Nota `notas/naturezas-numericas-2026-05-23.md` cataloga ~12 naturezas
  - 4 ja' welded (incremento, cadencia, alta-card numerica, comprimento)
  - Pacote 5 (enumerated) testado e refutado em sub-exp

- **2026-05-23 T-EXP-PACOTE5-T03-ENUMERATED**: CLOSED-NO-GO-M10-SUFICIENTE
  - Caracterizacao 37 low-card cols (Adult + TPC-H)
  - M10 ja' captura via dedup + seq-RLE eficientemente
  - Encoder explicit seria PIOR em runs adjacentes (l_linestatus -141%)
  - So' ganharia em valores LONGOS sem runs (c_mktsegment +30%)
  - Weighted total real-world: -2.28% (regressao)
  - **Aprendizado meta**: M10 e' encoder enumerated implicito eficiente
  - **Anti-incidente**: hipotese promissora conceitualmente refutada
    em medicao empirica (mesmo padrao Pacote 2)

- **2026-05-23 Pacote 3 (parser robustness) — ADR-0007 ACCEPTED + WELDED**:
  - Fix Opcao B (separator `*` em ref->lit ambiguo) ja' estava welded
    em src/tcf/composicional/syntax.py desde 2026-05-19 (sem docs atualizadas)
  - Sub-exp 05 valida: 10/10 casos minimos OK (era 7/10), M10 1523B
    preservado, RT 100% real-world (57/57)
  - ADR-0007 atualizado proposed -> accepted + welded
  - Roadmap H-FIX-03 atualizado para WELDED; H-FIX-01 refutada
    (Opcao A perde pra B); H-FIX-02 N/A

- **2026-05-23 T-EXP-H-DA-09c-d-e**: CLOSED-NO-GO-THRESHOLD-07-OTIMO
  - Varreu threshold detect_cadence {0.5, 0.6, 0.7, 0.8} em 66 cols
  - Thr 0.7 atual e' otimo (0.5/0.6 dao -3.06% regressao real-world)
  - H-DA-09d (multivariada) + H-DA-09e (adaptativo) adiados
  - **Consolidacao**: 3 refutacoes na sessao (Pacote 2, Pacote 5,
    H-DA-09c) confirmam que TCF M10 esta bem calibrada

- **2026-05-23 T-DOC-1/2 + T-CLEAN-1**: CLOSED (aderencia metodologica P3)
  - **T-DOC-1**: CITATION.cff criado (v0.6, MIT); README "How to cite";
    DOI Zenodo defer ate' v1.0/paper
  - **T-DOC-2**: ADR-0012 criado documentando mapeamento Diataxis local
    (docs/algorithms→reference, docs/theory→explanation); MAP.md atualizado
  - **T-CLEAN-1**: .pre-commit-config.yaml criado (ruff + detect-secrets +
    basicos + custom no-cache-dirs); pyproject.toml + README dev setup;
    `pre-commit install` pending owner

- **2026-05-23 T-EXP-NATUREZAS-RARAS**: CLOSED-NO-GO
  - Exploracao naturezas #5 (range narrow) e #8 (suffix/arredondamento)
  - #8 Suffix: -4.45% weighted (regressao — M10 ja' captura categoricas
    via dedup)
  - #5 Range: +1.08% marginal (3 cols com potencial isolado: l_quantity,
    l_linenumber, age — peso baixo no agregado)
  - **4a refutacao da sessao** (5 contando T-EXP-H-DA-09c)
  - Padroes financeiros reais precisariam dataset dedicado (defer)

- **2026-05-23 T-DATA-1**: CLOSED 2026-06-02 (3 datasets baixados + canonical setup; raw em Z:/tcf-data/external/, metadata em datasets/canonical/)
  - 3 datasets UCI canonicos planejados:
    - Online Retail (~45MB, UnitPrice .99/.95/.50 = #8 arredondamento)
    - Beijing PM2.5 (~2MB, PRES 991-1046 = #5 range narrow)
    - Wine Quality (~100KB, density/pH decimais cientificos)
  - Scripts setup criados: setup_wine_quality.py, setup_beijing_pm25.py,
    setup_online_retail.py (padrao similar a setup_adult.py)
  - READMEs + metadata.json em datasets/canonical/{name}/
  - Owner roda localmente: `pip install -e ".[datasets]"` + `python scripts/setup_*.py`
  - Futuro T-EXP-NATUREZAS-RARAS-V2 re-testa #5/#8 com novos datasets

- **2026-05-23 T-EXP-MULTI-COL-SCALING**: **CLOSED-WELDED-CANONICAL** (ADR-0013)
  - Port `multi_col.py` (EXP-011 M9) pra canonical M10 (`from tcf import encode, decode`)
  - D17a (sint 13x4): 322B preservado vs EXP-011, RT OK
  - **9 tabelas real-world** (Adult Census + TPC-H tier 1+2, 136k linhas):
    - **-33.02% weighted vs raw** (15,848,939 → 10,614,897 bytes)
    - **-31.46% weighted vs single-col concat** (controle)
    - RT **9/9** OK
    - Adult Census destaque: -65.14% vs raw (15 cols mixed)
    - **Lineitem 60k x 16**: -17.11% raw, -30.73% single, RT OK (16.6 min)
    - Header overhead < 1% em datasets >= 1500 rows (5/5)
    - Outlier region (5 rows): +3.87% vs raw (header dominante, esperado)
  - **WELDED em src/tcf** (Opcao A aprovada):
    - `src/tcf/multi.py` novo (encode_table + decode_table + MAGIC_MULTI)
    - `src/tcf/__init__.py` atualizado: API publica agora 4 funcs
    - ADR-0013 criado (accepted + welded)
    - `tests/test_multi_col_rt.py` novo (17/17 passing, D17a 322B INVARIANT)
  - Sub-exp dirty: `experiments/lab/dirty/2026-05-23-multi-column-scaling/`

- **2026-05-23 T-CI-1 + T-CI-2**: CLOSED (CI completo em uma rodada)
  - **T-CI-1**: .github/workflows/ci.yml com job lint (pre-commit)
  - **T-CI-2**: refactor tests + job test ativado
    - 5 tests v0.5 broken movidos pra tests/_archive_v05/
    - tests/conftest.py + pytest markers (requires_data)
    - pyproject.toml: testpaths + norecursedirs + markers
    - tests/test_core_rt.py NOVO (31 tests CI-friendly: M10 baseline
      INVARIANT 1523B + RT edge cases + Pacote 3 comma fix)
    - workflow CI matrix py 3.10/3.11/3.12 ativo
  - Validacao local: 30 passed + 1 xfailed (edge case `encode([])`),
    50 deselected (requires_data)

**Pacote 4 — Perf OBAT/HCC** (fechado 2026-05-20):
- H-PERF-02 WELDED (ADR-0009) — hash trigrama, alpha 1.75→1.42
- H-PERF-04/05/06 ADIADOS (Patricia trie, counter incremental, Cython)

**Proximo pacote — decisao pendente**:
- ~~**H-DA-11c** consolidar pre-pass features~~ (FEITO 2026-05-22)
- ~~**Pacote 1 weld canonical**~~ (FEITO 2026-05-22, ADR-0011)
- **H-DA-07** revalidacao (categoria B residual)
- **H-PERF-05d** counter incremental HCC (zero-risk, alto potencial)
- **T02-T07** outras naturezas pre-tx (criterio ainda nao atingido)

### Pacotes fechados (referencia)

| Pacote | Foco | Status | Welding |
|---|---|---|---|
| **Pacote 1** (Delta-aware) | auto-pre detect_cadence → OBAT hint → HCC seq-RLE | fechado | EXP-010 (clean), 20/20 RT |
| **Pacote 1 refino** (H-DA-09b-v2) | regra numeric+high-cardinality em real-world | fechado | ADR-0008 em EXP-010/auto_pre |
| **Pacote 2** (escape deduction) | H-ED-01..04: ganho real-world insuficiente | CLOSED-INSUFFICIENT-GAIN 2026-05-21 | — |
| **Pacote 3** (parser robustness) | bug `,` em literais HCC | fechado | ADR-0007 em src/tcf/composicional/syntax.py |
| **Pacote 4** (perf OBAT) — parcial | hash trigrama OBAT | **welded** (sub-pacote 1) | ADR-0009 em src/tcf/core/online.py |
| **T-REVAL Categoria B** | revalidacao H-DA-01/06/10 em real-world | CLOSED 2026-05-21 (surpresa H-DA-10 9.92%) | — |
| **T-EXP-H-DA-11** | auto-detect min_len por coluna | **WELDED canonical** 2026-05-22 | **ADR-0010 em src/tcf/auto_min_len.py + src/tcf/encoder.py** (9.87% real-world) |
| **T-CODE-H-DA-11c** | ColumnFeatures unificado (refactor) | CLOSED 2026-05-22 | **src/tcf/column_features.py + refactor auto_min_len.py** (zero-risk) |
| **T-CODE-PACOTE1-WELD-CANONICAL** | Pipeline delta-aware completo canonical (M9 → M10) | **CLOSED 2026-05-22** | **ADR-0011: auto_cadence + obat_shape + hcc_seqrle + encoder/decoder modificados** (11.73% real-world) |
| **T-REVAL-H-DA-07** | Shape-preserve gating em real-world | CLOSED-CONFIRMED 2026-05-22 | gating preserva 62/66 cols neutras; 2 wins (c_name -98%, D9 -48%), 2 losses pequenas |
| **T-EXP-H-PERF-05d** | Counter incremental HCC | CLOSED-VALIDATED-WITH-BYTE-DIVERGENCE 2026-05-23 | 37/41 byte-canonical OK; 4 datetime TPC-H divergem 0.08%; welding adiado |
| **T-EXP-PACOTE5-T03-ENUMERATED** | Encoder enumerated explicito | CLOSED-NO-GO-M10-SUFICIENTE 2026-05-23 | M10 ja' captura via dedup+seq-RLE; encoder explicit PIOR em runs adjacentes |
| **Pacote 3** (parser robustness, ADR-0007) | Fix bug `,` em literais (Opcao B separator) | **WELDED canonical** (welded 2026-05-19, ADR accepted 2026-05-23) | src/tcf/composicional/syntax.py:435-442 |
| **T-EXP-H-DA-09c-d-e** | Tunar threshold detect_cadence | CLOSED-NO-GO 2026-05-23 | thr 0.7 ja' otimo; H-DA-09d/e adiados |
| **T-DOC-1** | CITATION.cff | CLOSED 2026-05-23 | criado v0.6 MIT; DOI Zenodo defer |
| **T-DOC-2** | Diataxis naming local | CLOSED 2026-05-23 | ADR-0012 criado |
| **T-CLEAN-1** | Pre-commit hooks | CLOSED 2026-05-23 | config criado; install pending owner |
| **T-EXP-NATUREZAS-RARAS** | Naturezas #5 (range) #8 (suffix) | CLOSED-NO-GO 2026-05-23 | M10 ja' captura suffix categorico; range marginal +1.08% weighted |
| **T-CI-1** | GitHub Actions CI Fase 1 | CLOSED 2026-05-23 | workflow ci.yml lint + test ativado (matrix py 3.10/3.11/3.12) |
| **T-CI-2** | Tests refactor CI-friendly | CLOSED 2026-05-23 | 5 v0.5 archived; 31 RT tests novos; marker requires_data |
| **T-DATA-1** | 3 datasets UCI/OpenML canonicos | **CLOSED 2026-06-02** | online-retail, beijing-pm25, wine-quality baixados; canonical setup + raw em Z:/tcf-data/external/ |
| **T-EXP-MULTI-COL-SCALING** | Multi-col welded canonical em src/tcf (ADR-0013, Opcao A) | **CLOSED-WELDED-CANONICAL 2026-05-23** | src/tcf/multi.py + encode_table/decode_table API publica; D17a 322B INVARIANT; 17/17 tests novos; 9 tabelas real-world: -33.02% raw weighted |
| **T-CODE-UNIFIED-API** | API unificada `encode(list\|dict)` + SideOutputs (ADR-0014, supersede ADR-0013) | **CLOSED-WELDED-CANONICAL 2026-05-24** | encoder/decoder dispatcher + side_outputs.py + multi.py interno; D17a 322B preservado; 117 passed (+21); deprecated aliases mantidos |

### Pacotes registrados, nao iniciados

| Pacote | Foco | Status |
|---|---|---|
| **Pacote 2** (escape deduction) | H-ED-01..04: omitir `\digits` quando deduzivel | registrado, adiado |
| **Pacote 4** (perf — restante) | H-PERF-04/05/06: HCC opt + trigrama meio + Cython | em curso |

### Arquivo historico (superseded)

- **T01 incremental** (`2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/`):
  13 sub-exps pre-tx multi-pass. **Superseded** pelo Pacote 1 Delta-aware
  (que cabe no vertice triplice single-pass). Mantido como referencia
  metodologica; nao guia evolucao.
- **META-TYPE-ENCODERS** (`tickets/META-TYPE-ENCODERS.md`): planejou
  7 naturezas (T01-T07) + 5 estudos (L01-L05). Pos-Pacote 1, foi
  realinhado: T01 absorvido como OBAT-level, T02-T07 e L01-L05
  permanecem adiados aguardando 2-3 naturezas validadas.

**Roadmap cross-lab**: [`experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md`](experiments/lab/dirty/notas/2026-05/roadmap-hipoteses.md)
**Diario mais recente**: [`experiments/lab/dirty/notas/diario/2026-05-19.md`](experiments/lab/dirty/notas/diario/2026-05-19.md)

---

## Datasets ativos

### Canonical (`datasets/canonical/` — metadata+sample no git, dados reais em Z:)
| Dataset | Tipo | Volume | Nota |
|---|---|---|---|
| adult-census | real (UCI) | 48842 | single-table mixed |
| tpch-sf001 | gerado (DuckDB) | 60k lineitem | SF=0.01, 8 tabelas FK |
| tpch-sf01 | gerado (DuckDB) | 600k lineitem | SF=0.1, ~866k total |
| online-retail | real (UCI) | 541909 | free-text Description, .99 prices |
| beijing-pm25 | real (UCI) | 43824 | sensor decimais, range narrow — **ATENCAO: `Z:/tcf-data/interim/beijing-pm25.db` tem 0 BYTES** (arquivo vazio, sem tabelas; verificado 2026-08-14 na varredura de float). Buraco do corpus, nao erro de leitura |
| wine-quality | real (UCI) | 6497 | features quimicas decimais |
| ibge-municipios | real (IBGE) | 5571 | BR, categoria hierarquica acentuada |
| br-identidades | **sintetico** | 600k | CPF+CNPJ validos, geografia IBGE; vies declarado |
| receita-cnpj | **real non-PII** | 200k | CNPJ Receita; nature CNPJ 40.9% real |

> Gaps de cobertura + roadmap em memoria `project-dataset-coverage-map`
> (free-text longo, IP/UUID, monetary-string, >1M linhas).
>
> **VARREDURA DE FLOAT 2026-08-14** (9 bancos, 23 tabelas, 186 colunas, **31 com float**; classificacao na coluna INTEIRA, nao na amostra): **(a)** float real so' existe em 2 dos 9 bancos — `online-retail` e `wine-quality`; o resto do float e' TPC-H (sintetico) e **conta em dobro** (`sf001` e `sf01` sao o mesmo gerador em escala 10x: 18 das 31 colunas sao a duplicata). Os 4 bancos BR/censo tem **zero** float, inclusive escondido em TEXT (verificado por regex). **(b)** **ZERO notacao cientifica** e **ZERO artefato binario** no corpus inteiro — nenhum `0.30000000000000004` em lugar nenhum; fora de `wine.alcohol`, o maximo de casas de QUALQUER coluna e' 6 (`wine.density`). **(c)** `wine.alcohol` e' a UNICA coluna com decimal longo: histograma bimodal com buraco (6413 val em 1 casa, 44 em 2, **nada entre 3 e 12**, 40 em 13-14). Os 40 sao **n/30** — medias/divisoes por 3 exportadas com `%.15g`. **(d)** IDENTIFICADOR que virou float: `online_retail.CustomerID`, 406.829 valores, 100% inteiros, declarado `REAL` — paga um `.0` por valor em qualquer serializacao via `str`; idem `l_quantity`. **(e)** regime **semi-inteiro**: `free_sulfur_dioxide` 99,11% inteira e `total_sulfur_dioxide` 99,55%, com o residuo TODO em `.5`. **(f)** o teste de "money" por casas decimais e' QUEBRADO — `str()` suprime o zero final dos centavos (`45523.10` -> `45523.1`), entao "exatamente 2 casas" trava perto de 0,90 por construcao e **nenhuma** coluna monetaria do corpus passaria de 95%; o invariante real e' **"e' multiplo exato de 0,01"**. Fonte: `experiments/lab/dirty/2026-08/2026-08-14/2026-08-14-1745-grafia-fracional-e-escala-com-excecoes/result.md`.

### Synthetic (`datasets/synthetic/`):

### Core TCF (D1-D9) — controle algoritmo
Padroes estruturais (afixos, wrappers). Cobertos pelo TCF-CORE
canonical. Total 2981 raw -> 1523 TCF (51.1%, baseline M10/ADR-0011 pinado
em test_regression_v1_baseline.py; 1615B era M9 antigo). Referenciados em
EXP-007/008.

### ERP/CRM tipos (D10-D15) — variety (stress de tipos, nao guia)
Formatos misturados artificialmente — uteis pra entender limites,
nao guia de evolucao (cf. diretriz dados-realistas).

### Incremental T01 (D11a-m) — realistic
- `D11a-datas-dia.csv` (12 linhas) — sequencial maio-junho 2026 [day]
- `D11b-datas-borda.csv` (14 linhas) — bordas mes/ano + Feb 29 [day]
- `D11c-datas-mensal.csv` (13 linhas) — fatura mensal dia 5 [day]
- `D11d-datetime-min.csv` (13 linhas) — heartbeat top-of-minute [second]
- `D11e-datetime-mensal.csv` (13 linhas) — fatura mensal datetime (datas+9h) [second]
- `D11f-datetime-ms.csv` (13 linhas) — cadencia 1s [ms]
- `D11g-datetime-us.csv` (13 linhas) — cadencia 1ms (multi-char) [us]
- `D11h-datetime-ns.csv` (13 linhas) — cadencia 1us (multi-char) [ns]
- `D11i-datas-mensal-com-correcao.csv` (7 linhas) — mensal com day corrections (multi-position)
- `D11j-datetime-tz-Z.csv` (13 linhas) — minute cadence, tz constante `Z` [second+tz]
- `D11k-datetime-tz-offset.csv` (13 linhas) — minute cadence, tz constante `-03:00`
- `D11m-datetime-tz-variavel.csv` (6 linhas) — multiplas zonas (-03/+00/+02), mesma UTC absoluta

---

## Tickets ativos

`tickets/`:

| ID | Status | Foco |
|---|---|---|
| [META-NAMING](tickets/META-NAMING.md) | CLOSED | TCF/OBAT/HCC oficial |
| [META-DOCS-V05-OBSOLETE](tickets/META-DOCS-V05-OBSOLETE.md) | CLOSED | archive v0.5 |
| [META-THEORY-MOVE](tickets/META-THEORY-MOVE.md) | CLOSED | mover teoria pra docs/theory/ |
| [META-EXP-FORMAT](tickets/META-EXP-FORMAT.md) | CLOSED | template validacao vs comparativo |
| [META-TYPE-ENCODERS](tickets/META-TYPE-ENCODERS.md) | **OPEN** | plano-mestre T01-T07 + L01-L05 (adiados) |
| [META-PERF-PHASE2](tickets/META-PERF-PHASE2.md) | CLOSED-PARCIAL | Pacote 4 perf phase 2 |
| [META-ESCAPE-DEDUCTION](tickets/META-ESCAPE-DEDUCTION.md) | CLOSED-INSUFFICIENT-GAIN | Pacote 2 |
| [T-REVAL-H-DA-01-06-10](tickets/T-REVAL-H-DA-01-06-10.md) | CLOSED-COMPLETED-WITH-SURPRISES | Revalidacao Categoria B (2026-05-21) |
| [T-EXP-H-DA-11](tickets/T-EXP-H-DA-11.md) | **CLOSED-CANONICAL-WELDED** | Auto-detect min_len (ADR-0010, 9.87%) |
| [T-CODE-H-DA-11c](tickets/T-CODE-H-DA-11c-features-unificadas.md) | **CLOSED-REFACTOR-COMPLETED** | ColumnFeatures unificado (zero-risk) |
| [T-CODE-PACOTE1-WELD-CANONICAL](tickets/T-CODE-PACOTE1-WELD-CANONICAL.md) | **CLOSED 2026-05-22** | Pacote 1 canonical (ADR-0011, M9 → M10, 11.73% real-world) |
| [T-REVAL-H-DA-07](tickets/T-REVAL-H-DA-07.md) | **CLOSED-CONFIRMED-REAL-WORLD** | Shape-preserve gating valida em real-world |
| [T-EXP-H-PERF-05d](tickets/T-EXP-H-PERF-05d.md) | **CLOSED-VALIDATED-WITH-BYTE-DIVERGENCE** | Counter incremental HCC (welding adiado) |
| [T-EXP-PACOTE5-T03-ENUMERATED](tickets/T-EXP-PACOTE5-T03-ENUMERATED.md) | **CLOSED-NO-GO-M10-SUFICIENTE** | Encoder enumerated explicit refutado (M10 ja' captura) |
| [T-DOC-1-citation-cff](tickets/T-DOC-1-citation-cff.md) | **CLOSED 2026-05-23** | CITATION.cff (v0.6, DOI defer) |
| [T-DOC-2-diataxis-naming](tickets/T-DOC-2-diataxis-naming.md) | **CLOSED 2026-05-23** | ADR-0012 Diataxis local |
| [T-CLEAN-1-pre-commit-hooks](tickets/T-CLEAN-1-pre-commit-hooks.md) | **CLOSED 2026-05-23** | .pre-commit-config.yaml |
| [T-EXP-NATUREZAS-RARAS-EXPLORACAO](tickets/T-EXP-NATUREZAS-RARAS-EXPLORACAO.md) | **CLOSED-NO-GO** | naturezas #5/#8 raras em datasets gerais |
| [T-CI-1-github-actions](tickets/T-CI-1-github-actions.md) | **CLOSED 2026-05-23 (Fase 1+2)** | workflow CI completo (lint + test matrix) |
| [T-CI-2-tests-refactor](tickets/T-CI-2-tests-refactor.md) | **CLOSED 2026-05-23** | 5 v0.5 archived; 31 tests novos CI-friendly |
| [T-DATA-1-datasets-financeiros-cientificos](tickets/T-DATA-1-datasets-financeiros-cientificos.md) | **CLOSED 2026-06-02** | 3 datasets UCI/OpenML baixados + canonical setup (Z:/tcf-data/external/) |
| [T-EXP-MULTI-COL-SCALING](tickets/T-EXP-MULTI-COL-SCALING.md) | **CLOSED-WELDED-CANONICAL 2026-05-23** | src/tcf/multi.py welded (ADR-0013); encode_table/decode_table publicos; 17/17 tests; -33.02% raw weighted real-world |
| [ADR-0014 (welded direto)](docs/adr/0014-unified-api-side-outputs.md) | **CLOSED-WELDED-CANONICAL 2026-05-24** | API unificada encode(list\|dict) + SideOutputs; ADR-0013 superseded; 117 passed |
| [T-CODE-ENCODER-MANAGER](tickets/T-CODE-ENCODER-MANAGER.md) | **OPEN-FASES-1+1B-WELDED 2026-05-24** | Fase 1+1b: paralelismo `encode(data, parallel=N)` via ProcessPool + work-stealing (sorted desc workload), 14 tests, byte-canonical OK. Speedup ~1.23-1.30x (teto IPC overhead Windows spawn). Fases 1c/2/3/4 pendentes. |
| [T-CODE-OUTPUT-SINKS](tickets/T-CODE-OUTPUT-SINKS.md) | **OPEN P2 2026-05-24** | Contract Sink pluggable, refactor scripts/writers/ (bloqueado por encoder-manager) |
| [T-CODE-PLAN-CONTRACT](tickets/T-CODE-PLAN-CONTRACT.md) | **OPEN P3 2026-05-24** | Plan dataclass (group_by/order/batch_size), habilita O-FMT-01..04 |
| [T-CODE-SCHEMA-BUILDER](tickets/T-CODE-SCHEMA-BUILDER.md) | **OPEN-FASES-1+2-WELDED 2026-05-24** | Fase 1+2: `build_schema(data) -> TableSchema`; ColumnSchema + to_dict/to_json; 24/24 tests; reaproveita SideOutputs 100%. Fase 3 (naturezas) depende META-TYPE-ENCODERS reabrir. |
| [T-CODE-HCC-MULTI-DELTA-FIX](tickets/T-CODE-HCC-MULTI-DELTA-FIX.md) | **CLOSED-WELDED-CANONICAL 2026-05-24** | Bug #2 sub-exp 14 fixed via ADR-0016. D-IP-subnet 1000 sem nature: 117.51% -> 4.18% (-96.4%). M10 invariant preservado, marker CSV format opcional. |
| [T-CODE-HCC-ATOM-DETECTION-REFINE](tickets/T-CODE-HCC-ATOM-DETECTION-REFINE.md) | **CLOSED-SUPERSEDED-BY-ADR-0016 2026-05-24** | Bug #1 nao precisa fix isolado — cross-subnet ja' compactado via Bug #2 fix. |
| [ADR-0016 (welded direto)](docs/adr/0016-hcc-multi-delta-seq-rle.md) | **CLOSED-WELDED-CANONICAL 2026-05-24** | HCC seq-RLE multi-delta. Marker novo `*N+d1,d2,...|template` opt-in (uniform mantem M10 format). Bug #2 sub-exp 14 fix. 19 tests, D-IP-subnet 1000: 117% -> 4.18%. |
| [T-CODE-LAYERED-PIPELINE](tickets/T-CODE-LAYERED-PIPELINE.md) | **OPEN-FASE-1-WELDED 2026-05-24** | PipelineConfig dataclass + 3 toggles (pre_pass, obat_shape_preserve, hcc_seq_rle). encode(data, layers=cfg) opt-in. D17a 322B INVARIANT + D1-D9 byte-canonical preservados. 25 tests novos. Fase 2 (online adaptive) pendente. |
| [ADR-0015 (welded direto)](docs/adr/0015-natures-templated-checked-weld.md) | **CLOSED-WELDED-CANONICAL 2026-05-24** | TemplatedCheckedSpec + SPEC_CPF + SPEC_CNPJ + TemplatedPaddedSpec + SPEC_IP em `src/tcf/natures/`. API publica `encode(values, nature=SPEC_*)` opt-in. CAMADA 0 do funil welded. 37/37 tests, default preserva M10 INVARIANT. IP subnet 1000=229B (1.71%). |
| [T-REGRESSION-REAL-WORLD](tickets/T-REGRESSION-REAL-WORLD.md) | **CLOSED-DONE 2026-05-31** | Gate byte-canonical real-world (retail Description/StockCode + lineitem l_comment, n_tam_est>=3). Fixtures 2k em datasets/samples/. Mudancas HCC/prune DEVEM passar. |
| [T-SHAPER-SCIENTIFIC-GATING](tickets/T-SHAPER-SCIENTIFIC-GATING.md) | **CLOSED-DONE 2026-05-31** | 10 testes estatisticos (P1-P5) validam claims do shaper. Aprovado <=100k linhas. |
| [T-SHAPER-CODE-HARDENING](tickets/T-SHAPER-CODE-HARDENING.md) | **OPEN P2** | Hardening shaper p/ escala >100k (A1 filter-before-load, A3 lstrip bug, A4 dedup, A6 lazy-load). Nao bloqueia uso <=100k. |
| [ADR-0019 (welded)](docs/adr/0019-hcc-detect-compositions-topk-prune.md) | **CLOSED-WELDED 2026-05-30** | H-PERF-06-v2 Fase A: prune top-K + early-term em HCC _detect_compositions. Byte-canonical preservado. |
| [ADR-0020 (welded)](docs/adr/0020-cython-optional-accelerator.md) | **CLOSED-WELDED 2026-05-31** | H-PERF-06-v2 Fase B: acelerador Cython opcional de _detect_compositions, fallback pure-Python byte-identico. ~2.67x cumulativo. |
| [T-DATA-2-RECEITA-CNPJ](tickets/T-DATA-2-RECEITA-CNPJ.md) | **CLOSED-DONE 2026-06-02** | Dataset CNPJ real (200k, non-PII). Nature CNPJ ganho 40.9% em dado real -> confirmada-empirica (confianca Media). |
| [T-DATA-4-TPCH-PART-SAMPLES](tickets/T-DATA-4-TPCH-PART-SAMPLES.md) | **CLOSED-DONE 2026-06-01** | Samples part/partsupp TPC-H committed (categoria hierarquica observavel). |
| [T-DATA-3-EDGE-QUALITY-FIXTURES](tickets/T-DATA-3-EDGE-QUALITY-FIXTURES.md) | **DEFERRED** | Plano de dados de borda p/ gadget de qualidade (bloqueado por T-RECOVER-SCHEMA-MULTI-TABLE; gadget nao existe). |
| Reorg separacao de concerns (Fases 0-7) | **DONE 2026-06-02** | benchmark LLM -> llm-benchmark/; findings ficam em docs/; old/tcf revisto (LEVELS-REVIEW). src/tcf intocado. Ver memoria project-reorg-separation-of-concerns. |
| [T-CODE-EMPTY-FRAG-INDEX-RT](tickets/T-CODE-EMPTY-FRAG-INDEX-RT.md) | **CLOSED 2026-06-13** | [probatório] Bug de RT no core M10 (achado na caracterizacao V2-A): string vazia desloca index de fragmento HCC. 2 modos (syntax._parse_decl frag-index + hcc_seqrle rstrip vazio-final). Fix decode-only/byte-safe; 12 reproducers pinados em test_core_rt; 332 passed; D1-D9=1523B + real-world preservados. |
| [ADR-0022 (welded direto)](docs/adr/0022-v2a-fallback-identity-weld.md) | **CLOSED-WELDED 2026-06-13** | **V2-A fallback identity (abre v2.0)**: opt-in `encode(table, fallback=True)`; por coluna min(TCF, raw); emite `#TCF.7 M` + marcador `!<size>=<name>` sse alguma coluna cai pra raw. Default OFF preserva byte-canonical (D1-D9=1523B, D17a=322B). Caracterizado 9 fontes (7.85% weighted). 340 passed. V2-B/C/D seguem roadmap (ADR-0018). |
| [ADR-0023 (welded direto)](docs/adr/0023-v2-minimal-header-weld.md) | **CLOSED-WELDED 2026-06-14** | **Header v2 minimo** (O-FMT-15+16): opt-in `encode(table, min_header=True)`. Revisao do header: TODO `#TCF.7` dispensa o prefixo `# ` do meta (o flag `M` ja' declara colunas); min_header tambem omite o size da ULTIMA coluna (corpo ate' EOF). #TCF.6 mantem `# ` (congelado). Compoe com fallback. Default OFF preserva byte-canonical. Cadastro README 182->177B (−5). 351 passed. Foco: payload minusculo (memoria project-byte-level-compression-focus). |
| O-FMT-02 `sort_by` (welded direto) | **CLOSED-WELDED 2026-06-14** | **Ordenacao order-free** opt-in `encode(table, sort_by="col")`: reordena linhas pela chave -> agrupa similares -> +compressao (5-15% low-card). Decode retorna a ordem ORDENADA. Pre-encode transform (nao toca pipeline). Default None inalterado. 6 testes TestSortBy. Caracterizado em `2026-06-14-ordering-characterizacao`. |
| [ADR-0025 (welded direto)](docs/adr/0025-v2b-dictionary-categorical-weld.md) | **CLOSED-WELDED 2026-06-14** | **V2-B dicionario/categorico**: 3o candidato do fallback `min(tcf, raw, v2b)`, marcador `@<size>=<name>`. Coluna low-card vira [tabela de unicos]+[stream de indices 1-char] em vez de 1 ref `^idx` por linha. Order-free; gated `2<=K<N, K<=1024`. Zero-regressao por construcao. Caracterizado 8 datasets reais (13.9% weighted, RT 42/42). D17a 307->303 (re-pin ADR-0024/0025). 385 passed. GATE real-world verde. |
| [ADR-0026 (welded direto)](docs/adr/0026-structural-split-weld.md) | **CLOSED-WELDED 2026-06-14** | **Split estrutural** (H-STRUCT-01): 4o candidato do fallback `min(tcf, raw, dict, split)`, marcador `%<size>=<name>`. Valor estruturado (decimal/data/datetime/id) com template uniforme vira campos (template 1x) -> cada campo low-card esmagado pelo V2-B (sinergia = motor). Gate 100% uniforme + >=2 campos + variacao; sem mecanismo de excecao. Auto-detect gated, zero-regressao. **Maior lever do ciclo: 19.39% weighted** em 8 datasets reais (50.4% nas afetadas). Complementa natures CPF/CNPJ (min). Name-guard `!@%`. D17a=303/D1-D9=1523 INTOCADOS (nao dispara em tabela pequena). 398 passed. GATE verde. |

---

## Experimentos clean publicados

`experiments/lab/clean/`:

| EXP | Foco | Status |
|---|---|---|
| EXP-007-prototipo-tcf-core | Validacao byte-canonical src/tcf vs M14 baseline (9/9 OK, 1615 bytes) | pushed |
| EXP-008-compressao-comparada | TCF vs gzip/brotli/zstd/lzma/bz2 em 4 formatos × 15 datasets | pushed |
| EXP-009-pre-tx-natureza | Meta-pasta (stub) — sub-experimentos nascem ao fechar macros dirty | stub |
| EXP-010-tcf-delta-aware-prototype | Prototype clean welded do Pacote 1 (single-column, 20/20 RT, -18% vs canonical) | ativo |
| EXP-011-multi-column-basic | Multi-column basic (per-coluna independente, RT OK em D17a, -34.6% vs raw CSV) | ativo |
| EXP-012-real-world-adult-census | Real-world Adult Census via shaper (RT 4/4 OK, ratio 38-42% em 100-5000 rows) | concluido |
| EXP-013-real-world-tpch | Real-world TPC-H 8 tabelas (RT 8/8 OK apos welding ADR-0007; ratio 90.6% total raw->tcf) | concluido |
| EXP-014-tpch-lineitem-scale | Performance scale lineitem (1k-20k + full 60175). Pre-ADR-0009: O(N^1.75) / 71min full. **Pos-ADR-0009: O(N^1.42) / 18.5min estimado, 21.3min REAL (+15%, RT OK).** RT 5/5 OK | concluido |
| EXP-015-tcf-hierarquico-csv-json | Prototipo TCF.8H: JSON<->TCF.8H<->JSON preserva a arvore; CSV nao precisa de hierarquia | concluido |
| EXP-016-bn-familia-bits | Bateria sintetica da familia bN + polaridade: 72 casos / 11 familias, 4 provas por caso (RT estrito, determinismo, nunca-pior, correcao≠bN). **0 falhas**; bN ativa em 52. A lacuna da rota tipada (`regimes-que-perdem.md` §2) FECHOU com o weld do `T-BN-TIPADO` 2026-08-07; 6 casos re-pinados de `recusa` p/ `ativa`, bN ativa em 58 | concluido |

EXP-009.1+ ainda nao abertos (criterio: macro dirty fechar com hipotese
confirmada).

---

## Diretrizes ativas (memorias)

- **dados realistas** — TCF e' pra sistemas reais, nao caos artificial.
  D10/D13/D14 sao stress de variety extrema, nao guia.
- **staged pipeline** — "burros e trabalhadores agora, pequenos e
  rapidos depois". Pre-tx em 3 estagios explicitos (identify /
  normalize / optimize). Naive primeiro.
- **template comparativo** — experimentos multi-eixo precisam de
  subpastas + contra-prova + classes + reports multiplos + tabelas
  formatadas (vide META-EXP-FORMAT).
- **vocabulario disciplinado** — sem "incrivel/onde brilha/melhor"
  fora de cenario; usar "diferenca em cenario X".
- **dirty isolado** — codigo experimental nao vai pra src/ ate
  weld deliberado com testes byte-canonical.
- **commit local, push sob demanda** — desde 2026-05-16. Nao mandar
  pro GitHub sem confirmacao explicita.
- **self-containment do .tcf** — arquivo + algoritmo padrao =
  reconstrucao do original. Sem hint externo. Cabecalho (se preciso)
  vive dentro do .tcf. Validado em sub-exp 09.

---

## Estrutura de pastas (apos reorg separacao de concerns 2026-06-02)

```
TCF/
├── STATUS.md                        # este arquivo
├── README.md (enxuto v0.6), CHANGELOG.md, CLAUDE.md, MAP.md, AGENTS.md
├── src/tcf/                         # CANONICAL v0.6 (OBAT + HCC + natures + _core/detect.pyx)
├── datasets/
│   ├── synthetic/                   # D1-D17
│   ├── canonical/                   # 9 datasets (metadata+sample; dados em Z:)
│   └── samples/                     # fixtures committed (real-world gate)
├── llm-benchmark/                   # benchmark LLM v0.5 (ACESSORIO) — harness eval/ + scripts/
├── old/tcf/                         # motor v0.5 niveis L0-L3, congelado (LEVELS-REVIEW.md)
├── docs/
│   ├── algorithms/ adr/ theory/ how-to/ tutorials/   # v0.6 (Diataxis)
│   ├── findings/                    # catalogo cientifico v0.5 LLM (historico, FICA aqui)
│   └── archive/                     # v0.5/v0.1 congelado
├── tickets/                         # planejamento markdown (YAML frontmatter)
├── experiments/
│   ├── lab/{clean,dirty}/           # labs v0.6 (dirty/old/ = M0-M14 + welded + refuted)
│   ├── results/ scratch/            # output LLM (gitignored)
└── tests/                           # suite v0.6 + fixtures
```

---

## Proximas direcoes (ordenado por prioridade)

### Prioridade alta (caminho feliz)

1. ~~**H-DA-07 revalidacao real-world**~~ (FEITO 2026-05-22,
   T-REVAL-H-DA-07: CONFIRMADA)
2. ~~**H-PERF-05d counter incremental HCC**~~ (FEITO 2026-05-23,
   validated-with-byte-divergence; welding adiado)
3. ~~**Pacote 5 T03 enumerated**~~ (TESTADO 2026-05-23: NO-GO,
   M10 ja' captura via dedup+seq-RLE)
4. ~~**H-DA-09c/d/e** refinos detect_cadence~~ (TESTADO 2026-05-23:
   NO-GO, thr 0.7 ja' otimo; 09d/e adiados)
5. ~~**H-FIX-01/02/03** Pacote 3 parser robustness~~ (FEITO 2026-05-23:
   ADR-0007 ACCEPTED + WELDED, H-FIX-03 win via Opcao B separator)
6. ~~**T-DOC-1/2 + T-CLEAN-1**~~ (FEITO 2026-05-23: CITATION.cff,
   ADR-0012, .pre-commit-config.yaml)
7. **H-PERF-06 Cython/Rust port** — adiado, requer build system
8. ~~**Naturezas raras** (#5 range, #8 arredondamento)~~ (TESTADO
   2026-05-23: NO-GO em datasets gerais; #8 -4.45%, #5 +1.08%)
9. ~~**Multi-column scaling** — EXP-011 base, expansao futura~~ (FEITO
   2026-05-23 com Fase 4 lineitem + WELDED canonical: T-EXP-MULTI-COL-SCALING
   port M10 + 9 tabelas real-world + src/tcf/multi.py via ADR-0013;
   API publica encode_table/decode_table; 17/17 tests novos)
10. ~~**CI** — GitHub Actions com pre-commit + tests~~ (FEITO COMPLETO
    2026-05-23: T-CI-1 lint + T-CI-2 tests refactor + job test ativo)
11. ~~**T-CI-2** — refactor tests CI-friendly~~ (FEITO mesmo dia)

### Prioridade media (decisao pendente)

0. **⛔ bN-dense no FLOOR — COMO entrar (owner decide)**: (a) ligado por
   padrao + re-pin D17a/real-world com ADR, ou (b) atras de flag desligado
   (`fallback_bn=False`). Plano pronto, escopo multi-col `.8M`, marcador `#`
   ja' reservado no registry, nunca-pior por construcao (entra no `min()`).
   Ganho medido: tabela real 1.86x menor; mas gzip encolhe e N pequeno anula.
   Ver bloco ⚑ no topo + labs `2026-07-23-1857` (v2) e `-1832`. **Nada em
   `src/tcf` foi tocado.**
3. **H-PERF-05d counter incremental HCC** — unico zero-risk de alto
   potencial no Pacote 4 ainda aberto (~50-70% HCC perf). Implementacao
   complexa (state entre iters).
4. **H-DA-09c/d/e** — refino threshold/multivariada/adaptativo do
   auto-pre detect_cadence. Decorrentes do Pacote 1.
5. **H-PERF-06 Cython/Rust port** — adiar ate' Python opt esgotar
   (alto overhead, integrar build system).

### Prioridade baixa (adiados explicitamente)

6. **META-TYPE-ENCODERS T02-T07** — outras naturezas (templated,
   enumerated, checked, etc.). Criterio reabertura: real-world onde
   Pacote 1 + ADR-0008 + ADR-0010 nao bastem. Atual: ADR-0010 acabou de
   aumentar cobertura — criterio MENOS satisfeito.
7. **Track 2 L01-L05** — estudos de camada algoritmo (token-level,
   slot detection, markers tipados, tree-balance, pre-filter).

### Aberto/pendente apos sessoes 2026-05-30..06-02

- **T-SHAPER-CODE-HARDENING** (P2) — hardening shaper p/ >100k linhas
  (A1 filter-before-load destrava escala; A3/A4/A6). Nao bloqueia <=100k.
- **T-DATA-3-EDGE-QUALITY-FIXTURES** (deferred) — plano de dados de borda;
  bloqueado por T-RECOVER-SCHEMA-MULTI-TABLE (gadget de qualidade nao existe).
- **Roadmap v2.0** (ADR-0018) — format changes p/ naturezas raras reais
  (low-card padding, fallback identity); requer mudanca de formato.
- **Datasets gaps** (project-dataset-coverage-map) — free-text longo real,
  IP/UUID, monetary-string, >1M linhas, geo lat/lon.
- **CNPJ gate forte** — nature CNPJ e' confirmada-empirica com 1 fonte real;
  N>=5 fontes diferentes p/ confianca Alta (so' se quiser fortalecer claim).
- **Spin-off llm-benchmark/** — extrair p/ repo separado via git filter-repo
  quando a fronteira estabilizar (futuro, so' se owner quiser).
- **Fases parciais T-CODE** — ENCODER-MANAGER (1c/2-4), SCHEMA-BUILDER
  (Fase 3 naturezas), LAYERED-PIPELINE (Fase 2 online adaptive),
  OUTPUT-SINKS/PLAN-CONTRACT (bloqueados).

---

## Discipline de manutencao

Este arquivo deve ser **atualizado**:
- Ao fechar sub-experimento (status table)
- Ao tomar decisao estrutural (estrutura de pastas, ticket aberto/fechado)
- Ao mudar foco de natureza (T01 -> T02 etc.)

Se editar, lembrar: **status absoluto, nao incremental**. Substituir
o que mudou, manter o resto coerente.

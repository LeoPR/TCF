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
> | **`T-DATA-TIPADA-NATIVA`** | destrava `date`/`datetime` na API | HOJE e' FAIL-LOUD: `encode([datetime.date(...)])` -> `HierarchicalError: valor escalar de tipo nao suportado: date`. Entao o ramo "data entra tipada" NAO EXISTE — o lazy e' o unico caminho, nao uma escolha entre dois. Quando existir tera' uma decisao que o lazy nao tem: QUAL GRAFIA emitir na volta (um `date` nativo nao traz formato). Irmao do schema previo |
> | ~~`T-DATA-LAZY-ISO`~~ | **SOLDADO 2026-08-08** | `SPEC_DATA_ISO` no registry (`#TCF.8 :data-iso`). Detecta por `date.fromisoformat` + guard de re-emissao; alvo = ordinal DECIMAL (o `*N+M|` do seq-RLE). Medido n=600: `mensal` **6338->33 B (-99,5%)**, `diario` 414->32 (-92,3%), `espalhado` -17,1%; e **RECUSA** em `agrupado`/`k12`, onde o OBAT ja' resolve e o spec pioraria. De quebra: (a) o FLOOR da nature passou a comparar contra o baseline REAL (incluia so' o core, nao o bN — CPF k=2 saia 198 B com nature vs 61 sem); (b) `None` nas QUATRO natures estourava `TypeError` cru. Suite 1199 |
> | **`T-NATURE-STRICT`** | **−61% do encode**; risco de bytes assumido por quem pede | flag que AFIRMA a grafia: falha alto se o valor nao casar, E dispensa montar o baseline do FLOOR (medido: o baseline custa 58% do encode; 66.635 -> 25.821 us, mesmos bytes). Risco medido: ate **4,2x pior** onde o FLOOR recusaria (`k12-ciclado`). E' a origem HARD DECLARADA sem precisar do tipo nativo. EM ABERTO: sao dois eixos num flag so' (falhar x nao-comparar) — decidir se e' 1 parametro ou 2. Nota `2026-08-08-onus-do-fluxo-total` |
> | **`T-SPEC-PARSE-X-ALVO`** | "8 specs" vira "1 spec, 8 parsers" | separar o PARSE do ALVO no spec: N grafias -> data canonica -> N alvos, com o `min()` escolhendo o alvo por regime (medido: nenhum alvo ganha sempre — delta-dias 5/8, ordinal-denso 2/8, iso 1/8). Dissolve o atrito "CPF tem 1 grafia, data tem muitas". **CRITERIO ATINGIDO 2026-08-09** (lab `1853`): ja' sao DUAS grafias (`YYYY-MM-DD`, `YYYY-MM`) e TRES alvos medidos (ordinal-dia, mes-geral A4, mes-fim A2f) com payloads compartilhados — 2x3 fatoravel. Decidir junto com o `T-DATA-ALVO-MENSAL` |
> | **`T-DATA-ALVO-DELTA`** | delta-coluna: **2-11x** onde o ciclo nao e' exato; robusto a ruido | **MEDIDO 2026-08-09** (lab `0042-data-alvo-delta`, RT 12/12): transform de coluna `[1o ordinal, depois deltas; invalido → _literal]` compoe com o core inteiro — alfabeto pequeno cai no bN (`mensal` 1085→349, `quinzenal` 3951→349, `espalhado-ordenado` 4059→644), feriado vira SIMBOLO e nao quebra (345-353 B sob todo ruido testado). COMPLEMENTAR ao periodico (cada um ganha onde o outro nao alcanca; juntos sob FLOOR cobrem tudo). PRESSUPOE `T-NATURE-CANDIDATO-BN`. Aguarda decisao de design do owner (protocolo da nature: transform de coluna). O irmao `T-SEQRLE-PERIODICO` foi SOLDADO (ADR-0040) e cobre o ciclo EXATO; e o `T-DATA-ALVO-MENSAL` (lab `1853`) tirou o caso mensal deste ticket (31-33 B per-valor vs 349 do delta-coluna). SOBRAM pro delta-coluna: espalhado-ordenado (644) e ciclo-quebrado (345 vs 677) — urgencia caiu de novo |
> | ~~`T-SEQRLE-PERIODICO`~~ | **SOLDADO 2026-08-09** (ADR-0040, suite 1238) | `*N~d1,...,dp\|template` — o delta CICLA entre linhas. Ideia do owner, anterior a esta rodada. **O ciclo paga UMA vez**: 600 dias uteis = `*600~1,3,1,1,1\|\739617` (1590 → **40 B** com o spec de data), n=6000 → **41 B** (**O(1) em n** — cresce so' o contador), ids nao-data 1959 → **32 B** (nivel CORE, sem nature nenhuma). Terceiro candidato do MESMO `min()`; **D1-D9 = 1545 e real-world = 89430 byte-IDENTICOS**; 39 testes novos. **DUAS cacadas adversariais, SETE defeitos** — e DOIS foram criados pelos proprios consertos: (1) teto de memoria nao cobria o marcador novo; (2) detector O(n²) = 13,8 s em n=2400; (3) FLOOR invertia o desempate e reescrevia wire SEM periodicidade; (4) telemetria `seq_rle_runs` zerava CALADA em wire byte-identico ao do core (regressao de canal publico, nenhum teste pegava); (5) pad com cauda morta = nao-injetivo; (6) **o gate do (5) virou amplificador** — 48,8 KB → 126,87 s (16.881x) e 22 B → 85 MB, porque validava proporcional ao que o WIRE declara ANTES de validar; (7) `compact_body` por fragmento SEM piso ressuscitava marcador que o core recusou, e a POLARIDADE cobrava (corpo −9 B embarcando wire +19 B, 963 regressoes em 28.985 casos). Sintaxe `~` reversivel pre-1.0. Gerou `T-FLOOR-POS-POLARIDADE` |
> | **`T-NATURE-CANDIDATO-BN`** | **mediana 6,7% em dado REAL** (ate' 7,5%; 12.582 B em 12 colunas) — e vale p/ QUALQUER nature | **MEDIDO EM DADO REAL 2026-08-09** (EXP-017 clean, corpus de Z:): o candidato interno da nature sai de `_encode_column` — **so' o corpo do core**, SEM polaridade (ADR-0035) e SEM bN (ADR-0036) — enquanto a rota flat normal aplica os dois. TPC-H `o_orderdate` 13521 -> 12612 B; `br data_cadastro` 21366 -> 20101; football 16241 -> 15021. **Nao e' de data**: CPF real 19467 -> 18095 (1372 B, 7,0%). O sintetico anterior media 19/70/298 B e subestimava em uma ordem de grandeza. RECALIBRADO pela cacada (4 lentes): mediana **~5,7%** no corpus amplo (nao 6,7% — aquele era subconjunto), max **11,9%** (`socio_cpf`); total corrigido 10.453 B em 10 colunas DISTINTAS (2 eram duplicatas de input); a lacuna **varia com n** (mesma coluna: 6,4% em n=200 -> 0,24% em n=15000); em dado real e' quase toda POLARIDADE (22/26), o bN so' aparece em low-card sintetico. Os 'negativos' eram ARTEFATO de metrica (lacuna so' e' interpretavel quando a nature VENCE o FLOOR). E o conserto SIMPLIFICOU: **a rota plena e' nunca-pior por construcao** (o FLOOR da polaridade devolve sufixo vazio quando nao paga; stress 8000 colunas, 0 violacoes) — trocar o corpo do candidato pela rota plena, mantendo o FLOOR nature-vs-baseline que ja' existe. Aguarda aprovacao (mexe em src/tcf) |
> | **`T-DATA-ALVO-MENSAL`** | mensal **679→31 B** (21,9x); faltas **2799→41** (68x); fecho **655→31**; YYYY-MM **826→31** | direcao do owner 2026-08-09 ("olhar pelo mes, o incremento fica melhor"), MEDIDA no lab `1853-data-alvo-mensal`: alvos per-valor com valvula (MESMO protocolo do SPEC_DATA_ISO, zero mudanca de core) transformam constancia-de-dia em uniformidade-de-delta que o M10+ADR-0040 ja comem. Estrutura que os numeros revelam: **A4 `mes*31+dia`** e' o alvo geral SEM convencao (cobre dia-01/15/misto por 33-36 B, perde so' 2 B do otimo); **A2f fim-de-mes** e' a unica convencao que paga (31 vs 745 do A4 no fecho contabil); **A3 YYYYMM morre** (legibilidade custa a aritmetica — virada +89 quebra runs); **YM** = spec irmao p/ grafia `YYYY-MM` (uma grafia de re-emissao por tag, senao RT quebra). Controle diario: floor protege (A1 segue vencendo). **DECISAO do owner 2026-08-09: data E' SPEC mesmo** ("e nao caracteristica so' de multicolumn nem nada") — per-valor, valendo no single-col; NAO vira feature de rota. Resta escolher a forma (specs irmaos A4+A2f+YM vs fatorar parse-x-alvo). **EXP-017 CLEAN 2026-08-09 — NAO FECHA EM DADO REAL**: ganho mediano **0,0%** em 14 colunas reais contra **95%** nos sinteticos mensais. O motivo NAO e' o mecanismo, e' o CORPUS: nenhuma coluna real disponivel tem cadencia mensal (TPC-H, br-identidades, football, retail, receita = todas diarias/transacionais). O regime-alvo **nao esta representado** no que temos. Sinteticos seguem verdes (33-48 B contra 655-2799), nunca-pior 26/26, PINs fixados. CONSEQUENCIA: o weld dos alvos mensais fica **CONDICIONADO a corpus real com cadencia mensal** (competencia/vencimento/faturamento) — sem ele, nao ha' gate a bater. A bateria multi-vetor do lab `2228` vale para o REGIME, nao para o corpus atual. **CACADA ADVERSARIAL (4 lentes)**: o 95% sintetico e' O(n) e fragil (n=12 PERDE; jitter +-2 dias -> 1,1x; 15 variantes realistas -> mediana 13,6%); o regime mensal E' alcancavel como AGREGADO derivado do corpus (1,8-9,8x); e folha de pagamento fica NEGATIVA nos 3 alvos mas um 4o eixo **dia-UTIL** recupera 99% — o argumento medido do **spec-orienta-nao-manda** (triagem em docs/theory/spec-orienta-nao-manda-triagem.md): eixos como DICAS opt-in do `.9`, nao alvos mandatorios |
> | **`T-PENHASCO-INICIO`** | **6x-95x decidido pela POSICAO da 1a excecao** da coluna | achado da cacada adversarial do EXP-017 (2 lentes independentes): (a) UMA sujeira numa coluna de 600 meses custa 4073 B se cair no indice <20 e 43 B se cair no >=20 — fronteira bate com `analyze_column(sample_size=20)` + Regra 2 do `auto_cadence` ('todas as primeiras 20 strings sao numericas'); atinge o ordinal SOLDADO igual (4308 vs 666 B) — fragilidade de NUCLEO, nao de alvo; (b) mesma classe: o candidato ordinal cai num penhasco de n (0,3% em n=3000 -> **18,7% em n=4000**, fronteira n=3850-3900). Decisoes de pre-passe criam penhascos que o FLOOR nao ve. `.9`; caso pinado no EXP-017 (`valv-sujeira-no-inicio`) |
> | **`T-CORPUS-DATA-MENSAL`** | destrava o gate do `T-DATA-ALVO-MENSAL` | achado do EXP-017 (2026-08-09): o corpus de `Z:/tcf-data/` tem **10 colunas de data reais** (TPC-H x5, br-identidades x2, receita, retail, football) e **NENHUMA com cadencia mensal** — todas diarias/transacionais. Sem corpus do regime, o alvo mensal nao tem gate a bater (mede 0,0% real contra 95% sintetico). Regimes procurados: **competencia** (folha, faturamento mensal), **vencimento** (parcelas, assinaturas, contratos), **fecho contabil** (dia = ultimo do mes). Anexo ao `project_dataset_coverage_map`. NAO baixar sem decisao do owner |
> | **`T-OBAT-NOS-PROXIMIDADE`** | a RAIZ do H-SIM-DUPLA-01; **alvo 2.0, vontade de fazer LOGO** | diagnostico do owner 2026-08-09 (confirmando o lab `1943`): *"nao desenvolvi porque a parte da proximidade dentro do OBAT nao foi feita — os nos so' fazem comparacao de IGUALDADE; se tiver similaridade [proxima como delta] ele nao cria nos para o HCC desenvolver depois"*. Ou seja: proximidade-como-NO' (o no' delta que o detector de composicao poderia desenvolver) e' lacuna de nascenca do OBAT, nao do fluxo. Owner: **"deixe registrado a vontade de fazer logo, apesar disso parecer mesmo melhor pro 2.0"**. Ate' la', os paliativos sao os encaixes E1/E2 (tickets abaixo) e os SPECS (que escolhem dominio onde a aritmetica sobrevive). Irma da H-TH-02 (Patricia) e da familia comparacoes-nao-literais (2026-05-11). **REFORCO 2026-08-09 (EXP-017)**: a lacuna de rota da nature (`T-NATURE-CANDIDATO-BN`, 6,7% em dado real) mostra que hoje ate' os PALIATIVOS estao pela metade — o candidato semantico nem passa pela rota que os mecanismos cegos usam. Ordem sensata: fechar a rota (barato, ja' medido) ANTES de atacar a raiz no 2.0 |
> | **`T-CANDIDATO-SEM-DEDUP`** | teto ~20x nas colunas que CICLAM (mes 423->~35 B; dia 523->~35) | achado estrutural 2026-08-09 (lab `1943-fluxo-igualdade-x-proximidade`, direcao do owner): o nucleo tem DUAS nocoes de similaridade — IGUALDADE (dedup `^N`/bN/dict) e PROXIMIDADE (seq-RLE uniforme/periodico) — e elas **nao competem no mesmo `min()`**. A igualdade roda DENTRO do OBAT/HCC, antes; a proximidade le' o que sobrou. Medido: a leitura aritmetica morre na linha **k** (1a repeticao aciona o dedup) — coluna `01..12` ciclica tem 1a referencia `^N` na linha 12, **11 deltas legiveis** e 0 runs periodicos (423 B), enquanto a MESMA aritmetica sem repeticao (k=600) faz 20 B. O candidato aritmetico nunca e' CONSTRUIDO, entao o FLOOR nao pode escolhe-lo. **BATERIA MULTI-VETOR 2026-08-09** (lab `2228`): bytes 10x nos ciclicos (423->42, 321->30, 4024->43); candidato custa **+84-93% do encode**; mem ~igual; online igual (mesma gramatica — SONDA PROVOU que o corpo sem-dedup ja' DECODIFICA hoje, e' encoder-only). VEREDITO pela regra do owner: **VARIANTE** (perfil `compacto`/flag), promocao a default condicionada ao `T-GATES-ANTES` baratear o caminho; gate natural = so' coluna toda-digito. Corolario registrado: parte do ganho dos SPECS e' o nucleo compensando escolha propria (o alvo devolve k grande, onde a aritmetica sobrevive) |
> | **`T-SPLIT-SINGLE-COL`** | mensal 1085->**700 B** (-35%); uteis 2454->**903 B** (-63%) | o split estrutural (ADR-0026, marcador `%`) **ja' corta `ano\|mes\|dia`** e ja' esta' soldado — mas e' candidato so' do multi-col (`min(tcf, raw, dict, split)`); a rota **single-col flat NAO o consulta**. Medido (lab `1943`): no multi-col o split VENCE nas colunas mensal e uteis (`#TCF.8M%dt`), e no diario perde (e faz bem — 820 vs 414). **Terceira ocorrencia da classe "o candidato existe e a rota nao o consulta"** (antes: `T-BN-TIPADO` e o FLOOR da nature que nao via o bN). **BATERIA MULTI-VETOR 2026-08-09** (lab `2228`): alem do custo de CPU (+47-54% SEMPRE, mesmo quando perde), o corpo do split e' um **multi-col EMBUTIDO** (blocos por coluna-campo) — **NAO streama por linha**. Classe do modo C (ADR-0036): decodavel, nao-emitido-por-default, opt-in. VEREDITO: **VARIANTE/perfil** (`compacto`/`lote`), nao default |
> | **`H-TH-02` / `H-PERF-04` (Patricia)** | o indice NAO indexa em coluna de data | evidencia NOVA 2026-08-09 (lab `1943` S1): o indice do OBAT e' hash de **trigrama** (ADR-0009), nao Patricia. Em `diario ISO` e `uteis ISO` da' **1 bucket com 100% dos unicos** (todo `2026-...` cai em `202`) — o indice vira lista e o "achar o melhor pedaco" vira O(n) por string. A `H-PERF-04` foi adiada dizendo exatamente "precisaria Patricia trie (out of scope agora)"; a medicao de hoje e' evidencia a favor de reabrir. Unico dos tres encaixes que muda COMO os pedacos sao achados, nao QUAIS candidatos competem |
> | **`T-MAX-PERIODO-31`** | dia-do-mes fica na mesa: k28 so' 2,3x (523->227) onde o ciclo completo daria ~70 B | o teto `MAX_PERIODO=24` do detector periodico (ADR-0040) exclui os periodos NATURAIS de calendario 28/29/30/31 (medido no lab `2228`). Subir pra 31 custa +7 iteracoes no laco O(n*P). Weld de 1 linha; **aguarda aprovacao** |
> | **`T-NOME-SPEC-CURTO`** | `:data-iso` = **28% do artefato** (9 B de 32) | MEDIDO 2026-08-10: nao ha' formalizacao nenhuma do nome de spec (`name: str`, sem limite/validacao/grafia; o ADR-0027 fixou ONDE a tag mora, nunca COMO se escreve). 3 dos 4 specs ja' cabem em 8 chars (`ip`/`cpf`/`cnpj`); **so' `data-iso` destoa**, e e' o unico com hifen (1 B que nao informa). Custo por payload: n=12 -> 19,1%; n=600 -> **28,1%**; `dtiso` deixaria o wire **9,4% menor**. Bate direto na diretriz de payload minusculo (O-FMT-15/16). **PESQUISA PROFUNDA 2026-08-12** (nota `2026-08-12-tres-frentes-onde-atacar`): o id viaja em TRES gramaticas de wire com parses DIVERGENTES (single=primeiro `:`, multi=ultimo, .8H=ate' `,]}` — nome `a:b` quebra em multi e passa em .8H); ZERO validacao (nome com `,` explode como 'referencia a fragmento inexistente' — erro ENGANOSO); e o achado forte: **o comprimento do id FLIPA o FLOOR** — em N=11-15 diarias a nature PERDE com `data-iso` (47 B) e VENCE com `dt`/`d` (43-44): o nome longo SUPRIME a propria nature no payload minusculo. `dtiso` captura 2 flips; `dt`/`d` capturam 5. PROPOSTA FECHADA: ADR com regra `^[a-z][a-z0-9]{0,7}$` + validacao FAIL-LOUD em 2 pontos (registro + emissao); **minusculas-only e' decisao carregada** — reserva MAIUSCULA/pontuacao pros sufixos de rota que o T-NATURE-CANDIDATO-BN pode trazer pra MESMA linha (desarma o conflito lexicalmente); tabela de reserva de ids (1 char = 26 slots; terceiros = prefixo `x`). MIGRACAO LIBERADA: baselines NAO re-pinam (zero nature nos suites), wire velho falha loud, e a valvula runtime ja' existe (`decode(w, nature=dataclasses.replace(SPEC, name='data-iso'))`, decoder.py:71). De carona: registry gadget nao semeia data-iso (gap); view.py:156 usa decode_value cru (None-slot). DECISOES DO OWNER: (1) tamanho `dtiso`(5) x `dt`(2) — 3 B/artefato e 3 flips a mais pro `dt`; (2) rename simples x HIBRIDO id-no-wire+nome-na-API (unico que fecha byte E DX; custo: wire opaco). Aguarda aprovacao |
> | **`T-LAZY-BYPASS-ARITMETICO`** | filtro de data em **O(1) no tamanho do run**, hoje O(n) | MEDIDO 2026-08-10: o `tcf.view` ja' filtra data (`where(ano==2025)` -> 365 linhas, `where(mes==03)` -> 93, com `select` cruzando coluna), mas **materializa 100%** — decodifica tudo e filtra depois. As NOTAS do `view.py` (L3, 2026-06-16) concluiram que agregar runs no modo-tcf NAO era separavel porque OBAT+HCC entrelacam, e que havia **0 colunas "clean-numeric"** no corpus. **O SPEC CRIOU essa condicao**: coluna de data com spec vira corpo de **UMA linha** (`*900+1\|;9617`; uteis: `*900~1,3,1,1,1\|`). Payload ordinal e' MONOTONICO -> filtro de data = intervalo aritmetico -> `count`/`where`/`min`/`max` em duas divisoes, sem expandir. GENERALIZA p/ qualquer spec de alvo inteiro monotonico (contrapartida de leitura do "spec orienta"). **PESQUISA 2026-08-12**: (1) **BUG real e silencioso no view soldado, emissivel HOJE**: coluna nature que vence em modo dict (`#TCF.8M@1a9=dt:data-iso,@v`) responde where/group_count pelo PAYLOAD ordinal — `where('dt','2025-06-20')` = 0 onde a verdade e' 133, SEM erro (pior classe); **FIX SOLDADO 2026-08-12** (aprovacao do owner): a causa-raiz era DOIS CAMINHOS de reversao, um so' revertia — agora ha' fonte unica `LazyTCF._reverte_nature`, usada por `_col` E por `_dict_parts` (reverte nos K unicos, laziness intacta). De carona, o `_col` passou a usar o WRAPPER DE MODULO em vez do metodo cru do spec (trata o slot nulo, como o decoder ja' fazia). Teste de regressao `test_lazy_tcf8_nature_em_modo_dict_reverte_no_where_e_group` — verificado que FALHA com o fix removido. Suite 1238 -> **1239**. (2) **single-col no view e' DISPATCH-ONLY** (~20-25 linhas): LazyTCF montado a mao sobre `#TCF.8 :data-iso` roda RT/where/sum perfeito **inclusive wire PULSADO 2x300** (paridade por construcao via _decode_column) — o caso de stream do owner, e onde as frentes view+pulso se ENCONTRAM sem tocar formato. (3) bypass aritmetico MEDIDO: `ano=2025` num run de spec = **12us vs 12.285us (1000x), 0 B materializados**, indices identicos, compoe com sum via Filtered(parent,idx). (4) o view acompanhou o ADR-0040 (`*N~`) sem mexer em nada — paridade por construcao, registrar como propriedade. Caminho: fix bug [.8] -> dispatch single-col [.8] -> `entre=(lo,hi)` em 3 camadas + bypass [.9] |
> | **`T-PULSO-SINGLE-COL`** | 1o pulso entrega 50% em **+15 B**; a curva e' `32 + 15*(p-1)` | MEDIDO 2026-08-10: **o wire JA' ACEITA pulsos** — `*300+1\|X` + `*300+1\|Y` decodifica identico a `*600+1\|`; RT verificado em 1/2/4/6/12/60 pulsos. Falta so' o encoder ter o ponto de decisao "parar e emitir". **O bloqueio do V2-J (ADR-0018) e' de OUTRA rota**: `# size=name,...` e' multi-col; o single-col flat com spec nao tem sizes no header, entao o caso do owner (stream de datas, coluna unica) **nao esta' bloqueado pelo formato** — o registro atual nao fazia essa distincao. RESTRICOES NOVAS do periodico: (a) o pad do 2o pulso **rotaciona por `corte mod p`** (corte multiplo do periodo mantem; fora de fase exige rotacionar, e a rotacao tem de seguir canonica sob o guard do ADR-0040); (b) **pulso periodico tem minimo de `2p+1` valores** (o guard exige 2 ciclos) — com p=5 um pulso de 7 e' ILEGAL. Um modo de baixa latencia **nao pode cortar em qualquer lugar**. **PESQUISA 2026-08-12 — as decisoes de ESTRUTURA**: matriz de 48 colunas reais: pulsaveis HOJE = spec/flat/tipado-core (`#TCF.8n` e' fato novo); NAO-pulsaveis = tudo com n/w/size no header (denso/bN/bB/.8H/.8M — count-no-fim = format change 2.0). Custo do modo-pulso na flat: **+4,73%** no corpus real, 2/3 = forfeit de bN (ate +262% em categorica) -> o perfil roteia POR COLUNA. **O CONFLITO com o T-NATURE-CANDIDATO-BN se resolve pela via (b) com custo ZERO no regime de pulso** (medido: em serie monotonica o FLOOR da polaridade recusa o sufixo sozinho; bN nunca vence o corpo transformado) -> CONSTRAINT no weld: polaridade/bN na rota spec CONDICIONADOS a perfil batch, nunca min() incondicional. Trailer-no-fim REPROVADO (mataria streaming de decode — a algebra 17x do modo C). **Leniencia nao-contratada descoberta**: commit precoce de sufixo corrompe SILENCIOSO (`ab!cd`->`abcd`), mas o parser aceita escape `\!` nao-emitido — fechar OU contratar (decide se a via sufixo-precoce existe; tem prazo). CANONICIDADE: pulsado = **'emissivel nao-canonico'** (espelho do modo C), SEM flag de header — re-encode canonicaliza (verificado byte-igual); gate: baseline nunca pinna saida pulsada. Fase do periodico: 100% estado de encoder, ZERO formato. Multi-col por coluna: +6,4%/+28,8% -> 2.0 (fica como TETO) |
> | **`T-FLOOR-POS-POLARIDADE`** | o FLOOR mede a grandeza errada | achado da 2a cacada adversarial (2026-08-09, lab `0042`): o `min()` do HCC decide pelo **corpo canonico** (`hcc_seqrle.py:329`), mas o que embarca no wire e' `polariza(corpo)` (`encoder.py:456`) — e o ganho da polaridade e' proporcional ao numero de corridas `\digito`, que a compactacao DESTROI. Medido: um corpo **9 B menor** embarcando wire **19 B maior**. Vale pro core de HOJE, nao so' pro periodico (que so' tornou visivel). Conserto por construcao seria comparar `len(polariza(c))` no `min()` — mas isso faz o HCC conhecer a camada de borda (violacao de camada), entao a alternativa e' FLOOR na granularidade certa. Vizinho do `T-FLOOR-MULTIVETOR` |
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
| beijing-pm25 | real (UCI) | 43824 | sensor decimais, range narrow |
| wine-quality | real (UCI) | 6497 | features quimicas decimais |
| ibge-municipios | real (IBGE) | 5571 | BR, categoria hierarquica acentuada |
| br-identidades | **sintetico** | 600k | CPF+CNPJ validos, geografia IBGE; vies declarado |
| receita-cnpj | **real non-PII** | 200k | CNPJ Receita; nature CNPJ 40.9% real |

> Gaps de cobertura + roadmap em memoria `project-dataset-coverage-map`
> (free-text longo, IP/UUID, monetary-string, >1M linhas).

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

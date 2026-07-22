# Taxonomia de LOSS no TCF — revisao das vertentes (2026-06-14)

> **Status**: registro/revisao conceitual (decide-se DEPOIS como implementar).
> **Tipo**: [probatorio] revisao + [dispositivo] diretriz do owner.
> **Origem**: owner ampliou o escopo do V2-C: "loss de dados e amplo e e PRO TCF
> FAZER SIM". Quer ver TODAS as vertentes, inclusive em outros tipos de dado.
> Gerado por workflow (9 vertentes em paralelo + critico de completude) +
> PoC empirico. Decisao de weld continua PENDENTE (owner).

## 0. A diretriz e a ideia-chave do owner

Loss no TCF nao e' so' "arredondar e perder". A vertente que o owner destacou:
**loss por-linha, LOSSLESS NO AGREGADO**. Ex: 7 valores; arredonda alguns pra
baixo e deixa residuo em outros pra que a SOMATORIA total fique exata. E' o que
parcelamento de pagamento faz (dividir um valor que da' dizima em N parcelas).

Isso reposiciona loss: **o TCF nao perde o que o consumidor le'**. Se o consumidor
le' a soma (faturamento, relatorio), preserva-se a soma exata; as linhas viram
aproximacoes baratas de comprimir. A perda e' deliberada, declarada, inspecionavel
e determinista — coerente com a filosofia (textual + explicavel), so' que agora o
contrato pode ser "exato-no-agregado" em vez de "exato-por-linha".

### PoC (empirico, `2026-06-14-v2c-lossy-round-caracterizacao/poc_soma_preservada.py`)
Metodo do maior resto (Hamilton apportionment) preserva a soma EXATA e ainda
comprime — estritamente melhor que round ingenuo:
- Parcelar 100/3: ingenuo `[33.33,33.33,33.33]`=99.99 (drift); maior-resto
  `[33.34,33.33,33.33]`=**100.00 exato**.
- wine.density real: maior-resto preserva a soma (4975.542 a d=3) enquanto o
  ingenuo driftou **+1.99** a d=2; bytes caem **37% (d=3) / 65.5% (d=2)**, erro
  por-linha <= 1 step.

## 1. Eixo PRINCIPAL — por CONTRATO DE RECUPERACAO

O contrato e' o que o decoder PROMETE. Ortogonal ao tipo de dado.

| Contrato | O que recupera | Vertentes | Custo da "ancora" |
|---|---|---|---|
| **exato** (lossless) | tudo, byte-a-byte | estado atual (tcf/raw/dict/split) | 0 |
| **exato-no-agregado** | um agregado exato; linhas aproximadas | residuo-redistribuido (soma/media/grupo), extremos, contagem, ordem, histograma, **identidade cross-coluna** | O(1) a O(n_grupos): 1 soma/ancora por grupo |
| **dentro-de-tolerancia** | valor com erro <= eps declarado | round precisao-fixa, quantizacao/binning, truncamento temporal, geo-snap | poucos bytes no header (modo+precisao) |
| **lossy-puro / probabilistico** | so' a forma canonica, ou agregado com bound estatistico | near-dedup texto, merge-OUTRAS, stemming, sketches, amostragem, DP | varia |

### 1a. Exato-no-agregado (a familia da ideia do owner)
- **Soma** (residuo-redistribuido): maior-resto (Hamilton) ou error-diffusion
  (Floyd-Steinberg, 1-pass streaming). Guarda os valores arredondados (low-card
  -> split+V2-B) + 1 ancora (a soma exata). Redistribuir no ENCODE (decoder so'
  valida a ancora) — os restos originais nao sobrevivem ao arredondamento.
- **Media** = soma/contagem (contagem = n_rows, gratis). Custo zero alem da soma.
- **Contagem** = sempre exata (n_rows nunca se perde; com merge de linhas vira o
  `*N` do RLE).
- **Min/Max (extremos)** = guarda os K extremos EXATOS (pos+valor), miolo arredonda.
- **Ordem/ranking** = round monotono (bins que nao cruzam vizinhos) ou lista de
  swaps minima.
- **Histograma/quantis** = quantizar PARA as bordas do histograma -> contagem por
  bin exata por construcao.
- **Total por GRUPO (group-by)** = maior-resto por grupo; ancora = vetor soma por
  grupo (a chave ja' e' outra coluna -> custo so' do vetor de somas).

### 1b. Dentro-de-tolerancia
- **Round precisao-fixa** (V2-C ja' caracterizado): casas decimais OU algarismos
  significativos; truncar vs round-half-even (banker, sem vies). |erro| <= 0.5*10^-D.
  Nicho pequeno (~1.5% weighted, so' wine cientifico) — e' a PEDRA FUNDAMENTAL do
  vocabulario de header lossy, nao o ganho principal.
- **Quantizacao/binning**: codebook (uniforme ou k-means/Lloyd-Max) + indices ->
  reusa o stream de indices do V2-B. Vence o round simples a igual erro em
  distribuicoes concentradas/multimodais (gasta codigos onde tem massa).
- **Truncamento temporal**: segundo->minuto->hora->dia, ou snap a passo. O split
  ja' separa os campos; truncar zera campos de baixa-ordem -> constantes -> somem;
  e derruba a cardinalidade (timestamp quase-unico vira low-card -> dict/seq-RLE).
  Melhor relacao ganho/risco pra datetime.
- **Geo-snap** (geohash truncado, snap a grade 2D): irmao 2D do truncamento
  temporal — mesma familia "snap a grade".

### 1c. Lossy-puro / probabilistico
- **Texto**: normalizacao (case/acento/espaco), near-dedup fuzzy (colapsa
  variantes num canonico), stemming/abreviacao. Reduz cardinalidade -> alimenta o
  dict V2-B. Recuperavel-exato (guarda residuo) ou so'-canonico. Versao SEGURA =
  alert-only via SideOutputs (sinaliza near-dup, dev decide); a versao que ARRUMA
  precisa decisao explicita do owner.
- **Categorico/ID**: merge-OUTRAS (cauda rara -> 1 sentinel, preserva top-K e
  contagem), hash-bucketing (cardinalidade fixa, risco de falso-join), remap-de-ID
  (troca UUID/ID longo por indice denso; preserva joins se consistente cross-coluna
  — MAIOR teto em IDs opacos onde o TCF hoje infla).
- **Sketches** (Count-Min, Bloom, HyperLogLog), **amostragem** (reservoir,
  stratified), **differential privacy**: contrato "agregado com bound estatistico"
  ou nao-recuperavel. Mudam o PRODUTO (nao entregam linhas) -> gadget auxiliar,
  nao core.

## 2. Eixo SECUNDARIO — por TIPO DE DADO

| Tipo | Vertentes de loss aplicaveis |
|---|---|
| numerico decimal | round, quantizacao, residuo-soma, modelo+residuo, transformada |
| datetime | truncamento granularidade, snap a periodicidade |
| categorico / ID | merge-OUTRAS, hash-bucket, remap-ID |
| texto-livre | normalizacao, near-dedup fuzzy, stemming |
| semi-estruturado (JSON/lista) | canonicalizar chaves, dropar campos opcionais |
| geo (lat/long, trajetoria) | geohash truncado, snap a grade, Douglas-Peucker |
| bool/flag/enum | normalizar variantes a 1 codigo canonico |
| unidades ("1.5kg"/"1500g") | valor canonico + unidade-base |
| LINHAS inteiras | near-dedup de registros + multiplicidade; delta-aproximado inter-linha |

## 3. A vertente MAIS PROMISSORA (gap #1 do critico) — CROSS-COLUNA / relacional

Todas as 9 vertentes acima tratam cada coluna ISOLADA. A redundancia mais gorda
de tabelas reais e' ENTRE colunas — e nenhuma a captura:
- identidades aritmeticas: `total = base + imposto`, `subtotal = qtd * preco`,
  **`valor = soma(parcelas)`** (a propria ideia do owner E' uma identidade
  cross-coluna!).
- dependencias funcionais: `cep -> cidade -> uf`, `cpf -> nome`.

**DERIVED-DROP**: detecta `C = f(A,B)`; guarda so' a formula no header + residuos
por-linha (delta entre C real e f(A,B)). Tres regimes, degrade gracioso:
- **lossless** quando a identidade fecha exata (residuo=0) -> a coluna C **some
  inteira**, 0 bytes de body. PRESERVA o diferencial lossless do TCF.
- **exato-no-agregado** quando ha' residuo de arredondamento de centavo (ex
  `C=round(A*B,2)`) -> redistribui o residuo por maior-resto (reusa o motor da
  vertente da soma) + ancora.
- **dentro-de-tolerancia** quando f e' aproximada.

Por que e' a mais promissora: (a) ataca redundancia de PRIMEIRA ordem; (b) o ganho
e' dropar uma coluna inteira (~ordem de magnitude acima do nicho 1.5% de wine);
(c) conecta direto com o parcelamento do owner; (d) forca a 1a estrutura
cross-coluna do formato (que o remap-ID tambem pede — paga-se 1x, destrava 2); (e)
tem caminho lossless limpo. **Pre-requisito**: estrutura cross-coluna no formato
(hoje cada coluna e' independente).

## 4. Meta-camada TRANSVERSAL (pre-requisito de QUALQUER weld lossy)

- **Contratos de tolerancia + verificacao** (vertente 8): descritor por coluna
  (ABS/REL/DECIMALS/AGG/DIST), marcador inspecionavel no header (familia `!@%`),
  e camada de teste "valida-invariante" (o RT exato vira RT-de-contrato). SideOutputs
  mede o erro real de graca (erro_max_abs/rel, soma_orig vs soma_dec). **Comecar
  minimal: DECIMALS + AGG-soma.**
- **Composicao/ordem de multiplas perdas** (gap #6): ordem canonica fixa
  (snap/truncate -> round/sig-figs -> quantize -> dedup -> split -> dict);
  erro compoe por soma (eps_total <= eps1+eps2); ancora-de-agregado SO' sobrevive
  se recomputada APOS a ultima etapa. Sem isso, 2+ natures lossy = ponto cego.
- **Budget / rate-distortion** (gap #7): modo inverso "menor arquivo com erro <= E"
  ou "cabe em B bytes". Aloca precisao por coluna (mochila: gasta erro onde compra
  mais bytes). Liga com a diretriz [[project-byte-level-compression-focus]].

## 5. Prior art (so' o que sobrevive em ASCII inspecionavel)

- **Transferivel direto**: Largest Remainder/Hamilton (soma exata), Floyd-Steinberg
  error-diffusion (1-pass), banker's rounding (sem vies), k-means/Lloyd-Max VQ
  (codebook+indices = o dict V2-B), int8-com-K=256 (= V2-B 1-char), histogram binning.
- **So' a intuicao**: bfloat16/posit (range-vs-precisao -> sig-figs; nao-uniforme
  -> quantizacao log), Gorilla delta-of-delta (JA' existe no seq-RLE).
- **Binario, NAO importar o codec**: Gorilla-XOR, bfloat16/posit/decimal128 — quebram
  o pilar textual.
- **Gadget/futuro (muda o produto)**: Count-Min/Bloom/HyperLogLog (sketches),
  differential privacy (ruido nao-recuperavel, antitese do determinismo TCF).

## 6. Outras dimensoes ortogonais (gaps do critico, registradas)

- **Transformada / modelo+residuo** (gap #2): ajustar modelo barato (regressao/
  sazonalidade) ou DCT/wavelet/low-rank a uma SERIE, guardar coeficientes grandes +
  residuo quantizado. O lossy classico de verdade (JPEG/audio), que round nao toca.
  Nicho real em telemetria (beijing-pm25). Coeficientes saem em texto.
- **Probabilistico/amostral** (gap #3): top-K exato + cauda agregada; reservoir/
  stratified com IC; quant guiada por importancia (preserva outliers, esmaga miolo).
- **Semi-estruturado/geo/bool/blob** (gap #4): tipos esquecidos (o owner pediu
  "outros tipos de dado").
- **Inter-linha** (gap #5): near-dedup de LINHAS inteiras + multiplicidade (lossy do
  `*N` RLE); delta-aproximado entre linhas vizinhas.

## 7. Sequenciamento sugerido (quando o owner abrir lossy)

1. **Meta-camada de contrato** (vertente 8) + algebra de composicao (gap #6) —
   pre-requisito de seguranca; define marcador + camada de teste valida-invariante.
2. **DERIVED-DROP cross-coluna lossless** (gap #1, residuo=0) — prova de conceito da
   estrutura cross-coluna, MANTEM lossless, maior teto. Depois a variante lossy com
   ancora de soma (reusa motor do maior-resto).
3. **Residuo-redistribuido soma/grupo** (vertente 1) — a ideia-chave do owner;
   parcelamento como PoC trivial (total+N, zero residuo armazenado).
4. **Quantizacao** (vertente 4) no lugar do round simples (vertente 3) onde lossy-
   fixo fizer sentido — reusa o dict, domina o round a igual erro.
5. **Truncamento temporal** (vertente 6) — melhor ganho/risco datetime.
6. Demais (texto/categorico/transformada/tipos) sob demanda, **alert-only primeiro**
   onde o risco semantico e' alto.

**GATE (CLAUDE.md, anti-incidente 2026-05-21)**: qualquer weld lossy passa por
caracterizacao real-world N>=5 fontes + decisao explicita do owner (cruza a linha
lossless). O ganho de BYTES da maioria das vertentes por-coluna e' o nicho ~1.5%
(wine); o VALOR e' o CONTRATO novo (agregado-exato, cross-coluna) que o lossless
puro nao oferece — vender por isso, nao por bytes.

## Conexoes
- `2026-06-14-v2c-lossy-round-caracterizacao/` (V2-C round + PoC soma-preservada)
- ADR-0025 (V2-B dict, substrato), ADR-0026 (split, sinergia), ADR-0015 (natures opt-in)
- ADR-0018 (roadmap v2.0; V2-C era a entrada lossy original)
- [[project-byte-level-compression-focus]] (budget/rate-distortion)
- `roadmap-hipoteses.md` Pacote 10 (Loss) — registry das hipoteses derivadas daqui
- Workflow gerador: `_wf_loss_taxonomy.js` (9 facets + critico, reproducivel)

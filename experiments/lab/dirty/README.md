# dirty/ — workbench v0.6

**Reset em 2026-05-10.** Tudo que existia antes deste reset está em
[`old/`](old/) como blueprint de revisão. Nada em `old/` é referência
canônica para v0.6.

---

## Propósito

O dirty lab serve para **verificar comportamento**, não para "descobrir
algo incrível". Cada experimento responde a uma destas perguntas:

1. **Esta ferramenta pode ser implementada?** (viabilidade técnica)
2. **Este algoritmo tem o comportamento esperado?** (consistência)
3. **Este formato funciona?** (roundtrip, edge cases)
4. **Como este experimento se compara, ponto a ponto, com o anterior?**
   (diferenças, não juízo)

Análise de escala e complexidade algébrica indica **a possibilidade**
de vantagem em algum cenário. Não estabelece superioridade.

---

## Vocabulário — disciplina obrigatória

**Não usar** nas notas, READMEs, ou qualquer artefato deste lab:

- "incrível", "surpreendente", "muito melhor", "suipimpa"
- "onde brilha", "destaque", "vencedor", "campeão"
- "descoberta", "achado importante" (use: "comportamento observado")
- superlativos absolutos sem cenário ("melhor", "ótimo", "ideal")

**Usar**:

- "diferença", "variação", "delta"
- "comportamento sob X", "no cenário Y"
- "menor/maior em N bytes que A em cenário B"
- "comparável a / não comparável a"

Os dados deste lab são **sintéticos similares aos reais**, **variados em
formato e quantidade**, e **viesados por construção** (cenários
escolhidos para ver comportamento, não para vencer). Frases que afirmam
superioridade fora do cenário são inválidas por princípio.

---

## Nomenclatura

Padrão obrigatório para subpastas:

```
YYYY-MM-DD-NN-<nome-curto>/
```

| Componente | Descrição |
|------------|-----------|
| `YYYY-MM-DD` | Data de criação do experimento |
| `NN` | Ordinal sequencial do experimento neste dirty (01, 02, ...). É o "apontamento de versão" do experimento — sua identidade. Revisão do mesmo experimento ganha sufixo `-v2`, `-v3`, etc. |
| `<nome-curto>` | 1–3 palavras com a ideia central da ferramenta/algoritmo |

Exemplos:

- `2026-05-11-01-rle-baseline/`
- `2026-05-12-02-encoder-pipeline/`
- `2026-05-15-02-v2-encoder-pipeline/` (revisão do exp 02)

**Não incluir versão de formato** (v06, v05) no nome. O experimento é
uma ferramenta atemporal: pode ter nascido sob a motivação do v0.6, mas
serve para testar comportamento em qualquer cenário, inclusive coisas
de versões anteriores. O *princípio sob o qual nasceu* é registrado
dentro do README do experimento, não no nome da pasta.

---

## Estrutura mínima de cada experimento

Cada subpasta tem um `README.md` com estas seções:

```markdown
# NN — <nome-curto>

## Princípio / motivação
Sob qual princípio esta ferramenta nasceu. Pode ser uma ideia da v0.6,
uma dúvida sobre comportamento de uma técnica, uma questão herdada de
experimento anterior. **A ferramenta é atemporal**: nasce sob esta
motivação mas pode ser aplicada a outros contextos.

## Propósito
O que este experimento verifica. Em qual das 4 perguntas ele responde
(viabilidade / comportamento / formato / comparação).

## Comparação
- Compara com: <experimento anterior ou nenhum>
- É comparável? <sim/não — por quê>
- Se não é comparável: é experimento paralelo (ferramenta diferente,
  não pretende comparar nada)

## Cenários e valores possíveis
Datasets sintéticos usados, parâmetros, ranges testados. Por que estes
cenários (sem afirmar que cobrem o real).

## Resultado observado
Diferenças mensuradas em bytes/tempo/RT. Sem juízo "melhor/pior".
Apenas: "no cenário X, A ficou N bytes menor que B".

## Limitações
O que este experimento NÃO mostra.
```

---

## Comparações — regras

- **Pode comparar** dois experimentos se: mesmos dados, mesma métrica,
  mesma definição operacional. Caso contrário, declare incomparável.
- **Experimento paralelo** é legítimo: implementa uma ferramenta
  diferente sem intenção de comparar. Marque como "paralelo" no README.
- Diferença observada num cenário **não generaliza** para outros
  cenários. Se quiser generalizar, faça experimento de escala explícito.
- Análise algébrica/complexidade aponta **possibilidade**, não vantagem.

---

## Camadas de custo (convenção do dirty v0.6)

Quando comparamos serializações nestes experimentos, distinguimos
**quatro camadas** de custo, em ordem decrescente de importância:

1. **Dados efetivos** — strings e estruturas (pai+sufixo) que precisam
   estar lá para reconstruir o input. Aqui contamos em **bytes** para
   ter ideia numérica.
2. **Marcadores de referência** — `noN:`, `ref:noN`, `Mx`, etc. Notação
   sintática que liga referência ao referente. Conta em bytes mas
   pesamos qualitativamente também: cada marcador "vale" pelo conceito
   de ligação que carrega.
3. **Marcadores macro / estruturais** — `<body>`, `<patricia>`,
   delimitadores de seção. **Escala pequena**: podem existir ou ser
   implícitos por regra de formato. Lembrar que existem; **não medir
   bytes neles** ao comparar.
4. **Comentários** — `# coluna: ...`, intros explicativas. **Não
   contam.** Metadados humanos.

Comparações entre experimentos devem isolar o que muda em **uma**
camada de cada vez. Bytes brutos sem decomposição podem refletir
escolhas arbitrárias de comentário/marcador macro, não diferença
intrínseca da serialização.

---

## Index

| ID | Data | Tema | Tipo | Status |
|----|------|------|------|--------|
| 01 | 2026-05-10 | [amostras-iniciais](2026-05-10-01-amostras-iniciais/) | paralelo (fundação) | aberto |
| 02 | 2026-05-10 | [patricia-nomes](2026-05-10-02-patricia-nomes/) | viabilidade + comportamento | roundtrip OK |
| 03 | 2026-05-10 | [patricia-inline](2026-05-10-03-patricia-inline/) | comparação vs 02 (serialização) | roundtrip OK |
| 04 | 2026-05-10 | [formato-normalizado](2026-05-10-04-formato-normalizado/) | comparação justa + fórmula | 16/16 roundtrip OK |
| 05 | 2026-05-10 | [patricia-aninhado](2026-05-10-05-patricia-aninhado/) | viabilidade (decl aninhada recursiva) | 4/4 roundtrip OK |
| 06 | 2026-05-10 | [aninhado-emails-urls](2026-05-10-06-aninhado-emails-urls/) | viabilidade em dados realistas | 4/4 roundtrip OK |
| 07 | 2026-05-10 | [patricia-reverso](2026-05-10-07-patricia-reverso/) | viabilidade do espelho (reverse) | 8/8 roundtrip OK |
| 08 | 2026-05-10 | [patricia-bidir-composto](2026-05-10-08-patricia-bidir-composto/) | composição pref+mid+suf por string | 8/8 roundtrip OK |
| 09 | 2026-05-10 | [debug-bidir-d2](2026-05-10-09-debug-bidir-d2/) | instrumentação/debug do D2 do exp 08 | sem encoding (relatórios textuais) |
| 10 | 2026-05-10 | [decomposicao-com-avos](2026-05-10-10-decomposicao-com-avos/) | decomp escolhe nível na cadeia de ancestrais | 4/4 roundtrip OK; D2 0→12 compostas |
| 11 | 2026-05-10 | [padroes-no-encode](2026-05-10-11-padroes-no-encode/) | instrumentação de padrões (mid+suf) repetidos | só D2 tem ganho potencial (12.4%) |
| 12 | 2026-05-10 | [debug-hierarquia-decl](2026-05-10-12-debug-hierarquia-decl/) | analise de decl hierárquica para pref/suf | perda em 4/4 datasets atuais (gargalo sintático) |
| 13 | 2026-05-10 | [repair-bottomup](2026-05-10-13-repair-bottomup/) | Re-Pair (substring em qualquer posição) | 3/3 roundtrip OK; -31.8% em D2-completo, -16% em D4 vs exp 10 |
| 14 | 2026-05-10 | [online-sem-revisao](2026-05-10-14-online-sem-revisao/) | online incremental sem revisão (Opção A) | 3/3 roundtrip OK; vence Re-Pair em D4 (-25b), perde em D2 (+6, +16) |
| 15 | 2026-05-11 | [online-com-fix](2026-05-11-15-online-com-fix/) | fix do exp 14: busca sufixo/prefixo menor em overlap | 3/3 roundtrip OK; -33% a -37% em unidades vs Re-Pair |
| 16 | 2026-05-11 | [online-cleanup](2026-05-11-16-online-cleanup/) | refatoração estrutural do exp 15 (dominância de candidatos, RLE em função própria, remoção de ruído) | 3/3 roundtrip OK; TCFs byte-idênticos ao exp 15; -14% linhas de código |
| 17 | 2026-05-11 | [familias-variadas](2026-05-11-17-familias-variadas/) | comportamento do exp 16 em 6 famílias (URLs, UUIDs, ISO, IPs, CPFs, códigos) | 6/6 roundtrip OK; 2 regimes — Regime A (timestamps 88.8%, códigos 86.9%, URLs 80.6%, IPs 72.0%); Regime B adversarial (uuids 0.7%, cpfs 0.0%) |
| 18 | 2026-05-12 | [escala](2026-05-12-18-escala/) | tempo e cobertura do exp 16 em N=50, 200, 1000 nas 4 famílias do regime A | 12/12 roundtrip OK; cobertura sobe com N (até 96-99% em N=1000); tempo O(N²·L) confirmado; ~2 unidades/string em regime estável |
| 19 | 2026-05-12 | [par-AB-independente](2026-05-12-19-par-AB-independente/) | busca exaustiva sobre pares (prev_a, prev_b) — direção declarada como limitação no exp 15 | 21/21 roundtrip OK; **0 ganho em unidades** em 21/21 datasets; bytes verbosos pioram 4-6% em codigos; direção descartada cientificamente |
| 20 | 2026-05-12 | [marcadores-modulares](2026-05-12-20-marcadores-modulares/) | desacopla algoritmo (`online.py`) de sintaxe via interface `Syntax`; `VerboseSyntax` reproduz exp 16 | 21/21 roundtrip OK; TCFs byte-idênticos ao exp 16 em 21/21; trocar sintaxe agora é localizado em 1 arquivo |
| 21 | 2026-05-12 | [syntax-compact-v1](2026-05-12-21-syntax-compact-v1/) | primeira sintaxe alternativa: marcadores compactos explícitos (Direção 1 da nota `marcadores-compactos`) | 21/21 roundtrip OK em ambas sintaxes; total 156126 → 85508 bytes (**-45.2%**); razão verbose:compact ≈ 0.5 em regime A; algoritmo intocado |
| 22 | 2026-05-12 | [syntax-compact-v2](2026-05-12-22-syntax-compact-v2/) | segunda sintaxe alternativa: idx automático por fragmento (Direção 2 da nota — proposta do user) | 63/63 roundtrip OK; **vence v1 em 17/21 datasets** (até -41%); **perde em 4** (iso-N1000 +86%); trade-off: custo ∝ número de quebras por nó |
| 23 | 2026-05-12 | [syntax-variations](2026-05-12-23-syntax-variations/) | 5 sintaxes lado a lado em D2-mini + D2-completo (verbose, v1, v1b sem `@N:`, v2, v3 sem aspas) | 10/10 roundtrip OK; **v3 vence**: D2-mini 85B (-59% vs verbose, -27% vs v1), D2-completo 177B (-61%, -24%); v1b: ganho universal -16% vs v1; v3 limitado a literais sem dígitos |
| 24 | 2026-05-12 | [syntax-ambiguidade](2026-05-12-24-syntax-ambiguidade/) | resistência a chars ambíguos no literal — 4 sintaxes (v2, v3, v4-escape, v4-quote) em 4 datasets com gradiente | v2 e v3 falham em datasets reais; **v4-escape e v4-quote sempre funcionam mas trocam ganho**: escape vence K=1 (`'`, dispersos); quote vence K≥3 (vários dígitos contíguos); limiar empate K=2 |
| 25 | 2026-05-12 | [syntax-adapt](2026-05-12-25-syntax-adapt/) | v4-quote-fixed (correção do bug: `'` não dispara aspas) + v5-adapt-{escape,quote} (substituição global de marcadores secundários) | v4-q-fix valida intuição do user (**-20B em nomes-com-aspas**); v5-adapt **não compensa** nos 4 datasets — header de 4B não se paga com N≤2 ocorrências do char substituído por fragmento literal |
| 26 | 2026-05-12 | [syntax-mixed](2026-05-12-26-syntax-mixed/) | exp enxuto: 1 dataset realista (emails-quote-id), 3 sintaxes (v4-escape, v4-q-fix, v4-mixed) | 3/3 roundtrip OK; **v4-q-fix == v4-mixed empatam em 198B**; v4-escape 200B; escolha-por-literal não traz ganho — separador `*` compensa exatamente; **v4-q-fix é a sintaxe vencedora** consolidada |
| 27 | 2026-05-12 | [analise-ambiguidade](2026-05-12-27-analise-ambiguidade/) | **Etapa 1 do flow semântico**: analisador puro que classifica cada char dos literais em A (livre) / B (contexto resolve) / C (conflito real); sem emitir TCF | mapeou emails-quote-id: **80% A, 0% B, 20% C** (só dígitos); empate teórico escape vs aspas (+14B); identifica espaço para sumida/órfã (próximas etapas); raiz: tokens do exp 16 |
| 28 | 2026-05-12 | [sumida-e-slice](2026-05-12-28-sumida-e-slice/) | **Etapa 2 do flow semântico**: sumida (parser stateful para dígitos quando idx N não existe) implementada + análise de slice arbitrário (potencial medido sem implementar) | sumida ganha **só 1B em D2 e 2B em D3** (~0.5-0.9%); slice arbitrário tem potencial 2-5B; **algoritmo do exp 16 já faz o trabalho pesado**; refinamentos atingiram diminishing returns |
| M1 | 2026-05-12 | [M1-marcacao-ambiguidade](2026-05-12-M1-marcacao-ambiguidade/) | **macro experimento**: 4 micros (escape, quote, sumida, slice) × 4 datasets (D1-D4) com 4 fases (F1 viabilidade → F2 diferenças → F3 substituição → F4 fechamento) — reset mental a partir da raiz exp 16 | em curso — Setup OK; M1.A/B/C/D pendentes |

## Descrição dos experimentos

### 01 — amostras-iniciais (paralelo, fundação)

Catálogo de tipos de dado (datas, nomes, URLs, telefones, CPF/CNPJ,
produtos, monetários, enums, NULL, ...) com eixos de variação,
falhas de cadastro e regras de geração. Saídas: `ideias.md` (o
catálogo), `observacoes-reais.md` (o que vimos em Adult Census e
TPC-H), `amostras/pequenas/*.csv` (~25 linhas, ilustrativos),
`amostras/grandes/*.csv` (1000 linhas via `gerar.py`).

Não compara nada. Produz insumo para qualquer experimento posterior
que precise gerar dados controlados de um tipo específico.

### 02 — patricia-nomes (viabilidade + comportamento)

Refaz a árvore Patricia do zero (sem importar nada de `dirty/old/`).
Dois cenários sintéticos:

- **A**: 50 linhas de nomes simples (Ana, Bob, Carlos, Diana, Edu)
  com runs adjacentes e dispersão.
- **B**: 30 linhas com identificadores hierárquicos `USR0001..USR0010`
  + `PRD0001..PRD0005` misturados.

Comportamento observado: em A, Patricia não fatorou (nenhum prefixo
comum ≥ 3 chars); a árvore degradou para DICT simples. Em B, fatorou
recursivamente — criou `USR000`, depois `PRD000`, depois `USR00` como
pai de `USR000`+`USR0010`. RLE adjacente emergiu da serialização do
body em ambos os cenários (50→33 entradas em A, 30→20 em B).
Roundtrip OK.

Formato de saída tem duas seções: `<patricia>` (declarações de nós) +
`<body>` (referências `ref:noN` com RLE).

### 03 — patricia-inline (comparação vs 02 na camada de serialização)

Mesmo input, mesma árvore Patricia. Muda **só a serialização**:
declarações embutidas na 1ª ocorrência no body (sem seção `<patricia>`
separada). Refs a pais ainda não declarados ficam como **forward refs**;
o pai aparece em **decl tardia** ao final do body. Decode em 2 passadas
resolve. Roundtrip OK.

Análise por camada de custo (vs 02):

- **Marcadores macro**: o 03 elimina `<patricia></patricia>`. Ordem
  de grandeza pequena; lembramos que existe, sem contar bytes.
- **Marcadores de referência**: o 03 funde a declaração de cada nó
  com sua 1ª ocorrência. Onde o 02 paga `decl + 1ª ref` (dois
  marcadores), o 03 paga `decl-com-ocorrência` (um marcador). O 03
  paga adicionalmente **decls tardias** para nós internos Patricia
  (pais sem ocorrência própria). Em ordem de grandeza:
  - 02: `N_unique` decls + `N_total` refs (todas as ocorrências
    referenciadas).
  - 03: `N_unique` decls (que já são 1ªs ocorrências) +
    `N_total - N_unique` refs subsequentes + `N_patricia_interno`
    decls tardias.
  - Diferença esperada: o 03 economiza `N_unique - N_patricia_interno`
    marcadores. Em A isso é 5; em B é 12.
- **Dados efetivos**: idênticos entre 02 e 03 (mesma árvore, mesmas
  strings, mesma sequência de RLE).
- **Comentários**: ignorados.

A medição de bytes brutos do 03 atual (689 em A, 824 em B) ficou
contaminada por escolhas de formato (comentário extra, `1x` explícito
em refs de count=1) que pertencem à camada "comentários" ou são
divergências artificiais de marcador. Removendo essas inflações
artificiais, a estimativa fica em -9 bytes (-1.6%) em A e -127 bytes
(-15%) em B vs 02. Detalhe em
[03/README.md](2026-05-10-03-patricia-inline/README.md).

### 04 — formato-normalizado (comparação justa + fórmula)

Mesma árvore Patricia dos 02/03, mas com **formato normalizado**:
sem comentários, omitir `1x` em count=1. Aplica a régua única em
ambas serializações para isolar a camada 2 (marcadores de
referência).

Cenários expandidos: 4 datasets × 4 ordenações = **16 cenários**.

- **D1**: 5 únicos sem Patricia (~ exp02 cenário A)
- **D2**: 40 únicos sem Patricia
- **D3**: 5 únicos com 1 Patricia interno (~ versão simplificada do exp02 B)
- **D4**: 25 únicos com 4 Patricia internos (~ exp02 cenário B com mais nós)

Ordenações: original / sorted / random / agrupado.

`formula.py` traz previsão simbólica por camada (macro / ref / dados).
Validação: previsão = medição em **16/16 cenários**.

Resultados centrais:

- **Roundtrip 16/16 OK** em ambas serializações.
- **Camada 1 (dados)** idêntica em todos os 16 cenários.
- **Camada 2 (ref)**: inline economiza em todos os 16. Magnitude
  praticamente constante por dataset, **independente da ordenação**.
  Ex: D2 economiza -467 ou -468 bytes em todas as 4 ordenações.
- **Fórmula simplificada**: `delta ≈ -11·N_unique + 5·N_pat_int`
  (chars). Ordem de grandeza correta para todos os 4 datasets,
  imprecisões de ~10-35 bytes pelo `len(str(eid))` variável e counts
  > 1.

Implicação: a economia da serialização inline é função de
**propriedades estruturais da árvore** (`N_unique`, `N_pat_int`),
não da ordem do CSV. Ordenação afeta o tamanho absoluto do body em
ambas serializações na mesma proporção, sem mudar a diferença.

Tipo: comparação ponto a ponto vs 02 e 03 sob régua única.

### 05 — patricia-aninhado (viabilidade)

Continua a serialização inline do 03/04, levando o conceito mais
fundo: **a decl de um pai Patricia também é embutida** — dentro da
própria decl do filho que primeiro o referencia. Avôs ainda não
declarados são embutidos recursivamente.

Eliminação completa das "decls tardias" do exp 03/04. Decode passa
a ser em 1 passada (forward refs deixam de ser necessárias).

Sintaxe (didática, marcadores verbosos):

```
no1: filho_de(no2=decl folha "Mar") + "ina"          # Marina; embute pai Mar
no3: filho_de(no2) + "cio"                            # Marcio; Mar já declarado
no4: filho_de(no5=decl filho_de(no2) + "c") + "io"   # cadeia profunda
```

4 cenários didáticos, 30 linhas cada (D1 sem Patricia, D2 com
prefixo profundo, D3 hierárquico raso, D4 duas famílias). Roundtrip
4/4 OK.

Numeração de eids ainda é sequencial por ordem de aparição
(incluindo dentro de decls aninhadas). Próximo experimento pode
otimizar esta numeração para indices mais curtos ou implícitos.

Tipo: viabilidade — confirma que aninhamento recursivo funciona
end-to-end (encode + decode em 1 passada + roundtrip).

### 06 — aninhado-emails-urls (viabilidade em dados realistas)

Mesmo algoritmo do 05 (encoder/decoder/Patricia byte-idênticos)
aplicado a 4 datasets de emails e URLs com hierarquia natural:

- **D1**: 10 emails `user001..user010@gmail.com` — Patricia detecta
  `user0` e `user00` em cadeia.
- **D2**: 4 nomes × 3 domínios — cada nome vira prefixo paralelo
  (`maria.silva@`, `joao.souza@`, etc).
- **D3**: 10 URLs com path comum
  (`https://api.example.com/v1/users/N`) — 1 prefixo de 33 chars
  cobre todas.
- **D4**: URLs multi-recurso (users/orders/products sob mesma base
  URL) — hierarquia de 3 níveis Patricia (base + recurso + ID).

Roundtrip 4/4 OK. Observações:

- **Cadeia aninhada de 3 níveis** acionou em D1 e D4. Profundidade
  do aninhamento na 1ª linha do body é igual à profundidade da
  árvore Patricia.
- **Reaproveitamento do avô** em D4: a URL base
  `https://api.example.com/v1/` é declarada **uma única vez** (na
  1ª linha) e serve de raiz para 3 nós intermediários (users/,
  orders/, products/) declarados nas 1ªs ocorrências dos seus ramos.
- **Patricia só fatora prefixos**, não sufixos. Sufixos comuns como
  `@gmail.com` (D1) ou `.com` (D2) permanecem duplicados em cada
  folha — sufixo-DICT é outra ferramenta, fora do escopo atual.

Tipo: viabilidade em dados realistas — confirma que o algoritmo do
05 funciona sem modificação em hierarquias naturais profundas.

---

## Síntese consolidada

Documento de síntese dos algoritmos do ciclo v0.6 (até exp 15) em
[`docs/workbench/research-notes/2026-05-11-sintese-algoritmos-v06.md`](../../../docs/workbench/research-notes/2026-05-11-sintese-algoritmos-v06.md).
Inclui trade-off triangular, evolução Patricia bidir → Re-Pair →
online incremental, métricas, e mapeamento conceito ↔ código.

## Notas técnicas (`notas/`)

Notas conceituais que atravessam vários experimentos ou registram
direções futuras a resgatar:

| Nota | Tema |
|---|---|
| [custo-de-marcadores](notas/2026-05-11-custo-de-marcadores.md) | teoria dos 4 níveis de custo e da métrica de unidades de informação |
| [comparacoes-nao-literais](notas/2026-05-11-comparacoes-nao-literais.md) | delta encoding (lossless) e modalidades lossy (texto aproximado, numérico) — futuro |
| [marcadores-compactos](notas/2026-05-11-marcadores-compactos.md) | sintaxe ultra-compacta e marcadores inferidos pela ordem — futuro |
| [tipos-com-estrutura](notas/2026-05-11-tipos-com-estrutura.md) | tipos com estrutura conhecida (CPF, UUID, IP, ISO, etc.) como pré-transformação — futuro |

## Evolução do v0.6 até o exp 06

Linha de progresso da serialização baseada em Patricia (exps 02 a 06):

```
02 patricia-nomes        — Patricia do zero. Header <patricia> + <body> com refs.
                           Roundtrip OK. RLE adjacente emerge no body.

03 patricia-inline       — Decl da folha embutida na 1ª ocorrência no body.
                           Pais Patricia viram "decl tardia" no fim. Forward refs.
                           Decode em 2 passadas.

04 formato-normalizado   — Régua única (sem comentários, count=1 implícito).
                           4 datasets x 4 ordenações = 16 cenários. Fórmula
                           simbólica em formula.py bate medição em 16/16.
                           Convenção das 4 camadas de custo formalizada.
                           Observação: economia em camada 2 escala com N_unique,
                           independente da ordenação.

05 patricia-aninhado     — Pai Patricia embutido recursivamente dentro da decl
                           do filho que primeiro o referencia. Avôs também,
                           em cadeia. Decls tardias eliminadas. Decode em 1
                           passada. Cadeias de 2-3 níveis aninhadas observadas.

06 aninhado-emails-urls  — Mesmo algoritmo do 05 em dados realistas (emails
                           +URLs). Cadeia de 3 níveis em D1 e D4. Avô
                           reaproveitado em ramos paralelos. Patricia só fatora
                           prefixos — sufixos comuns ficam duplicados.
```

Pendência registrada após o 06: a árvore atual é estritamente
**forward** (LCP — Longest Common Prefix). Sufixos comuns como
`@gmail.com` ou `.com` em emails não são fatorados. Próximos
experimentos abordam Patricia que avalia também sufixos
(direção reversa) e o casamento das duas direções.

## Old (revisão)

A pasta [`old/`](old/) contém 26 experimentos de 2026-05-07 a
2026-05-25 do ciclo anterior. **Obsoletos como referência canônica**.
Servem para:

- Revisar conceitos que podem retornar à v0.6 (recriados, não
  importados)
- Localizar bugs já diagnosticados
- Não citar como evidência em ticket, finding ou paper

A decisão sobre o que retorna à v0.6 será feita por experimento novo,
não por reaproveitamento de notas antigas.

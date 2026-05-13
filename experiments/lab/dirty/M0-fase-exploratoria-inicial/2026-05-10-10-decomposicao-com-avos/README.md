# 10 — decomposição com cadeia de ancestrais

## Princípio / motivação

Implementa a melhoria identificada no exp 09: a fase de decomposição
do exp 08 usava apenas o **pai imediato** de cada folha nas árvores
forward e reverse, perdendo ancestrais (avô, bisavô) já capturados
pelo Patricia. Em D2 do exp 08, todos os pais imediatos do reverse
(`a@hotmail.com`, `a@gmail.com`) eram tão longos que causavam
overlap obrigatório com o prefixo forward — composição nunca
ativava.

A melhoria aqui: para cada folha, **percorrer a cadeia inteira de
ancestrais** (forward e reverse) e escolher a combinação `(p, x)`
de maior cobertura que satisfaz `len(p) + len(x) ≤ len(s)`. Em D2,
isso permite escolher `mail.com` (avô na cadeia reverse) ou `.com`
(bisavô) quando o pai imediato não cabe.

Algoritmo Patricia (construção das árvores) é byte-idêntico ao
exp 08. Encode e decode também são idênticos. **A única mudança
está em `arvore_bidir.py`**, na função `decompor_strings`.

## Contexto da literatura (registrado para fase prototype futura)

Pesquisa feita após o exp 09 confirmou **três gaps genuínos** na
literatura para o caminho que estamos seguindo:

1. **Escolha por-string de ancestral em trie para encoding** — não
   publicada. CoCo-trie (Boffa 2022/2023) decide colapso de níveis
   estaticamente no layout do dicionário; nosso problema é dinâmico
   por-string.
2. **Front coding multi-nível** — front coding clássico (Witten/
   Moffat/Bell) e variantes do grupo Navarro/Brisaboa (PFC, HTFC,
   RPFC, etc.) usam apenas vizinho imediato em ordem lexicográfica.
3. **Fusão forward+reverse para codificação** — MergedTrie
   (Arroyuelo et al. 2019) funde double-tries mas só para indexação.
   Affix tree (Maaß 2003) combina via affix links caractere-a-caractere,
   não fragmento. Para encoding com escolha de fragmento, território
   original.

**Decisão registrada**: usar heurística gulosa simples ("best
fragment first" adaptado de Fraenkel-Mor-Perl 1983 com tratamento
de overlap). Não buscar ótimo global (NP-difícil pelo argumento de
Fraenkel-Mor-Perl). Aceitar resultado sub-ótimo — o foco do dirty
é estrutura informática correta, não bytes mínimos.

**Decisão registrada**: **não** implementar fusão das duas árvores
em grafo único (MergedTrie / affix tree). A literatura é unânime
em que isso é overkill para strings curtas (< 50 chars) em coluna —
overhead de ponteiros/labels domina o ganho. Front-coding com
bucketing + Re-Pair (HTFC) costuma vencer empiricamente nesse
regime. Manter as 2 árvores Patricia separadas é a escolha
razoável.

**Para fase prototype/limpa futura**: estes são pontos a revisitar
quando reorganizar o código. Particularmente:
- (a) heurística de escolha: ainda greedy ou tentar DP local?
- (b) sintaxe do encode: mais compacta para reduzir overhead por
  linha (o exp 10 mostra que composição pode custar mais bytes que
  economiza com a sintaxe verbosa atual).
- (c) considerar bucketing + Re-Pair (HTFC) como baseline a vencer.
- (d) decidir se fusão em grafo justifica para datasets maiores.

## Propósito

Responde a três perguntas:

1. **Viabilidade**: percorrer cadeia de ancestrais e escolher
   melhor combinação preserva roundtrip?
2. **Comportamento em D2**: composição ativa de fato? Quantas das
   12 strings ficam compostas?
3. **Robustez nos demais datasets**: D1, D3, D4 não degradam
   semanticamente nem em bytes?

## Comparação

- **Compara com**: [08-patricia-bidir-composto](../2026-05-10-08-patricia-bidir-composto/)
  (pai imediato).
- **É comparável?** Sim. Mesmos 4 datasets, mesmo algoritmo de
  Patricia, mesmo encode/decode. Só muda a função de decomposição.
- Métrica: ref+dados por dataset + distribuição da decomposição
  (compostas / só pref / só suf / folhas).

## Cenários e valores possíveis

Mesmos 4 datasets do exp 08 (copiados em `data/`). `MIN_PREFIXO=3`
fixado (testado em 08 que threshold não fez diferença).

### Algoritmo de escolha (heurística greedy)

Para cada string `s`:

1. Coletar `pref_cands` = cadeia de ancestrais na árvore forward
   (do pai imediato à raiz top-level), filtrada por `len ≥ min_prefixo`.
2. Coletar `suf_cands` = cadeia de ancestrais na árvore reverse,
   des-invertendo cada texto, filtrada por `len ≥ min_prefixo`.
3. Adicionar `""` (opção vazia) em ambas as listas.
4. Para cada par `(p, x)`:
   - se `len(p) + len(x) > len(s)`: descarta (overlap).
   - se `p` não é prefixo de `s` ou `x` não é sufixo: descarta.
   - calcula `cobertura = len(p) + len(x)`.
5. Escolhe o par de maior cobertura. Tie → maior `len(p)`
   (determinista, arbitrário).
6. Se nenhum par é válido, decompõe como folha simples (`pref=""`,
   `suf=""`, `middle=s`).

## Resultado observado

Roundtrip **4/4 OK**.

### Distribuição da decomposição

| Dataset | únicas | compostas | só pref | só suf | folhas |
|---|---:|---:|---:|---:|---:|
| D1 | 10 | 10 (era 10) | 0 | 0 | 0 |
| D2 | 12 | **12 (era 0)** | 0 | 0 | 0 |
| D3 | 10 | 0 (era 0) | 10 | 0 | 0 |
| D4 | 12 | 0 (era 0) | 12 | 0 | 0 |

**D2 passou de 0/12 para 12/12 compostas** — todas as strings
agora têm pref + middle + suf. Demais datasets mantiveram a
distribuição do exp 08 (a melhoria não degrada onde já funcionava).

### Bytes ref+dados — exp 10 vs exp 08

| Dataset | exp 08 | exp 10 | delta | menor |
|---|---:|---:|---:|---|
| D1 | 494 | 494 | 0 | empate |
| D2 | **610** | 655 | +45 | exp 08 |
| D3 | 372 | 372 | 0 | empate |
| D4 | 505 | 505 | 0 | empate |

**Achado importante (gap semântica vs bytes)**: o exp 10 captura
**mais informação semântica** em D2 (12 compostas com pref +
`mail.com`/`.com` como suf reaproveitado), mas custa +45 bytes.

Análise do trade-off em D2:
- exp 08 (cada linha: `noN: pref:noP + "X"` ou `noN: "X" + suf:noY`):
  ~1 ref por linha, middle ≈ 8-10 chars.
- exp 10 (cada linha: `noN: pref:noP + "X" + suf:noY`): 2 refs por
  linha, middle ≈ 3-5 chars.
- Economia em middle: ~6 chars × 12 linhas = -72 chars.
- Overhead da 2ª ref: ~12 chars × 12 linhas = +144 chars.
- Saldo de marcadores: +72 chars.
- Decls novas (`mail.com`, `.com`) — 2 decls extra ≈ +30 chars.
- Decls economizadas (sufixos `a@dominio.com` longos) ≈ -50 chars.
- Total estimado: ~+50 chars. Confere com +45 medido.

A sintaxe verbosa do encode atual (`pref:noN + "X" + suf:noN`,
30+ chars por linha) **não amortiza o ganho semântico em D2**. Para
um formato compacto, espera-se que a balança vire — mas isso é
trabalho da fase prototype, não deste dirty.

## Decomposição de D2 (lado a lado, para inspeção)

```
maria.silva@gmail.com    -> pref="maria.silva@"  mid="g"     suf="mail.com"
joao.souza@hotmail.com   -> pref="joao.souza@"   mid="hot"   suf="mail.com"
maria.silva@hotmail.com  -> pref="maria.silva@"  mid="hot"   suf="mail.com"
ana.lima@gmail.com       -> pref="ana.lima@"     mid="g"     suf="mail.com"
joao.souza@gmail.com     -> pref="joao.souza@"   mid="g"     suf="mail.com"
pedro.alves@yahoo.com    -> pref="pedro.alves@"  mid="yahoo" suf=".com"
ana.lima@hotmail.com     -> pref="ana.lima@"     mid="hot"   suf="mail.com"
joao.souza@yahoo.com     -> pref="joao.souza@"   mid="yahoo" suf=".com"
pedro.alves@gmail.com    -> pref="pedro.alves@"  mid="g"     suf="mail.com"
maria.silva@yahoo.com    -> pref="maria.silva@"  mid="yahoo" suf=".com"
ana.lima@yahoo.com       -> pref="ana.lima@"     mid="yahoo" suf=".com"
pedro.alves@hotmail.com  -> pref="pedro.alves@"  mid="hot"   suf="mail.com"
```

`mail.com` é usado em 8 strings (hotmail + gmail). `.com` em 4
strings (yahoo). Middle é 1-5 chars. Cobertura semântica clara.

## Limitações

- 4 datasets, 20 linhas cada. Não fala sobre escala.
- Heurística greedy simples — escolhe por cobertura, não por
  "ganho líquido em bytes". Pode haver casos onde escolher um
  ancestral mais curto mas com mais ocorrências no corpus dá menos
  bytes totais. Não otimizado.
- **Gap semântica vs bytes** registrado: composição custa marcadores.
  A sintaxe verbosa atual não amortiza. Esperar que isso se inverta
  num formato compacto.
- Sem comparação com formato compacto, CSV, JSON, ou HTFC. A
  literatura indica que HTFC seria baseline natural a vencer em
  fase prototype.
- Roundtrip valida só decode bem-formado; corrupção de input não
  testada.
- Não testa o caso `pref` na árvore forward com cadeia profunda
  (em D1 forward, `user0`/`user00` aparece mas só user010 cai em
  `user0` lateral — sem cadeia real para subir). Datasets onde
  forward tem cadeia de 3+ níveis poderiam ativar mais o lado
  pref da heurística.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-10-10-decomposicao-com-avos
python run.py
```

4 tabelas + decomposição detalhada de D2 + TCF completo de D1 e D2.
Arquivos em `encoded/*.tcf` e `decoded/*.csv`.

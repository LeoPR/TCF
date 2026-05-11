# 08 — patricia bidirecional composto

## Princípio / motivação

Continua dos exps 06 (forward inline com aninhamento) e 07 (reverse
isolado). Aqui as duas direções **atuam simultaneamente na mesma
encodagem**: cada string única pode ser decomposta em
`prefix_text + middle + suffix_text`, onde o prefix vem da árvore
forward e o suffix vem da árvore reverse.

Base teórica: a literatura (Maaß 2003, Strothmann 2007) tem a affix
tree para busca bidirecional. Para compressão, Fraenkel/Mor/Perl
(1983, *"Is text compression by prefixes and suffixes practical?"*)
provam que a decomposição ótima combinada é NP-difícil e recomendam
heurística gulosa **"best fragment first"** — escolher o fragmento
de maior ganho líquido primeiro. Aqui usamos a versão simples:
**mais longo vence em caso de overlap**, com tie-break por prefixo.

Sem heurística de escolha por dataset (composição emerge por linha).
Sem otimização — foco em estrutura informática correta.

## Propósito

Responde a três perguntas:

1. **Viabilidade da composição**: dá pra encodar
   `pref + middle + suf` numa mesma linha do body, com decode
   correto?
2. **Comportamento por dataset**: em quais cenários a composição
   ativa, e em quais cada string acaba só com um lado?
3. **Efeito do threshold (`MIN_PREFIXO`)**: 2 vs 3 chars muda algo?

## Comparação

- **Compara com**: [06](../2026-05-10-06-aninhado-emails-urls/)
  (forward only) e [07](../2026-05-10-07-patricia-reverso/)
  (forward vs reverse isolados).
- **É comparável?** Sim, com cuidado: mesmos 4 datasets, mas o
  encoder do 08 muda sintaxe de declaração (`pref:` em vez de
  `filho_de(` — 3 chars mais curto por ocorrência). Parte da
  diferença em bytes vem dessa mudança sintática, não só da
  composição em si.
- Métrica: `ref + dados` (camada 3 macro = 15 bytes constantes;
  camada 4 inexistente neste formato).

## Cenários e valores possíveis

Mesmos 4 datasets dos exps 06/07. Cada um rodado com
`MIN_PREFIXO ∈ {3, 2}` — 8 cenários totais.

### Sintaxe

Namespace único de eids (1, 2, 3, ...). Tipo do nó distinguido pela
sintaxe da declaração:

```
no1: folha "X"                                # string folha
no2: pref:(no3=decl folha "P") + "X"          # string com pref (pref decl aninhado)
no4: "X" + suf:(no5=decl folha "S")           # string com suf
no6: pref:no3 + "X" + suf:no5                 # composto (pref e suf ja decl)
no7: 3x pref:no3 + suf:no5                    # composto, middle vazio, com RLE
```

Decls de pref/suf são folhas simples (sem cadeia recursiva — exp 05
manteria, aqui simplificamos para o caso comum).

## Resultado observado

Roundtrip **8/8 OK**.

### Distribuição da decomposição por dataset

| Dataset | únicas | compostas | só pref | só suf | folhas |
|---|---:|---:|---:|---:|---:|
| D1 — emails 1 domínio | 10 | **10** | 0 | 0 | 0 |
| D2 — emails multi | 12 | 0 | 7 | 5 | 0 |
| D3 — URLs path comum | 10 | 0 | 10 | 0 | 0 |
| D4 — URLs multi-recurso | 12 | 0 | 12 | 0 | 0 |

Observação central: **só D1 ativou composição** (todas as 10
strings). Em D2 a heurística de overlap descartou um dos lados em
toda string. Em D3/D4 reverse não detectou nada.

### Por que D2 não compõe

Strings de D2 têm len 21-23. Prefix `nome.sobrenome@` (11-12 chars)
+ suffix `@dominio.com` ou `a@dominio.com` (10-13 chars) **somam
mais que a própria string** — overlap obrigatório. A heurística
best-fragment-first escolhe o mais longo e descarta o outro.

Exemplo: `joao.souza@hotmail.com` (len 22):
- pref="joao.souza@" (11), suf="a@hotmail.com" (13) — soma 24 > 22
- mais longo vence → fica `mid="joao.souz" + suf="a@hotmail.com"`

Para D2 produzir composição, precisaria de strings mais longas (com
algo "no meio" não coberto pelos dois lados), ou heurística mais
sofisticada que aceite cobertura parcial.

### Bytes (ref + dados) por cenário

| Dataset | 08 composto | 06 forward | 07 reverse | menor |
|---|---:|---:|---:|---|
| D1 | 494 | 518 | **456** | reverse |
| D2 | **610** | 617 | 726 | composto |
| D3 | **372** | 420 | 602 | composto |
| D4 | **505** | 551 | 710 | composto |

Em 3 de 4 datasets o composto ficou com menos bytes. Em D1 o
reverse-only ainda venceu — a sintaxe `pref:noN + "X" + suf:noN` é
mais verbosa por linha que `filho_de(noN) + "X"` no reverse-only,
e o ganho semântico (prefix capturado) não compensa quando o reverse
sozinho já cobre quase tudo.

**Atenção sobre comparação com 06**: o encoder 08 usa marcador
`pref:` (9 chars com id) onde 06 usava `filho_de(` (12 chars). Essa
mudança sintática contribui para a vantagem do 08 em D3 e D4 (onde
só pref atua e a estrutura é equivalente). A comparação não isola
"composição" de "sintaxe nova"; isso fica para experimento posterior
se for relevante.

### Threshold 3 vs 2

| Dataset | min=3 | min=2 | delta |
|---|---:|---:|---:|
| D1 | 494 | 494 | 0 |
| D2 | 610 | 610 | 0 |
| D3 | 372 | 372 | 0 |
| D4 | 505 | 505 | 0 |

**Idêntico nos 4 datasets**. Razão: Patricia gulosa escolhe o
prefixo mais longo disponível. Em todos esses datasets há prefixos
≥ 3 chars com count ≥ 2, então o algoritmo nunca chega a considerar
candidatos de 2 chars. Para ver diferença, seria preciso dataset
sem padrões de 3+ chars (não testado aqui).

## Limitações

- 4 datasets, 20 linhas cada. Não fala sobre escala.
- Composição só ativou em D1. Cenários onde p+x < s para muitas
  strings (com "meio" significativo) não foram testados.
- Heurística de overlap é a simplificação "mais longo vence". A
  literatura clássica (Fraenkel-Mor-Perl 1983) recomenda "ganho
  líquido por bytes" — não implementado aqui. Em datasets onde
  prefix e suffix têm contagens muito diferentes, o ganho real
  varia (descartar o de count alto custa mais que descartar o de
  count baixo, mesmo que igual em len).
- Threshold 2 não fez diferença porque os datasets têm padrões ≥ 3
  chars dominantes. Dataset com só padrões de 2 chars não foi
  testado.
- Decl de pref/suf é sempre folha simples (`decl folha "X"`).
  Cadeia recursiva (exp 05) não foi reaproveitada — pref/suf não
  têm "pais" de pref/suf nesta implementação. Aceitável: pref e
  suf são folhas terminais por design do algoritmo Patricia atual.
- Sintaxe `pref:noN + "X"` vs `filho_de(noN) + "X"` é uma mudança
  arbitrária. Comparação direta com exp 06 mistura "composição" e
  "sintaxe nova".
- Roundtrip valida apenas decode bem-formado; robustez contra
  inputs malformados não foi testada.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-10-08-patricia-bidir-composto
python run.py
```

Imprime 4 tabelas + decomposição + TCF para cada cenário. Arquivos
em `encoded/{D}-min{2,3}.tcf` e `decoded/{D}-min{2,3}.csv`.

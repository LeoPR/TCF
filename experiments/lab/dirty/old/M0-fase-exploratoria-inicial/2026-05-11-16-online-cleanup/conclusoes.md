# Conclusões — cleanup do exp 15

Refatoração estrutural pura. Resultado: TCFs **byte-idênticos**
aos do exp 15 nos 3 datasets, com 14% menos linhas de código.

## O que a refatoração ensinou

### 1. Dominância de candidatos em `_escolher_par`

A versão original gerava 4 candidatos em caso de overlap. A análise
de dominância mostrou que **dois deles eram redundantes**:

```
overlap entre best_pref (bp) e best_suf (bs):
  (a) bp + maior_suf que caiba       ← dominante
  (b) maior_pref que caiba + bs      ← dominante
  (c) bp + 0                          ← dominado por (a)
  (d) 0 + bs                          ← dominado por (b)
```

Justificativa formal:

- Se `espaco_suf = n - bp_len < min_len`, então `_melhor_suf` com
  `max_len = espaco_suf` retorna `(0, 0)` (nenhum suf >= min_len
  cabe). Nesse caso (a) produz `(bp_id, bp_len, 0, 0)` que é
  exatamente (c).
- Se `espaco_suf >= min_len`, então (a) pode produzir
  `novo_suf_len > 0`, cobrindo mais que (c). Se (a) achar
  `novo_suf_len = 0` (nenhum suf válido), volta a coincidir com (c).
- Em qualquer caso, (a) domina (c). Análise simétrica para (b)/(d).

A coincidência byte-a-byte em 3 datasets é evidência empírica de
que a análise está correta no escopo testado. Falta prova formal
(ou contra-exemplo) para o caso geral.

### 2. Funções helper são naturais aqui

`_melhor_pref(s, anteriores, max_len, min_len)` apareceu como
abstração natural quando o overlap forçou busca limitada. A versão
do exp 15 tinha duas funções (`maior_pref_ate`, `maior_suf_ate`)
mas só usava cada uma em um lugar — agora cada uma é usada **duas
vezes** (caso geral + caso overlap), justificando a função.

### 3. RLE adjacente é função independente

`_rle_adjacente(linhas)` antes estava embutido dentro de
`encode_online`. Extrair para função tornou explícito que é
**ortogonal** à serialização de tokens. Em experimentos futuros
(p.ex. com revisão retroativa) o RLE pode mudar de forma sem
mexer no resto.

### 4. Comentários explicando "por que funciona" tendem a virar
   ruído

O exp 15 tinha um bloco grande explicando que
`string_id == eid` por construção. Verdadeiro, mas:
- Quem lê o código consegue verificar isso em 30s
- O comentário não aparece em ferramentas de busca
- Ele envelhece se a construção mudar (e ninguém atualiza)

Removido. Se um leitor futuro tiver dúvida, o teste de roundtrip
falha em segundos caso a invariante quebre.

## O que NÃO mudou

- Comportamento algorítmico (TCFs byte-idênticos).
- Métricas (bytes, unidades).
- Limitações do exp 15 (persistem todas).

## Pontos a registrar

1. **A refatoração não é "melhoria"** — é higiene. O algoritmo
   continua o mesmo, apenas mais legível e com menos branches a
   inspecionar.

2. **Critério de equivalência foi forte**: diff binário do TCF +
   bytes + unidades + roundtrip. Os 3 datasets cobrem casos de
   overlap (D2-mini, D2-completo) e ausência de overlap (D4).

3. **A redução de candidatos de 4 para 2 abre espaço conceitual**
   para o próximo experimento. Se quisermos testar "par A+B
   independente" (exp 19 proposto), precisamos pensar nele
   **acima** dessa base — não vamos mais perder tempo verificando
   se (c) ou (d) ajudariam.

## O que este experimento não mostra

- Que a dominância (c) ⊆ (a), (d) ⊆ (b) vale em todos os casos
  possíveis. Vale nos 3 datasets, raciocinada para o caso geral
  mas não provada formalmente.
- Comportamento em escala (N >> 20).
- Comportamento em famílias variadas de string.
- Que o algoritmo é correto além do que já foi validado no exp 15.

## Próximo passo natural

Antes de variantes algorítmicas (revisão retroativa, par A+B),
verificar se o algoritmo atual generaliza além de emails:

- **exp 18 (próximo)**: famílias variadas — URLs, UUIDs, ISO
  dates, IPs, CPFs. Em quais o exp 16 mantém comportamento? Em
  quais degrada?

Esse mapa de comportamento é input necessário para escolher quais
variantes algorítmicas valem a pena testar a seguir.

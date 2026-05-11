# 14 — Online incremental SEM revisão (Opção A)

## Princípio / motivação

Paralelo ao Re-Pair do exp 13. Implementa a **Opção A** do
trade-off triangular discutido: algoritmo **online incremental**
que processa strings uma por vez, **sem revisar nada já feito**.

Permite:
- **Streaming**: cada string pode ser emitida assim que processada
- **Memória previsível**: só mantém strings já vistas (sem
  necessidade de batch global)
- **Latência mínima**: primeiro byte sai com a 1ª string

Em troca de:
- **Possível perda de compressão** vs Re-Pair batch (que tem visão
  global de todas as strings)

Este experimento mede **quanto se perde** ao abrir mão da visão
global. Não substitui Re-Pair — paralelo a ele.

## Propósito

Responde a duas perguntas:

1. **Viabilidade**: algoritmo online sem revisão funciona e
   produz roundtrip OK?
2. **Custo da ausência de visão global**: comparado ao Re-Pair
   batch (exp 13), quanto se perde em compressão?

## Comparação

- **Compara com**: [13-repair-bottomup](../2026-05-10-13-repair-bottomup/)
  (Re-Pair batch) e (indiretamente)
  [10-decomposicao-com-avos](../2026-05-10-10-decomposicao-com-avos/).
- **É comparável?** Sim, mesmos 3 datasets. Algoritmo diferente,
  sintaxe levemente diferente.
- Métrica: ref+dados.

## Cenários

3 datasets (mesmos do exp 13):

| Nome | Strings | Padrão dominante |
|---|---:|---|
| D2-mini | 6 | 2 nomes × 3 domínios |
| D2-completo | 20 (12 únicas) | 4 nomes × 3 domínios |
| D4 | 20 (12 únicas) | 1 base URL × 3 recursos |

## Algoritmo

Online incremental, sem revisão retroativa:

```
para cada nova string s (em ordem):
    se primeira string:
        emitir como literal puro
        continuar

    para cada string anterior s_prev:
        calcular LCP(s, s_prev) = comprimento do prefixo comum
        calcular LCS(s, s_prev) = comprimento do sufixo comum

    melhor_pref = (s_prev, LCP) com maior LCP (>= min_len)
    melhor_suf  = (s_prev, LCS) com maior LCS (>= min_len)

    se LCP_max + LCS_max > len(s):  # overlap
        descartar o menor

    emitir s como:
        ref_pref(s_prev_id, LCP) + literal(meio) + ref_suf(s_prev_id, LCS)
```

Não modifica strings anteriores. Cada nova string aponta para a
**melhor anterior** (que dá o maior LCP ou LCS).

**Sintaxe TCF** (didática):

```
no1: "maria.silva@gmail.com"           # literal puro (1a string)
no2: no1[0:12] + "hotmail.com"         # primeiros 12 chars de no1
no3: "joao.souza@hot" + no1[-8:]       # literal + últimos 8 chars de no1
```

`noN[0:K]` = primeiros K chars de noN.
`noN[-K:]` = últimos K chars de noN.

## Resultado observado

Roundtrip **3/3 OK**.

| Dataset | exp 13 (Re-Pair) | exp 14 (online) | delta |
|---|---:|---:|---:|
| D2-mini | 192 | 198 | +6 |
| D2-completo | 447 | 463 | +16 |
| D4 | 424 | **399** | **-25** |

**Surpresa em D4**: o algoritmo online **venceu** Re-Pair por
25 bytes. Em D2 (completo e mini) perdeu por margem pequena
(+6, +16).

### Por que D4 venceu

Em D4, strings consecutivas (ou próximas) compartilham prefixo
**muito longo** (33-37 chars). Re-Pair extraiu só
`https://api.example.com/v1/` (27 chars) como símbolo. O online
captura LCP = 33-37 chars entre pares de strings:

```
no1: "https://api.example.com/v1/users/1"               (literal puro)
no2: no1[0:27] + "orders/100"                          (27 chars de no1 + meio)
no3: no1[0:33] + "2"                                   (33 chars = "...users/")
no4: no2[0:36] + "1"                                   (36 chars = "...orders/10")
no5: no1[0:27] + "products/50"                         (27 chars + meio)
```

A flexibilidade de "prefixo arbitrário" (não preso a um símbolo
fixo) ganhou sobre o "símbolo de tamanho fixo" do Re-Pair.

### Por que D2 perdeu

Em D2, o padrão dominante (`mail.com` aparece em 8 strings) é
**globalmente disperso** — em strings não-consecutivas. Re-Pair
captura porque tem visão global. Online sem revisão só compara
com strings já vistas, então:

- Quando a 1ª `mail.com` aparece, é só uma string isolada — não
  vira símbolo.
- Quando a 2ª aparece, casa por sufixo com a 1ª. OK.
- Quando a 3ª aparece, casa com qualquer das 2 anteriores.
- Etc.

Cada novo `mail.com` paga `no1[-8:]` (5 chars de overhead). Em
Re-Pair, paga `R1` (3 chars). Diferença pequena × 8 strings =
margem do delta.

### Padrão captado em D2-completo via sufixo

```
no1: "maria.silva@gmail.com"                            (literal)
no2: "joao.souza@hot" + no1[-8:]                       (sufixo "mail.com" de no1)
no3: "maria.silv" + no2[-13:]                          (sufixo "a@hotmail.com" de no2)
no4: "ana.lim" + no1[-11:]                             (sufixo "a@gmail.com" de no1)
no5: no2[0:11] + "gmail.com"                           (prefixo "joao.souza@" de no2)
no6: "pedro.alves@yahoo" + no1[-4:]                    (sufixo ".com" de no1)
```

Note como `no1[-8:]` traz `mail.com` sem precisar criar símbolo
separado. Compacto e simples.

## Limitações

- 3 datasets pequenos.
- Algoritmo é O(N²) — cada nova string compara com todas as
  anteriores. Para grandes N, custo cresce. Exp 16 (janela
  deslizante) atacaria isso.
- Heurística simples: maior LCP, maior LCS, descarte por overlap.
  Sem ganho líquido por bytes (Fraenkel-Mor-Perl) — pode escolher
  match longo de single uso onde match curto repetido seria
  melhor (mas online não sabe disso sem revisão).
- Cada referência aponta para **uma anterior única** (pref ou
  suf). Não há símbolos compartilhados explicitamente.
- Sintaxe `noN[a:b]` ainda verbosa. Compacta poderia economizar
  mais.
- **Sem revisão retroativa**: padrões mais rasos que apareçam em
  strings futuras NÃO são reaproveitados nas anteriores. Exp 15
  ataca isso.

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-10-14-online-sem-revisao
python run.py
```

Tabela consolidada no stdout. Detalhe por dataset em `debug-output/`.
TCFs em `encoded/`. Decode validado.

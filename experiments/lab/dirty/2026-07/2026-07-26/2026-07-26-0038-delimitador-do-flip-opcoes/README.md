# 2026-07-26-0038 — O delimitador do flip: variantes materializadas, e a RETRATAÇÃO

Duas correções, ambas do owner e de uma verificação adversarial.

**1ª (owner)**: *"as pastas não têm as variações, sem cabeçalho nem nada — elas ficaram em sua
imaginação. preciso de evidências."* Certo: a rodada anterior **estimava** e gravava só o corpo
normal. Agora há 60 arquivos com os três wires completos.

**2ª (verificação adversarial)**: o round-trip que eu usei para dizer "lossless" era
**CIRCULAR**. E o flip tem **três** bloqueadores estruturais, não um.

---

## O RT era circular — e isso invalidou a conclusão, não os bytes

O lab fazia `flip → des-flip → decode`. Isso testa a consistência do **par de funções do
próprio lab**, não a decodabilidade da forma flipada — nenhum `.tcfp` era passado ao `decode`.
Um verificador escreveu um leitor independente do corpo FLIP e achou **2 de 12 colunas com
RT=OK e wire corrompido**.

Escrevi então um **detector estrutural** (que não usa o round-trip) e ele chega às mesmas 2
colunas — confirmação cruzada de duas implementações independentes.

## Os três bloqueadores

| # | bloqueador | natureza |
|---|---|---|
| 1 | valor começando com `^` perdia a barra | **bug meu** — corrigido |
| 2 | linha `0` = literal "0" em FLIP, mas `0` já é a grafia do **slot null** | **estrutural** |
| 3 | o seq-RLE localiza os dígitos a incrementar **pelo escape** | **estrutural** |

### 1 — o `^` (corrigido)

O encoder escapa `^` só no **início** do valor (é o namespace de referência de linha):
`['^a']` → `\^a`, mas `['a^b']` → `a^b`. Meu `_esc_chr` era por-caractere e perdia a barra.
Agora é posicional.

### 2 — colisão com o slot null

```
encode(['0'])   -> corpo '\0'   -> FLIP '0'
encode([None])  -> corpo '0'                 ← a MESMA linha
```

O corpo FLIP da string `"0"` é byte-idêntico ao corpo NORMAL do null. O delimitador **não
resolve** — ele desambigua referência-colada-em-literal *dentro* da declaração, não a linha
inteira. E o round-trip byte-a-byte é cego a isso, porque `de_flip` recoloca a barra e o corpo
volta idêntico.

### 3 — o seq-RLE (o pior)

O marcador `*N±d|` acha os dígitos a incrementar com `find_escape_digit_runs`. O flip muda o
que o escape significa, e a quebra tem **duas formas**, ambas silenciosas:

```
somem:              *10+1|\0   →  *10+1|0
                    expande p/ dez cópias de "0" em vez de 0..9

mudam de token:     *2-10|14\22;c   →  *2-10|\14;22\;c
                    o delta agia no LITERAL 22; agora age na REFERÊNCIA 14
```

A segunda é a mais traiçoeira: as corridas de escape continuam existindo, só que apontando
para a coisa errada. Um detector que só perguntasse "tem barra?" não a acharia — foi
exatamente o erro da minha primeira versão do detector.

## Resultado — bytes reais, com a validade marcada

| forma | tag | JSON | normal | flipA | Δ A | flipB | Δ B | wire flipado |
|---|---|---:|---:|---:|---:|---:|---:|---|
| hex | `s` | 5501 | 5718 | 4509 | **−1209** | 4509 | −1209 | ok |
| moeda | `s` | 6443 | 6233 | 5439 | **−794** | 5454 | −779 | ok |
| int-ruído | `n` | 3423 | 3930 | 3431 | **−499** | 3431 | −499 | ok |
| telefone | `s` | 9001 | 8251 | 7899 | **−352** | 7903 | −348 | ok |
| int-seq | `n` | 1891 | 39 | 37 | −2 | 37 | −2 | **INVÁLIDO** |
| versão | `s` | 4645 | 4936 | 5057 | +121 | 5182 | +246 | ok |
| data-BR | `s` | 6501 | 4912 | 5157 | +245 | 5198 | +286 | ok |
| URL | `s` | 15388 | 6570 | 7190 | +620 | 7207 | +637 | ok |
| com-delim | `s` | 5443 | 3715 | 4650 | +935 | 4936 | +1221 | **INVÁLIDO** |
| email | `s` | 8943 | 5750 | 6714 | +964 | 7202 | +1452 | ok |
| path | `s` | 12403 | 6326 | 7445 | +1119 | 7848 | +1522 | ok |
| JSON-ish | `s` | 13947 | 5355 | 6807 | +1452 | 7297 | +1942 | ok |

As duas linhas `INVÁLIDO` medem bytes de um corpo que **nenhum decoder consegue ler**. O
número é real; o que ele mede não serve.

**Os quatro ganhos sobrevivem** — hex, moeda, int-ruído e telefone têm wire flipado válido.

## Custo de cabeçalho

O flag mora no char de **modo** (índice 7), que só existe **depois de uma tag**:

| tipo | hoje | com flag | custo |
|---|---|---|---:|
| número | `#TCF.8n` | `#TCF.8nf` | +1 B |
| string | `#TCF.8` (implícita) | `#TCF.8sf` | +2 B |

Flipar string **força torná-la explícita**. Já somado na tabela.

## Veredito: o flip NÃO é um esquema válido como prototipado

O ganho é real onde aparece, mas o esquema precisa de **três** regras a mais, não uma:

1. escape posicional do `^` (resolvido)
2. uma regra para o literal `"0"` que não colida com o slot null
3. o marcador seq-RLE precisa saber a polaridade — hoje ele deduz pelo escape

Só depois disso faria sentido discutir **qual char** é o delimitador. A pergunta do char é
prematura: ela pressupõe que o resto do esquema fecha, e ele não fecha.

## Lição de método

Round-trip byte-a-byte do par `para/de` é **prova de consistência interna, não de validade**.
Para um formato, a única prova é **decodificar a forma proposta** com o parser real (ou com um
leitor escrito independentemente). Um fuzz de 100 mil round-trips não acharia os bloqueadores
2 e 3 — porque neles o round-trip **passa**.

## Rodar

```
python run.py     # 12 formas × 3 wires + detector estrutural
```
`polaridade.py` tem as transformações, as inversas e o detector de bloqueadores.
**Não toca `src/tcf`.**

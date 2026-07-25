# Proveniência — inteiros: ordem, cardinalidade, null, magnitude (2026-07-25-2036)

**Fonte**: 100% sintético/determinístico. Nenhum download, nenhum dado real.

## Como cada grupo foi construído, e por quê

**1. ORDEM** — `seq(n)` é `0..n−1`; `desordenado(n)` é **a mesma multiset** embaralhada por
Fisher-Yates com LCG de seed fixa. Usar a mesma multiset é o ponto: isola o efeito da **ordem**
de qualquer efeito de conteúdo. `decresc` é `seq` invertida.

**2. PASSO** — cadências regulares não-unitárias (5, 100), uma faixa de ids (`1000..1099`) e
epoch a cada 60 s. Testam se o seq-RLE depende de o passo ser 1.

**3. CARDINALIDADE** — `k` valores distintos sorteados por LCG, `n=100` fixo. `k` varre
1, 2, 3, 5, 10, 20, 50, 100 na seção dedicada.

**4. NULL** — null sorteado por LCG sobre a sequência **e** sobre a desordenada, para separar
"custo do null" de "custo de quebrar a cadência".

**5. MAGNITUDE** — mesma estrutura (`k=10`, `n=100`) com literais de 1, 6 e 21 dígitos, mais
um caso float. Isola a largura do literal de todo o resto.

## Limites declarados

- **Dados sintéticos, não realistas.** `range(n)` é o **melhor caso possível** para o seq-RLE
  e o embaralhado é próximo do pior. Colunas reais ficam entre os dois, e nenhuma linha aqui
  deve ser lida como "o TCF comprime X% em inteiros".
- **A densidade de null efetiva difere do rótulo** (`p50` deu 36 nulls em 100, `p90` deu 80):
  o LCG sorteia por elemento. A coluna `nulls` mostra o valor real.
- **JSON compacto entra só como régua de ordem de grandeza**, em bytes. Não há porcentagem
  nesta rodada por decisão de método (ver README).
- **Métrica única: bytes.** Sem gzip, sem latência, sem memória.
- **Uma coluna, um tipo.** Multi-col e `.8H` fora.

## Reprodutibilidade

`python run.py` regenera byte a byte — LCG de seed fixa, sem `random` global, sem relógio,
sem rede. **Zero escrita em `src/tcf`.**

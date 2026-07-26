# Proveniência — polaridade do escape (2026-07-25-2337)

**Fonte**: 100% sintético/determinístico (LCG de seed fixa). Nenhum download, nenhum dado real.

**Os CPFs do caso `A-cpf-like-n200` são FORMA, não documento**: `f"{i:03d}.{i*7%1000:03d}.…"`
gera a *máscara* de um CPF a partir do índice, sem qualquer validação de dígito verificador.
Não há CPF válido aqui, e nenhum é publicado.

## Por que cada caso existe

Os grupos separam a **decisão**, não amostram o mundo:

- **A (5)** — dado dominado por número: onde o escape é frequente e a referência é rara. É a
  hipótese do owner. Cobre inteiro aleatório (2 tamanhos), documento formatado, hex e preço.
- **B (1)** — datas ISO: **mistura** escape e referência na mesma linha. Entrou para testar a
  fronteira, e foi o único que expôs o bloqueador de adjacência.
- **C (2)** — texto: emails (mais referência que escape) e texto sem dígito nenhum. São o
  **controle negativo** — se o flip fosse sempre bom, não precisariam existir.
- **D (2)** — regimes onde o flip é irrelevante: cadência (corpo já minúsculo) e baixa
  cardinalidade (domina o `^N`, que é outro namespace).

## Método

- **`corpo NORMAL`** = `_encode_column(...)` real, do `src/tcf`.
- **`corpo FLIP`** = materializado pela função `flip` do lab, que é uma **involução** por
  construção — e a validação é justamente aplicar duas vezes e exigir identidade byte a byte.
- **`adjacências ambíguas`** = contador **independente** do flip, escrito separadamente. O
  `run.py` tem um `assert` exigindo que os dois concordem — se divergirem, o lab falha em vez
  de reportar número errado.

## Limites declarados

- **Nada foi soldado.** O `flip` vive no lab; o `src/tcf` não foi tocado.
- **Métrica única: bytes do corpo.** O cabeçalho fica fora (seria +1 B do flag, igual nas
  duas formas). Sem gzip, sem latência.
- **O ganho somado (2522 B) é da matriz**, não uma expectativa — depende inteiramente de
  quantos casos numéricos se inclui. A matriz é deliberadamente enviesada para o caso A,
  porque a pergunta era "quanto dá para ganhar ali".
- **O bloqueador de adjacência foi encontrado em 1 de 10 casos.** Isso **não** significa 10%
  de incidência no mundo real — significa que uma forma comum (data ISO) já o produz.

## Reprodutibilidade

`python run.py` regenera byte a byte — LCG de seed fixa, sem `random` global, sem relógio,
sem rede.

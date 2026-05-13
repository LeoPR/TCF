# Dataset rico — propositadamente fora de ordem

**Objetivo da mesa:** explorar o limite teórico de compressão antes de quebrar
em chunks. Estudar primeiro sem mexer na ordem, depois com 4 ordenações
distintas. Ver se algum formato é **sempre** melhor ou se há combinações onde
um vence o outro.

---

## Dados (30 linhas, ordem original embaralhada)

```
nome, produto, quantidade, valor_unitario
Helena, Lápis, 20, 0.50
Beto, Caneta, 10, 1.50
Diana, Mochila, 1, 50.00
Ana, Caderno, 3, 3.00
Carlos, Caneta, 12, 2.00
Eduardo, Régua, 5, 2.00
Beto, Caderno, 5, 3.00
Fernanda, Marcador, 2, 4.50
Gabriel, Caneta, 10, 1.50
Helena, Borracha, 4, 0.75
Ana, Lápis, 30, 0.50
Diana, Apontador, 8, 1.00
Carlos, Caderno, 1, 5.00
Eduardo, Caneta, 10, 1.50
Beto, Lápis, 15, 0.50
Helena, Régua, 5, 2.00
Fernanda, Caneta, 20, 1.50
Ana, Marcador, 3, 4.00
Gabriel, Borracha, 4, 0.75
Diana, Caderno, 5, 3.00
Carlos, Régua, 5, 2.00
Eduardo, Lápis, 25, 0.50
Helena, Caneta, 12, 2.00
Beto, Apontador, 8, 1.00
Fernanda, Caderno, 3, 3.00
Gabriel, Régua, 5, 2.00
Ana, Caneta, 10, 1.50
Diana, Borracha, 4, 0.75
Carlos, Lápis, 20, 0.50
Eduardo, Mochila, 1, 50.00
```

---

## Distribuições

### nome (8 distintos, ~4 ocorrências cada)

| Nome | Ocorrências |
|---|---|
| Ana | 4 |
| Beto | 4 |
| Carlos | 4 |
| Diana | 4 |
| Eduardo | 4 |
| Fernanda | 3 |
| Gabriel | 3 |
| Helena | 4 |

### produto (8 distintos, frequência variável)

| Produto | Ocorrências | Quantidades vistas | Valores vistos |
|---|---|---|---|
| Caneta | 7 | 10, 12, 20 | 1.50, 2.00 |
| Caderno | 5 | 1, 3, 5 | 3.00, 5.00 |
| Lápis | 5 | 15, 20, 25, 30 | 0.50 |
| Régua | 4 | 5 | 2.00 |
| Borracha | 3 | 4 | 0.75 |
| Apontador | 2 | 8 | 1.00 |
| Marcador | 2 | 2, 3 | 4.00, 4.50 |
| Mochila | 2 | 1 | 50.00 |

### quantidade (12 distintos)

`1 (×3), 2 (×1), 3 (×3), 4 (×3), 5 (×6), 8 (×2), 10 (×4), 12 (×2), 15 (×1), 20 (×3), 25 (×1), 30 (×1)`

### valor_unitario (10 distintos)

`0.50 (×6), 0.75 (×3), 1.00 (×2), 1.50 (×5), 2.00 (×6), 3.00 (×4), 4.00 (×1), 4.50 (×1), 5.00 (×1), 50.00 (×2)`

---

## Diferença para o dataset anterior

Naquele, produto/quantidade/valor eram **bijetivos**: cada produto tinha um único
preço e quantidade. Resultado: sort por qualquer um dos três comprimia igual.

Aqui, **a correlação foi quebrada de propósito**:
- Caneta sai a 1.50 OU 2.00 (promoção?)
- Caderno sai a 3.00 OU 5.00 (capa dura?)
- Marcador tem 2 quantidades e 2 preços diferentes

Isso significa que ordenar por produto **não vai mais propagar RLE perfeito**
para quantidade/valor. As 4 ordenações vão divergir em compressão.

---

## Cota teórica de informação (ordem de grandeza, não meta)

Conteúdo informacional puro (entropy-coded):
- nome: 30 × log₂(8) = 90 bits ≈ 12 B
- produto: 30 × log₂(8) = 90 bits ≈ 12 B
- quantidade: 30 × log₂(12) ≈ 107 bits ≈ 14 B
- valor: 30 × log₂(10) ≈ 100 bits ≈ 13 B
- Dicionários (~50 B em strings únicas)

→ Cota inferior estimada: **~100 B** (entropy + dict).
Nossos formatos textuais ficam acima dessa cota porque carregam estrutura por
linha. A pergunta é: quanto se aproximam, e onde travam?

---

## Plano

| Arquivo | Conteúdo |
|---|---|
| `01-sem-ordem.md`     | Compressão na ordem original, sem reordenar |
| `02-ordem-nome.md`    | Sort por nome + compressão |
| `03-ordem-produto.md` | Sort por produto + compressão |
| `04-ordem-quantidade.md` | Sort por quantidade + compressão (palpite: "inútil") |
| `05-ordem-valor.md`   | Sort por valor + compressão (palpite: "inútil") |
| `06-analise.md`       | Comparação cruzada + pergunta teórica |

Em cada ordenação, aplicar: C2 (col literal), C3 (RLE local), **C11-híbrido**
(dict implícito + RLE), e quando relevante C9, C12. Bytes aproximados —
foco no **comportamento estrutural**, não em microbytes.

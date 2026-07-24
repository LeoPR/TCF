# Fechamento — hex-n: saúde do output vs corrupção externa

Prova a garantia do owner: **tudo que o TCF produz decodifica saudável; fail-loud só ocorre por corrupção/bug**, nunca em saída legítima. Duas propriedades testadas separadamente: (A) SAÚDE do que o encoder produz; (B) CORRUPÇÃO deve sempre falhar-alto.

## A. SAÚDE — fuzz amplo do que o `encode` produz

- **127 casos** (N de 0 a 50.000, regimes: all-true/all-false/alternado, proporções 1–99%, runs mistos) — todos gerados a partir do `encode` REAL.
- **0 falhas.**

✅ **Nenhuma falha.** Todo wire produzido pelo encoder: decodifica sem exceção, RT exato (`decode(encode(v)) == v`), tipo `bool` preservado, e — quando denso — o `n` em hex que o PRÓPRIO encoder escreveu já é a grafia canônica que o decoder exige (autoconsistência: o encoder nunca produziria algo que o decoder rejeitaria).

## B. CORRUPÇÃO — mutações adversariais devem falhar-alto

- **506 mutações** aplicadas a 60 wires válidos (flip de char no header, truncamento do corpo, lixo no fim, zero-à-esquerda no `n` hex). Classificadas em 4 categorias — **por origem**, não só por sintoma:

1. **88 bit-flip DENTRO do payload denso** (base64) — mudam o DADO, não a estrutura. **Esperado**: o formato não tem checksum de dados (é textual/inspecionável por design); um bit invertido no meio de bits válidos produz OUTRO conjunto de bits igualmente válido. Isto é propriedade do design (como qualquer msgpack/protobuf sem CRC), não um gap de fail-loud — o que o weld anterior fechou foi a integridade ESTRUTURAL (tamanho, padding, alfabeto), que é o que É detectável.
2. **1 mudança ESTRUTURAL sem falhar** — candidato a bug real (diferente de 1: aqui a mutação alterou header/framing, não só dado).
3. **42 `KeyError` também no ÓRFÃO puro** (sem tag `b`, sem qualquer weld desta sessão) — confirmado: **lacuna PRÉ-EXISTENTE no core genérico** (`_decode_column`/HCC), não introduzida pelo weld hex-n/#4. O fuzz só a expôs agora por testar corpo malformado de propósito.
4. **0 `KeyError` SÓ no caminho tipado** (não reproduz no órfão) — seria bug NOVO introduzido pelos welds desta sessão, o único item realmente urgente.

### 2. Estrutural sem falhar — GAP REAL, causa raiz explicada

| caso | mutação | wire (início) | resultado |
|---|---|---|---|
| n15-all-false | flip@8 | `#TCF.8b19
AAA=` | `[False, False, False, False, False, False, False, ` |

**Causa raiz** (`n15-all-false`, `n=15`→`n=9` via flip no hex): `ceil(15/8)` e `ceil(9/8)` são **o mesmo nº de bytes (2)** — o check de tamanho exato não distingue `n` dentro do mesmo quantum de byte. E como os dados são **all-false (todos zero)**, os bits que viram 'padding' ao encolher `n` também são zero — passam no check de padding-zero. **É um gap genuíno, mas estreito**: só ocorre quando (a) `n` corrompido cai no mesmo `ceil(n/8)` do original E (b) os bits reais na região encolhida também são zero. Estruturalmente é a MESMA classe da categoria 1 (sem checksum de dado, `n` e o payload não têm vínculo criptográfico) — só que via um campo de HEADER em vez do corpo. Não é introduzido pelo weld hex-n especificamente (a mesma ambiguidade existiria com `n` decimal); é uma limitação de design do formato (sem CRC), não um bug de implementação.

## Inspeção de saídas (amostra real, pra você conferir)

| caso | n | wire (linha-0) | modo | detalhe (hex/dec/economia) | bytes |
|---|---:|---|---|---|---:|
| `n0-vazia` | 0 | `#TCF.8` | ? | - | 7 B |
| `n7-all-true` | 7 | `#TCF.8b17` | denso(w=1) | n_hex='7' n_dec=7 econ_vs_dec=0B | 14 B |
| `n15-all-false` | 15 | `#TCF.8b1f` | denso(w=1) | n_hex='f' n_dec=15 econ_vs_dec=1B | 14 B |
| `n63-alt` | 63 | `#TCF.8b13f` | denso(w=1) | n_hex='3f' n_dec=63 econ_vs_dec=0B | 23 B |
| `n100-all-true` | 100 | `#TCF.8b` | core | - | 18 B |
| `n256-all-false` | 256 | `#TCF.8b` | core | - | 19 B |
| `n1000-alt` | 1000 | `#TCF.8b13e8` | denso(w=1) | n_hex='3e8' n_dec=1000 econ_vs_dec=1B | 180 B |
| `n4097-all-true` | 4097 | `#TCF.8b` | core | - | 19 B |
| `n64-p5` | 64 | `#TCF.8b140` | denso(w=1) | n_hex='40' n_dec=64 econ_vs_dec=0B | 23 B |
| `n256-p10` | 256 | `#TCF.8b1100` | denso(w=1) | n_hex='100' n_dec=256 econ_vs_dec=0B | 56 B |
| `n1000-p25` | 1000 | `#TCF.8b13e8` | denso(w=1) | n_hex='3e8' n_dec=1000 econ_vs_dec=1B | 180 B |
| `n4096-p50` | 4096 | `#TCF.8b11000` | denso(w=1) | n_hex='1000' n_dec=4096 econ_vs_dec=0B | 697 B |

## Veredito

- **Saúde (A)**: ✅ CONFIRMADA — 127/127 sem falha (fuzz de 0 a 50.000 elementos).
- **Corrupção (B)**: ✅ zero bug de implementação NOVO — 0 `KeyError` novo. Os outros 3 achados são explicados, não bugs deste weld:
  1. `88` bit-flips de payload = limite de DESIGN (sem checksum de dado).
  2. `1` gap de `n` dentro do mesmo quantum-de-byte (all-false) = mesma classe (1), via header; INDEPENDENTE de hex/decimal (existiria com `n` decimal também — não introduzido por este weld).
  3. `42` `KeyError` também reproduz no ÓRFÃO puro = lacuna PRÉ-EXISTENTE do core genérico, fora do escopo deste weld.

**Garantia do owner: SUSTENTADA para os welds desta sessão** (0 bug de implementação novo). Os itens 1-2 são limitação de design conhecida (sem checksum) — não fecháveis sem mudar o formato (adicionar CRC), o que é decisão maior, fora deste fechamento. O item 3 é um achado À PARTE (core genérico, não deste weld) — registrado, não bloqueia.

---
Artefatos: `inputs/*-fonte.json` · `outputs/*-wire.tcfp` (amostra de 12). Regenera: `python run.py`.

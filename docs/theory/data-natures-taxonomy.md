# Taxonomia das naturezas dos dados — pre-tx por comportamento

**Status**: rascunho 2026-05-15 (criado junto com plano-mestre [META-TYPE-ENCODERS](../../tickets/META-TYPE-ENCODERS.md)). Evoluira conforme macros dirty descobrirem necessidade de refinar/dividir/unir categorias.

## Tese

Em vez de escrever encoders separados pra cada **tipo de dado**
(CPF, UUID, data, email, ...), classificar dados por **natureza
comportamental** e escrever encoders por nature. Tipos especificos
sao **exemplos** dessas naturezas. Um dado pode pertencer a
multiplas naturezas (composicao).

## As 8 naturezas

### 1. Incremental — Δ de referencia

**Definicao**: valor pode ser expresso como pequena diferenca
(`delta`) em relacao a uma referencia (`base`).

**Mecanismo**: encoder devolve `(base, deltas)`. Base e' o
representante canonico (ex: primeira data). Deltas geralmente sao
numeros pequenos que se codificam em poucos bytes.

**Exemplos**: data, timestamp, contador/ID sequencial, versao
semantica em serie, coordenadas geograficas em path/rota.

**Composicao com outras naturezas**: tipicamente apos templated
(extrai estrutura do formato data) e antes de high-entropy
detection (se deltas forem "random walk", talvez skip).

### 2. Templated — layout fixo + slots variaveis

**Definicao**: strings seguem um **template fixo** com pontos de
variacao (slots). O template e' compartilhado; so' os slots variam
entre instancias.

**Mecanismo**: encoder extrai o template (offline, via
anti-unificacao ou regex) e codifica so' os slots. Decoder
reconstroi via template + slot inserido.

**Exemplos**: CPF (`NNN.NNN.NNN-DD`), UUID (`8-4-4-4-12 hex`),
email (`local@domain.tld`), IP (`X.X.X.X`), URL
(`scheme://host/path?query`), telefone (`+CC (AA) NNNNN-NNNN`).

**Composicao**: nature mais composta — quase sempre opera **antes**
de outras naturezas que processarao os slots (incremental,
enumerated, checked, etc.).

### 3. Enumerated — dominio finito

**Definicao**: valor pertence a **dominio finito conhecido**
(idealmente caber em dicionario pequeno).

**Mecanismo**: dicionario maps valor → indice. Encoder devolve
indice; decoder reverte.

**Exemplos**: gender (`M`, `F`, `X`), status (`active`, `inactive`),
country code (`BR`, `US`, ...), currency (`USD`, `BRL`),
dominios populares de email (`gmail.com`, `yahoo.com`).

**Composicao**: tipicamente em **um slot** de um template
(ex: dominio em email). Stand-alone tambem possivel (coluna inteira
de status).

### 4. Checked — digito verificador redundante

**Definicao**: valor contem um sufixo (ou outro local) que e'
**funcao deterministica** dos outros bytes. Pode ser elidido no
encode e regenerado no decode sem perda.

**Mecanismo**: encoder remove os bytes-check; decoder recalcula.

**Exemplos**: CPF (2 digitos check), CNPJ (2 digitos),
EAN/UPC (1 digito), Luhn (cartao de credito), IBAN (2 chars).

**Composicao**: opera **depois** do templated (so' nos slots
numericos relevantes). **Antes** de incremental ou enumerated
nao faz sentido (precisa do valor completo pra calcular check).

### 5. Composite — multiplos sub-valores

**Definicao**: valor e' agregado de **sub-valores distintos** que
podem ser separados e tratados independentemente.

**Mecanismo**: encoder split na fronteira semantica; aplica encoder
por sub-tipo. Decoder recompoe na ordem.

**Exemplos**: datetime = (date, time, timezone); money = (currency,
amount); endereco = (rua, numero, cidade, ...); phone = (cc, area, num).

**Composicao**: orquestrador de outras naturezas — composite
chama incremental no `date`, enumerated no `timezone`, etc.

### 6. Hierarchical — arvore de prefixos

**Definicao**: valores compartilham prefixos em **estrutura
hierarquica** (arvore).

**Mecanismo**: arvore de prefixos compartilhada. Encoder devolve
caminho desde a raiz; decoder navega de volta.

**Exemplos**: paths (`api/users/123`, `api/users/456`), DNS names,
namespaces, URLs com path estavel, JSON paths.

**Composicao**: tipicamente em **um componente** do template
(ex: path em URL). Sub-arvore via incremental se folhas formam
serie (e.g., ID sequencial em path).

### 7. Lossy-recoverable — aproximado com erro controlado

**Definicao**: valor numerico pode ser **arredondado** com
**erro registrado** explicitamente. Recomposicao exata via
`(rounded_value, error_term)`.

**Mecanismo**: encoder devolve valor arredondado + pequeno termo de
erro. Decoder soma. Termo de erro varia em tamanho conforme precisao.

**Exemplos**: coordenadas geograficas com tolerancia configurada,
floats com aproximacao + delta, medicoes cientificas com erro
amostral.

**Composicao**: orthogonal a outras; opera em valores numericos.

**Cuidado**: lossy "puro" (sem erro registrado) **nao** e' essa
categoria — perde RT. Essa categoria preserva recuperabilidade.

### 8. High-entropy — sem redundancia exploravel

**Definicao**: valor e' **maximally random** dado seu dominio;
pre-tx **nao ajuda** alem de eventualmente dropar formato textual
e empacotar como bytes raw.

**Mecanismo**: passthrough. Encoder nao transforma; documenta
nature pra que o pipeline saiba pular outros encoders.

**Exemplos**: UUID random (v4), hashes (SHA-256, MD5), base64 de
dados criptografados, strings aleatorias verdadeiras.

**Composicao**: passthrough — pra que outras naturezas saibam parar.

## Mapeamento com D1-D15

| Dataset | Naturezas presentes |
|---|---|
| D1 emails-simples | Templated (email format) + Enumerated (3 dominios) |
| D2 emails-quote-id | Templated + Enumerated + (apostrofe no local-part — caso especial templated) |
| D3 stress-substring | Templated + Hierarchical (paths `api/users/...`) |
| D4 caos-mix | High-entropy (parcial) + Templated (estrutura `[X]*'Y'@4Z`) |
| D5 padroes-multiplos | Composite (email + uuid em mesma coluna) |
| D6 poucos-em-ruido | Composite (log = template + timestamp + payload) + Incremental (timestamps) |
| D7 aninhamento | Hierarchical (padroes aninhados) |
| D8 cabeca-cauda | Templated (prefix/suffix estaveis) |
| D9 frequencia-alta | Templated (wrapper) — slot detection nature alvo da [L02] |
| D10 datas-mundiais | Templated (multiplos layouts) |
| D11 datetime-precisao | Templated + Incremental + Composite |
| D12 datetime-timezone | Templated + Composite + Enumerated (timezone) |
| D13 cpf-variados | Templated + Checked + (Enumerated formato com/sem mascara) |
| D14 uuid-variados | Templated + High-entropy (slots random) |
| D15 base64-variados | Templated (alfabeto + padding) + High-entropy (data) |

Composicao de natures e' visivel: D6 (3 naturezas), D11/D12 (3),
D13 (3), D14/D15 (2 — templated estrutural + entropy nos slots).

## Datasets necessarios pra cobrir gaps

D1-D15 cobrem maioria; gap atual:

- **Lossy-recoverable** — sem dataset. Sugestao: criar `D16 floats-tolerantes` quando T-lossy abrir.

## Conexoes

- [`../../tickets/META-TYPE-ENCODERS.md`](../../tickets/META-TYPE-ENCODERS.md) — plano-mestre
- [`perspectiva-triplice-e-pre-tx.md`](perspectiva-triplice-e-pre-tx.md) — analise das 3 estrategias
- [`../algorithms/OBAT.md`](../algorithms/OBAT.md) — OBAT tokenizer (camada 1, abaixo do pre-tx)
- [`../algorithms/HCC.md`](../algorithms/HCC.md) — HCC composicional (camada 2)

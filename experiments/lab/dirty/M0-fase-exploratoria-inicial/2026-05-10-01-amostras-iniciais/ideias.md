# Catálogo de ideias — tipos de dados

> **A ideia é mais importante que o dado**. Cada seção descreve um
> tipo conceitual, suas variações e a regra de geração. As amostras em
> [`amostras/`](amostras/) são exemplos da regra; [`gerar.py`](gerar.py)
> regenera variantes sob seed.

---

## Eixos transversais

Estes eixos aplicam-se a **todos** os tipos. Toda regra de geração
deve poder controlar cada um deles.

| Eixo | Domínio | Exemplos |
|---|---|---|
| **Cardinalidade** | baixa (≤10), média (10–100), alta (100+), ≈N (única) | sex (2) vs país (40) vs UUID (≈N) |
| **Distribuição** | uniforme, Pareto (1 valor domina), bimodal, gaussiana, cauda-longa | `native-country` é Pareto extremo |
| **Repetição contígua** | runs longos vs fragmentado | dado ordenado tem runs; embaralhado, não |
| **Coerência de formato** | uniforme (todas linhas iguais) vs misto (formatos coexistem na mesma coluna) | telefone com 50% formatado e 50% sem |
| **Encoding** | ASCII puro, UTF-8 com acentos, scripts não-latinos | `José` vs `王明` |
| **Comprimento** | curto fixo, curto variável, longo | `M` vs nome próprio vs comentário |
| **Ausência (NULL)** | 0%, esparsa (<10%), densa (>50%) | survey real é esparsa |
| **Ordem** | sortado (cronológico, lexicográfico), embaralhado | afeta runs RLE |
| **Erros de cadastro** | 0%, raros, frequentes | "não informado", parcial, mascarado |

Regra: **toda amostra grande gerada por `gerar.py` declara explicitamente
seus parâmetros de eixo no início do arquivo** (comentário ou metadado).

---

## 1. Datas e tempos

### 1.1 Datas

**Conceito**: ponto no calendário, sem hora.

**Formatos observados**:
| Variante | Exemplo |
|---|---|
| ISO 8601 | `2026-05-10` |
| BR slash | `10/05/2026` |
| BR hífen | `10-05-2026` |
| US slash | `05/10/2026` |
| Por extenso PT | `10 de maio de 2026` |
| Por extenso EN | `May 10, 2026` |
| Compacto | `20260510` |
| Abreviado | `10 mai 26` |

**Eixos próprios**:
- Granularidade: dia (canônico), mês (`2026-05`), ano (`2026`).
- Range: histórico (1900+), recente (5 anos), futuro.
- Densidade temporal: sequencial denso (toda data da semana),
  esparso (gaps de meses), com clusters (pico em datas comerciais).

**Falhas de cadastro**:
- 29/02 em ano não-bissexto (inválida).
- Mês 13, dia 32.
- Formato misto na mesma coluna.
- "0000-00-00" (placeholder MySQL).
- Datas no futuro improváveis (cadastro com ano errado: `2226`).

**Padrão real**:
- Adult: não há datas (survey atemporal).
- TPC-H: ISO `1992-01-01` a `1998-12-31`, range 7 anos, distribuição
  aproximadamente uniforme (`o_orderdate`, `l_shipdate`).
- Lab old `2026-05-09-delta-datas`: deltas em dias têm 11 valores
  distintos em 29 transições — repetição alta em delta.

**Para que serve testar**: delta encoding, dict de mês/ano, RLE em
mesmo-dia, sortabilidade.

**Regra de geração**:
```
gerar_datas(n, formato, range_inicio, range_fim, densidade, seed)
  - formato ∈ {iso, br_slash, br_hifen, us_slash, extenso_pt, ...}
  - densidade ∈ {sequencial, esparsa, clusters}
  - retorna lista de strings
```

### 1.2 Datas com hora

**Conceito**: ponto temporal com granularidade até segundo (ou fração).

**Formatos observados**:
| Variante | Exemplo |
|---|---|
| ISO com T | `2026-05-10T14:30:00` |
| ISO com espaço | `2026-05-10 14:30:00` |
| ISO com fração | `2026-05-10T14:30:00.123` |
| ISO com Z | `2026-05-10T14:30:00Z` |
| ISO com offset | `2026-05-10T14:30:00-03:00` |
| BR com hora | `10/05/2026 14:30` |
| Unix timestamp | `1746896400` |
| Unix ms | `1746896400123` |

**Eixos próprios**:
- Granularidade: hora, minuto, segundo, fração (3, 6, 9 dígitos).
- Timezone: ausente, Z (UTC), offset numérico, abreviação (`BRT`).
- Sincronização: relógio quebrado, drift.

**Falhas de cadastro**:
- Sem timezone quando deveria ter.
- Mistura de UTC e local na mesma coluna.
- Timestamps em ms vs s misturados.

**Padrão real**:
- TPC-H: apenas data, sem hora.
- Lab old `2026-05-09-tempo-fracoes`: explorou granularidade variável.

**Para que serve testar**: delta em segundos vs delta em dias,
quantização (truncar para minuto/hora antes do dict), separação de
componentes (data + hora em colunas distintas).

### 1.3 Datas relativas

**Conceito**: expressões linguísticas, não absolutas.

**Formatos**: `hoje`, `ontem`, `há 3 dias`, `próxima semana`,
`em 2 horas`, `now()`, `T-1`.

**Para que serve testar**: cardinalidade muito baixa em campo "tempo
de cadastro relativo", dict natural.

---

## 2. Identidade pessoal

### 2.1 Nomes de pessoas

**Conceito**: identificador humano, comprimento variável, com
estrutura cultural.

**Variações**:
| Variante | Exemplo |
|---|---|
| Simples | `Maria` |
| Composto 2 | `Maria Silva` |
| Composto 3+ | `Maria Aparecida da Silva Santos` |
| Com apelido | `Maria "Mari" Silva` |
| Com título | `Sra. Maria Silva`, `Dr. João Souza` |
| Iniciais | `M. A. S. Santos` |
| Com sufixo | `João Silva Jr.`, `Pedro III`, `Carlos Filho` |
| Acentos | `José`, `André`, `Müller` |
| Com apóstrofo | `O'Brien`, `D'Ávila` |
| Não-latino | `王明`, `محمد`, `Иван` |
| Caps | `MARIA SILVA`, `maria silva` |

**Eixos próprios**:
- Cobertura cultural: PT-BR, EN, mistura.
- Padrão de repetição:
  - mesmo primeiro nome, sobrenomes diferentes (clã extenso).
  - mesmo sobrenome, primeiros diferentes (família).
  - duplicatas exatas (homônimos).
- Comprimento: 2–60 chars.

**Falhas de cadastro**:
- Em maiúsculas/minúsculas inconsistente: `MARIA SILVA`, `maria silva`,
  `Maria Silva` no mesmo campo.
- Espaço extra: `Maria  Silva`, ` Maria Silva`.
- Truncado: `Maria Silv` (cortou no insert).
- Junk: `xxx`, `teste`, `aaa`.

**Padrão real**:
- Adult: não há nomes.
- TPC-H: `Customer#000000001` é pseudo-nome com estrutura — ver
  seção 4.1 (IDs com prefixo).
- Lab old: nomes simples (Maria, João, Ana, Carlos) com cardinalidade
  baixa em datasets de 30 linhas.

**Para que serve testar**: dict em campo de cardinalidade alta,
detecção de prefixo/sufixo (sobrenome comum), tratamento de
caracteres especiais.

### 2.2 CPF

**Conceito**: 11 dígitos, com validação de dígito verificador.

**Formatos**:
| Variante | Exemplo |
|---|---|
| Formatado | `123.456.789-09` |
| Sem formatação | `12345678909` |
| Com mascaramento | `***.456.789-**` |

**Falhas de cadastro**:
- `000.000.000-00` (placeholder).
- `111.111.111-11` (sequência repetida — tecnicamente válida em
  dígito mas inválida na origem).
- Parcial: `123.456.7` (truncado).

**Para que serve testar**: estrutura fixa com separadores; em formato
sem máscara, é só um inteiro grande de 11 dígitos.

### 2.3 CNPJ

**Conceito**: 14 dígitos.

**Formatos**:
- Formatado: `12.345.678/0001-90`.
- Sem formatação: `12345678000190`.

**Eixos próprios**:
- Matriz vs filial: sufixo `/0001` = matriz; `/0002` em diante = filial.
- Empresas com várias filiais compartilham 8 dígitos iniciais.

**Para que serve testar**: prefix-DICT em coluna de empresas com
matriz+filiais (compartilham raiz de 8 dígitos).

---

## 3. Contato

### 3.1 Telefones

**Formatos observados**:
| Variante | Exemplo |
|---|---|
| BR celular formatado | `(11) 91234-5678` |
| BR celular sem máscara | `11912345678` |
| BR fixo formatado | `(11) 3456-7890` |
| BR fixo sem máscara | `1134567890` |
| Com +55 | `+55 11 91234-5678` |
| Internacional EUA | `+1 (415) 555-1234` |
| TPC-H style | `25-989-741-2988` |
| Genérico E.164 | `+551191234567` |

**Falhas de cadastro**:
- Vazio.
- "não informado", "N/A".
- Parcial: `(11)`, `12345`.
- Caracteres extras: `(11) 91234-5678 ramal 22`.
- Formato misto na mesma coluna (50% mascarado, 50% não).

**Padrão real**:
- TPC-H: `25-989-741-2988` — formato `NN-NNN-NNN-NNNN` rígido.
- Lab old: telefones BR com falha de cadastro citados em
  `2026-05-08-tipos-restantes-v05`.

**Para que serve testar**: estrutura fixa permite separar componentes
(DDI/DDD/número); mistura de formatos na mesma coluna estressa
detecção de padrão.

### 3.2 Emails

**Formatos observados**:
| Variante | Exemplo |
|---|---|
| Simples | `user@gmail.com` |
| Com ponto | `john.doe@gmail.com` |
| Com tag | `john.doe+promo@gmail.com` |
| Com underscore | `john_doe@gmail.com` |
| Com subdomínio | `user@dept.empresa.com.br` |
| Caps misturado | `John.DOE@Gmail.com` |

**Eixos próprios**:
- Quantidade de domínios distintos (1, 2, 3, ≈N).
- Cobertura de domínio (Pareto vs uniforme).

**Padrão real**:
- TPC-H: não há emails.
- Lab old `2026-05-11-affix-implicit-bidir`: 1 domínio, 2 domínios,
  3 domínios — testou suffix-DICT.

**Para que serve testar**: suffix-DICT em coluna com 1 domínio (caso
canônico); detecção falha em multi-domínio (heurística greedy).

---

## 4. Endereçamento

### 4.1 IDs

**Variantes**:
| Tipo | Exemplo |
|---|---|
| Sequencial puro | `1`, `2`, ..., `100` |
| Com zero-padding | `0001`, `0002`, ..., `0100` |
| Com prefixo fixo | `INV-2026-0001` |
| Estilo TPC-H | `Customer#000000001` |
| UUID v4 | `550e8400-e29b-41d4-a716-446655440000` |
| Hash curto | `a3f1`, `7c2b` (4-8 hex chars) |
| Composto | `ACME-FIN-USER-00` (org-dept-tipo-num) |

**Eixos próprios**:
- Densidade: contíguo (1..N) vs esparso (com gaps).
- Ordem: monotônico vs embaralhado.
- Estrutura interna: prefixo simples vs hierárquico.

**Padrão real**:
- TPC-H: `c_custkey` sequencial monotônico; `Customer#NNNNNNNNN`
  zero-padded de 9 dígitos.
- Lab old `2026-05-20-hierarquia-profunda`: IDs hierárquicos
  ORG×DEPT×USER.

**Para que serve testar**: delta-encoding em sequencial; prefix-DICT
em padded; PATRICIA em hierárquico.

### 4.2 URLs

**Variantes**:
| Tipo | Exemplo |
|---|---|
| Domínio puro | `example.com` |
| Com path raso | `https://example.com/about` |
| Com path profundo | `https://shop.example.com/cat/sub/sub2/item` |
| Com query | `https://api.example.com/v1/users?id=123&fmt=json` |
| Com fragmento | `https://docs.com/page#section` |
| URL-encoded | `https://x.com/path%20with%20spaces` |
| Mesma estrutura, IDs variáveis | `/users/1`, `/users/2`, ... |
| Slugs | `/blog/como-fazer-cafe-frio` |
| Multi-domínio | mistura de `gmail.com`, `yahoo.com`, ... |

**Eixos próprios**:
- Profundidade de path (1 a 6).
- Repetição de domínio.
- Query string presente / ausente.
- Padrão hierárquico (prefixos compartilhados em PATRICIA).

**Padrão real**:
- Adult, TPC-H: não têm URLs.
- Lab old `2026-05-17-arvore-patricia` e `2026-05-20-hierarquia-profunda`:
  URLs hierárquicas testaram PATRICIA tree.

**Para que serve testar**: PATRICIA em hierárquico; prefix em
domínio comum; alta entropia em query string (não comprime).

### 4.3 Endereços

**Componentes**:
| Componente | Exemplo BR | Exemplo US |
|---|---|---|
| CEP / ZIP | `01310-100` | `94103` |
| CEP sem máscara | `01310100` | — |
| Logradouro | `Av. Paulista` | `Market Street` |
| Número | `1578` | `123` |
| Complemento | `Apt 42`, `S/N` | `Apt 4B` |
| Bairro | `Bela Vista` | — |
| Cidade | `São Paulo` | `San Francisco` |
| UF / State | `SP` | `CA` |

**Falhas de cadastro**:
- "S/N" (sem número).
- Complemento em campo errado.
- CEP misturando formatado e não-formatado.

**Para que serve testar**: dict em UF/Estado (alta repetição); prefix
em CEP (regiões compartilham 5 primeiros dígitos).

---

## 5. Comerciais

### 5.1 Produtos

**Variantes**:
| Tipo | Exemplo |
|---|---|
| Nome simples | `Caneta`, `Caderno` |
| SKU | `PRD-2026-00123` |
| Hierárquico | `Eletrônicos > TV > LED 50"` |
| Com marca + modelo | `Samsung Galaxy S23`, `Samsung Galaxy A14` |
| Com variante | `Camiseta Azul M`, `Camiseta Azul G` |
| Internacional | `Apple iPhone 15`, `iPhone 15` (mesmo produto, nomes diferentes) |

**Eixos próprios**:
- Repetição exata vs com variação (`Galaxy s23` vs `Galaxy S23`).
- Hierarquia: profundidade de 1 a 4 níveis.
- Vocabulário compartilhado entre linhas (marca, categoria).

**Padrão real**:
- Adult: não tem.
- TPC-H: tabela `part` (não amostrada) tem nomes procedurais com
  prefixos de cor + tipo.
- Lab old `2026-05-07-combinatoria-simples`: 8 categorias com
  cardinalidade fixa, repetição contígua quando sortado.

**Para que serve testar**: dict de marca/categoria, RLE quando
sortado por categoria, prefix em SKU.

### 5.2 Valores monetários

**Formatos**:
| Variante | Exemplo |
|---|---|
| BR | `R$ 1.234,56` |
| US | `$1,234.56` |
| ISO 4217 | `BRL 1234.56`, `USD 1234.56` |
| Sem moeda | `1234.56` |
| Com sinal | `+1234.56`, `-50.00` |
| Notação científica | `1.234e3` |
| Centavos como inteiro | `123456` (representa R$ 1234.56) |

**Eixos próprios**:
- Range: pequeno (centavos) vs grande (milhões).
- Precisão: 2 casas vs mais.
- Distribuição: uniforme vs cauda longa (poucos valores muito altos).
- Bimodalidade: muitos zeros + alguns altos (capital-gain do Adult).

**Padrão real**:
- Adult `capital-gain`/`capital-loss`: bimodal extremo, >90% zeros.
- TPC-H `o_totalprice`: ~$10k–$500k, distribuição cauda longa.
- TPC-H `c_acctbal`: pode ser negativo.

**Para que serve testar**: RLE em zero (capital-gain), dict em
quantizado (discount, tax), delta em sequencial (`acctbal` por mês),
representação como inteiro de centavos vs decimal.

---

## 6. Categóricos

### 6.1 Booleans

**Representações**:
- `true`/`false`, `True`/`False`
- `1`/`0`
- `S`/`N`, `Y`/`N`
- `sim`/`não`
- `ativo`/`inativo`
- com NULL no meio (ternário implícito)

**Para que serve testar**: dict cardinalidade 2 (caso ótimo); decisão
de NÃO usar dict quando valores já são 1 char.

### 6.2 Enums

**Categorização por cardinalidade**:
| Cardinalidade | Exemplo |
|---|---|
| 2 | sex (M/F), boolean |
| 3–10 | mktsegment TPC-H, marital-status |
| 10–50 | UF brasileiros (27), education (16), states US (50) |
| 50–500 | países (~250), cidades capitais |
| 500+ | já é alta cardinalidade, não enum prático |

**Distribuição**:
- Uniforme: cada valor ~igualmente frequente.
- Pareto: 1 valor domina (>80%).
- Bimodal: 2 valores dominam.

**Estrutura interna**:
- Simples: `BUILDING`, `MACHINERY`.
- Hifenizado: `Married-civ-spouse`, `Some-college`.
- Com prefixo numérico: `5-LOW`, `1-URGENT` (TPC-H).
- Com espaços: `REG AIR`, `DELIVER IN PERSON`.
- Com case mix: `Male`/`Female` vs `MALE`/`FEMALE`.

**Falhas de cadastro**:
- Vazios (workclass do Adult).
- Variações de spelling: `Male`, `male`, `M`.
- Valor "Outro" / "Other" como catch-all.

**Padrão real**:
- Adult: enums diversos com vazios.
- TPC-H: enums limpos, sem vazios.

**Para que serve testar**: dict em variações de cardinalidade,
distribuição Pareto força repetição contígua quando sortado.

---

## 7. Numéricos

### 7.1 Inteiros

**Categorias**:
| Tipo | Range | Exemplo |
|---|---|---|
| Pequeno bounded | 0–100 | idade, hours-per-week |
| Médio | 0–10⁶ | fnlwgt, custkey |
| Grande | 10⁶+ | timestamps, IDs UUID-like |
| Negativo permitido | qualquer sinal | acctbal |
| Bimodal com zero | maioria 0 | capital-gain |

**Eixos próprios**:
- Sequencial vs aleatório.
- Padding implícito (sempre 4 dígitos) vs largura variável.
- Presença de sinal.

### 7.2 Decimais

**Categorias**:
| Tipo | Exemplo |
|---|---|
| Quantizado | `0.00`, `0.01`, ..., `0.10` (discount) |
| Monetário 2 casas | `1234.56` |
| Medida científica | `3.14159265` |
| Percentual | `0.85`, `85%`, `85.0%` |
| Notação E | `1.5e-3` |

**Falhas de cadastro**:
- Casas decimais inconsistentes: `3.0` vs `3.00` vs `3` no mesmo campo.
- Separador decimal misto: `3.14` vs `3,14`.
- Notação científica em alguns, decimal em outros.

**Para que serve testar**: quantização para baixar cardinalidade,
representação como inteiro escalado, RLE em quantizado.

---

## 8. Espécies (nomes científicos vs comuns)

**Variantes**:
| Tipo | Exemplo |
|---|---|
| Comum (PT) | `Maçã` |
| Comum (EN) | `Apple` |
| Científico binomial | `Malus domestica` |
| Variedade | `Maçã Fuji`, `Maçã Gala`, `Maçã Verde` |
| Comum + variedade | `Apple - Fuji` |
| Misto | dataset com algumas linhas em comum, outras em científico |

**Eixos próprios**:
- Cardinalidade do gênero (Malus pode ter 30 espécies).
- Repetição de gênero (compartilhamento em prefix-DICT natural).

**Para que serve testar**: prefix-DICT em coluna de espécies (mesmo
gênero compartilha primeira palavra); contraste lossy (variedade
ignorada se quantizada).

---

## 9. Texto livre

**Categorias**:
| Tipo | Exemplo |
|---|---|
| Curto | `OK`, `Pendente`, `Cancelado` (mas é enum, não livre) |
| Médio | assunto de email (~50 chars) |
| Longo | comentário/descrição (~200+ chars) |
| Bilíngue | mistura PT+EN |

**Padrão real**:
- TPC-H `c_comment`, `o_comment`, `l_comment`: ~50–80 chars,
  procedural, com pontuação variada (`,`, `.`, `?`, `:`).

**Para que serve testar**: alta entropia, baixa compressibilidade
estrutural; serve para validar que algoritmo NÃO afirme ganho onde
não há.

---

## 10. Ausência (NULL)

**Representações observadas**:
| Forma | Onde aparece |
|---|---|
| Vazio `""` | Adult Census workclass |
| `NULL` literal | dump SQL |
| `null` | JSON |
| `N/A` | survey export |
| `NA` | R, abreviado |
| `?` | UCI ML datasets antigos |
| `não informado` | sistemas BR |
| whitespace `" "` | bug de export |
| `-` | sistemas legacy |

**Eixos próprios**:
- Frequência: 0%, esparsa (<10%), densa (>50%).
- Clustering: NULLs contíguos (dataset com colunas opcionais
  preenchidas em ondas) vs aleatórios.

**Para que serve testar**: RLE em coluna sparse (>70% NULL ganha
muito); dict trata NULL como valor especial (idx reservado).

---

## Síntese — agrupamento por algoritmo de compressão

Para um experimento futuro decidir qual tipo testar com qual algoritmo:

| Algoritmo | Tipos onde tem possibilidade de vantagem |
|---|---|
| **RLE em valor** | Booleans, enums baixa cardinalidade quando sortados, NULL denso, capital-gain (zero majoritário) |
| **DICT (substituição por idx)** | Enums todos, países, UF, marcas, categorias |
| **Prefix-DICT** | IDs com prefixo (`Customer#NNN`), CNPJ matriz/filial, espécies (gênero), URLs (domínio) |
| **Suffix-DICT** | Emails 1 domínio |
| **Delta encoding** | IDs sequenciais, datas ISO em série, timestamps Unix, valores monotônicos |
| **PATRICIA tree** | URLs hierárquicas, IDs hierárquicos, paths de arquivo |
| **Quantização** | Discount/tax (já quantizado), medidas com precisão excessiva |
| **Não comprime (caso de controle)** | UUIDs, hashes, endereços de alta entropia, comentário texto livre |

Cada experimento posterior escolhe **uma combinação tipo × algoritmo**
e usa este catálogo para gerar entrada controlada.

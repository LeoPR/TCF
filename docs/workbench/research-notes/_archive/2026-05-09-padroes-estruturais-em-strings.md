# Padroes estruturais em strings — onde affix-DICT e variantes valem

**Data**: 2026-05-09
**Origem**: insights do user durante revisao de EXP-005

## Insight 1 — Datasets pequenos sao refens do header

Em datasets muito pequenos (D1: 50 rows, D5: 59 rows), header eh
**fracao significativa** do payload. Pouco a explorar em compressao
real — o que importa eh **organizacao do formato** (estrutura colunar
+ ordem) mais que ganho de bytes.

Decisao didatica: **datasets pequenos servem para entender DINAMICA
da compressao**, nao para julgar ganho absoluto. Eles mostram:
- Como o formato se comporta em escala minuscula
- Onde overhead domina
- Limiar de equilibrio (quando TCF empata com CSV)

Para julgar ganho real, ir para datasets medio/grande (D2: 1000 rows
deu -98%; D6: 1100 rows multi-tabela deu -35%).

## Insight 2 — Padroes estruturais em strings (alem de prefix)

Identificadores estruturados aparecem em muitos dominios reais:

| Tipo | Exemplo | Padrao | Estrategia |
|------|---------|--------|-----------|
| **CPF** | `123.456.789-00` | `XXX.XXX.XXX-XX` (3+1+3+1+3+1+2 chars com `.` e `-`) | extrair separadores fixos + so dígitos |
| **CNPJ** | `12.345.678/0001-90` | `XX.XXX.XXX/XXXX-XX` (similar) | idem CPF |
| **UUID** | `f47ac10b-58cc-4372-a567-0e02b2c3d479` | 8-4-4-4-12 hex com `-` | extrair `-` fixos, so hex |
| **Data ISO** | `2026-05-09` | `YYYY-MM-DD` | flag δ (delta) ou separadores fixos |
| **Hora** | `14:30:00` | `HH:MM:SS` | separadores fixos `:` |
| **Codigo PED** | `PED-2026-0001` | prefixo + serie | flag P (prefix elision) |
| **MAC** | `00:1A:2B:3C:4D:5E` | hex com `:` | separadores fixos |
| **IP v4** | `192.168.1.100` | 4 octetos com `.` | separadores + nums |
| **EAN-13** | `7891000100103` | 13 digitos puros | apenas digitos (sem separadores) |
| **Email** | `user@dominio.com` | local@dominio | dominio compartilhado (cluster) |

### Estrategia generica — "estrutura ortogonal ao valor"

Em vez de tratar cada string como opaca, o formato pode declarar:

```
col_X: pattern="<MASCARA>"
<so a parte variavel>
<so a parte variavel>
...
```

Mascara descreve onde estao os separadores fixos. Body emite so a
parte variavel (digitos puros ou hex).

**Exemplo CPF**:
```
cpf: pattern="XXX.XXX.XXX-XX"
12345678900   ← decoder reconstroi como 123.456.789-00
98765432100   ← decoder reconstroi como 987.654.321-00
```

Economia: 4 chars de separador por linha × N linhas. Em 1000 CPFs,
4000 bytes economizados.

**Exemplo UUID**:
```
uuid: pattern="XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
f47ac10b58cc4372a5670e02b2c3d479
abc12345def67890fed12345abc56789
```

4 hifens por linha × N linhas.

### Indicador "quando aplicar"

User propos: cada coluna pode ter indicador que diz quando o padrao
se aplica vs quando o decoder deve ler literal.

Possibilidades:
1. **Sempre** (default quando coluna eh uniforme): `col: pattern="..."`
2. **Excecoes marcadas**: linhas com `\!<full>` sao literais, nao seguem padrao
3. **Per-row marker**: opt-in linha-a-linha (raro, custoso)

Default proposto: opcao 1 + 2 (coberto pela mesma logica do affix).

## Insight 3 — Generalizar affix → "structural-DICT"

A flag P (prefix elision) atual cobre so prefixo comum simples:
```
col: affix="PROD-2026-"
0001
0002
```

A generalizacao seria:
```
col: pattern="<MASCARA>"
<so as partes variaveis>
```

Onde mascara pode incluir:
- Prefixo fixo
- Separadores intermediarios (`-`, `.`, `:`, `/`, `@`)
- Sufixo fixo

Mas mascara generica eh **complexa de detectar automaticamente**. A
versao simples (so prefixo) ja captura uma fatia grande dos casos
reais (codigos sequenciais, URLs, datas com prefixo de mes/ano).

### Decisao de implementacao por etapas

1. **Etapa 1 (agora)**: Affix-DICT simples (so prefixo) — flag P
   - Detecta LCP (longest common prefix)
   - Threshold: `|P| ≥ 4 chars` E `cobertura ≥ 70%`
   - Auto-bypass quando nao vale (`|P| < 4` ou cobertura baixa)
2. **Etapa 2 (futuro)**: Sufixo (P-suffix ou flag separada)
   - Email: `@dominio.com` comum
   - URLs: `.html` comum
3. **Etapa 3 (futuro)**: Mascaras estruturais (X.X.X-X)
   - CPF, UUID, IP, MAC, etc.
   - Detecta em datasets reais; protótipo apenas
4. **Etapa 4 (futuro, talvez nao)**: Dialetos por dominio
   - "tipo CPF" detectado, encoder aplica regra fixa
   - Risco: vira lista interminavel de dialetos

Etapas 3+ entram **so se** datasets reais mostrarem ganho. Caso
contrario, gzip do transporte resolve.

## Pendencias registradas

- Etapa 1 (Affix-DICT prefix only) — implementar agora
- Etapa 2 (Affix-DICT suffix) — backlog
- Etapa 3 (mascaras estruturais) — backlog, depende de evidencia em
  datasets reais
- Aplicar em D5 (TPC-H supplier `Supplier#NNN`) e ver ganho real

## Datasets reais com padroes (para testes)

- **TPC-H supplier.s_name** — `Supplier#000000NNN`, prefixo claro
- **TPC-H part.p_name** — descricoes, sem padrao obvio
- **TPC-H lineitem.l_shipinstruct** — categoricas (poucos valores)
- **Adult Census** — categoricas mas sem prefixo estruturado
- **Datasets sinteticos** — gerar com `PROD-2026-NNNN`, UUIDs, CPFs

## Conclusao

A insight do user (alem do affix simples) eh real e importante. **Cada
classe de identificador estruturado tem padrao explorável**. Mas
implementar tudo de uma vez complicaria o formato. Estrategia:
- Comecar simples (Affix prefix only)
- Medir em datasets reais
- Estender so quando evidencia justificar

Para a etapa 1 (agora), o desenho do encoder ja sera **extensivel**:
o conceito de "modificador per-coluna" (`col: <modifier>`) acomoda
prefix/suffix/pattern futuramente sem quebrar gramatica.

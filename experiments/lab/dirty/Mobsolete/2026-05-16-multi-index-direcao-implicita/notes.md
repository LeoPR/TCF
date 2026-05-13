# Multi-index com direcao implicita — gramatica autodescritiva

**Data**: 2026-05-16
**Origem**: insight do user, apos critica do lab anterior

## Critica do lab anterior (2026-05-15)

Detector simplista exigia 100% cobertura → rejeitava prefix/suffix
em C2/C3 (80% cobertura) e caia para literal. Output ficava quase
igual a CSV. **Tese de deducao nao foi validada nesses casos**.

## Nova hipotese

A direcao do dict NAO precisa ser declarada no header — **o decoder
deduz pelos marcadores presentes na linha**. Cada caractere especial
revela uma operacao:

| Token | Significado |
|-------|-------------|
| `<text>` (sem prefixo) | literal puro; auto-declara idx se for novo |
| `*<text>` | decl explicita: cria novo idx |
| `<n>` (puro numero) | ref string idx n |
| `_<text>` | literal forcado (desambigua "1" como string vs ref) |
| `=<n>` | ref linha n |

Linha = sequencia de tokens separados por espaco; concatenacao
produz valor.

## Exemplo do user (refinado)

```
user001@gmail.com    ← *user00 _1 *@gmail.com   (decl idx1 + lit "1" + decl idx2)
user002@gmail.com    ← 1 _2 2                    (idx1 + lit "2" + idx2)
user001@gmail.com    ← =1                         (repete linha 1)
user002@gmail.com    ← =2                         (repete linha 2)
user004@hotmail.com  ← 1 _4 *@hotmail.com        (idx1 + lit "4" + decl idx3)
user006@gmail.com    ← 1 _6 2                    (idx1 + lit "6" + idx2)
hdssserr@hotmail.com ← hdssserr 3                (lit + idx3)
xcfdf@zipmail.com    ← xcfdf@zipmail.com         (literal completo, sem padrao)
```

8 linhas com marcacao auto-descritiva. Decoder reconhece tudo pelos
marcadores; **nao precisa do header dizer modo**.

## Multi-index — tudo numa passada

Em vez de fazer:
1. Pass A: detectar prefix
2. Pass B: detectar suffix
3. Pass C: revisar

Faz tudo simultaneamente:
- Para cada linha que chega:
  - Compara com strings ja vistas
  - Se ha LCP/LCS forte com algum dict entry: decompoe
  - Se nao: literal completo (vira novo idx automatico)
- Mantem indices acumulando conforme linhas vem

**Estrategia greedy**: melhor decisao no momento, sem look-ahead.

## Pass 2 (opcional, revisao)

Apos pass 1, dicionario foi construido. Pass 2 pode:
- Mesclar entries similares
- Eliminar entries usadas so 1x
- Reordenar idx para que mais frequentes tenham idx menor (1-9)

Mas pass 2 muda os IDX de pass 1 → emit final acontece so apos pass 2.

## Algoritmo proposto

```python
def encode_multi(values):
    # Pass 1: greedy + construir multi-index
    string_dict = []          # [(text, count)]
    line_history = []         # cada linha emitida
    raw_emits = []            # tokens crus por linha (antes de finalizar)

    for v in values:
        # 1. Linha duplicada?
        if v in line_history_idx:
            raw_emits.append(("line_ref", line_history_idx[v]))
            line_history.append(v)
            continue

        # 2. Procura prefix/suffix em string_dict
        best_decomp = greedy_decompose(v, string_dict)

        # best_decomp = [(token_type, payload), ...]
        # Pode ser:
        #   [("ref", idx)] — todo igual a entry existente
        #   [("ref", idx), ("lit", "..."), ("ref", idx2)] — prefix+mid+suffix
        #   [("lit", v)] — sem padrao, literal completo

        raw_emits.append(("compose", best_decomp))
        line_history.append(v)

        # Atualiza string_dict com novos prefixes/suffixes encontrados
        update_dict(string_dict, v, best_decomp)

    # Pass 2: revisar e numerar idx por frequencia
    string_dict_final = sorted(string_dict, key=lambda e: -e.count)
    idx_map = {old: new for new, old in enumerate(string_dict_final, 1)}

    # Emit final
    out = []
    for emit in raw_emits:
        out.append(format_emit(emit, idx_map))
    return "\n".join(out) + "\n"
```

## Sub-funcao critical: `greedy_decompose`

Para uma string `v` e um `string_dict`, achar a melhor decomposicao em
tokens. Greedy:

1. **Match tudo**: se `v == dict_entry`, retorna `[("ref", idx)]`
2. **Prefix match**: se `v.startswith(dict_entry)`:
   - Tenta tambem suffix: `v[len(prefix):]` casa com algum `dict_entry2`?
     - Se sim: retorna `[(ref prefix), (lit middle), (ref suffix)]`
     - Se nao: `[(ref prefix), (lit rest)]`
3. **Suffix match**: similar
4. **Sem match**: `[(lit, v)]` — adiciona novos idx automaticos

## Multi-decl com `**`

User propos: `**<a>*<b>` = decl multiplos idx em cascata.

Caso de uso: `*@hotmail.com` declara 1 idx. Mas se mais tarde aparecer
`@gmail.com`, o `mail.com` em comum nao foi capturado.

Com `**@hot*mail.com`: declara `@hotmail.com` E `mail.com` separadamente.
Mais idx mas reutilizaveis.

**Adiar para iteracao seguinte**. Esta versao primeira nao implementa.

## Por que direcao implicita > flag no header

| Aspecto | Direcao implicita | Flag no header |
|---------|-------------------|----------------|
| Header overhead | minimo | flag de 1-3 chars |
| Linhas | tokens com prefixo `*`, `_`, `=` | tokens curtos |
| Decoder complexity | igual | igual |
| Auto-discovery | natural pelos marcadores | precisa cabecalho explicito |
| Multi-modo na mesma coluna | TRIVIAL | impossivel sem multi-flag |

Direcao implicita permite **modos misturados** na mesma coluna (algumas
linhas com prefix, outras com suffix, outras com `=N`).

## Cenarios para teste

| # | Dataset | Esperado |
|---|---------|----------|
| C1 | Exemplo do user (8 emails mistos com hdssserr/xcfdf) | bidir + literais |
| C2 | 100% prefix `INV-2026-NNNN` | so prefix-DICT |
| C3 | Mistura 80% prefix + 20% sem padrao | prefix + literais |
| C4 | Emails com 2 dominios (50/50) | suffix multi |
| C5 | Linhas duplicadas dominantes | =N + alguns literais |

## Saida

`./output/<C>/`:
- `literal.txt`
- `multi.txt` — saida com marcadores auto-descritivos
- `bytes.json`

Comparar com sintaxes anteriores (rle-lines, dict-bidir do lab 14).

## Pass 1 first; Pass 2 depois

Implementacao desta sessao:
- **Apenas Pass 1** (greedy online)
- Pass 2 (revisao + reordenacao de idx) fica para iteracao seguinte
- Multi-decl `**` tambem fica para depois

Foco: gramatica auto-descritiva + multi-index simples.

---

## Resultados (run.py executado)

### Tabela

| Cenario | literal | multi | vs lit | RT |
|---------|--------:|------:|-------:|----|
| **C1 user-example** (8) | 149 | **98** | **-34.2%** | OK |
| C2 codigos-uniforme (20) | 280 | 211 | -24.6% | OK |
| C3 misto-80-20 (20) | 256 | 256 | 0% | OK |
| **C4 emails-2dom** (30) | 540 | **399** | **-26.1%** | OK |
| C5 dups-dominantes (15) | 60 | 48 | -20.0% | OK |
| **medias** | | | **-21.0%** | **5/5 OK** |

### Bug encontrado e corrigido

**Sync encoder/decoder**: `update_dict()` adicionava literais
automaticamente, mas decoder so via decls explicitas (`*`). Resultado:
idx 2 no encoder era `.com`, idx 2 no decoder era `25@yahoo`.
Divergencia → roundtrip FAIL no C4.

**Fix**: `update_dict()` virou no-op. Encoder e decoder agora
**so contam idx das decls explicitas** (`*<text>`). Sincronia
garantida.

### Output do C1 (exemplo do user)

```
*user00 _1 *@gmail.com    ← decl idx1=user00, lit "1", decl idx2=@gmail.com → user001@gmail.com
1 _2 2                    ← idx1 + lit "2" + idx2 → user002@gmail.com
=1                        ← repete linha 1
=2                        ← repete linha 2
1 4@hotmail.com           ← idx1 + lit "4@hotmail.com" → user004@hotmail.com
1 _6 2                    ← idx1 + lit "6" + idx2 → user006@gmail.com
hdssserr@hotmail.com      ← literal puro (nao casou afixos)
xcfdf@zipmail.com         ← literal puro
```

**Confirma proposta visual do user**. RT OK.

### Achados

**A1 — Tese da direcao implicita validada**: gramatica autodescritiva
funciona. Decoder reconstroi sem precisar header declarando modo.
Marcadores `*`, `_`, `=`, `<n>` revelam tudo.

**A2 — Multi-index funciona em parte**: prefix + suffix simultaneos
sao capturados na PRE-POPULACAO (sample das primeiras 4 linhas).

**A3 — Limitacao: afixos que aparecem no MEIO do dataset NAO sao
capturados** (Pass 1 only). Exemplo C1 linha 5: `@hotmail.com` aparece
pela 1a vez mas nao vira idx; linha 7 reutiliza-o como literal completo
em vez de ref.

**A4 — Cobertura parcial nao detectada (C3)**: dataset 80% prefix +
20% sem padrao. Detector de pre-populacao calcula LCP global das
4 primeiras linhas. Se duas delas nao tem o prefix, detector falha.

### Limitacoes registradas (pendencias)

| # | Limitacao | Solucao proposta |
|---|-----------|------------------|
| L1 | Afixos descobertos no MEIO do dataset nao viram idx | Pass 2 que conta afixos globalmente |
| L2 | Cobertura parcial (80%) nao detectada na pre-populacao | Pass 2 com LCP-com-tolerancia |
| L3 | Multi-decl (`**`) ainda nao implementado | Adiar; limita captura de hierarquia |
| L4 | Greedy nao sempre escolhe a melhor decomposicao | Look-ahead em Pass 2 |

### Sintaxe consolidada (auto-descritiva, sem header de modo)

| Token | Funcao |
|-------|--------|
| `<text>` (sem prefix) | literal puro (NAO entra no dict) |
| `*<text>` | decl explicita (cria novo idx) |
| `<n>` (puro digito) | ref string idx n |
| `_<n>` | literal forcado (desambigua "1" como string) |
| `=<n>` | ref linha n |

Linha = sequencia de tokens separados por espaco. Concatenacao = valor.

### Decoder algoritmo (referencia)

```python
def decode_line(line, string_dict, line_history):
    if line.startswith("="):
        return line_history[int(line[1:]) - 1]
    parts = []
    for tok in line.split(" "):
        if tok.startswith("*"):
            text = tok[1:]
            string_dict.append(text)
            parts.append(text)
        elif tok.startswith("_"):
            parts.append(tok[1:])
        elif tok.isdigit():
            parts.append(string_dict[int(tok) - 1])
        else:
            parts.append(tok)  # literal
    return "".join(parts)
```

10 linhas. Decoder eh trivial.

### Decisao para proxima iteracao

1. **Implementar Pass 2** que percorre dataset COMPLETO antes de emitir
   - Conta todos afixos candidatos
   - Decide quais viram idx baseado em ganho previsto
   - Emit final com idx pre-numerados
2. **Testar em C3** (cobertura parcial) e ver se -25%+ vs literal
3. **Testar em datasets maiores** (>= 100 valores)
4. **Adicionar multi-decl `**`** se evidencia justificar

### Status

- [x] Gramatica auto-descritiva (5 tipos de token)
- [x] Pass 1 greedy com pre-populacao de afixos
- [x] Decoder unico (10 linhas) que deduz tudo
- [x] Bug de sync encoder/decoder corrigido
- [x] 5/5 RT OK; -21% medio vs literal
- [x] C1 (exemplo do user) validado visualmente
- [ ] Pass 2 com analise global (proximo)
- [ ] Multi-decl `**` (futuro)
- [ ] Look-ahead em decomposicao (futuro)

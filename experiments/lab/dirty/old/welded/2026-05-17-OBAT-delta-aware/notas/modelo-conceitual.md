# Modelo conceitual — Pre / OBAT / HCC com peso relativo vs absoluto

**Data**: 2026-05-17 (revisado pos-baseline + discussao de framing)
**Status**: hipotetico. Modelos abaixo serao informados/refutados
pelas tentativas 02/03/04. Mantido como referencia evolutiva.

## Tripartição

Pre / OBAT / HCC tem responsabilidades distintas. O **tipo de peso**
que cada um exerce e o que separa naturalmente a linha cinzenta.

| Camada | Responsabilidade | Tipo de peso | Conhece tipo? |
|---|---|---|---|
| **Pre** | Detectar tipo + gerar **dica generica** | Analise (nao emite bytes) | Sim |
| **OBAT** | Comparacoes relativas + decidir se quebra | Pesos relativos (cabe/nao-cabe) | Nao (so' modos calibrados pela dica) |
| **HCC** | Materializar marcadores + juntar inteligentemente | Pesos absolutos (bytes no body) | Nao |

### O ponto-chave: marcadores abstratos vs. peso absoluto

OBAT ja' opera assim hoje:
- `TokRefPref(string_id, length)` e' **abstrato** — nao sabe quantos
  bytes vai custar no body
- Decisao de "qual ref escolher" e' por **comprimento relativo** — o
  maior LCP/LCS vence, independente de bytes finais
- HCC depois decide a representacao concreta (`~`, `^N`, `*N|`, etc.)

Estender pra delta segue o mesmo padrao:
- OBAT emite metadata abstrata ("este literal varia por +1 relativo ao
  predecessor no mesmo lugar")
- HCC decide se isso vira: nada (descarta metadata), serializacao
  inline, RLE compacta, virtual ref dedicada

OBAT **nao nomeia** o delta como "+1 dia". Isso seria peso absoluto
(semantica fixada). OBAT so' constata "+1 unidade na regiao variavel"
— relativo, abstrato.

## A dica generica (vs. viciada)

Restricao critica: a dica do pre-stage **nao pode dizer "voce e' uma
data"**. Isso violaria o type-agnosticismo do OBAT.

Dicas genericas aceitaveis (espectro):
- `byte_window=(X,Y)` — onde provavelmente esta a variacao
- `enable_relative=True` — habilitar comparacao quanto-maior/quanto-menor
- `monotonic_expected=True` — esperar sequencia ordenada
- `max_delta=N` — limiar pra emitir delta vs. literal

Dicas viciadas (rejeitar):
- `type="date"` — viola separacao
- `parse_as_datetime=True` — viola separacao
- `calendar_unit="day"` — viola separacao

**Linha movediça**: `byte_window` parece neutra mas pode ser viciada
disfarcada (se Pre detectou "data ISO" pra computar a janela, a info
escorrega indiretamente). Por enquanto, aceitar: o canal e' generico
mesmo se a fonte foi tipo-aware. O que importa e' o que OBAT recebe.

## Como o "barateamento" acontece (revisado)

Exemplo do user (originalmente): "se ele ver que e' incremental so' do
ultimo digito, esse digito deixa de ser ascii puro, ele pode ganhar
um marcador mais barato".

Traducao em termos de tripartição:

| Camada | Acao |
|---|---|
| Pre | Detecta cadencia regular na coluna → emite `enable_relative=True` |
| OBAT | Compara linha N com N-1; literal variavel = +1 unidade → emite `TokLit("1", rel=+1)` |
| HCC | Ve 9 tokens com `rel=+1` consecutivos → RLE-agrupa em forma compacta |

Bytes:
- Sem agregacao: 9 linhas × ~10 bytes = 90 bytes
- Com RLE: 1 forma compacta `*9|<estrutura>+1` ≈ 12-15 bytes

**Barateamento e' por agregacao no HCC**, nao por substituicao
linha-a-linha no OBAT. Validar em tentativa 02 (HCC sozinho) e 04
(integrado).

## Nova hipotese (registrada 2026-05-17)

> Se um no e' quebrado onde tem diferenca, talvez o unico esforco
> depois seja verificar se essa diferenca **faz parte da estrutura
> anterior** e como otimiza-la. OBAT pode estar quase pronto.

Implicacao: OBAT ja' isola a variacao automaticamente (Pref + **Lit**
+ Suf — o Lit e' exatamente a diferenca). O trabalho restante e':

1. Pegar o Lit isolado (ja' feito por OBAT)
2. Verificar: este Lit faz parte de uma sequencia/estrutura observada
   antes? (trabalho novo)
3. Se sim, como representar mais barato? (trabalho novo, possivelmente
   HCC)

Esta hipotese **fortalece a tentativa 02** (HCC sozinho): se OBAT ja'
quebra no lugar certo, talvez HCC sozinho consiga reconhecer o padrao
nas sequencias de Lits isoladas.

## Tentativas praticas planejadas

### Tentativa 02 — HCC sozinho

Sem mexer em OBAT. HCC detecta: N linhas com mesma estrutura de
tokens, **so' literal varia**. Encoda como run compacto.

**Hipotese**: alinhada com "OBAT esta quase pronto". Se HCC sozinho
resolve, OBAT nao precisa mudar.

### Tentativa 03 — OBAT com dica "janela de busca"

Pre detecta byte window de variacao. OBAT recebe `byte_window=(X,Y)`,
calibra LCP/LCS pra focar la'. Zero conhecimento de tipo.

**Hipotese**: valida que pre-stage gera dica util sem nomear tipo.

### Tentativa 04 — OBAT com modo relativo

Pre habilita modo relativo. OBAT calcula Δ vs literal correspondente
do predecessor. Emite `TokLit(text, rel=+N)`. HCC RLE-agrupa por rel.

**Hipotese**: comparacao relativa + RLE inteligente = ganho mensuravel.

## Linhas cinzentas que vao tomar forma com os experimentos

| Linha cinzenta | Tentativa que clarifica |
|---|---|
| HCC sozinho consegue agrupar near-identical? | 02 |
| Dica generica e' realmente util? | 03 |
| Onde fica o "decidir se emite delta"? | 04 |
| Como o decoder reconstroi sem tipo explicito? | 04 (decoder espelho) |
| Memoria O(1) sobrevive a comparacao relativa? | 03 + 04 (medir) |

## O que **nao** vai ser explorado (out-of-scope)

- Multi-coluna delta-aware (uma natureza por vez)
- Auto-deteccao no OBAT sem hint (viola separacao)
- Tipos estruturados de delta com unidade semantica (viola
  "OBAT nao nomeia")
- Look-ahead no OBAT (viola single-pass)
- Buffer > O(1) no OBAT (viola low-mem)

## Documentacao continua

Resultados das tentativas em `observacoes.md` (diario). Conclusoes
estaveis migram pra esta nota conforme se sedimentam.

# Affix implicito bidirecional — variante avancada da flag P

**Data**: 2026-05-11
**Origem**: proposta do user durante revisao do EXP-006

## Proposta

Em vez de declarar affix no header da coluna (`col: affix="..."`),
fazer **inline com o body** usando espaco interno como marcador
e direcao via marcador no col header.

### Sintaxe proposta

```
column,>:           ← > indica prefix
<var> <affix-decl>  ← linha com 1+ espaco interno declara affix
<var>               ← linha sem espaco usa o ULTIMO affix declarado
<var> <idx>         ← linha com numero apos espaco refencia affix idx
```

`>` = prefix (affix vai antes da var)
`<` = suffix (affix vai depois da var)

### Disambiguacao da parte 2

Quando linha tem espaco interno, a parte 2 pode ser:
- **Numero puro** (regex `^\d+$`) → ref a affix declarado anterior (1-based)
- **Qualquer outra coisa** → declaracao de novo affix

Limitacao conhecida: affixes puramente numericos nao funcionam (raro).

### Exemplos

#### Prefix uniforme

```
codigo,>:
INV-2026-00 011        ← declara affix idx 1 = "INV-2026-00"
021                     ← INV-2026-00021
058
001
```

#### Suffix com 2 dominios mistos

```
email,<:
ana @gmail.com          ← declara affix idx 1 = "@gmail.com"
bruno                   ← bruno@gmail.com
carlos @yahoo.com       ← declara affix idx 2 = "@yahoo.com"
diana                   ← diana@yahoo.com
ana 1                   ← ana@gmail.com (ref idx 1)
ana 2                   ← ana@yahoo.com (ref idx 2)
```

#### Multiplos prefixes em codigo

```
codigo,>:
INV-2026- 0001          ← affix idx 1
0002
PED-2026- 0001          ← affix idx 2 (NOVO)
0002
1 0010                  ← INV-2026-0010 (var=0010, ref affix idx 1)
2 0010                  ← PED-2026-0010
```

Hmm — aqui ha tensao: `1 0010` poderia ser interpretado de 2 jeitos:
- var=`1`, affix=ref idx 0010 → erro (idx 10 nao existe)
- var=`0010`, affix=ref idx 1 → INV-2026-0010

A gramatica precisa decidir **qual parte vem primeiro**. Convencao
proposta: **var sempre vem primeiro** (lado oposto ao affix).
- `>` (prefix): linha = "<var> <affix-or-ref>" — mas entao prefix esta
  do lado direito??

Espera, isso ta confuso. Vou repensar.

### Repensando a sintaxe

Se affix eh PREFIX (vem antes da var), a ordem visual deveria ser
**affix primeiro, var segundo**:

```
codigo,>:
INV-2026-00 011        ← prefix=INV-2026-00, var=011 (ordem: prefix var)
021                     ← so var; usa ultimo prefix → INV-2026-00021
1 0010                  ← ref idx=1, var=0010 → INV-2026-00010
```

Para SUFFIX, a ordem visual deveria ser **var primeiro, affix segundo**:

```
email,<:
ana @gmail.com          ← var=ana, suffix=@gmail.com (ordem: var suffix)
bruno                   ← so var; usa ultimo → bruno@gmail.com
carlos 1                ← var=carlos, ref idx 1 → carlos@gmail.com
```

A direcao (`>` ou `<`) determina qual eh o **lado da declaracao**
(esquerda em `>`, direita em `<`).

Isso eh mais consistente: **a direcao indica onde o affix esta na
linha emitida**.

| Direcao | Linha eh `<X> <Y>` | X eh | Y eh |
|---------|-------------------|------|------|
| `>` prefix | `<X> <Y>` | prefix (declarado/ref) | var |
| `<` suffix | `<X> <Y>` | var | suffix (declarado/ref) |

Linha sem espaco: so var (usa ultimo affix declarado).

### Casos especiais

**Linha 1 obrigatoriamente declara**:
A primeira linha da coluna **deve** ter affix explicito (declaracao).
Caso contrario, decoder nao tem affix para usar.

Excecao: linha 1 sem affix significa que **nao tem affix** (string
literal). Mas isso eh inconsistente — se a coluna tem direcao, ha
affix. Se nao tem affix, omitir direcao do col header.

**Excecao linha sem affix em coluna com affix**:
Como marcar uma linha que NAO segue o padrao? Por exemplo:
```
email,<:
ana @gmail.com
bruno
\!leonardo@unique.com  ← excecao, sem suffix
diana
```

Marker `\!` continua valido (igual no EXP-006).

## Cenarios a testar

| # | Cenario | Esperado |
|---|---------|----------|
| S1 | 100 codigos `INV-2026-NNNN` (1 prefix) | ganho similar a affix simples |
| S2 | 100 emails `userNNN@gmail.com` (1 suffix) | ganho similar (com `<`) |
| S3 | 100 emails 50/50 em 2 dominios | melhor que affix simples (multi) |
| S4 | 100 emails 33/33/33 em 3 dominios | melhor que affix simples |
| S5 | 100 codigos misturados (INV/PED/REQ) | melhor que affix simples |
| S6 | 100 strings sem padrao (nomes pessoais) | nao ativa (auto-bypass) |

## Comparacao planejada

Para cada cenario:
- CSV puro
- TCF SRDMP atual (Etapa 1, affix simples)
- **TCF affix-bidir** (Etapa 2, proposta)
- gzip de cada

Roundtrip OK requerido.

## Pendencias / cuidados

1. **Encoder precisa detectar split** — heuristica: separadores `@`, `/`, `-`
2. **Decoder precisa parsear linha com 1 espaco interno** corretamente
3. **Custo de declaracao** = `<affix> ` (1 espaco extra) por declaracao
4. Em cenarios com 1 affix dominante, o ganho extra vs Etapa 1 eh **so**
   a remocao do header `affix="..."`.

## Saida

`./output/` com arquivos por cenario.

---

## Resultados (run.py executado)

### Tabela

| Cenario | csv | SRDM | SRDMP | **bidir** | bidir vs SRDMP | rt |
|---------|----:|----:|------:|----------:|---------------:|----|
| S1 codigos uniforme (1 prefix) | 1407 | 1420 | **440** | **421** | -4.3% | OK |
| **S2 emails 1 dominio (1 suffix)** | 1806 | 1819 | 1334 | **820** | **-38.5%** | OK |
| S3 emails 2 dominios (mistura) | 1806 | 1819 | 1334 | 1414 | +6.0% | OK |
| S4 emails 3 dominios | 1872 | 1885 | 1400 | 1480 | +5.7% | OK |
| S5 codigos misturados (3 prefixes) | 1407 | 1420 | 1421 | 1610 | +13.3% | OK |
| S6 nomes sem padrao (auto-bypass esperado) | 1073 | 1086 | 1087 | 1276 | +17.4% | OK |
| **medias** | | | | | **-0.07%** | 6/6 OK |

### Achados criticos

**A1 — S2 mostra o ganho real do bidir: SUPORTE A SUFFIX (-38.5%)**

SRDMP atual SO faz prefix. Em emails com 1 dominio comum
(`@gmail.com`), nao detecta nada. Com `<` (suffix), bidir captura.

**Aprendizado**: a flag P atual deveria ser estendida para suportar
suffix simples (sem multi-cluster) — ganho rapido e barato.

**A2 — S3/S4 (multi-dominio) PERDEM porque algoritmo de split eh
simplista**

O `_split_suffix` encontra **um** sufixo dominante (LCP global de
sufixos) e usa para todos. Em S3/S4, ele detecta `.com` (ultimo
separador comum) em vez de `@gmail.com`/`@yahoo.com` separados.
Resultado: 1 affix mediocre em vez de N affixes especificos.

**Para multi-affix funcionar**: precisaria detectar **clusters** de
strings com sufixos comuns. Algoritmo:
1. Para cada string, listar todos os sufixos candidatos (de cada `@`,
   `.`, `/`)
2. Agrupar strings por sufixo comum
3. Escolher os top-K sufixos mais frequentes
4. Atribuir cada string ao seu sufixo
5. Strings sem sufixo dos top-K viram excecoes `\!`

Isso eh mais sofisticado mas factivel. **Nao implementado nesta
iteracao**.

**A3 — S5 (3 prefixes) PERDE porque algoritmo nao deteta multi-prefix**

Mesma limitacao de A2. LCP global entre `INV-2026-`, `PED-2026-`,
`REQ-2026-` eh apenas `-2026-` (e mesmo assim quebra ordem). Nenhum
prefix detectado por inteiro. Todas as linhas viram `\!` (excecoes).

**A4 — S6 (sem padrao) PERDE porque NAO HA auto-bypass**

Implementacao atual sempre tenta extrair affix, mesmo quando nenhum
existe. Se LCP < 4 chars, deveria CAIR para forma simples (sem header
de direcao). Auto-bypass faltando.

**A5 — Roundtrip 6/6 OK**

Apesar dos ganhos negativos em alguns casos, **a gramatica eh
sound** — todos os 6 cenarios reconstroem dados identicos. Conceito
validado.

### Conclusao da iteracao

A proposta do user **tem merito fundamental** (S2: -38.5% prova),
mas tem **2 niveis de implementacao** distintos:

1. **Nivel 1 — direcao `<` simples** (suffix detection)
   - Custo: extender flag P existente p/ aceitar `<` direction
   - Ganho: cobre cenario emails com 1 dominio (~30% de casos comuns)
   - **Recomendado para incluir em SRDMP++** (etapa 1.5)

2. **Nivel 2 — multi-affix com clusters**
   - Custo: algoritmo de detec de clusters (k-means simples ou frequency)
   - Ganho: cobre S3/S4/S5 (multi-dominio, multi-prefixo)
   - **Adiar** para Etapa 3 — depende de evidencia em datasets reais

3. **Auto-bypass forte**: requisito tanto p/ Nivel 1 quanto Nivel 2.
   Detectar quando affix nao vale (cardinalidade alta de prefixes/
   sufixos, LCP curto demais).

### Decisao registrada

Para a proxima iteracao do TCF v0.5:
- **Incluir suffix em flag P** (Nivel 1 — simples, ganho claro)
- **Adiar multi-affix** ate evidencia em datasets reais
- **Reforcar auto-bypass** com threshold mais conservador

Algoritmo proposto para Nivel 1 (extensao da Etapa 1):
```
1. Detectar prefix (ja implementado)
2. Detectar suffix com mesma logica:
   - LCP-suffix: maior sufixo comum (a partir do fim da string)
   - Threshold: |suffix| ≥ 4 E coverage ≥ 70%
3. Escolher direcao com maior ganho previsto:
   - prefix gain vs suffix gain
4. Se nem prefix nem suffix → no-op
```

Sintaxe sugerida (ainda compatible com Etapa 1):
```
codigo: affix="INV-2026-"           ← prefix (Etapa 1)
email:  suffix="@gmail.com"         ← suffix (Etapa 1.5, NOVO)
```

A sintaxe **bidir implicita inline** (proposta deste lab) fica
**adiada para Etapa 3** quando quisermos multi-affix.

### Outputs salvos

`./output/{S1..S6}/` com:
- `source.csv` — fonte
- `tcf-SRDM.tcf` — referencia
- `tcf-SRDMP.tcf` — affix etapa 1 (so prefix)
- `tcf-bidir.txt` — proposta etapa 2 (bidir implicito)
- `results.json` — dados estruturados

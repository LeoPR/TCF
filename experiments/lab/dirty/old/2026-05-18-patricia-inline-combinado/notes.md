# PATRICIA + inline — combinado dos labs 16 e 17

**Data**: 2026-05-18
**Origem**: decisao do user, apos lab 17 mostrar que header verboso
era pior que inline. Combinar **analise PATRICIA** + **emit inline**.

## Tese

- **Lab 17** mostrou que PATRICIA captura hierarquia globalmente
- **Lab 16** mostrou que serializacao inline economiza bytes
- **Combinacao**: PATRICIA descobre afixos do dataset INTEIRO; emit
  inline declara cada afixo na 1a vez que aparece (sem header)

## Sintaxe (mesma do lab 16)

| Token | Significado |
|-------|-------------|
| `*<text>` | decl inline (cria novo idx) |
| `<n>` (puro digito) | ref idx |
| `_<n>` | literal numerico (desambigua) |
| `=<n>` | ref linha n |
| `<text>` | literal puro |

Linha = tokens separados por espaco; concatenacao = valor.

## Algoritmo

```
Pass 1: constroi PATRICIA inserindo todas as strings
Pass 2: coleta prefixos uteis (count >= 2, len >= 4) via DFS
Pass 3: coleta suffixes uteis (PATRICIA invertida)
Pass 4: para cada string, decompoe em (prefix, mid, suffix) usando
        afixo MAIS LONGO disponivel
Pass 5: emit inline — declara afixo na 1a vez, ref nas demais
```

## Resultados

### Tabela bytes (texto puro)

| Cenario | literal | **lab18** | 18 vs lit | RT |
|---------|--------:|----------:|----------:|----|
| C1 user-example (8) | 149 | 117 | -21.5% | OK |
| **C2 codigos-uniforme** (20) | 280 | **136** | **-51.4%** | OK |
| **C3 misto-80-20** (20) | 256 | **130** | **-49.2%** | OK |
| **C4 emails-2dom** (30) | 540 | **304** | **-43.7%** | OK |
| C5 dups-dominantes (15) | 60 | 48 | -20.0% | OK |
| C6 4-emails (4) | 72 | 60 | -16.7% | OK |
| **medias** | | | **-33.75%** | **6/6 OK** |

### Comparativo com labs anteriores

| Lab | Tecnica | Avg vs literal |
|-----|---------|---------------:|
| 16 | inline only (prepop 4 linhas) | -21.0% |
| 17 | PATRICIA + header verboso | -11.2% |
| **18** | **PATRICIA + inline** | **-33.75%** |

**Ganho de +12pp sobre lab 16, +22pp sobre lab 17**. A combinacao
provou-se claramente superior.

### C3 finalmente brilha (-49.2%)

Lab 16 tinha **0%** em C3 (80% prefix + 20% sem padrao) porque
prepopulacao de 4 linhas falhava. Lab 18 com PATRICIA detecta
`INV-2026-` em 16/20 strings (cobertura parcial) e usa. Resultado:
-49.2%.

### Bytes apos gzip

| Cenario | lit+gz | enc+gz | enc+gz vs lit+gz |
|---------|-------:|-------:|-----------------:|
| C1 | 76 | 93 | +22.4% |
| C2 | 82 | 90 | +9.8% |
| C3 | 93 | 97 | +4.3% |
| C4 | 129 | 157 | +21.7% |
| C5 | 42 | 46 | +9.5% |
| C6 | 57 | 68 | +19.3% |

Apos gzip, encoded eh +5 a +22% PIOR que literal+gz. **Esperado**:
gzip captura padroes em literais melhor que nossos tokens estruturais
(`*`, `_`, `=`) que sao bytes adicionais.

**Mas isso eh OK** para TCF: o objetivo eh **legibilidade + LLM-
friendly**, nao razao maxima apos gzip generico. Pre-gzip, ganho
substantial (-33.75%).

## Output do C1 — analise visual

```
*user001@gmail.com       ← decl idx 1 = "user001@gmail.com"
*user002@gmail.com       ← decl idx 2 = "user002@gmail.com"
=1                       ← repete linha 1
=2                       ← repete linha 2
*user00 _4 *@hotmail.com  ← decl idx 3="user00" + "4" + decl idx 4="@hotmail.com"
3 _6 *@gmail.com          ← idx3 + "6" + decl idx 5="@gmail.com"
hdssserr 4                ← literal + idx 4
xcfdf@zip *mail.com       ← literal + decl idx 6="mail.com"
```

Heuristica escolheu strings completas (`user001@gmail.com`) como idx
1 e 2 porque elas duplicam. Lab 16 escolheu `user00` como idx 1
(prefix mais curto mas reutilizavel mais vezes). Trade-off:

- Lab 16 (idx curto): 98B
- Lab 18 (idx longo): 117B

Em C1, lab 16 venceu (paradoxalmente). **Bug do lab 18**: heuristica
prefere afixos LONGOS, mas afixos CURTOS podem ser melhores quando
reutilizaveis em mais linhas.

**Fix conceitual proposto**: usar **ganho previsto** = `count * (len -
1) - decl_overhead` em vez de so `len` para ordenar.

Apesar deste sub-otimo em C1, o agregado eh muito melhor que lab 16.

## Conclusao

A combinacao **PATRICIA (analise global) + serializacao inline**
captura o melhor dos dois labs anteriores:
- PATRICIA ve o dataset inteiro (vs prepop de 4 linhas no lab 16)
- Inline elimina header verboso (vs lab 17)

**Avg -33.75% vs literal**, **6/6 RT OK**.

Bug residual em C1 (heuristica de selecao) eh refinamento futuro;
nao bloqueia o approach.

## Status

- [x] PATRICIA constroi arvore + coleta afixos globais
- [x] Inline emit declara afixos na 1a aparicao
- [x] 6/6 RT OK
- [x] Ganho mensurado: -33.75% medio (vs -21% e -11.2% labs 16/17)
- [x] C3 finalmente brilha (-49.2%) com cobertura parcial
- [ ] Refinar heuristica de selecao (preferir afixos com mais reuso,
      nao apenas mais longos)
- [ ] Multi-decl (`**`) para hierarquia profunda

## Pendencias para proxima iteracao

1. **Heuristica refinada**: `gain = count * (len - 1) - overhead`
2. **Multi-decl (`**`)** para sub-hierarquia (ex: `@hotmail.com` +
   `mail.com` em cascata)
3. **Cenarios maiores** (>= 100 valores) para escalar
4. **Comparacao com gzip do CSV**: apos gzip, encoded ainda eh +9 a
   +22% pior. Aceitavel para TCF mas vale registrar

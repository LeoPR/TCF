# Revisao critica dos outputs M1.E

Releitura dos 4 TCFs M1.E cruzando com tokens raiz, antes de seguir
pra M1.C. Objetivo: nao escapar redundancia, padrao residual ou
fragilidade.

## 1. Redundancia ENTRE LINHAS (escapou — fora do escopo de M1)

### D1 — sufixos/prefixos repetidos em refs

```
linha 6  (eid=6):  7,8,3,11,5,6
linha 7  (eid=7):  9,2,3,11,5,6
linha 8  (eid=8):  10,8,3,11,5,6
linha 10 (eid=10): 7,8,3,12,6
linha 11 (eid=11): 9,2,3,12,6
linha 12 (eid=12): 10,8,3,12,6
```

Sufixo `,3,11,5,6` aparece 3x (linhas 6-8). Sufixo `,3,12,6` aparece
3x (linhas 10-12). Prefixo `7,8` aparece em 6 e 10. M1.E nao ataca
isso porque so' age **dentro de uma linha**.

**Semantica nova necessaria**: alias de tupla de refs. Ex:
`$1=3,11,5,6` declarado uma vez, depois `7,8,$1`.

**Custo/beneficio nos datasets atuais**:
- D1: substituir 3 ocorrencias de `,3,11,5,6` (10 chars) por `,$1`
  (3 chars) economiza 7 chars × 3 = 21. Custo de declarar `$1`: ~12
  chars. Liquido = +9 bytes.
- Em datasets reais com K >> 3 ocorrencias, ganho cresce linearmente.

**Decisao**: anotar pra M2 ("aliases / templates de refs"). NAO
implementar dentro de M1 (sai do escopo "marcacao de ambiguidade").

### D3 — estruturas identicas em pares

```
linha 3 (eid=2): 1..3\103*5..7
linha 4 (eid=3): 1..3\256*5..7
```

Estrutura `1..3 + <id> + 5..7`, so' muda `103`/`256`. Idem
linhas 6-7 (`web2..7` vs `web` + variantes). Idem D4 linhas 3-4
(`1..4\3` / `1..4\4`).

**Semantica nova necessaria**: slot/template entre linhas
(`pattern + 1-char-diff`). Provavelmente sai pra macro de "RLE
estrutural" ou template-with-slot.

**Decisao**: NAO em M1. Anotar.

## 2. Overhead de declaracao do no fonte (escapou — outra camada)

### D1 eid=1

```
joa*o*@*g*mail*.com    (TCF M1.E)
```

7 fragmentos literais (porque cada um sera referenciado por algum
no descendente: 'joa' em eid=5,9, 'o' em ?, '@' em ?, etc.).
6 `*` separadores = 6 bytes de overhead so' pra declarar.

### D3 eid=1

```
api*/*users/\00*\042*/profile*.*json
```

7 fragmentos com 6 `*` + 2 `\` escapes de escopo. ~8 bytes overhead.

### D2 eid=1

```
d'a*nge*lo*\1*@g*mail*.com
```

7 fragmentos com 6 `*` + 1 `\`. ~7 bytes overhead.

**Padrao**: cada no fonte com muitos fragmentos paga ~N-1 bytes em
separadores onde N = numero de fragmentos.

**Semantica nova necessaria**: declaracao alternativa do no fonte
(com posicoes explicitas, ou marcador unico de fim de fragmento,
ou formato binario por camada). Nao e' marcacao de ambiguidade.

**Decisao**: NAO em M1. Pode entrar em macro de "formato de
declaracao compacta" mais tarde.

## 3. Fragmentacao forcada pelo algoritmo (limitacao de exp 16)

O algoritmo do exp 16 fragmenta um literal quando ele recebe quebras
de descendentes. Resultado: nos fontes ficam picotados.

Exemplo D3 eid=1: tem `users/00042/profile.json` no original, mas
fica `users/00` + `042` + `/profile` em fragmentos. Isso e' porque
eid=2 (`...00103...`) precisa referenciar `users/00` separado do
`042`.

**Implicacao para M1.D (slice arbitrario)**: poderia atacar isso.
Em vez de fragmentar eid=1, declara `eid=1` inteiro e eid=2 usa
`slice(1, 0, 12) + L('103') + slice(1, 15, 28)`. Custo: refs com
posicoes vs refs com idx. Trade-off depende de quanto `00` e `042`
sao reutilizados.

**Decisao**: M1.D vale implementar pra mapear comportamento. Mas
ele MEXE NO ALGORITMO, nao so' na sintaxe.

## 4. Fragilidade conhecida em M1.E (decoder)

Cenario hipotetico: literal `.` seguido por dígito. Ex: linha
`1,2..5.10more`.

Parser:
- ref-mode: consome `1,2..5` (porque j+1=`.`, OK consome `..`,
  depois j+1=`1` ≠ `.`, BREAK). refs_str = `1,2..5`.
- next char `.10more`. lit-mode acumula `.` (`1` digit break).
  lit = `.`.
- next char `1`. ref-mode. while: `10`. refs_str = `10`. Mas frag
  10 pode nao existir.

Atualmente: **nenhum dataset D1-D4 dispara isso**. Mas e' fragilidade
latente. Vai aparecer se literal `.` aparecer DEPOIS de uma ref ou
range.

**Mitigacao possivel**: sempre emitir separador `*` entre ref/range
e literal seguinte que comece com `.`. Custo: ~1 byte por
ocorrencia. Vale fazer se algum dia aparecer.

**Decisao**: anotar como TODO. Nao corrigir agora porque nao ha
caso real ainda.

## 5. K=2 sequencial nao agrupa (correto)

`5,6` (3 chars) vs `5..6` (4 chars). M1.E correto em manter virgula.
Consistente com calculo de custo.

## 6. Refs nao-sequenciais que estao "perto" mas sem hit

D1 linhas 6/8: `7,8,3,11,5,6`. Refs nao formam sequencia aritmetica
+1. Mas 5,6 forma K=2 (nao agrupa). 11 sozinho. Nao tem o que fazer
dentro de M1.E.

Poderia haver semantica alternativa "range invertido" ou "lista
classificada", mas overhead torna improvavel ganhar.

## 7. Limitacoes do dataset D1 que poderiam mascarar problema

D1 nao tem nada com `'` ou `*` ou `\` no literal — todos OK. Mas
isso significa que **M1.E nao foi testado em literal com chars
ambiguos + range adjacente**.

Exemplo de stress nao testado: linha onde literal termine em digito
escapado E proxima coisa seja range:
- `\103*1..3` — funciona porque `*` separa.
- E se faltasse o `*`? `\1031..3` — parser leria `\1031` como
  escape escopo (todos digitos), entao `..3` problema.

M1.E ja' insere `*` quando lit termina em digit-seq antes de ref
(herdado de M1.A'). Isso cobre o caso. **Verificado nos TCFs**:
ex D2 linha 11 `12\42*14,6,7` (separador `*` antes de `14`).

OK, sem regressao.

## Resumo: o que NAO escapou e o que NAO esta em M1.E

| Item | Status |
|---|---|
| Range dentro de linha | M1.E cobre (K>=3) |
| Escape escopo (digitos) | herdado de M1.A' |
| Separador `*` lit-ref | herdado de M1.A' |
| RT 4/4 | OK |
| Redundancia entre linhas (alias tupla) | **fora do escopo M1** — anotar pra M2 |
| Overhead declaracao no fonte | **fora do escopo M1** — outra camada |
| Slice arbitrario | **M1.D pendente** (extende algoritmo) |
| Sumida (parser stateful) | **M1.C pendente** (so' sintaxe) |
| Fragilidade decoder com `.` literal | anotar TODO, sem caso real ainda |
| K=2 nao agrupa | comportamento correto |

## Perspectiva alternativa que vale apresentar

Olhando alem do escopo "marcacao de ambiguidade" de M1, ha 3
camadas distintas de redundancia visiveis nos outputs:

1. **Camada local (linha)**: M1.A/B/A'/E atacam isso. M1.C/D ainda
   por testar.
2. **Camada estrutural (entre linhas similares)**: refs idênticas
   sao repetidas. Templates/aliases atacariam. **Macro novo (M2?)**.
3. **Camada de declaracao (no fonte)**: fragmentacao forcada cria
   overhead. Slice arbitrario (M1.D) ataca parte; formato alternativo
   ataca o resto. **Misto de M1 e macro futuro**.

Recomendacao: completar M1 com C e D, depois decidir se abrir M2
para camada estrutural ou se ja' migrar pra prototype com decisao
de "M1.E como sintaxe base + aliases como camada opcional".

## Decisao para o proximo passo

**Implementar M1.C (sumida)** agora. Razoes:
- Esta no escopo do macro M1
- E' sintaxe pura (nao mexe no algoritmo) — implementacao rapida
- Ataca dimensao NAO testada (verbosidade quando contexto resolve)
- Mesmo se ganho for zero ou negativo, mapeia DIFERENCA semantica
  conforme metodologia [[exploracao_semantica]]

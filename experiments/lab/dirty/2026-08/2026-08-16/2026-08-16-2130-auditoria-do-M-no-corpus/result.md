# Resultado — o `.8M` no corpus real: 23 tabelas, 186 colunas, 0 falhas

Janela contígua do meio (alvo 2000 linhas), a régua do lab `0530`. `src/tcf` intocado.

---

## 1. O que está OK — e foi verificado em dado real, não sintético

| verificação | resultado |
|---|---:|
| RT em todas as tabelas | **23/23** |
| paridade `view` × `decode` | **23/23** |
| as 6 invariantes de fronteira (I1–I6) | **23/23 cada** |
| — incluindo **I4: decode PARALELO == serial** | **23/23** |
| os 3 guards recém-soldados disparando espúrio | **0** |

**As invariantes que eu tinha medido só em sintético valem em dado real.** O decode paralelo
por coluna deu resultado idêntico ao serial nas 23 tabelas, com `src/tcf` intocado — a
orquestração é externa, o formato não precisa de nada.

E os guards não incomodam: **151 das 186 colunas reais têm nome com caractere não-alfanumérico**
(`education-num`, `marital-status`, `capital-gain`…) e **nenhum** disparou o guard do C1, do C2
ou do C3.

## 2. Os 4 candidatos: nenhum é morto

| modo | colunas onde vence |
|---|---:|
| `@` dict | **70** |
| `tcf` (core) | **59** |
| `%` split | **37** |
| `!` raw | **20** |

**Os quatro têm domínio real.** Nenhum é compute desperdiçado — o que valida o `min()` do
`_best_of` como está.

## 3. A CORREÇÃO — e ela desmonta uma afirmação minha

Eu havia dito, com base no **adult-census**: *"a soma de 15 wires flat separados é 32.972 B
contra 41.925 do `.8M` — o `.8M` é +27,2%"*, e usei isso para dimensionar o Grupo A.

**No corpus inteiro é o contrário**:

| | bytes |
|---|---:|
| `.8M` (23 tabelas) | 2.257.869 |
| Σ dos wires flat separados | 2.379.176 |
| **gap** | **−121.307 B (−5,1%)** |

**O `.8M` VENCE no agregado.** Ele perde em 11 tabelas (soma +14.521 B) e ganha em 12
(soma −135.828 B).

E o detalhe que condena a generalização: **o adult-census é exatamente a tabela onde o `.8M`
mais perde** (+8.976 B, 62% de toda a perda do corpus). Eu generalizei do pior caso.

## 4. O teto REAL do Grupo A: 2,3%, não 27%

O gap por *tabela* não é o que a união captura — a união pega o `min()` **por coluna**. Medido
coluna a coluna, comparando corpos (sem header, para ser justo):

| | |
|---|---:|
| colunas onde o candidato do flat venceria | **77 de 186 (41%)** |
| bytes que a união recuperaria | **52.220 B** |
| como % do `.8M` do corpus | **2,3%** |

Onde renderia mais: `adult-census` (+9.573 B, 12/15 colunas), `tpch/lineitem` (+8.946 e
+7.531), `wine-quality` (+4.625).

**O Grupo A continua valendo — 41% das colunas têm candidato melhor no flat — mas o tamanho
é 2,3% do corpus, não os 27% que eu extrapolei de uma tabela.**

## 5. O que isto muda na fila

1. **O Grupo A encolhe em prioridade.** 2,3% agregado não justifica abrir a gramática do meta
   (B1) sozinho. Continua certo como *unificação de caminho* (`T-UM-CAMINHO-SO` é sobre
   manutenção — cada mecanismo soldado uma vez em vez de duas), mas **o argumento de bytes
   ficou fraco** e não deve ser o que sustenta a decisão.
2. **O `.8M` está saudável.** Os 4 candidatos funcionam, as invariantes valem, o RT fecha, o
   `view` concorda, os guards não incomodam. Não há defeito aberto conhecido nesta rota.
3. **O caso do `.8H` continua grande** — os 99,986% de overhead por candidato único não foram
   tocados por esta auditoria, e ali o problema é de outra ordem.

## 6. Ressalvas

- **Amostra de 2000 linhas por tabela**, janela do meio. Tabelas grandes (`br-identidades`
  500k, `tpch-sf01/lineitem` 600k) entram com 0,4% e 0,3% das linhas. As proporções por coluna
  são estáveis nesse regime, mas o **agregado** do corpus é da amostra, não do corpus inteiro.
- **`NULL` do SQLite vira string vazia** — o `.8M` é `dict[str, list[str]]`. Tabela com muitos
  nulos está sendo medida como tabela com muitas strings vazias.
- **`tpch-sf001` é prefixo do `tpch-sf01`** (registrado no EXP-017): as duas contribuem para
  o agregado, então o TPC-H tem peso dobrado. Sem elas o `.8M` ainda vence, mas por menos.
- **Não é teste de stress.** É o corpus como ele é, no caminho normal.

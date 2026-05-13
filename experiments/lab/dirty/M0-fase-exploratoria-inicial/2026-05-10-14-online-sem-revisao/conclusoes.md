# Conclusões — online sem revisão

Roundtrip **3/3 OK**.

## Resultado central

| Dataset | exp 13 (Re-Pair) | exp 14 (online) | delta | vencedor |
|---|---:|---:|---:|---|
| D2-mini | 192 | 198 | +6 | exp 13 |
| D2-completo | 447 | 463 | +16 | exp 13 |
| D4 | 424 | **399** | **-25** | **exp 14** |

**Resultado quebra expectativa**: o online sem revisão venceu em
D4. Em D2 perdeu por margem pequena (+6, +16).

## Trecho TCF — D4 (onde online venceu)

```
no1: "https://api.example.com/v1/users/1"
no2: no1[0:27] + "orders/100"               (27 chars de no1 = base URL)
no3: no1[0:33] + "2"                        (33 chars = base + "users/")
no4: no2[0:36] + "1"                        (36 chars = base + "orders/10")
no5: no1[0:27] + "products/50"              (27 chars + recurso novo)
no6: no1[0:33] + "3"                        (33 chars + "3")
no7: no5[0:37] + "1"                        (37 chars de no5 = base + "products/5")
no8: no2[0:36] + "2"                        (36 chars de no2 = base + "orders/10")
...
```

**Cada string aponta para a anterior mais similar**, pegando o
LCP máximo. Re-Pair só extraía a base URL (27 chars) como símbolo
único — aqui o online captura LCPs de até 37 chars.

## Trecho TCF — D2-completo (onde online perdeu por pouco)

```
no1: "maria.silva@gmail.com"
no2: "joao.souza@hot" + no1[-8:]                       (sufixo "mail.com")
no3: "maria.silv" + no2[-13:]                          (sufixo "a@hotmail.com")
no4: "ana.lim" + no1[-11:]                             (sufixo "a@gmail.com")
no5: no2[0:11] + "gmail.com"                           (prefixo "joao.souza@")
no6: "pedro.alves@yahoo" + no1[-4:]                    (sufixo ".com")
no7: "ana.lim" + no2[-13:]
no8: no2[0:11] + "yahoo.com"
no9: no6[0:12] + "gmail.com"
no10: no1[0:12] + "yahoo.com"
no11: "ana.lim" + no8[-11:]
no12: no6[0:12] + "hotmail.com"
```

`mail.com` é referenciado via `no1[-8:]` cada vez. Em Re-Pair
viraria símbolo `R1` (3 chars de ref vs 8 chars de `no1[-8:]`).
×8 ocorrências = margem de ~15-25 chars que Re-Pair economiza.

`ana.lima` (que Re-Pair perdeu por heurística greedy) aqui não
foi capturado também — `"ana.lim"` aparece como literal em 4 linhas.
Trade-off com o Re-Pair: nenhum dos dois pegou ana.lima
inteiro neste cenário.

## Pontos a registrar

1. **Online sem revisão é viável** — roundtrip 3/3, decode em 1
   passada, sem forward refs.

2. **Vence onde há alta similaridade local entre strings
   consecutivas/próximas** (D4: URLs do mesmo recurso seguidas).
   LCP de 33-37 chars é capturado integralmente; Re-Pair só
   pegava 27 (símbolo fixo).

3. **Perde onde há padrão disperso globalmente** (D2: `mail.com`
   em 8 strings espalhadas). Cada uso paga `noN[-8:]` em vez do
   `RN` (3 chars) do Re-Pair.

4. **Streaming-friendly real**: cada string pode ser emitida
   assim que processada. Memória = O(N × max_len) para manter
   strings reconstruídas.

5. **Trade-off claro identificado**:
   - Datasets com **similaridade local forte** (URLs por recurso,
     IDs sequenciais, strings ordenadas): online ganha.
   - Datasets com **padrões globais dispersos** (sufixos de
     domínio universal, palavras frequentes): batch (Re-Pair) ganha.

6. **Decode mais simples** que tudo que veio antes:
   - Sem forward refs (todos os noN antes de noK)
   - Sem aninhamento de decls
   - Cache linear de strings reconstruídas

## Insight para próximo passo

O **trade-off não é unidimensional**. Não é "Re-Pair é melhor
universalmente" nem "online é sempre pior". Depende da estrutura
do dataset:

| Padrão de dados | Algoritmo mais econômico |
|---|---|
| Strings similares em sequência (D4) | online (LCP máximo) |
| Padrões dispersos globalmente (D2) | batch (Re-Pair) |
| Misto | possivelmente híbrido |

**Isto motiva o exp 15** (online COM revisão retroativa):
- Mantém a captura de LCP local (vantagem do online)
- Adiciona revisão: quando padrão emergir entre strings
  não-consecutivas, pode "agarrar" retroativamente
- Hipótese: pode bater Re-Pair em ambos os tipos de dataset

Mas isso é exp 15. Aqui foi só Opção A — a versão mais simples.

## O que este experimento NÃO mostra

- Comportamento em N > 20.
- Streaming real (com flush em momentos arbitrários).
- Performance de tempo (não medido).
- Janela deslizante limitada (exp 16).
- Revisão retroativa (exp 15).
- Comparação com formato compacto.
- Heurística mais sofisticada para escolha de pref/suf.

# Conclusões — patricia bidirecional composto

Roundtrip **8/8 OK** (4 datasets × 2 thresholds).

## D1 — emails-um-dominio (composição ativa em 10/10 strings)

Decomposição:

```
user001@gmail.com -> pref="user00"  mid="1"  suf="@gmail.com"
user002@gmail.com -> pref="user00"  mid="2"  suf="@gmail.com"
...
user010@gmail.com -> pref="user0"   mid="10" suf="@gmail.com"
```

`user010` cai num pref mais raso (`user0`) porque Patricia
forward detectou `user00` cobrindo só 9 strings (001-009).
Suf `@gmail.com` é universal aos 10.

TCF gerado:

```
<body>
  no1: pref:(no2=decl folha "user00") + "1" + suf:(no3=decl folha "@gmail.com")
  no4: pref:no2 + "2" + suf:no3
  ref:no1
  no5: pref:no2 + "3" + suf:no3
  ref:no4
  no6: pref:no2 + "4" + suf:no3
  ref:no1
  no7: pref:no2 + "5" + suf:no3
  ref:no5
  no8: pref:no2 + "6" + suf:no3
  ref:no4
  no9: pref:no2 + "7" + suf:no3
  ref:no1
  no10: pref:no2 + "8" + suf:no3
  ref:no6
  no11: pref:no2 + "9" + suf:no3
  ref:no5
  no12: pref:(no13=decl folha "user0") + "10" + suf:no3
  ref:no7
  ref:no1
</body>
```

Leitura:
- **Linha 1**: declara no1 (a folha completa), embute decl aninhada
  do pref `no2 = "user00"` e do suf `no3 = "@gmail.com"`. Tudo
  numa única linha.
- **Linhas 2 em diante**: as 8 strings `user002..user009` só
  referenciam `pref:no2 + "N" + suf:no3`. O middle é 1 char.
- **Última linha de decl**: `user010` precisa de outro pref
  (`no13 = "user0"`) — é uma decl aninhada nova, mas reusa
  `suf:no3` já declarado.

Comparação ref+dados:
- 08 composto: **494 bytes**
- 06 forward only: 518 bytes
- 07 reverse only: 456 bytes
- **reverse-only ainda vence em D1**. A sintaxe composta paga
  overhead por linha (`pref:no2 + "..." + suf:no3` ≈ 25 chars) que
  excede a simples reverse (`filho_de(no2) + "..."` ≈ 20 chars).
  Composição agrega informação semântica mas custa em sintaxe atual.

## D2 — emails-multi-dominio (composição falha, overlap sempre)

Decomposição (extrato):

```
maria.silva@gmail.com    -> pref="maria.silva@" mid="gmail.com"  suf=-
joao.souza@hotmail.com   -> pref=-              mid="joao.souz"  suf="a@hotmail.com"
maria.silva@hotmail.com  -> pref=-              mid="maria.silv" suf="a@hotmail.com"
joao.souza@gmail.com     -> pref="joao.souza@"  mid="gmail.com"  suf=-
pedro.alves@yahoo.com    -> pref="pedro.alves@" mid="yahoo.com"  suf=-
```

**Nenhuma string composta**. Por quê: as strings têm len 21-23, e
para cada uma:
- pref candidato (`nome.sobrenome@`) tem len 11-12
- suf candidato (`a@dominio.com` ou similar) tem len 10-13
- Soma p+x > len(s) → overlap obrigatório
- Heurística best-fragment-first descarta o mais curto

Resultado:
- Strings com pref vencendo: as 4 marias + 4 pedros + 4 joaos
  (12 das 12)... espera, mas a tabela mostra 7 só pref e 5 só suf.
  Vamos checar: ana.lima (4 strings) → suf vence porque
  `a@hotmail.com` (13) > `ana.lima@` (9). joao.souza →
  `a@hotmail.com` (13) vs `joao.souza@` (11) → suf vence. Etc.

A heurística produz mistura imprevisível baseada em qual lado tem o
fragmento mais longo no Patricia daquele dataset.

TCF (extrato, ver run.py para completo):

```
no1: pref:(no2=decl folha "maria.silva@") + "gmail.com"
no3: "joao.souz" + suf:(no4=decl folha "a@hotmail.com")
no5: "maria.silv" + suf:no4
no6: "ana.lim" + suf:(no7=decl folha "a@gmail.com")
no8: pref:(no9=decl folha "joao.souza@") + "gmail.com"
no10: pref:(no11=decl folha "pedro.alves@") + "yahoo.com"
...
```

Mistura de decls "só pref" e "só suf" sem composição em nenhuma
linha.

Comparação ref+dados:
- 08 composto: **610 bytes** (na verdade, "só uma direção por
  linha", composto não ativou)
- 06 forward only: 617
- 07 reverse only: 726
- **08 ainda venceu por pouco** vs 06, porque em algumas strings o
  algoritmo escolheu suf (mais longo) onde 06 tinha sido obrigado
  a usar pref. Diferença não é da composição — é da heurística que
  pode escolher dinamicamente entre pref/suf.

## D3 — urls-path-comum (só pref em todas)

Decomposição:

```
https://api.example.com/v1/users/1   -> pref="https://api.example.com/v1/users/" mid="1"  suf=-
https://api.example.com/v1/users/2   -> pref="..."                                  mid="2"  suf=-
... (todas iguais)
```

Suf não acionou (reverse Patricia não detecta IDs `1..10` como
prefixo comum dos invertidos). 10 strings só pref.

Comparação ref+dados:
- 08 composto: **372 bytes**
- 06 forward only: 420
- 07 reverse only: 602
- **08 venceu** — 48 bytes a menos que 06, mesma estrutura. A
  diferença vem da sintaxe nova (`pref:noN + "X"` mais curta que
  `filho_de(noN) + "X"`).

## D4 — urls-multi-recurso (só pref em todas)

Padrão similar ao D3. Comparação ref+dados:
- 08 composto: **505 bytes**
- 06 forward only: 551
- 07 reverse only: 710
- **08 venceu por 46 bytes** (mesma razão sintática do D3).

## Pontos a registrar

1. **Composição funciona end-to-end**: roundtrip 8/8 OK. A sintaxe
   `pref:... + "mid" + suf:...` parseia corretamente, com decls
   aninhadas de pref/suf na 1ª aparição.

2. **Composição só ativou em D1**. Em D2 a heurística de overlap
   sempre descarta um lado. Em D3/D4 reverse não detectou nada.

3. **Quando p + x > len(s) (overlap)**: a heurística "mais longo
   vence" é simples mas pode ser sub-ótima. Em D2, prefixos de
   nomes (11-12 chars) e sufixos de domínios (10-13 chars)
   competem em quase todas as strings. A escolha greedy local
   pode não maximizar o ganho global (Fraenkel-Mor-Perl 1983).

4. **Comparação com 06/07 tem ressalva**: a sintaxe foi mudada
   (`pref:` em vez de `filho_de(`), o que dá -3 chars por
   ocorrência. Parte da vantagem do 08 em D3/D4 vem dessa
   mudança, não da composição.

5. **Threshold 2 vs 3 deu idêntico** em todos os 4 datasets.
   Patricia gulosa escolhe sempre o mais longo, e há prefixos ≥ 3
   chars disponíveis. Para ver efeito de threshold, precisaria de
   dataset com padrões curtos (≤ 2 chars).

6. **Resultados absolutos por dataset (ref+dados)**:

   | Dataset | menor | que método |
   |---|---:|---|
   | D1 | 456 | reverse-only (07) |
   | D2 | 610 | composto (08) |
   | D3 | 372 | composto (08) |
   | D4 | 505 | composto (08) |

   Composto venceu em 3 de 4; reverse venceu em D1.

## O que este experimento NÃO mostra

- Comportamento em datasets onde p + x < len(s) para muitas
  strings (composição ativa de fato).
- Comparação isolando "composição" de "sintaxe nova" — exigiria
  refazer 06 com sintaxe `pref:`.
- Heurística "ganho líquido" de Fraenkel-Mor-Perl (escolher por
  bytes economizados, não por len). Aqui usamos só len.
- Threshold < 2 ou > 5. E datasets com padrões curtos.
- Decls recursivas de pref/suf (avô de pref). Apenas folhas
  simples são declaradas em pref/suf.
- Escala. Apenas 20 linhas por dataset.
- Comparação com formato compacto, CSV ou JSON.
- Caso degenerado onde nenhuma string compõe — testado em D3/D4
  mas o algoritmo degrada graciosamente.

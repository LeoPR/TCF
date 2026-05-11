# Conclusões — patricia reverso

Roundtrip **8/8 OK** (4 datasets × 2 direções).

## Trechos do TCF lado a lado

### D1 — emails-um-dominio (reverse vence em bytes totais)

**Forward** captura cadeia `user0 → user00 → folhas`:

```
no1: filho_de(no2=decl filho_de(no3=decl folha "user0") + "0") + "1@gmail.com"
no4: filho_de(no2) + "2@gmail.com"
...
no12: filho_de(no3) + "10@gmail.com"
```

`user010@gmail.com` cai em `user0` lateral (não em `user00`).
Cada folha carrega `@gmail.com` no fragmento.

**Reverse** captura `@gmail.com` (invertido: `moc.liamg@`) como
prefixo único de todas as 10 folhas:

```
no1: filho_de(no2=decl folha "moc.liamg@") + "100resu"
no3: filho_de(no2) + "200resu"
no4: filho_de(no2) + "300resu"
...
no11: filho_de(no2) + "010resu"
```

10 folhas, 1 pai. Estrutura mais plana, e os fragmentos das
folhas (`100resu`, `200resu`, ...) são curtos (7 chars cada).

Comparação:
- forward: ref=401 + dados=117 = 518 bytes
- reverse: ref=376 + dados=80 = **456 bytes** (-62)

A vantagem do reverse aqui é estrutural: o sufixo `@gmail.com`
(10 chars × 10 ocorrências) sai do fragmento em 9 das 10 folhas e
vira só uma vez no pai.

### D2 — emails-multi-dominio (forward vence)

**Forward** acha 4 prefixos `nome@`:

```
no1: filho_de(no2=decl folha "maria.silva@") + "gmail.com"
no3: filho_de(no4=decl folha "joao.souza@") + "hotmail.com"
no5: filho_de(no2) + "hotmail.com"
no6: filho_de(no7=decl folha "ana.lima@") + "gmail.com"
no9: filho_de(no10=decl folha "pedro.alves@") + "yahoo.com"
...
```

**Reverse** acha apenas `.com` (sufixo comum a todos os 3
domínios). Os domínios `gmail`, `hotmail`, `yahoo` ficam separados,
sem prefixo comum entre as folhas invertidas.

```
no1: filho_de(no2=decl folha "moc.") + "liamg@avlis.airam"
no3: filho_de(no2) + "liamtoh@azuos.oaoj"
no4: filho_de(no2) + "liamtoh@avlis.airam"
...
```

1 pai (`.com`), 19 folhas grandes (cada uma com domínio + nome
invertidos). Pai é curto (4 chars), fragmentos são longos.

Comparação:
- forward: ref=457 + dados=160 = **617 bytes** (-109)
- reverse: ref=592 + dados=134 = 726 bytes

Forward vence porque os 4 prefixos `nome@` cobrem mais bytes
(`maria.silva@` = 12 chars × 3 ocorrências) que o único sufixo
`.com` (4 chars × 20 ocorrências) detectado pelo reverse.

### D3 — urls-path-comum (forward vence muito)

**Forward** acha o prefixo grande:

```
no1: filho_de(no2=decl folha "https://api.example.com/v1/users/") + "1"
no3: filho_de(no2) + "2"
...
no11: filho_de(no2) + "10"
```

10 folhas com sufixo numérico de 1-2 chars.

**Reverse** **não fatora nada**. Os sufixos invertidos (`1`, `2`,
..., `01`) não compartilham prefixo ≥ 3 chars. 10 folhas top-level
independentes:

```
no1: folha "1/sresu/1v/moc.elpmaxe.ipa//:sptth"
no2: folha "2/sresu/1v/moc.elpmaxe.ipa//:sptth"
...
no10: folha "01/sresu/1v/moc.elpmaxe.ipa//:sptth"
ref:no1
...
```

Comparação:
- forward: ref=376 + dados=44 = **420 bytes** (-182)
- reverse: ref=261 + dados=341 = 602 bytes

Forward vence por margem grande. Reverse fica estagnado porque o
padrão dos dados (variação no fim, base comum no início) é
forward-friendly por construção.

### D4 — urls-multi-recurso (forward vence)

**Forward** acha hierarquia de 3 níveis (base + recurso + IDs):

```
no1: filho_de(no2=decl filho_de(no3=decl folha "https://api.example.com/v1/") + "users/") + "1"
no4: filho_de(no5=decl filho_de(no3) + "orders/10") + "0"
no8: filho_de(no9=decl filho_de(no3) + "products/5") + "0"
...
```

**Reverse** **não fatora nada** novamente. IDs invertidos (`1`,
`2`, ..., `001`, `101`, ...) sem prefixo comum:

```
no1: folha "1/sresu/1v/moc.elpmaxe.ipa//:sptth"
no2: folha "001/sredro/1v/moc.elpmaxe.ipa//:sptth"
...
```

Comparação:
- forward: ref=487 + dados=64 = **551 bytes** (-159)
- reverse: ref=275 + dados=435 = 710 bytes

Mesmo padrão do D3: estrutura forward-friendly por construção.

## Pontos a registrar

1. **Roundtrip 8/8 OK**. O espelho funciona: inverter strings antes
   do Patricia + inverter de volta no decode = roundtrip preservado
   em ambas as direções.

1a. **Captura semântica de sufixos confirmada**. Apesar do arquivo
    intermediário aparecer com texto invertido (`moc.liamg@`,
    `100resu`), a leitura conceitual mostra que o algoritmo
    identificou padrões reais de sufixo nas strings originais:
    `@gmail.com` (D1 todas as folhas), `.com` (D2 sufixo universal
    dos 3 domínios), e implicitamente padrões intermediários
    como `mail.com` se houvesse cenários com `@hotmail.com`,
    `@gmail.com` partilhando os 8 chars finais. **Reverse Patricia
    funciona como detector de sufixos**, exatamente como forward
    funciona como detector de prefixos. A inversão é detalhe de
    implementação, não de capacidade.

2. **Forward foi a direção com menos bytes em 3 de 4 cenários**
   (D2, D3, D4). Reverse venceu apenas em D1, onde o sufixo
   `@gmail.com` é dominante e regular.

3. **Camada 2 (ref) isolada não é métrica válida** quando se
   comparam árvores diferentes. Em D3 e D4 reverse, ref era menor
   que forward, mas dados era muito maior — saldo negativo.
   Comparação válida usa ref + dados. Esta observação atualiza a
   convenção das 4 camadas (do exp 04): camada 1 é constante
   apenas quando a mesma árvore é serializada de formas diferentes;
   ao mudar a árvore, camada 1 também muda.

4. **Direção dominante depende do dataset**. Não há vencedor
   universal. A escolha por dataset (sem heurística automática
   neste experimento) requer rodar as duas direções e comparar
   ref + dados.

5. **Caso degenerado em D3/D4 reverse**: Patricia não fatora nada.
   Resultado: todas as folhas top-level com strings completas.
   Estrutura "plana" → ref baixo, dados alto.

6. **Estrutura da árvore reflete a regularidade dos dados na
   direção avaliada**:
   - D1 reverse: 1 top, 10 filhos (sufixo dominante)
   - D2 reverse: 1 top, 19 filhos (só `.com` foi detectado)
   - D3, D4 reverse: 10/12 tops, 0 filhos (sem padrão)

## O que este experimento NÃO mostra

- Comportamento em N > 20.
- Heurística automática para escolher direção sem rodar as duas.
- **Casamento das direções**: uma linha usar prefix E suffix
  simultaneamente. Exemplo: `maria.silva@gmail.com` poderia ser
  `<pref:maria.silva@> + <meio> + <suf:.com>`. Não testado aqui.
  Fica para exp 08 ou 09.
- Datasets onde forward e reverse têm ganhos comparáveis (margem
  pequena). Os 4 cenários atuais têm decisões claras por construção.
- Affix tree real (Maaß 1999) com affix links. Aqui usamos a versão
  "duas Patricias paralelas" — equivalente em capacidade, mais
  simples em implementação. Sem comparação direta com affix tree.
- Comparação com formato compacto, CSV ou JSON.
- Cálculo de tempo de encode/decode.

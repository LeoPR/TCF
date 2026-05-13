# Conclusões — padrões repetidos no encode

## Tabela consolidada

```
dataset                           exp10  ganho_ms  ganho_pm   soma     %
D1-emails-um-dominio                494         0         0      0   0.0%
D2-emails-multi-dominio             655        81         0     81  12.4%
D3-urls-path-comum                  372         0         0      0   0.0%
D4-urls-multi-recurso               505         0         0      0   0.0%
```

## Distribuição assimétrica

Apenas D2 ativa o padrão `(mid, suf)` com repetições. Os demais
datasets têm distribuição diferente:

- **D1** (emails 1 domínio): todas as 10 strings têm o mesmo
  `suf="@gmail.com"`. Mas o `mid` é único por string (`"1"`,
  `"2"`, ..., `"10"`). Logo `(mid, suf)` não repete.

- **D2** (emails multi-domínio): `(mid, suf)` repete 3 vezes:
  - `("yahoo", ".com")` cobre 4 strings (yahoo dos 4 nomes)
  - `("hot", "mail.com")` cobre 4 strings (hotmail dos 4 nomes)
  - `("g", "mail.com")` cobre 4 strings (gmail dos 4 nomes)

- **D3** (URLs path comum): não tem `suf` (só `pref`). Logo
  `(mid, suf)` impossível.

- **D4** (URLs multi-recurso): mesmo, só `pref`.

`(pref, mid)` não repete em nenhum dos 4 datasets. Em D2,
significaria 2 strings com mesmo nome e mesmo mid mas sufs
diferentes — não acontece com nossa amostra (cada nome aparece em
3 sufs distintos com 3 mids distintos).

## Por que D2 é onde o padrão emerge

D2 tem estrutura **produto cartesiano** (4 nomes × 3 domínios = 12
únicas). A árvore reverse capturou `mail.com` e `.com` como
sufixos. A árvore forward capturou `nome.sobrenome@` como
prefixos. A decomposição (com cadeia de ancestrais, exp 10) produz:

- Lado esquerdo: 4 valores únicos de `pref` (um por nome)
- Lado direito: combinações de `(mid, suf)` em apenas **3 formas
  distintas** (uma por domínio):
  - `("g", "mail.com")` → gmail
  - `("hot", "mail.com")` → hotmail
  - `("yahoo", ".com")` → yahoo

12 linhas × 3 formas de lado-direito → cada forma se repete 4
vezes. **Esta é exatamente a estrutura que Re-Pair / fatorização
exploraria.**

## Estimativa para exp 12 hipotético

Se implementarmos a fatorização real (B-médio) com os 3 padrões
de D2:

| Versão | D2 ref+dados | Comentário |
|---|---:|---|
| exp 08 (composição zero) | 610 | sintaxe mais simples por linha |
| exp 10 (composição completa) | 655 | semântica rica, mais bytes |
| **exp 12 estimado** | **574** | composição + fatorização |

Diferença vs exp 08: **-36 bytes (-5.9%)**.

Pela primeira vez no caminho composição, **B-médio venceria
exp 08 em bytes** em D2 mantendo a riqueza semântica. Os 81 bytes
de ganho de fatorização compensam os 45 bytes de overhead da
composição.

## Por que os outros datasets não ganham

D1 tem repetição de `suf` (todos `@gmail.com`) mas não de `(mid,
suf)` — porque cada `mid` é único. Para D1 ganhar com fatorização,
seria preciso outro tipo de padrão: por exemplo, `(pref, suf)` com
mid variável, mas isso exige parameterização (não testada aqui).

D3 e D4 não têm `suf` em nenhuma string (só pref). Fatorização
de `(mid, suf)` não se aplica. `(pref, mid)` também não repete
porque cada folha tem `mid` único.

## Pontos a registrar

1. **D2 é o único dataset com ganho potencial** (12.4%). É também
   o único dataset onde composição ativou (12 strings com pref +
   mid + suf), o que cria a oportunidade de fatorizar sub-expressões.

2. **Estimativa simbólica**: 81 bytes de ganho potencial em D2.
   Limite superior — exato neste caso porque padrões não se
   sobrepõem por string.

3. **Asymetria (mid, suf) vs (pref, mid)**: nenhum dataset teve
   padrões `(pref, mid)` significativos. Faz sentido — `(mid, suf)`
   é "lado direito" e tende a repetir em datasets com produto
   cartesiano (vários "donos" do mesmo "tipo"); `(pref, mid)` é
   "lado esquerdo" e exige que o mesmo "dono" apareça com várias
   variações específicas — menos frequente em colunas reais.

4. **Promissor para exp 12**: a estimativa indica que com a
   fatorização (B-médio), D2 sairia de 655 para ~574 bytes —
   melhor que exp 08 (610) e melhor que exp 10 (655). Mantendo a
   semântica completa do exp 10.

5. **Custo do exp 12**: implementar parser estendido para refs a
   nós compostos `(mid + suf)`, ajustar encode/decode, validar
   roundtrip. Médio. Vale a pena pelo ganho identificado em D2 e
   pelo padrão genérico (datasets com produto cartesiano são
   comuns no real — emails, identificadores nome+tipo, etc).

## O que este experimento NÃO mostra

- Implementação real da fatorização (B-médio).
- Bytes reais — só estimativa simbólica.
- Fatorização recursiva (Re-Pair completo) — apenas 1 nível.
- Padrões com parameterização (`(pref, ?, suf)` com mid variável).
- Comportamento em datasets maiores ou com mais repetições.
- Validação de roundtrip — não há encoding novo.

## Recomendação

Se o objetivo é diminuir o gap "semântica vs bytes" identificado
no exp 10, **exp 12 = B-médio justifica-se em D2** (ganho estimado
-5.9% vs exp 08, mantendo composição). Para D1, D3, D4 não há
ganho — exp 12 seria neutro nesses datasets.

Se o objetivo for outro (ex: testar composição em dataset com
forward hierárquico profundo), outro experimento seria mais
prioritário.

# Análise crítica — M1.A vs M1.B

Análise feita após implementar M1.A (escape pontual) e M1.B (quote
em grupo), **antes** de implementar M1.C/D. Baseada nos tokens
salvos em `tokens_dump/` e nos TCFs gerados em
`M1-A-escape/encoded/` e `M1-B-quote/encoded/`.

## Resumo bytes nos 4 datasets

| Dataset | M1.A | M1.B | Diff | Vencedor |
|---|---:|---:|---:|---|
| D1-emails-simples | **162** | **162** | 0 | empate |
| D2-emails-quote-id | 200 | **198** | -2 | M1.B (margem 1%) |
| D3-stress-substring | 242 | **233** | -9 | M1.B (margem 3.7%) |
| D4-caos-mix | **152** | 160 | +8 | M1.A (margem 5.3%) |
| **Total** | **756** | **753** | -3 | quase empate |

Cada técnica vence ~50% dos cenários. Diferenças entre 0-9 bytes
(0-5% do total).

## Inventário de fragmentos por categoria

### Fragmentos puros (sem dígito, sem `*`)

Emitidos RAW em ambas as sintaxes. **Custo de marcação: 0**.

| Dataset | Fragmentos puros / total |
|---|---|
| D1 | **12 / 12** (100%) |
| D2 | 11 / 18 (61%) |
| D3 | 9 / 15 (60%) |
| D4 | 4 / 13 (31%) |

A maior parte dos fragmentos já é **livre de ambiguidade**.
O algoritmo do exp 16 fatorou bem.

### Fragmentos com K chars ambíguos

Onde M1.A e M1.B diferem de fato:

| K | M1.A custo | M1.B custo | Vencedor |
|---:|---|---|---|
| 0 | 0 | 0 | empate (raw) |
| 1 | +1 (1 escape) | +2 (aspas) | M1.A |
| 2 | +2 | +2 | empate |
| 3 | +3 | +2 | M1.B |
| 4+ | +K | +2 | M1.B |

Tabela teórica simples — confirma observação empírica.

### Distribuição de K nos datasets

| Dataset | K=0 | K=1 | K=2 | K=3 | K=4+ |
|---|---:|---:|---:|---:|---:|
| D1 | 12 | 0 | 0 | 0 | 0 |
| D2 | 11 | 2 | 3 | 2 | 0 |
| D3 | 9 | 0 | 2 | 4 | 0 |
| D4 | 4 | 8 | 1 | 0 | 0 |

D4 tem **8 fragmentos K=1** → M1.A brilha aqui.
D3 tem **4 fragmentos K=3** → M1.B brilha aqui.

## Onde está a eliminação total

**Frase honesta**: a "eliminação total" já está acontecendo na
camada **algoritmo** (exp 16), não na sintaxe. 31-100% dos
fragmentos são emitidos sem nenhuma marcação.

A pressão de otimização **só existe em fragmentos K≥1**, que são
minoria.

## Onde poderia ser órfã

Órfã = marcador de abertura sem fechamento, deduzido pelo parser
(EOF/transição).

Inspeção das linhas TCF M1.B:

| Dataset | Linhas que terminam com literal aspas (candidatas a órfã) |
|---|---|
| D1 | 0 (todas terminam com ref) |
| D2 | 0 (todas terminam com ref ou literal raw) |
| D3 | 0 (idem) |
| D4 | 0 (idem) |

**Nenhuma candidata.** O algoritmo do exp 16 quase sempre coloca
um suf (ref) ao FIM da linha. Literal ambíguo nunca é o último
elemento.

**Conclusão**: órfã **não tem aplicação** com a estrutura atual de
tokens. Para órfã valer, seria preciso que o algoritmo
ocasionalmente emitisse literal **sem suf depois** — caso atípico.

## Onde uma forma facilita dedução sobre a outra

| Eixo | M1.A escape | M1.B quote |
|---|---|---|
| Decoder stateless? | **sim** | não (modo aspas) |
| Parse linear? | **sim** | não (busca aspa de fechamento) |
| Lookahead? | **não** | sim (procura `'` final) |
| Erro recuperável? | **sim** (char por char) | não (perde sincronia) |

**M1.A é estritamente mais simples de implementar** o decoder.
M1.B exige estado mas é mais econômico em bytes em alguns casos.

## Padrão visual nos casos extremos

### D4 eid=1 (M1.A vence por 4 bytes em 1 linha)

```
tokens: [L("[a]*'foo'@42")]
fragmentos: [a, ]*', foo, '@4, 2

M1.A: [a*]\*'*foo*'@\4*\2
M1.B: [a*']*\''foo*'\'@4''2'
```

**Por que M1.A vence aqui**: cada fragmento tem K=1 (uma estrela ou
um dígito isolado). M1.B precisa aspas+escape do `'` interno em
fragmentos com `'`. M1.A só escapa o char ambíguo isolado.

### D3 eid=1 (M1.B vence por 3 bytes em 1 linha)

```
tokens: [L('api/users/00042/profile.json')]
fragmentos: api, /, users/00, 042, /profile, ., json

M1.A: api*/*users/\0\0*\0\4\2*/profile*.*json
M1.B: api*/*'users/00''042'/profile*.*json
```

**Por que M1.B vence aqui**: o fragmento "users/00" tem K=2 e
"042" tem K=3. M1.A precisa 5 escapes. M1.B usa 2 pares de aspas
(+4 chars total) mas economiza em chars de dígito.

## Insight central da análise

O **trade-off é estrutural**, não acidental:

- **M1.A**: paga proporcional a K (chars ambíguos). Linear.
- **M1.B**: paga constante por fragmento ambíguo (+2). Constante.

Logo:
- Em datasets com **muitos fragmentos K=1** (dispersos): M1.A vence
- Em datasets com **poucos fragmentos K≥3** (concentrados): M1.B vence
- Em datasets sem fragmentos ambíguos: **empate** (raw)

**Não há técnica que engula a outra em todos os regimes.**

## Alternativas não exploradas (vale considerar?)

### Escape com escopo (M1.A variante)

Em vez de `\X` por char, `\` antes da sequência sinaliza "tudo até
próximo `*` é literal".

Exemplo D3 fragmento "042": M1.A faz `\0\4\2` (+3). Escape-escopo:
`\042` (+1). Vence para K≥2.

Custa parser stateful pequeno (modo escape-escopo até `*`). Equivalente
a aspas mas com `\` como abridor único.

### Órfã condicional (M1.B variante)

Em vez de aspas pareadas, **abrir** com `'` e fechar com `*` ou EOL.

`'042*` em vez de `'042'`. Ganha 1 byte por fragmento ambíguo.

Mas requer que o `*` SEMPRE venha depois (separador). Pode dar
conflito se literal seguir literal.

### Substituição local de marcador

`\` antes de dígito é o mais comum. Que tal trocar `\` por `_` ou
outro char livre? Não economiza nada — só renomeia.

### M1.C (sumida) — não implementada ainda

Promete economizar quando idx N não existe. Pelo exp 28, ganho
foi 1-2 bytes em D2/D3. Marginal.

### M1.D (slice arbitrário) — não implementada

Promete capturar substring central. Pelo exp 28, potencial 2-5
bytes em D2/D3. Marginal.

## Recomendação para próxima sessão

Considerando que:

1. M1.A e M1.B são **complementares** (cada um vence em regime
   próprio)
2. Diferenças são pequenas (0-9 bytes, 0-5%)
3. Órfã não tem aplicação no contexto atual
4. M1.C e M1.D prometem ganhos marginais (1-5 bytes adicionais)
5. **A maior fonte de compressão é o algoritmo do exp 16**, não a
   sintaxe

3 caminhos possíveis:

### Caminho 1 — Implementar M1.C e M1.D (completar plano)

Mantém o plano original. Ganho esperado: 1-5 bytes adicionais por
dataset. Custo: 2 sessões.

### Caminho 2 — Pular para F2/F3 (consolidar com 2 técnicas)

Fecha M1 com apenas M1.A e M1.B. Decide a partir das diferenças
medidas:
- Se um regime domina (datasets reais), escolhe a técnica para ele
- Se não há regime dominante, marca como complementares e abre M2
  (mistura adaptativa)

Custo: 1-2 sessões. **Mais econômico.**

### Caminho 3 — Implementar 1 variante minimalista (escape escopo)

Pular M1.C/D originais e tentar uma técnica nova:
**M1.A' — escape com escopo** (`\` abre, próximo `*` fecha). 

Conceitualmente é "escape + órfã" combinados. Pode vencer M1.A em
K≥2 e bater M1.B no agregado.

Custo: 1 sessão. **Maior chance de novidade.**

## Recomendação pessoal

**Caminho 3** (M1.A' escape com escopo). Razões:

- É a variante MAIS PROMISSORA dado a análise: M1.A perde em K≥2
  por ser "char por char". M1.A' resolve isso.
- Mantém a propriedade boa de M1.A (parser stateless ou quase)
- Economiza o que ambas perdem nos casos K=2,3
- Implementa rápido (1 sessão)

Se M1.A' empatar com M1.B no agregado, está claro: **as duas
técnicas são equivalentes em bytes mas M1.A' tem decoder mais
simples** — escolha por simplicidade.

Se M1.A' ganhar de M1.B, fecha o macro com 3 técnicas testadas e
M1.A' como vencedora.

Se M1.A' perder, o trade-off fundamental fica claro: complementares.

## Notas técnicas para registro

1. **Algoritmo do exp 16 já elimina 40-100% dos fragmentos
   ambíguos**. A sintaxe disputa só os 0-60% restantes.

2. **K=1 e K≥3 são os pontos de divisão**. K=2 é sempre empate.

3. **Órfã/sumir não tem aplicação atual** — algoritmo coloca ref no
   fim de linha sempre.

4. **`'` interno em literal com aspas custa +1 byte de escape** —
   prejudica M1.B em datasets com aspóstrofos (sobrenomes
   irlandeses, etc.).

5. **Diferenças <10 bytes em 200B totais** indicam que a "sintaxe
   ótima" é uma decisão de **gostos** (simplicidade vs bytes),
   não de **viabilidade**.

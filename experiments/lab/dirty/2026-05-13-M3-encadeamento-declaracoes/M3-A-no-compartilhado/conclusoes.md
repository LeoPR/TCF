# Conclusoes M3.A — No compartilhado simples

## Resultado

**Net 0 em todos os 4 canonicos** (D1=D2=D3=D4 igual a M1.E baseline).
Detector nao selecionou nenhum alias — todos candidatos tiveram
net <= 0.

## Diagnostico estrutural

### Por que serializacao real e' mais curta que estimei

Estimativa inicial (D1, S(5,11)="hotmail.com" em eids 6,7,8):
- "Refs sao [3,11,5,6] (4 refs)" → Lr=8 chars
- Net previsto = 3·6 - 15 = +3

Realidade (instrumentando):
- Refs sao **[11,5,6]** (3 refs) → Lr=6 chars
- Net real = 3·4 - 15 = -3

Diferenca: eid 6 tem **dois subs** consecutivos:
1. `P(2,6)` herda 3 frags do eid 2: [7,8,3]
2. `S(5,11)` herda 3 frags do eid 5: [11,5,6]

O fragmento "@" (frag 3 do eid 1) e' parte do P(2,6) — NAO do
S(5,11). M1.E serializa **ambos os subs agregados como uma unica
lista** `7,8,3,11,5,6` (12 chars), mas o "@" (frag 3) pertence ao
prefixo, nao ao sufixo.

Se eu substituir SO o sufixo por &N, sobra `7,8,3&1` ou similar —
nao economiza o "@".

## Por que M3.A simples nao escala em D1-D4

Lt (texto da substring) tipicamente >= 8 chars (ex: "hotmail.com" 11,
"yahoo.com" 9, "joao@" 5).

Lr (chars da serializacao M1.E) tipicamente 4-6 chars (3 frags, com
ou sem range).

Net = R·(Lr-2) - (3+Lt)

Para Lr=4, Lt=5: Net = R·2 - 8 → R >= 4 para ganho. Mas R=2 nos
canonicos.

Para Lr=6, Lt=11: Net = R·4 - 14 → R >= 4. Mas R=3 nos canonicos.

**M1.E ja' comprime refs de modo agressivo via range, deixando pouco
espaco para M3.A simples ganhar.** A serializacao M1.E e' competitiva
exatamente porque os frags do eid ancestral sao referenciados
contiguamente.

## Onde M3.A SIMPLES poderia ganhar (hipoteses nao testadas)

1. **Datasets com R >> 3** (famílias grandes). Em N=100 strings da
   mesma familia, R pode ser 50+. Net cresce linearmente com R.
2. **Substrings curtas** com refs longas (ex: literais com escape
   escopo `\103` virando lit `103` no alias) — caso especifico.
3. **Strings muito longas** (m grande) onde Lt e' grande mas refs
   ainda sao curtos.

Nos canonicos D1-D4: nada disso acontece. M3.A simples nao ataca
o regime.

## Quando M3.B (encadeamento) ganharia

A hipotese do user e' especificamente sobre **encadeamento**
(`&N=&P+ext`), nao no compartilhado simples. Em hierarquia profunda:

- Lab 20 antigo: C7 URLs subpath -72.4% vs literal
- Lab 21 antigo: C9 URLs 4 niveis -61.6%

D1-D4 nao tem hierarquia profunda (2-3 niveis no maximo). Para
provocar M3.B, precisa datasets com hierarquia 4+ niveis.

## Decisao

M3.A FECHA com net 0 nos canonicos. Conclusao:
- M3.A simples e' estruturalmente equivalente a M1.E nos datasets
  testados
- Hipotese real do user (nos compostos) requer **encadeamento**
  (M3.B) para mostrar valor
- Datasets canonicos nao disparam o regime onde M3.A simples
  ganharia

## Proximos passos

Opcao A: Implementar M3.B (encadeamento profundo) com dataset
enviesado pra hierarquia (data_extra/ DE7-hierarquia-profunda).

Opcao B: Fechar M3 inteiro como "dimensao mapeada, sem ganho no
regime exp 16 + D1-D4" e ir pra prototipo.

Opcao A e' mais informativa (replica Lab 20-21 com metodologia
atual). Opcao B e' mais rapida.

## Limitacao metodologica reconhecida

Datasets D1-D4 foram desenhados para mapear semantica de marcacao
(M1) e redundancia entre linhas (M2). **Nao foram desenhados para
disparar redundancia em declaracao** (M3).

Para M3 funcionar bem, precisaria datasets com:
- Hierarquia 3+ niveis em prefixos
- R alto (familias homogeneas)
- Padroes ortogonais (ORG-DEPT-USER-ID)

Estes existem em dados reais (URLs estruturadas, paths) mas nao em
D1-D4 sinteticos.

Issue documentada como "data_extra/" pendente.

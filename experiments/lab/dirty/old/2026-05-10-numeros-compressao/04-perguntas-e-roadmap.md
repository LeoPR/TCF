# Perguntas abertas e roadmap das próximas mesas

Síntese do que esta mesa de pesquisa identificou como **lacunas** e a
ordem proposta para preenchê-las.

---

## Perguntas abertas (formalizadas)

### Q-N1 — Generalização do δ

O δ atual é acumulativo (Δᵢ = vᵢ - vᵢ₋₁). Para oscilações em torno de
baseline, melhor seria não-acumulativo (Δᵢ = vᵢ - B).

Q: A flag δ deve ter sub-modo `δ-baseline`, ou nova flag (`B`)?

**Hipótese**: sub-modo. `# ext: tensao=delta:mode=baseline:value=110`.

**A testar**: dataset IoT com oscilação real. Comparar acumulativo vs
baseline.

### Q-N2 — Detecção automática de baseline

Encoder pode detectar baseline analisando a coluna (média, mediana, moda).

Q: Qual estatística é mais útil para minimizar bytes de delta?

**Hipótese**: para distribuições aproximadamente gaussianas, média
minimiza |Δ| médio; para outras, mediana.

**A testar**: simulação com várias distribuições.

### Q-N3 — Sum-preserving — qual algoritmo?

Largest Remainder, Sainte-Laguë, D'Hondt, etc. Cada um aloca o "erro"
de forma diferente.

Q: Qual gera a codificação mais compacta após dict/RLE? Ou a diferença
é desprezível?

**Hipótese**: Largest Remainder com escala mínima é o mais eficiente
em bytes (poucos valores ajustados).

**A testar**: dataset financeiro (preços, parcelas) com diversos
algoritmos de apportionment.

### Q-N4 — Erro como coluna paralela compensa?

Codificar valores quantizados + erros separadamente: o overhead da
coluna extra fica menor que o ganho do quantizado?

Q: Em quais condições erro paralelo vale a pena?

**Hipótese**: erro paralelo vale quando:
- Erros têm cardinalidade << N (dict eficaz)
- OU quando a aplicação precisa do reconstituível em alguns casos
  (negocia)

**A testar**: comparar (a) só quantizado + assumir perda; (b)
quantizado + erro coluna; (c) lossless original.

### Q-N5 — Operação-aware é parte do TCF?

Permitir `# usage: valor=sum-stable` no header diz à TCF qual a
intenção da aplicação.

Q: TCF deve aceitar isso ou é fronteira de responsabilidade
(aplicação decide)?

**Argumentos a favor**: encoder pode escolher quantização melhor
sabendo a intenção.

**Argumentos contra**: cria contrato semântico mais forte; fronteira
fica turva.

**Decisão sugerida**: por agora, NÃO. Aplicação faz pré-quantização
fora do TCF e passa valores prontos. TCF expõe `# ext: <col>=quant:step`
mas não interpreta uso.

### Q-N6 — Quantização adaptativa por bloco

A precisão pode mudar entre blocos. Ex: fase A do dataset tem precisão
de 0.1, fase B precisa de 0.001.

Q: TCF suporta quantização variável por bloco/chunk ou só por coluna
inteira?

**Hipótese**: por coluna por chunk. Liga com a mesa de chunks
(transporte) ainda pendente.

### Q-N7 — Predictive coding (regressão linear) vale a pena?

Para coluna com tendência linear forte: armazenar (a, b) + resíduos é
menor que delta?

Q: Qual o ponto de virada — quanta tendência precisa ter?

**Hipótese**: quando R² > 0.9 e N > 100, regressão começa a vencer.

**A testar**: simulação com tendências de várias intensidades.

### Q-N8 — Frame-of-Reference em texto

FOR clássico é bit-pack. Em texto, equivale a "delta com baseline
fixo + RLE/dict nos offsets".

Q: Vale codificar FOR explicitamente como flag separada, ou ele já
emerge da combinação δ-baseline + dict?

**Hipótese**: emerge. Não vale flag dedicada.

---

## Tickets de pesquisa abertos (a virar mesas futuras)

### T-N-IoT-baseline (próxima mesa numérica)

**Problema**: oscilação em torno de baseline, padrão B do `01`.

**Dataset necessário**: tensão IoT 110V × 100-1000 amostras com ruído
gaussiano.

**Investigar**:
- δ-acumulativo vs δ-baseline em bytes
- Detecção automática de baseline (média, mediana, moda)
- Quantização adicional (granularidade da medição)

**Cobre**: Q-N1, Q-N2.

### T-N-financial-sum-preserving

**Problema**: dataset financeiro com necessidade de soma exata + economia
de bytes.

**Dataset necessário**: 1000 transações com 2 casas decimais, soma a
preservar.

**Investigar**:
- Largest Remainder vs alternativas
- Bytes ganhos vs lossless
- Verificação automática de soma

**Cobre**: Q-N3.

### T-N-erro-paralelo

**Problema**: vale a pena guardar o erro em coluna anexa?

**Dataset necessário**: qualquer um com quantização aplicada (real ou
sintético).

**Investigar**:
- Distribuição típica do erro de quantização
- Cardinalidade do erro (dict vale?)
- Custo da coluna extra vs ganho da quantização

**Cobre**: Q-N4.

### T-N-regressao-linear

**Problema**: tendência linear vale ser modelada?

**Dataset necessário**: série temporal com tendência (vendas, métricas
crescentes).

**Investigar**:
- Ponto de virada (a partir de qual N e R²)
- Custo do (a, b) em texto
- Resíduos: dist e compressibilidade

**Cobre**: Q-N7.

---

## Roadmap proposto

### Curto prazo (próximas 2-3 mesas)

1. **T-N-IoT-baseline** — começar pela técnica mais imediata e
   genérica. Generaliza δ; mesmo dataset que IoT real (acessível).
2. **T-N-financial-sum-preserving** — a inovação mais original que o
   usuário levantou. Depois do δ generalizado.
3. **Mesa P (prefix elision)** já estava planejada — pode entrar antes
   ou depois das numéricas, conforme dataset disponível.

### Médio prazo

4. **T-N-erro-paralelo** — depende das anteriores para ter contexto.
5. **Mesa L' (line-RLE)** — datasets de log/eventos.
6. **T-N-regressao-linear** — após validar técnicas mais simples.

### Longo prazo (depois das mesas de extensões)

7. **Voltar à mesa de transporte** (chunks).
8. **Protótipo Python** validando todas as flags + extensões.
9. **TCF-binary** (dialeto opcional) — se demanda justificar.

---

## Decisões pré-aprovadas para v0.5+

Independente das mesas pendentes, alguns acrescentos numéricos podem
entrar agora:

### Quantização uniforme — flag δ existente

`# ext: valor=quant:step=0.01` declara arredondamento ao step. Encoder
arredonda; decoder retorna arredondado. Aplicação aceita por contrato.

Não muda hierarquia Lxxx. É sub-modo de δ ou flag nova `Q`?

→ **Decisão**: nova flag `Q` (quantization). Δ é para sequencial, Q é
para precisão. Conceitualmente diferentes.

### Hierarquia Lxxx (atualizada)

```
flags = SRDMA + δ + Π + I + Q + ...

Q = quantization (per-column via # ext)
```

Compatível com tudo já decidido.

---

## O que sai desta mesa de pesquisa

1. **Catálogo organizado** das técnicas conhecidas
2. **Mapeamento padrão → técnica**
3. **Lacunas identificadas** (sum-preserving, erro paralelo)
4. **Roadmap de mesas experimentais** com datasets sugeridos
5. **Flag Q proposta** para v0.5 (quantização explícita)
6. **Distinção sólida**: lossless / lossy controlado / lossy estatístico

---

## Princípio extraído

A pesquisa-primeiro evitou:
- Inventar do zero coisa que já existe (apportionment, FOR, Gorilla...)
- Confundir técnicas binárias com text-friendly
- Misturar quantização (lossy) com delta (lossless)

→ Para próximas mesas com tópicos novos (outras dimensões de dado,
estruturas mais exóticas), repetir o **modo pesquisa primeiro** quando
o espaço de soluções é grande e bem-estudado fora.

---

## Atualizações no PROGRESSO geral

Adicionar:
- Mesa de pesquisa numérica (esta) concluída
- Tickets T-N-IoT, T-N-financial, T-N-erro, T-N-regressao abertos
- Flag Q (quantization) reservada na hierarquia Lxxx

Em `docs/workbench/PROGRESSO-formato-v05-2026-05-09.md` (atualizar com
data 2026-05-10).

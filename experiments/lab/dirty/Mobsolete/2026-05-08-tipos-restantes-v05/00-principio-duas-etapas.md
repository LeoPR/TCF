# Princípio das duas etapas — algoritmo separado da representação

**Data:** 2026-05-08

Princípio meta-conceitual que organiza todo o trabalho do TCF e
estabelece a fronteira de v0.5.

---

## A separação

Compressão de dado tem duas etapas independentes que devem ser tratadas
**separadamente**:

### Etapa 1 — Algoritmo lógico em ASCII/decimal

Mantém os dados em representação **textual humano-legível**:
- Números em decimal (`0-9`)
- Strings literais
- Datas em ISO 8601
- Caracteres ASCII printáveis

Aceita-se "desperdício" computacional: cada caractere ocupa 8 bits de
byte mas carrega ~3.3 bits úteis de informação decimal (log₂(10) ≈ 3.32).
**Estamos usando ~40% da capacidade física do byte.**

**Foco da Etapa 1**: correção e elegância do algoritmo de compressão.
- A regra unificada (RLE+dict) funciona?
- Sort multi-chave compõe bem?
- Delta + RLE captura padrões sequenciais?
- Quantização sum-preserving fica matematicamente correta?

### Etapa 2 — Otimização da representação computacional

Depois que o algoritmo da Etapa 1 está validado, **substitui-se** a
representação por algo mais denso:
- Índices em alfabetos densos (hex, base64, binário) — ticket
  S-representacao-de-indice
- Empacotamento de absolutos (Π) — já implementado parcialmente
- Bit-packing de runs — futuro
- Dialeto TCF-binary completo — futuro distante

**Foco da Etapa 2**: aproveitar o restante do byte físico.

---

## Por que separar

### 1. Validação algorítmica primeiro

Bugs de compressão lossy (sum-preserving quebrado, delta com overflow)
são quase impossíveis de debugar em representação binária. Em ASCII
decimal, basta abrir o arquivo no editor.

### 2. Comparação justa

Quando comparamos δ+RLE vs delta puro, queremos comparar **o algoritmo**,
não "qual codifica melhor em base64". Isolar variáveis.

### 3. Compatibilidade com gzip downstream

A questão "TCF + gzip recupera o que TCF não fez?" só é respondível se
TCF e gzip têm zonas distintas de atuação. Etapa 1 deixa redundância
exploitável; Etapa 2 a remove. Cada uma serve um pipeline.

### 4. LLM como consumidor

LLM lê texto. ASCII decimal é o que o LLM processa. Se TCF for sempre
binário, perde-se o caso de uso central. Etapa 1 = TCF para LLM.
Etapa 2 = TCF para storage/network bulk.

### 5. Previne reinvenção

Etapa 2 já tem técnicas binárias maduras (varint, Gorilla XOR, Frame-of-
Reference, ZFP). Não vale gastar tempo "inventando" se a Etapa 1 ainda
tem coisa para fechar.

---

## Onde estamos

Toda a base do TCF v0.5 está sendo construída na **Etapa 1**:

| Decisão | Etapa | Status |
|---|---|---|
| Regra unificada (RLE+dict) | 1 | madura |
| Sort multi-chave | 1 | madura |
| δ acumulativo | 1 | madura |
| δ multi-escala (timestamps) | 1 | madura |
| Auto-discriminador bare/marcado | 1 | madura |
| Alfabeto adaptativo (letras) | 1.5 | madura — único elemento "Etapa 2" embutido por ganhar muito |
| Empacotamento Π de absolutos | 1.5 | madura — pequena entrada em Etapa 2 |
| Inline mode (I) | 1 | madura |
| Quantização Q | 1 | proposta |
| Sum-preserving | 1 | pesquisa em andamento |
| Bit-packing | 2 | deferido |
| TCF-binary dialeto | 2 | deferido |
| Gorilla XOR para floats | 2 | deferido |

A flag `A` (alfabeto) e `Π` (packed) são pequenas concessões à Etapa 2
porque o ganho em chars é grande sem perder legibilidade catastrófica.
Tudo mais binário fica deferido.

---

## Implicação para fechar v0.5

V0.5 = **toda a Etapa 1** + as duas concessões pequenas (A, Π).

Para fechar, falta:
1. **Cobrir os tipos de dado restantes** (próximo arquivo inventaria)
2. **Validar algoritmos com protótipo** Python
3. **Testar em escala** (TPC-H ou similar)

Etapa 2 começa em **v0.6 ou TCF-binary** (paralelos), não bloqueia v0.5.

---

## Princípio operacional

> "Vamos desperdiçar espaço olhando como ASCII/números, e depois fazer
> as otimizações extras, assim como pensamos pro índice e pra data.
> Separar isso permite a gente pensar na forma do algoritmo e depois no
> espaço computacional que ele ocorre de fato."

Esta frase do usuário fica como princípio ordenador. **Algoritmo
primeiro, representação depois.** Sempre.

---

## Próximos arquivos

| Arquivo | Conteúdo |
|---|---|
| `01-inventario-completo.md` | Lista exaustiva de tipos de dado, com status de cobertura |
| `02-fechamento-v05.md` | O que falta cobrir para encerrar a Etapa 1 / v0.5 |

# M4.C1' — Batch greedy com subsequencias contiguas

## Tecnica

Estende M4.C1 v1. Detector identifica **subsequencias contiguas
internas de runs** (nao apenas runs inteiras). Sintaxe identica:
`~SUBSEQ~` na 1a aparicao, `&N` nas seguintes.

## Detector iterativo

```
loop:
  conta sub-tuplas contiguas K>=2 sobre runs atuais
  escolhe maior net (R-1)*(Lr - 1 - len(N)) - 2
  se net <= 0: para
  substitui em todas runs (divide em pre + alias + pos)
```

Custo: O(N · L² · iter) por dataset.

## Resultado nos canonicos

| Dataset | M1.E | M4.C1 v1 | **M4.C1'** | delta vs M1.E |
|---|---:|---:|---:|---:|
| D1 | 149 | 148 | **138** | -11 (-7.4%) |
| D2 | 180 | 178 | **174** | -6 (-3.3%) |
| D3 | 206 | 203 | **196** | -10 (-4.9%) |
| D4 | 141 | 137 | **128** | -13 (-9.2%) |
| **TOTAL** | **676** | **666** | **636** | **-40 (-5.9%)** |

RT 12/12 OK (4 datasets × 3 sintaxes).

## Comparacao com baselines

| Tecnica | Total | delta vs M1.E |
|---|---:|---:|
| M1.E (baseline) | 676 | 0 |
| M2.A (sufixos de runs, com preambulo $N) | 666 | -10 (-1.5%) |
| M4.C1 v1 (runs inteiras, idx implicito) | 666 | -10 (-1.5%) |
| **M4.C1' (subsequencias, idx implicito)** | **636** | **-40 (-5.9%)** |

M4.C1' captura ~35% do limite teorico (114B intermediario
implicito do M4.A) — o resto fica em conflitos entre candidatos
sobrepostos que greedy nao resolve otimo.

## Casos concretos capturados

### D1 — sufixo `3,11,5,6` repetido 3x (linhas 7-9)
```
M1.E:    7,8,3,11,5,6 / 9,2,3,11,5,6 / 10,8,3,11,5,6
M4.C1':  7,8,~3,11,5,6~ / 9,2,&2 / 10,8,&2
```
Economiza: 6+6 (-`3,11,5,6` vs `&2`) por linha 2-3 = ~12 bytes
no D1.

### D4 — `2..4` em sufixo + meio
```
M1.E:    1..4\3 / 1..4\4 / [b2..5 / 8,2..4\3 / 8,2..4\4
M4.C1':  1,~2..4~\3 / 1,&1\4 / [b&1,5 / 8,&1\3 / 8,&1\4
```
`&1=2..4` reusado 5 vezes. Inclusive em meio de `[b...,5`.

## Bugs encontrados e corrigidos

1. **Separador `*` perdido entre lit-digit-seq e refs**: Linha
   `12\4214,6,7` deveria ser `12\42*14,6,7`. Fix: condicao
   explicita `if prev_tipo == 'lit' and prev_emit_termina_em_digito`.

2. **Ordem de alocacao de idx**: encoder alocava por net descending;
   decoder aloca por ordem de `~` no TCF. Fix herdado de M4.C1 v1
   (alocacao por 1a aparicao no body).

## Limitacoes

- **Greedy nao otimo**: candidatos sobrepostos competem; escolha
  do maior pode bloquear combinacoes melhores
- **Linear scan O(L²)**: para datasets grandes precisa estrutura
  indexada (registrado em `notas/indice-incremental-de-padroes.md`)
- **`~` e `&` reservados**: literais com esses chars precisam
  escape (raros em D1-D4)
- **Batch only**: nao testado em streaming (cabera em M4.C2 se
  vier)

## Estrutura

```
M4-C1p-batch-subsequencias/
  README.md       (este)
  syntax.py
  output/         TCFs gerados
  decoded/        contra-prova
  debug/          detalhado
```

## Como rodar

```bash
cd 2026-05-13-M4-desfragmentacao-arvore
python run_lote.py
```

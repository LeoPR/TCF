# 02 — patricia em nomes (roundtrip)

## Princípio / motivação

Nasceu sob o reset v0.6 (2026-05-10). Refazer do zero a árvore Patricia
como ferramenta de identificação de nós, sem importar nada de
`dirty/old/`. Verificar se serve como base de busca/dedupe e se RLE
adjacente emerge naturalmente da serialização do body — ou se RLE
precisa ser tratado como camada separada.

Ferramenta atemporal: a árvore aqui pode ser usada para indexar
qualquer coluna de string em experimentos futuros, independente da
versão do formato.

## Propósito

Responde a duas das quatro perguntas:

1. **Viabilidade**: a árvore Patricia consegue resolver
   busca + dedupe + roundtrip num CSV de 1 coluna?
2. **Comportamento**: RLE adjacente emerge como subproduto da
   serialização do body? Em quais cenários ela não acontece?

## Comparação

- Compara com: nenhum.
- É comparável? Não. É experimento **paralelo de viabilidade**:
  primeira execução da Patricia v0.6, sem baseline a vencer.
- Não há afirmação "melhor" ou "pior" comparando a outra ferramenta
  ou a versões antigas. Os números reportados são descritivos do
  comportamento observado.

## Cenários e valores possíveis

Dois cenários sintéticos, fixos:

| Cenário | Linhas | Conteúdo | Hipótese sobre Patricia |
|---|---|---|---|
| **A** | 50 | `Ana`, `Bob`, `Carlos`, `Diana`, `Edu` (cardinalidade 5) com runs adjacentes e dispersão | Sem prefixos comuns ≥ 3 chars → Patricia não fatora; degrada para DICT simples |
| **B** | 30 | `USR0001..USR0010` (10) + `PRD0001..PRD0005` (5) misturados | Com prefixos compartilhados → Patricia fatora hierarquia |

Parâmetros do algoritmo (constantes em [patricia.py](patricia.py)):

- `MIN_PREFIXO = 3` — só fatora se prefixo comum tem ≥ 3 caracteres.
- `MIN_GRUPO = 2` — só fatora se prefixo aparece em ≥ 2 folhas top-level.

Marcadores TCF deliberadamente verbosos:
- `no1 = folha "Ana"`
- `no3 = filho_de(no1) + "1"`
- `2x ref:no1`

Otimização de bytes não é alvo deste experimento.

## Resultado observado

Saídas:

- Algoritmo: [algoritmo.md](algoritmo.md) — descrição em 3 fases.
- Conclusões: [conclusoes.md](conclusoes.md) — comportamento observado
  por cenário, com árvore ASCII e amostras do TCF.

Numéricos do roundtrip (descritivos):

| Métrica | Cenário A | Cenário B |
|---|---|---|
| linhas input | 50 | 30 |
| nós total | 5 | 18 |
| nós top-level | 5 | 2 |
| nós filhos (Patricia) | 0 | 16 |
| body bruto (entradas) | 50 | 30 |
| body com RLE adjacente | 33 | 20 |
| RLE runs (rep > 1) | 14 | 9 |
| TCF tamanho (bytes) | 624 | 901 |
| roundtrip | OK | OK |

Em A, Patricia não fatorou (esperado: nomes não compartilham prefixos
≥ 3 chars). Em B, fatorou recursivamente: criou `USR00`, depois
`USR000` dentro, depois `PRD000` separado.

## Limitações

- Cardinalidade muito baixa (5 e 15 valores únicos): este experimento
  **não fala sobre escala**. Comportamento em cardinalidade média/alta
  é matéria de outro experimento.
- `MIN_PREFIXO=3` e `MIN_GRUPO=2` são heurísticas escolhidas para
  o demonstrativo. Resultado para outros valores não foi medido.
- Marcadores verbosos inflam bytes; comparar bytes desta serialização
  com formatos compactos (CSV, JSON, TCF compactado) seria
  comparação **não pertinente**.
- Cenário B tem prefixos uniformes por construção. Quando vários
  prefixos coexistem com sobreposição parcial, a heurística gulosa
  pode produzir árvores diferentes — não testado aqui.
- O algoritmo trata strings exatas. Não trata variações de
  capitalização, espaços, encoding diferente. Cada variação é uma
  folha distinta.
- RLE adjacente foi aplicado no body. Não há RLE "dentro" de um nó
  (como `2xAna` no próprio nó). Decisão registrada em
  [algoritmo.md](algoritmo.md).

## Como reproduzir

```bash
cd experiments/lab/dirty/2026-05-10-02-patricia-nomes
python run.py
```

Saída no console mostra contagens, árvore ASCII e status do roundtrip
para cada cenário. Arquivos gerados: `encoded/input-{A,B}.tcf` e
`decoded/input-{A,B}.csv`.

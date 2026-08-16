# Procedência — o mesmo cadastro, e a variável é a GRAFIA do header

## O dado

**Importado** de `../2026-08-16-1400-cadastro-popular-header-do-M/run.py::cadastro()` — os
mesmos 500 registros, seed 20260815. Terceiro lab da série a usar a mesma base (`1400` header,
`1450` ordem, `1530` piso+fronteira), de propósito: **os números são comparáveis entre eles**.

**A CONSTANTE**: os valores nunca mudam. Muda só (a) a grafia do header (`drop_names`,
`min_header`, com/sem spec) e (b) **quem decoda e em que ordem** (serial, embaralhado,
paralelo).

## O caso de 2 colunas (Bloco 1)

`{"a": ["x","y"], "b": ["p","q"]}` — reproduz o cenário mínimo do O-FMT-11 para comparar o
piso do header contra a medição de 2026-07-05. **Unidade importa**: O-FMT-11 mediu **header**
(13 B = `#TCF.8M!14,!\n`), não wire — a primeira versão deste lab comparou wire contra header
e errou por 5 B. Corrigido.

## A curva de break-even — e o viés que ela quase teve

Primeira versão: colunas `v0..vN`. **Errada** — é progressão, o seq-RLE a esmaga, o corpo não
cresce com N e a curva ficava artificialmente alta (N=20 e N=100 davam wire idêntico de 53 B).

Versão medida: fatias reais de `nome` e `email` do cadastro. É a mesma classe de viés do lab
`0530` (amostragem espalhada destruindo a adjacência): **dado sintético regular esconde a
variável**.

## O decode paralelo (I4)

`ThreadPoolExecutor` com 1 worker por coluna, cada um recebendo **só o seu recorte de bytes**.
Não é medição de desempenho — é **prova de correção**: o resultado tem de ser idêntico ao
`decode()` público. Nenhum tempo é reportado, de propósito.

## Vieses declarados

- **Uma tabela, uma seed, 7 colunas.** As invariantes são estruturais (saem da gramática), mas
  foram exercitadas sobre 4 modos (`tcf`, `raw`, `dict`, `split`) e 1 nature — não sobre todas
  as combinações possíveis.
- **Threads, não processos.** I4 prova independência lógica; não prova ausência de estado
  global compartilhado sob processos (o `parallel=` do encode já usa `ProcessPoolExecutor` e é
  byte-idêntico, mas isso é do encode, não do decode).
- **Os 4 B do `min_header=False` são deste header.** O custo é `len(size_hex da última)+1`;
  tabela com última coluna maior paga mais.

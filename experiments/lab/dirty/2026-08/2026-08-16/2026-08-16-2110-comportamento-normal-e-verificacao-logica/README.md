# Comportamento normal + verificação lógica dos welds C1/C2/C3

> **Owner (2026-08-16)**: *"precisamos de algumas simulações pra ver se ele está resistente
> mesmo, e até uma verificação lógica do código, pois se ele está determinístico não tem
> porque achar que o código vai 'pifar' sem seguir ao menos alguma lógica. O teste em massa
> que dirá isso depois, mas agora é só pra testar comportamento simples e normal."*
>
> E a regra de processo, aceita: *"mesmo código temporário tem que ser colocado no mesmo lab,
> pois pertence a ele... o que não pode é largar código sem evidência."* — **toda** sonda
> deste ciclo está aqui dentro, incluindo a do subprocesso de determinismo.

## A tese

Você está certo de que, sendo determinístico, não faz sentido supor que "pifa" sem lógica.
E há algo melhor que testar: **os três guards decidem sobre espaços FINITOS**. Onde o espaço
é finito, dá para **enumerar** — e enumeração exaustiva não é evidência estatística, é
cobertura total.

| weld | a decisão é sobre | o que o lab faz |
|---|---|---|
| **C1** | 1 caractere (o discriminador) | enumera os **128 chars ASCII**: 126 rodam o pré-passe, 2 pulam (`M`,`H`) — partição total e disjunta |
| **C2** | multiconjunto de nomes | enumera **150 combinações** (k=2 e k=3 sobre 5 símbolos): levanta em 82, **coerente com a definição em 150/150** |
| **C3** | a FORMA do argumento | enumera a **taxonomia da API** (8 formas) + os **subconjuntos de colunas** (5 casos) — 8/8 e 5/5 |

## O que foi verificado, além da enumeração

- **Determinismo**: 20 encodes no mesmo processo → **1 wire**. E 5 processos com
  `PYTHONHASHSEED` diferente (`0`, `1`, `42`, `12345`, `random`) → **1 hash**. Isso descarta
  a suspeita mais plausível de não-determinismo em Python: ordem de iteração de `set`.
- **Pureza** do guard do C2: duas chamadas dão o mesmo, e o argumento sai intacto.
- **Nenhuma regressão**: os discriminadores que o encode emite são `\n`, `!`, `H`, `M`, `n`;
  os que **mantêm** o pré-passe (`\n`, `!`, `n`) não são `M`/`H`, logo nenhum caminho
  polarizado legítimo foi afetado.
- **Caminho normal, ponta a ponta**: 7 operações do dia a dia (tabela, com spec, sem nomes,
  todos com size, coluna única, registros `.8H`, datas com spec), todas com RT gravado, mais
  `view` com `select` e `where` conferidos contra a verdade.

## Dois erros MEUS que o lab pegou (e nenhum era do código)

1. **`drop_names` comparado por chave.** Com ele os nomes viram posicionais **por design**
   (ADR-0029) — a prova tem de ser por VALORES. **Terceira vez que escrevo esse assert
   errado**; agora o `grava_caso()` tem um parâmetro `posicional` que **obriga a declarar a
   semântica**, e o `meta.json` grava qual prova foi usada.
2. **`list[list]` classificado como "aceita".** Ele é rejeitado — mas pelo **`.8H`**, com
   mensagem própria e mais informativa (*"não é folha ESCALAR do dataset"*), e o guard do C3
   deixa passar de propósito para não piorar o erro. Faltava a terceira categoria.
   Agravante: `HierarchicalError` **é subclasse de `ValueError`**, então não dá para separar
   por tipo — separa-se pela assinatura da mensagem.

## Como rodar

```
python run.py    # sai 0 só se o normal fechar E as enumerações cobrirem o espaço
```

`src/tcf` intocado. Sem `Z:` — cadastro sintético determinístico (seed 20260816), o mesmo
dos labs `1400`/`1450`/`1530`.

## Vínculo

Welds: `0dec1a06` (C2) · `ec08634c` (C3) · `2464f561` (C1) ·
[`2020-verificacao-dos-welds`](../2026-08-16-2020-verificacao-dos-welds-C1-C2-C3/) (a prova
vermelho→verde contra o git) · [`INDEX do dia`](../INDEX.md)

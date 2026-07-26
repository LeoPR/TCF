# 2026-07-26-0330 — O escape como MÁSCARA (passo 1, focado no CPF)

> *"regras binárias não são estilo do TCF — a gente precisa sempre ter a função que aborda
> todas, e usar a que usa menos. (…) a gente NÃO PODE ficar testando cada um pra ver qual é
> mais barato (…) vetores ortogonais de memória, CPU, latência. (…) pense na regra mais burra
> possível. (…) primeiro achar uma regra que compense pra UM caso, vamos focar no CPF."*

## A ideia, em uma frase

O escape é, em cada corrida de dígito, a resposta a **uma** pergunta: *literal ou
referência?* Essa sequência de respostas é um **fluxo** — e fluxo é o que o formato já sabe
comprimir. Hoje ela é paga 1 byte por literal, embutida no corpo. A máscara a move para um
canal próprio, com o RLE mais burro que existe (`<count><char>`).

No CPF o fluxo inteiro é `L` repetido 800 vezes. A máscara é `800L` — **4 bytes contra 800**.

```
#TCF.8                       #TCF.8m
\000.\000.\000-\00           800L
\001.\007.\013-\01           000.000.000-00
                             001.007.013-01
```
(`outputs/cpf-wire-normal.tcf` × `outputs/cpf-wire-mascara.tcfp`)

## Medição — n=500 (CPF n=200)

| forma | corpo | decisões | runs | adjac. | inline | máscara | escolha | Δ |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| `cpf` | 3800 | 800 | 1 | 0 | 800 | 4 | **mascara** | **−795** |
| `ip` | 2851 | 256 | 1 | 0 | 256 | 4 | **mascara** | **−251** |
| `texto` | 1807 | 25 | 1 | 0 | 0 | 3 | inline | 0 |
| `cartao` | 11960 | 2019 | 39 | **6** | 2000 | 104 | inline | 0 |
| `cep` | 5990 | 1000 | 7 | **2** | 997 | 22 | inline | 0 |
| `telefone` | 8244 | 1780 | 821 | 410 | 1272 | 1660 | inline | 0 |
| `data-iso` | 5513 | 1442 | 661 | 318 | 677 | 1327 | inline | 0 |
| `email` | 5743 | 1546 | 464 | 150 | 367 | 959 | inline | 0 |

- aplicável em **3 de 8**; a máscara vence em **2**; ganho somado **−1046 B**
- reconstrução byte-exata **e** RT pelo `decode` REAL nas aplicáveis: **6/6**

## O bloqueador — terceira aparição, agora com nome

Sem o contador de adjacência, `cartao` daria **−1895 B** e um wire **corrompido**:

```
original    56\033-\0910      (`56` = referência, `033` = literal)
sem escape  56033-0910        <- `56` e `033` FUNDIRAM
volta       56033-\0910       <- fronteira perdida
```

> O escape carrega **duas** informações: o **tipo** (literal × referência) e a **fronteira**
> entre corridas de dígito. A máscara captura só o tipo.

Isso é o mesmo obstáculo do flip (lab `0038`) e do sem-escape (lab `0200`), visto de frente.
Naqueles a leitura foi "o seq-RLE quebra"; aqui o seq-RLE **não** quebra (o escape é
reconstruído antes de tudo — verificado: 0 marcadores divergentes). O que trava é a
adjacência, e o seq-RLE era sintoma dela.

## As etapas que você pediu

| etapa | resposta |
|---|---|
| 1. o que é **possível** | tirar o escape de onde ele responde sempre a mesma coisa: −795 B no CPF |
| 2. a **regra** | `min(inline, máscara)` quando `adjacências == 0` — não é binária, cobre qualquer mistura, e recusar = o inline de hoje |
| 3. **genérica?** | sim (não conhece tipo nem formato); **larga não** — 2 de 8 formas |
| 4. **dinâmica?** | sim por construção: por coluna, do próprio dado; flag no cabeçalho |
| 5. **online, poucos loops?** | sim — **3 contadores na passada que já existe**: literais, trocas L↔R, adjacências. A decisão é uma **conta**, não um experimento |

A etapa 5 é a que responde à sua restrição sobre os vetores ortogonais: nada é
materializado duas vezes para comparar. E a conta bate com a medição em **8 de 8**
(seção "Passo 5" do `result.md`).

## Limites

- **Nada soldado.** `src/tcf` intocado.
- O `m` no cabeçalho é notação do lab, não proposta fechada de grafia.
- Formas **sintéticas por LCG** — ver `datasets-provenance.md`. Nenhum CPF válido.
- A métrica é **bytes de corpo + máscara**. O `+1 B` do char de modo não entra (ruído).
- O `texto` é aplicável mas escolhe inline (0 literais) — a regra recusa sozinha, como deve.
- **Não medido**: um delimitador de fronteira mais barato que o escape, pago só nas
  adjacências. No `cartao` seriam 39 contra 2000 — é o próximo passo óbvio.

## Rodar

```
python run.py
```
`mascara.py` tem a transformação, os 3 contadores e as duas direções.

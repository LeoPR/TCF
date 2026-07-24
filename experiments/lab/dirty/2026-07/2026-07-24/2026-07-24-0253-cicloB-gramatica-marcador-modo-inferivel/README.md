# 2026-07-24-0253 — O marcador de modo é necessário, ou a ausência é inferível? (CORRIGIDO)

Responde à pergunta do owner, que separou **duas coisas**: (1) a DECISÃO de modo (core/denso/misto) =
heurística FLOOR ([ticket](../../../../../tickets/T-TYPED-SINGLECOL-MODE-HEURISTIC.md)); (2) a GRAMÁTICA
da inferência = **este lab**: o marcador precisa estar escrito, ou a ausência pode ser implícita?

> **⚠️ v1 CORRIGIDA pós-verificação `wf_3a7ab214`.** A v1 concluiu "o `~` é NECESSÁRIO" — **overclaim**,
> por dois erros meus: (a) omiti o **G2** do teste decisivo (viés pró-`~`); (b) chamei de "corrompe" o
> que **crasha (fail-loud)**. A resposta correta está abaixo.

## Três gramáticas candidatas

- **G1** `#TCF.8b~<n>\n<base64>` — marcador `~` dedicado + `n` (denso); core = sem `~`.
- **G2** `#TCF.8b<n>\n<base64>` — SEM marcador dedicado; o byte após a tag desambigua (dígito=denso, `\n`=core).
- **G3** `#TCF.8b\n<base64(n|bits)>` — sem nada; deduz o modo pela FORMA do corpo.

## Resposta (medida)

**SIM, existe gramática marker-free segura e desacoplada da heurística: é o G2.** O disambiguador é o
**byte logo após a tag fixa** — dígito → denso (início do `n`), `\n` → core. Disjuntos por construção,
sem char reservado, sem olhar tamanho. E como o `n` do denso é **obrigatório** (o bit-pack tem padding
0-7 bits → `n` ambíguo), ele **já serve de disambiguador de graça**.

| teste | G3 (forma) | G2 (n-header) | G1 (`~`) |
|---|:---:|:---:|:---:|
| core forçado nas colisões (§4) | ❌ 2/8 (**crash**, fail-loud) | ✅ 8/8 | ✅ 8/8 |
| bytes no denso (§5) | — | **122 B** | 130 B (+1/wire) |
| acopla à heurística? | sim | não | não |

## O que É e o que NÃO é

- **Um disambiguador É preciso** — deduzir por FORMA (G3) é inseguro: `true`/`false` são base64-limpos,
  a dedução crasha, e resolver por "denso só quando vence" acoplaria a gramática à heurística (as duas
  coisas que o owner pediu pra separar).
- **Um marcador DEDICADO (`~`) NÃO é preciso** — o `n` obrigatório já desambigua (G2).
- **A colisão é minúscula**: só `n=1` bool (2 de 2046 corpos core n≤10). `number` `[1]`/`[0]` → `\1`/`\0`
  (backslash) não colide. Para n≥2 todo corpo core tem `\n`/`*`/`|`/`^`.

## O trade-off real (pra você decidir)

- **G2 (n-header)**: mais barato (−1 byte/denso), marker-free, desacoplado. **Ótimo se forem só 2 modos**
  (core + 1 denso) — dígito-vs-`\n` é um split binário.
- **`~` (ou char de modo)**: +1 byte, mas **estende limpo pra ≥3 modos** — a família bN do roadmap
  (`b1`/`b2`/`b4`/`b8`) + `misto`, onde dígito-vs-`\n` não basta. O marcador vira `~<modo><n>`.

**A assimetria que se mantém** (a v1 acertou isto): seja G2 ou `~`, o **core (comum) fica nu** e o
**denso (raro) se declara** — marcar o raro/grande e deixar o comum/pequeno implícito é o lado certo.

## Escopo / método

Bool `w=1`, sintético, lab-local. **Nada em `src/tcf`.** Correção registrada honestamente: a verificação
adversarial pegou o mesmo tipo de erro (teste enviesado) que a memória `metodo-lab-verificacao-adversarial`
já anotava — reforça rodar a verificação como passo fixo.

## Rodar

```
python run.py     # 8 datasets · 5 seções (forma, n, RT das 3, teste decisivo, bytes)
```

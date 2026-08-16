# O piso do header do `.8M`, e as invariantes de fronteira que habilitam paralelismo

> **Owner (2026-08-16)**: *"veja um caminho barato para olharmos o M agora pra fechar ele de
> forma consistente, quero tirar o máximo de explicitudes do header e fechar muito bem as
> questões de limites de colunas pra preparar para as opções de paralelismo... também dê uma
> olhada no view/lazy mas sem se ocupar demais."*

## A resposta curta

**Os dois pedidos estão em tensão, e o projeto já resolveu a tensão.** Os byte-sizes do header
**são** o mecanismo de paralelismo — o O-FMT-19 tentou removê-los e foi **refutado** por matar
o decode paralelo e o acesso O(1) do lazy. E o O-FMT-11 já **fechou** o header como
near-optimal (*"cada campo é load-bearing"*).

Então este lab não reabre nada: (1) re-verifica o piso pós-welds novos (`:id`, split, FLOOR —
todos posteriores ao O-FMT-11) e (2) transforma *"dá pra paralelizar"* em **6 invariantes
testadas**, incluindo decode paralelo real.

## O caminho barato que o lab encontra

**`min_header=False` custa +4 B (+0,019%) e zera as colunas que dependem de EOF.** É o perfil
"pronto para stream/paralelo", o kwarg já existe, e não é mudança de formato — é escolha.

## Estado — era / foi / é / será

- **Era**: "o header pode encolher mais?" tratado como pergunta aberta.
- **Foi**: recuperar O-FMT-11/18/19 antes de medir — dois já fechados, um refutado.
- **É**: o piso confirmado pela mesma fórmula; **6 invariantes de fronteira passam**, e o
  decode paralelo (7 threads) dá resultado idêntico ao serial **com `src/tcf` intocado** — o
  formato não precisa de nada. Resultado em [`result.md`](result.md).
- **Será**: os 4 abertos, e nenhum é byte-tweak — O-FMT-14 (header derivável, feature de
  contrato), `T-SPEC-SEM-CARIMBO`, `T-META-COLISAO-NOME-POSICIONAL`, `T-UM-CAMINHO-SO`.

## As 6 invariantes (declaradas antes de rodar, todas OK)

| # | invariante |
|---|---|
| I1 | o plano de fatiamento sai **só da linha 1** |
| I2 | independência — uma coluna não lê byte de outra |
| I3 | ordem livre |
| I4 | **paralelismo real** — 7 threads == serial |
| I5 | só a última depende de EOF; `min_header=False` zera |
| I6 | o plano é completo (Σ sizes + resto = corpo) |

## Como rodar

```
python run.py    # sai 0 só se as 6 invariantes passarem e todos os RTs fecharem
```

Sem `Z:`. Dado importado do lab [`1400`](../2026-08-16-1400-cadastro-popular-header-do-M/)
(mesma seed). `src/tcf` **intocado** — o decode paralelo é orquestração externa, de propósito.

## Uma correção de método dentro do próprio lab

A primeira curva de break-even usava `v0..vN` — progressão que o seq-RLE esmaga, então o corpo
não crescia e a curva mentia (N=20 e N=100 davam o mesmo wire). Refeita com dado real. Fica
registrado porque é a mesma classe do achado de amostragem do lab `0530`: **dado sintético
regular pode esconder a variável que você quer medir.**

## Vínculo

O-FMT-11 (fechado) · O-FMT-18 (hex decidido, T-FMT-HEADER-BASE-HEX) · O-FMT-19 (refutado) ·
O-FMT-13 (per-channel, registrado não-implementar) · O-FMT-14 (o frontier real) ·
ADR-0023 (min_header) · ADR-0029/0032 · Labs [`1400`](../2026-08-16-1400-cadastro-popular-header-do-M/)
e [`1450`](../2026-08-16-1450-ordem-de-colunas-no-M/) · Nota
[`estagios-e-soldas-do-M`](../../../notas/2026-08/2026-08-16-1510-estagios-e-soldas-do-M.md)

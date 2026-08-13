# Latência é o eixo; o período é acessório

> **Correção do owner (2026-08-13)**: *"a questão do período é acessório para relacionar com
> a latência, ou seja a rigor o que existe é tentar responder por slices de tempo, ou menor
> latência. e isso vale pra virtualmente qualquer tipo. logo não é só pegar a data e picotar,
> é sobre como transmitir em pequenos slices de tempo, seja um parâmetro do tipo menor
> latência ou algo orientativo como 'responder algo em até 200ms'. […] veja se não está
> soldando a data pra criar uma latência muito presa e artificial demais, ela tem que derivar
> da latência."*

## Estado — era / foi / é / será

- **Era**: a nota de 2026-08-10 mediu pulsos **na coluna de data** e concluiu que o corte
  deveria ser *"alinhado ao período"*, fechando com **"um modo de baixa latência não pode
  cortar em qualquer lugar"**. A latência ficou subordinada à estrutura do dado.
- **Foi**: o alerta acima. Se a fatia deriva da latência, então nem o período nem o
  calendário podem estar governando o corte.
- **É**: este lab mede quem manda. **A conclusão anterior é falsa** — 40 de 40 tamanhos de
  fatia fora de fase são legais. E o custo de fatiar **não é propriedade da data**: a mesma
  coluna custa 2,69× sem spec e 16,46× com spec; um inteiro sequencial sem período nenhum
  custa 14,40×. O que governa é **de onde vem a compressão** (global × local).
- **Será**: reenquadrar `MAX_PERIODO` (hoje justificado por calendário, na prática é
  orçamento de detecção) e desenhar `deadline_ms` a partir da régua `[piso, teto]`.

## As 4 perguntas (e a 5ª que faltava)

1. O custo de fatiar é propriedade da **data**?
2. Cortar "fora de fase" é realmente **ilegal**?
3. O que governa o **preço** de uma fatia?
4. Onde está o **penhasco** — o menor slice antes do custo explodir?
5. *(acrescentada ao rodar)* Quanto vale **200 ms** em número de valores?

Respostas medidas em [`result.md`](result.md).

## Como rodar

```
python run.py     # regenera inputs/, intermediates/, outputs/ e resultado.json
```

Sai 0 só se todos os round-trips fecharem. `src/tcf` não é tocado.

## Onde olhar

| arquivo | o que é |
|---|---|
| `intermediates/corte-fora-de-fase.json` | os 40 tamanhos de fatia (1..40) em dias úteis (período 5), com RT por tamanho — a prova da pergunta 2 |
| `intermediates/penhasco-por-tamanho-de-fatia.json` | bytes/valor por tamanho de fatia + se o marcador seq-RLE ativou — a prova da pergunta 4 |
| `intermediates/tempo-por-fatia.json` | ms por fatia e a conversão deadline → nº de valores |
| `outputs/<tipo>.inteiro.tcf` | 600 valores em **uma** fatia |
| `outputs/<tipo>.8fatias.tcf` | os mesmos 600 em **8 fatias independentes** (separador `=== FATIA ===` é do arquivo, não do wire) |
| `outputs/<tipo>.*.roundtrip.json` | contra-prova: `diff` contra `inputs/<tipo>.entrada.json` |

Cada fatia de `*.8fatias.tcf` é um wire completo, decodificável sozinho — é isso que
"responder em slices" quer dizer.

## Ressalvas

- Os tempos são **ordem de grandeza** (mediana de 7, máquina não-quiescente). Número
  probatório é o `bench_perf`. Servem para a conversão deadline → N, não para comparar
  performance entre versões.
- É dirty: conclusão **orientativa**. O que ela produz de duro é a *refutação* de um
  registro anterior — e essa é reproduzível por `python run.py`.

## Vínculo

Tickets: `T-PULSO-SINGLE-COL` · `T-MAX-PERIODO-31` · `T-LAZY-BYPASS-ARITMETICO` ·
`H-ENCODE-DEADLINE-01` · `V2-J` (ADR-0018, streaming).
Corrige: [`notas/2026-08/2026-08-10-nomes-lazy-e-pulsos-revisao.md`](../../../notas/2026-08/2026-08-10-nomes-lazy-e-pulsos-revisao.md) §3.
Lab irmão (mesmo dia): [`…-1650-inspecao-data-estado-atual`](../2026-08-13-1650-inspecao-data-estado-atual/).

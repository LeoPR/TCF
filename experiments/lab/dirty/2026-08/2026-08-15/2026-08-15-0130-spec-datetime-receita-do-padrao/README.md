# Spec de datetime — a receita do padrão

> **Owner (2026-08-15)**: *"o datetime pode entrar no mesmo esquema do date e do time, ou seja,
> eles são **pré-formatados ou padronizados** para entrar no tcf; aí formatos variantes podem
> ser tratados como **string**. Como sabemos que não tem um tipo nativo de relógio (tirando
> timestamp, que é praticamente um inteiro), então é justo pensar que o dataset interno de uma
> linguagem ao entrar no tcf seja um **string com semântica forte**, principalmente se foi
> **confiado** isso. Só seguir a receita de padrão. Isso ajuda a focar num estilo de compressão
> que é melhor pro datetime."*

Sua decisão **elimina** o problema das 13 grafias que o lab [`…-0020`](../2026-08-15-0020-datetime-grafias-regimes-mecanismos/)
mediu: uma canônica, o resto é string. É literalmente o que o `data_iso.py` já declara —
*"nenhum adivinhador de formato… outras grafias são specs nomeados irmãos"*.

## A restrição que decidiu o desenho

O contrato de nature é `encode_value(v) -> (payload, status)`: **um valor, um payload**. Um spec
**não pode** partir a coluna em campos — isso é o `split`, que é multi-col. Então a única
pergunta de desenho é **qual inteiro emitir**, e o lab mede três: `ordinal`, `epoch` e `par`.

## Estado — era / foi / é / será

- **Era**: `dtm` reservado no ADR-0041, **sem dono**; nenhum spec de datetime em lugar nenhum,
  nem em lab.
- **Foi**: sua decisão de tratar datetime como pré-formatado, seguindo a receita.
- **É**: o protótipo segue a receita linha a linha e **ganha em 7 de 8 regimes** (14,3% a
  99,8%), nunca perde. Resultado em [`result.md`](result.md).
- **Será**: decidir o separador canônico (o lab mostra que **errar custa zero**) e abrir o
  ticket da interação OBAT × seq-RLE.

## Os três achados

1. **O payload não se escolhe por "menos dígitos"** — se escolhe por *quantos dígitos ficam
   invariantes*. Com prefixo longo, o **OBAT fatora o número e o seq-RLE perde a corrida**:
   mesma progressão, 11 dígitos com passo 300 dá 79 B; com passo 30000 dá **32 B**.
2. **Escolher o separador errado custa ZERO** — o wire fica byte-idêntico ao sem-spec (o FLOOR
   descarta). E **nenhuma das duas grafias de 19 chars é RFC 3339** (falta o `time-offset`
   obrigatório), então o argumento de norma que elegeu o `YYYY-MM-DD` **não transfere**.
3. **A irmã com `T` é pega pela RE-EMISSÃO, não pela largura** — as duas canônicas concorrentes
   têm 19 chars. É a peculiaridade que o datetime tem e a data não.

## O que este lab NÃO testa

Robustez a grafia misturada. Sua direção é explícita: a coluna vem pré-formatada de um banco, e
mistura seria **corrupção de transmissão**. Há **um** caso (`b-mista`) só para verificar que
metade cai em literal sem quebrar o RT — e cai (apply 0,5, RT ok).

## GATE

Protótipo em lab. **`src/tcf` intocado** — o spec é uma classe local que o `encode(nature=)`
aceita por duck-typing. Nada aqui é proposta de weld.

## Como rodar

```
python run.py     # sai 0 só se todo RT fechar
```

**Não precisa de `Z:`** — inteiramente sintético. Reusa os regimes do lab `…-0020`.

## Onde olhar

| arquivo | o que é |
|---|---|
| `spec_datetime.py` | o protótipo: a receita do `data_iso` aplicada, com 6 variantes |
| `inputs/<caso>.entrada.json` · `.fonte.json` | a coluna e a procedência |
| `outputs/<regime>.spec-<payload>.tcf` · `.roundtrip.json` | o wire de cada payload |
| `outputs/b-*.tcf` | as 13 bordas de canonicidade |
| `intermediates/bloco{1,2,3}-*.json` | as medições, com `CONSTANTE_na_comparacao` |

## Vínculo

`T-DATETIME-TIPO` · ADR-0041 (`dtm` reservado) · ADR-0015 (natures opt-in; a opção de
auto-detect por apply-rate foi **considerada e descartada**) · `data_iso.py` (o gabarito) ·
`T-NATURE-IGNORADA-CALADA` (4ª situação) · lab irmão:
[`…-0020-datetime-grafias-regimes-mecanismos`](../2026-08-15-0020-datetime-grafias-regimes-mecanismos/)

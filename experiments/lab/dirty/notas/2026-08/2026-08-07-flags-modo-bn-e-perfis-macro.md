# Flag do modo `C` e os perfis macro — avaliação superficial

**2026-08-07 · esboço para o `.9`; nada soldado**

Correção de rota do owner: **`B` × `C` nunca foi decisão em aberto.** Os dois existem, são
duas trocas conhecidas — `B` é stream-friendly, `C` espera o fim para descomprimir — e isso
está decidido há tempo. O default é `B` (stream), e o `C` entra **só quando declarado**.

Eu estava tratando como pendência o que já era escolha feita. O item sai da lista de
fechamento do bN.

---

## O que já existe de knob (levantado, não inventado)

`encode()` já tem **13 parâmetros** opt-in:

```python
encode(data, *, side_outputs=None, parallel=False, nature=None, nature_per_col=None,
       layers=None, fallback=True, min_header=True, min_len=None, sort_by=None,
       name=None, stamp=None, drop_names=False)
```

Documentados em [`docs/reference/encode-knobs.md`](../../../../docs/reference/encode-knobs.md).
E existe um **agrupador declarativo**: `layers: PipelineConfig` (`src/tcf/pipeline.py`), que
liga/desliga camadas (`pre_pass`, `obat_shape_preserve`, `hcc_seq_rle`) num objeto só.

O conceito de **perfil** também já está registrado, em
[`contrato-externalizado-e-aceleradores.md`](../2026-07/contrato-externalizado-e-aceleradores.md):

> *"modo-pulsos produz output declarado (perfil), nunca default — senão reprodutibilidade e
> baselines morrem"*

Ou seja: nem o knob nem o perfil são conceito novo. O que falta é **um lugar pro modo do bN**
e **nomes** pros perfis.

---

## O flag do `C` — a forma mínima

O ticket já existe: **`T-BN-LOTE`**. O que falta é só o opt-in de emissão; o decode já aceita.

Forma mais barata que encaixa no que existe:

```python
encode(data, bn_modo="B")     # default — stream-friendly
encode(data, bn_modo="C")     # lote: domínio por último, ~1 B menor, NÃO streama
```

- default `"B"` preserva byte-canonicidade e todos os baselines;
- o `min()` do FLOOR continua igual — o flag só decide **qual candidato entra na lista**,
  não muda o critério;
- `"C"` é uma escolha do produtor sobre o **consumo**, não sobre o tamanho: ganha 1 byte e
  paga 100% de prefixo antes do 1º valor (medido, lab `2026-08-07-2055`).

**Alternativa** que talvez seja melhor: não expor `bn_modo` cru, e sim deixar o modo cair de
um perfil (abaixo). Um knob por mecanismo não escala — hoje seriam `bn_modo`, amanhã
`denso_modo`, `polaridade`, `tipado_legivel`… É a mesma razão pela qual `PipelineConfig`
existe em vez de 3 booleanos soltos.

---

## Os perfis macro — esboço, nomes a decidir

A ideia: o usuário declara **a intenção**, não o mecanismo. Cada perfil é um conjunto de
defaults; o mecanismo individual continua acessível pra quem quiser.

| perfil (nome provisório) | o que prioriza | o que provavelmente liga/desliga |
|---|---|---|
| **`stream`** | latência do 1º valor, buffer mínimo | bN modo `B`; evita mecanismo que exige o fio inteiro |
| **`lote`** / `arquivo` | bytes; o consumidor lê tudo | bN modo `C`; tolera qualquer coisa que espere o fim |
| **`rapido`** | CPU de encode | pula pré-passe, menos candidatos materializados |
| **`memoria`** | pico de alocação | menos candidatos simultâneos, evita materializar o que perde |
| **`compacto`** | bytes acima de tudo | todos os candidatos, sem limite de CPU |
| **`auto`** (default) | o de hoje | comportamento atual, byte-canônico |

Observações que já dá pra fazer sem medir nada:

- **`auto` tem de ser o default e tem de ser o comportamento de hoje.** Se o perfil mudar o
  wire por default, os baselines byte-exatos morrem — é o mesmo argumento já registrado
  sobre o modo-pulsos.
- **Os eixos não são independentes.** `compacto` e `rapido` brigam; `stream` e `compacto`
  brigam (o `C` é menor e não streama). Um perfil é uma **política de desempate**, não uma
  otimização — o que reforça o `T-FLOOR-MULTIVETOR`: enquanto o `min()` só enxerga byte, os
  perfis não têm em que mandar.
- **`memoria` e `rapido` não são mensuráveis hoje** com confiança: o lab de vetores mostrou
  CV de ±14–24% nesta máquina, sinal confiável e magnitude não. Perfil que promete CPU
  precisa do `bench_perf` por trás.
- Nomes tipo `--fast` / `--memory=low|auto` sugerem **CLI**. Não existe CLI hoje; a API é
  `encode(...)`. Se um dia houver, o perfil é o candidato natural a virar flag de linha de
  comando — mas isso é decisão de superfície, não de formato.

---

## O que fica registrado para o `.9`

| ticket | o que é |
|---|---|
| **`T-BN-LOTE`** (já aberto) | opt-in de emissão do modo `C`. Decidir se vira knob próprio (`bn_modo`) ou cai de um perfil |
| **`T-PERFIS-MACRO`** (novo) | perfis declarativos (`stream`/`lote`/`rapido`/`memoria`/`compacto`/`auto`). Depende do `T-FLOOR-MULTIVETOR` pra ter em que mandar. Nomes a decidir |
| `T-FLOOR-MULTIVETOR` (já aberto) | o `min()` só enxerga byte — sem isso, perfil não tem alavanca |
| `T-FORCAR-MECANISMO-PARAM` (já aberto) | forçar mecanismo por parâmetro; é o degrau abaixo do perfil |

**Nada disso é `.8`.** O `.8` já tem os dois modos existindo e funcionando, que é o critério
de completude. Escolher entre eles com ergonomia é otimização.

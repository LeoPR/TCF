# Data — alvos de transformação × declaração da grafia

**2026-08-08 · dirty · exploratório** · só **data** (sem hora)

```
python run.py     # 56 medições, n=600; exit ≠ 0 se algum RT quebrar
```

---

## Como achar o que você quer, só pelo nome

Nada aqui exige abrir arquivo pra descobrir o que é.

```
inputs/        regime-<regime>--<higiene>.input.json
                 └ o dado de partida. `<higiene>` diz se ele sobrevive a um round-trip
                   por JSON: `json-lib-like` = sim (nada aqui é artefato de serialização).
                   Dentro: o que é, por que este regime existe, e a amostra.

intermediates/ <regime>--<alvo>.trilha.json
                 └ POR ONDE O DADO PASSOU dentro do codec, em 5 etapas
                   (entrada → pré-passe → OBAT → HCC/seq-RLE → saída).
                   Telemetria REAL (`SideOutputs`), não narrativa minha.
               medicoes.json          números crus de tudo

outputs/       <regime>--<alvo>.tcf              o fio
               <regime>--<alvo>.roundtrip.json   a CONTRAPROVA, em 2 níveis
               medicoes.md                       as tabelas
```

`<regime>` ∈ `diario` `semanal` `mensal` `agrupado` `repetido-k12` `espalhado`
`espalhado-ord` `decada-espalhada` · `<alvo>` ∈ `iso` `ordinal-dec` `ordinal-denso`
`ordinal-b64` `epoch-seg` `compacto` `delta-dias`

Os `.tcf`/`.roundtrip` só são gravados para **`diario`** e **`espalhado`** — os dois
extremos. Os outros 6 regimes entram nas tabelas; gravar 56×3 arquivos atrapalharia em vez
de ajudar.

### O round-trip, em dois níveis

O `.roundtrip.json` existe pra **você conferir sem rodar nada**:

```
entrada_iso        →  apos_o_alvo  →  [ .tcf ]  →  decode_do_wire  →  depois_da_inversa
                        ↑                             ↑                    ↑
                   o que o TCF vê          tem de bater com        tem de bater com
                                            `apos_o_alvo`           `entrada_iso`
```

O campo `confere` traz os dois booleanos. **Os dois fechando** = o alvo é reversível **e** o
wire é fiel. É a contraprova do lab inteiro.

---

## O que este lab decide

Sete formas de reescrever a data antes de ir pro core, cada uma com a inversa. A pergunta
não é "qual é a melhor" — a resposta **inverte** entre regimes. É **quantos alvos bastam**.

| alvo | o que explora |
|---|---|
| `iso` | linha de base — o que o TCF faz hoje |
| `ordinal-dec` | decimal: o `*N+M\|` enxerga a progressão aritmética |
| `ordinal-denso` | base-80 largura 4 — o alvo da nature do CPF |
| `ordinal-b64` | base64 de 3 bytes = 4 chars, sem padding |
| `epoch-seg` | segundos desde 1970 — o formato timestamp |
| `compacto` | `YYYYMMDD`: numérico E legível |
| `delta-dias` | 1ª data por extenso + diferenças |

E três formas de declarar a grafia: **H1** header (`#TCF.8 :data-iso`, **10 B**), **H2**
template no 1º registro (7–9 B), **H3** inferir do 1º registro (**0 B**, se desambiguar).

> Adivinhar a grafia **não substitui declará-la**: se o encoder escolhe e não registra a
> escolha, o decode não tem como inverter. O sniff é front-end do H1/H2, não uma quarta via.

## Os achados

- **Dois alvos morreram.** `epoch-seg` (×86400 = 5 dígitos sem informação) e `ordinal-b64`
  (base-64 contra o base-80 que já temos) **nunca vencem em regime nenhum**.
- **A declaração inverte metade do quadro.** Pagando os 10 B, o `ordinal-dec` — campeão sem
  declaração, até **275×** — deixa de vencer em qualquer regime.
- **`delta-dias` vence 5 de 8** porque guarda o 1º valor **verbatim**: a grafia viaja de
  graça. Responde à ideia do "primeiro registro formatador" — um alvo já faz isso sozinho.
- **Inferir do 1º valor: 100% para ISO.** Só o par BR/US é ambíguo, e só entre si (60,4%).

Detalhe em [`result.md`](result.md).

---

## As conclusões do plano de opções — repetidas aqui pra não se perderem

Do [plano de entrada e saída](../../notas/2026-08/2026-08-08-data-plano-de-opcoes-entrada-e-saida.md),
porque um lab que não carrega seu contexto envelhece mal:

**1. O bool já resolveu esta pergunta.** Os dois contratos coexistem, e **o tipo de entrada
decide qual vale**: `[True,False]` vira bits e volta `bool` (RT **semântico** — a grafia é
escolha do formato); `["true","false"]` volta string byte-exata (RT **textual**). Data seria
idêntica em estrutura.

**2. O `DATE` do SQL já é binário lá dentro** — o que o `SELECT` mostra é conversão de saída.
"Data como string" nunca foi armazenamento; foi sempre **transporte**. O TCF não escolhe como
guardar data — escolhe o que fazer com uma tradução que já aconteceu antes dele.

**3. O maior retorno está FORA do TCF**, no guia de normalização:

| origem | recomendação | por quê (medido) |
|---|---|---|
| SQL `DATE` | serialize em **ISO** | 100% desambigua sozinho |
| **JSON** | **ISO string, não epoch** | epoch nunca vence: ×86400 = 5 dígitos sem informação |
| CSV | ISO, **uma grafia por coluna** | 25% de BR dentro de ISO derruba −93,7% → −5,5% |
| qualquer | **ordene se a ordem não importar** | `espalhado-ord` fez **8,4×** sobre o desordenado |

**4. O "pré-filtro" já existe**: `nature_per_col=` é exatamente isso, opt-in. Falta um
`SPEC_DATA_*` no registry — não uma etapa nova.

**5. A ordem de ataque**, por retorno/esforço: (1) escrever o guia de normalização — **não
mexe em `src/tcf`**; (2) `SPEC_DATA_ISO` no registry; (3) tipo data nativo; (4) os outros
`SPEC_DATA_*`. **Os passos 2 e 3 não competem** — são os dois contratos do bool.

**6. A pergunta que sobrou pro owner:** se alguém quiser **texto** na saída do tipo nativo,
quem escolhe a grafia? O precedente do bool diz: **o TCF devolve o tipo, formatar é do
consumidor.**

---

## Arquivos de código

- [`alvos.py`](alvos.py) — os 7 alvos, as inversas, e a inferência de grafia
- [`run.py`](run.py) — as duas partes, os artefatos, o relatório
- [`result.md`](result.md) — os achados com as tabelas completas

`src/tcf` **não é tocado**.

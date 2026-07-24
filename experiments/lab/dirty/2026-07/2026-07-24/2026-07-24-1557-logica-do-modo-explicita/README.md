# 2026-07-24-1557 — A lógica do `~` (modo), forma EXPLÍCITA — referência do weld #4

Codifica a lógica do modo (o conceito do `~`) na **forma geral/explícita** que o owner pediu: a
**variável de decisão visível** (o `var`), não a otimizada. Tudo já existe no código (o FLOOR/`min`, a
dispatch posicional) — aqui só **nomeamos as etapas** e as materializamos num protótipo com RT.

## O princípio codificado

```
lógica geral (AGORA):              otimizada (.9 / compilador):
  var = <default>                    if (cond) then função_var
  if (cond) then var = <x>
  if var then função_var
```

A **função é acionada pela VARIÁVEL, não pelo caractere.** O `~` **não é byte de wire** (categoria 4) —
é o nome (livre) dessa variável `modo`. Explícito agora; a fusão que faz o `var` sumir fica pro `.9`.

## As 3 camadas, no código

- **caractere**: byte no índice 6 (tag) e índice 7 (fronteira de modo).
- **significado**: `tag→tipo` (`b`→bool), `char→largura` (`1`→w=1). Registros `TAG_TIPO`,
  `LARGURA_DE_MODO`. O `~` **não está aqui** (nunca é byte).
- **presença/decisão** = a variável `modo`:
  - **encode**: o FLOOR — `modo=core (default); if denso menor → modo=denso`.
  - **decode**: deduzida da posição — `if c7=='\n' → core; elif c7 é largura → denso`.
  - **É o `var` explícito, o `~` conceitual.** A função é acionada por ela.

## Resultado (8/8 RT-tipado ✅)

Wire canônico: `#TCF.8b\n<core>` (modo implícito) · `#TCF.8b1<n>\n<base64>` (denso w=1). **Sem `~`.**
FLOOR escolhe: core em `all-true`/`all-false`/`n1` (seq-RLE do core esmaga), denso em `alt`/`runs`/`p*`.

## Bug que o RT pegou (registrado)

1ª rodada: RT falhou em `runs`/`p10`. Causa: `_indices` usava domínio por **ordem de aparição**
(`dict.fromkeys`) — em `runs` (começa `True`) o True virava índice 0, mas o decode assume índice 1 =
True. **Domínio IMPLÍCITO exige convenção FIXA (canônica), não ordem de aparição** — senão o domínio
teria que viajar. Corrigido: bool = `false=0, true=1` sempre. (n/s densos precisariam de domínio
embutido — fora do escopo bool deste protótipo.)

## Mapa 1:1 pro weld #4

- `encode_typed` → ramo no dispatch de `encoder.py` (antes do `.8H`); reusa `_encode_column` (core) +
  pack bN. A variável `modo` = o FLOOR que já existe (`multi/core.py`).
- `decode_typed` → ramo no discriminador de `decoder.py` (hoje `disc8` desconhecido = fail-loud; add
  `elif tag in whitelist {b,n,s}`). A variável `modo` = a dispatch posicional que já existe.
- **Escopo**: bool `w=1` (domínio implícito). Larguras 2/4/8 e subtipos = namespace preparado, não
  exercido. n/s densos = domínio embutido, depois.

## Rodar

```
python run.py     # 8 perfis bool · RT-tipado 8/8
```
`inputs/*-fonte.json` · `intermediates/*-dataset-consumido.json` · `outputs/*-wire.tcfp`. Protótipo
lab-local — **não toca `src/tcf`** (é a referência pronta pra promover ao weld #4).

# Resultado — amostra de população com seleção honesta (hierarquia / ligações diversas)

**[probatório]** `study.py` (Shaper honesto + codec weldado, read-only). Números:
[outputs/01-estudo.txt](outputs/01-estudo.txt).
**RE-ROTULADO 2026-07-15 após auditoria adversarial** (workflow 4 lentes + síntese; probes
verificados em [probes_auditoria.py](probes_auditoria.py) →
[outputs/02-probes-auditoria.txt](outputs/02-probes-auditoria.txt)). O texto abaixo já incorpora
as correções; a seção "Auditoria" no fim registra o que mudou.

## (A) RT em estratos HONESTOS — 18/18 byte-exato (robustez a VALORES numa topologia)

Amostragem estratificada proporcional (Shaper `fk_preserving`) por `c_mktsegment` e `c_nationkey`,
volumes {0.1, 0.3, 0.6} × seeds {7, 42, 101} = **18 estratos honestos**. Todos RT byte-exato.
Representatividade alta (TVD 0.0011–0.029). Multiplicidade exercitada: pedidos/cliente 2–32,
média 15; itens/pedido 1–7; **500 clientes SEM pedido** (cauda de array vazio).
**Rótulo honesto (pós-auditoria)**: isto prova **robustez a valores/fan-out numa ÚNICA topologia**
(espinha arr_objects, profundidade 3) — os 18 estratos variam valores sobre o MESMO schema, então
NÃO são 18 testes estruturais independentes. A cobertura TOPOLÓGICA (profundidades, `{}` 1:1,
arr_scalars, arrays irmãos) vem do fuzz sintético seedado (lab 2120 + property-test em `tests/`),
não deste estudo. E TPC-H é in-class **por construção** (dbgen: schema uniforme, sem null) — evita
a fatia de sorte, mas é uma **população favorável**.

## (B) FRONTIER — ligações diversas NÃO cobertas (correção de wording)

- `partsupp`: 8000 arestas **N:N** (part até 4 suppliers; supplier até 80 parts) → não é árvore.
- `lineitem`: multi-pai (orders + part + supplier) → snowflake.
- **Correção pós-auditoria**: o codec **não DETECTA N:N** (não há guarda disso em
  `hierarchical.py`); o correto é que N:N é **inexpressável no contrato de entrada** (`list[dict]`
  é árvore por construção) — dado N:N tem que ser PRÉ-projetado a 1:N, e a projeção **duplica** o
  filho compartilhado (blow-up silencioso da projeção, não do codec). O único fail-loud executável
  hoje é **ragged** (testado em `tests/test_hierarchical_rt.py`). `1:N ≡ N:1` por ponto de vista;
  falta representar múltiplas raízes/junção simultâneas (H-HIER-MULTITABELA-01).

## (C) 2ª fonte REAL — br-identidades (correção de rótulo: é 1:N PURO, não N:N)

**Correção pós-auditoria (verificada no hub)**: `empresas` tem 100000 linhas = 100000 CNPJs, cada
um com UM `socio_cpf` → o vínculo é **1:N puro** (não N:N como o texto original disse). Fan-out
médio 1.03, máx 4; **846 sócios multi-empresa na população** — a fatia original (LIMIT 3000 +
alfabética) pegou só 3, ou seja, era **fatia de conveniência**, não amostra honesta (a mesma falha
que o estudo critica). O RT=True vale, mas como corroboração fraca (fan-out degenerado).

## (D) Valores-quebradores — censo 0 + PROBES adversariais (pós-auditoria)

Censo: 0 ocorrências de `\n`/controle nas free-text desta população (ressalva mantida: achado da
amostra, contrato `\n` pendente). A auditoria apontou que censo ≠ probe; os **probes construídos**
([probes_auditoria.py](probes_auditoria.py)) verificaram:
- **Robustos**: `\t`/`\x00` em valor, espaço/`\` em nome, string vazia, coluna toda-vazia (sem
  dessincronização de cursor), todas-folhas-vazias. `\n`-em-valor = fail-loud claro do core.
- **BUGS R0-class encontrados** (entrada aceita quebra RT — preempção pela regra do T-REL-08):
  **nome com `,` → corrupção silenciosa** (`{'c,d':'2'}` → `[{'c':'2','d':'2'}]`); **nome com `{` →
  corrupção silenciosa** (objeto fantasma); **nome com `[` → HANG** no parse (classe BUG-12);
  nome com `:`/`#` → fail-loud tardio no decode. Causa: `_build_meta` emite nomes CRUS; o `.8M`
  já escapa nomes com `\` (T-FMT-NAME-ESCAPING) — o `.8H` nasceu sem portar. **Fix aguarda
  aprovação do owner** (mexe em `src/tcf`).

## Síntese honesta (pós-auditoria)

- **Coberto por ESTE estudo**: robustez a valores/fan-out reais em contenção 1:N, numa topologia,
  com amostragem honesta — mais 1:N degenerado em 2ª fonte. Cobertura topológica = fuzz sintético.
- **Fronteira**: N:N/multi-pai inexpressável (não "fail-loud"); projeção 1:N duplica (declarar).
- **Bugs achados pela auditoria**: nomes com chars do meta corrompem/travam — repro pinado, fix
  proposto, aguarda aprovação.
- **Limite de população**: TPC-H sintético favorável + br-identidades degenerado. Fontes
  hierárquicas reais NÃO usadas: receita-cnpj (matriz→filiais, hub pronto) e online-retail
  (InvoiceNo→itens, precisa build). Registradas como próximos probes de dado real.

`confianca: Média` p/ generalização (rebaixada de Alta pela auditoria — a evidência real cobre uma
topologia; o resto é sintético). Auditoria completa: workflow `wf_4960112e-d45`, 4 lentes, síntese
com 6 lacunas confirmadas + 11 probes ranqueados.

## (E) PROBE de dado real não-sintético — receita-cnpj matriz→filiais (ROI-7 da auditoria)

A auditoria apontou que TPC-H é in-class **por construção** (dbgen: fan-out uniforme, sem null).
[probe_receita.py](probe_receita.py) roda o oposto — agrupamento real matriz+filiais por raiz-CNPJ
([outputs/03-probe-receita.txt](outputs/03-probe-receita.txt)):
- **(1) topologia, população inteira**: 51536 raízes, **200000 estabelecimentos**, fan-out
  **max 396** (cauda pesada real, ausente no TPC-H uniforme), avg 3.88 → **RT byte-exato**.
- **(2a) conteúdo real + null coerido**: 5% estratificado por UF (27 estratos), 4723 nulls reais
  coeridos a `""` (declarado) → **RT byte-exato**.
- **(2b) null CRU**: **coerção silenciosa de TIPO** (`str(None)='None'` → decode devolve `'None'`) —
  achado conhecido (H-TYPE-01). Null real em 48% de `nome_fantasia` **reforça** que o contrato null
  (deixado pro fim pelo owner) é pré-requisito p/ ingerir sem coerção declarada.

**Efeito na confiança**: contenção 1:N agora vale em **fonte real não-sintética com cauda pesada**,
não só TPC-H. Sobe de volta a **Média-Alta** p/ contenção 1:N all-string; o gap que resta é
topológico-sintético (profundidades/`{}`/irmãos = fuzz) + o contrato de tipo/null (pro fim).

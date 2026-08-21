# ADR-0044 — Um `cnpj` só: alfanumérico é o padrão, e o numérico é caso dele

- **Status**: **aceito — SOLDADO** (2026-08-21, direção explícita do owner). Suíte **1304**;
  byte-neutralidade no domínio numérico provada por diferencial contra os parâmetros
  **históricos** (0 divergências em 4 011 encodes + 3 505 decodes).
- **Supersede**: [ADR-0042](0042-cnpj-alfanumerico-dois-specs.md) (dois specs + chooser) e
  [ADR-0043](0043-cnpj-um-so-compacto-por-valor.md) (que já tinha unificado o *algoritmo*,
  mas mantinha dois `wire_id`). Ambos ficam como registro do caminho; a **mecânica** do 0043
  (sub-alfabeto compacto por valor) permanece vigente — o que muda é a identidade.
- **Escopo**: `SPEC_CNPJ` passa a **ser** o alfanumérico; `SPEC_CNPJ_ALFA`, `cnpja` e
  `cnpj_spec_para` deixam de existir.
- **Origem**: owner, 2026-08-21.

---

## Contexto

O ADR-0043 já tinha resolvido o *algoritmo* (numérico como caso compacto por valor), mas
manteve **duas identidades**: `cnpj` (legado) e `cnpja` (unificado), com um helper para
escolher. O owner cortou isso:

> *"a ideia é ter só 'cnpj' mesmo, ou seja nada de ter dois. [...] agora o alfa é padrão, e o
> só numérico pode até ser oportunidade, mas acho que ela será transitória, já que com o
> tempo a variação entre número e letra prevalecerá. [...] O ideal é ter um algoritmo só pro
> cnpj novo, e só se tiver uma real vantagem e fácil implementação [...] aí vc avisa."*

Duas identidades para um formato que a lei unificou era complexidade nossa, não do domínio.

## O relatório que o owner pediu: o caso compacto **vale**, e por um motivo melhor

Medido antes de decidir (`vale_o_compacto`):

**1. Não há versão numérica melhor a achar.** 7 e 10 chars são **mínimos** em base-80:
`80⁶ = 2,62×10¹¹ < 10¹²` e `80⁹ = 1,34×10¹⁷ < 36¹²`. E o DV nunca foi gravado (é recomputado
no decode) — a redundância de 100% já estava eliminada.

**2. O ganho é transitório, como o owner previu — mas o custo é zero.** Varredura da mistura:

| fração numérica | compacto ON | compacto OFF | ganho |
|---:|---:|---:|---:|
| 1,00 | 17 586 | 24 292 | **+27,61%** |
| 0,75 | 19 315 | 24 364 | +20,72% |
| 0,50 | 20 959 | 24 367 | +13,99% |
| 0,10 | 23 861 | 24 530 | +2,73% |
| 0,00 | 24 455 | 24 455 | +0,00% |

Decai a zero exatamente como previsto, **e nunca fica negativo** (0 de 9 frações). A largura
mista (7 e 10 na mesma coluna) **não cobra pedágio** a jusante.

**3. E o motivo decisivo: o compacto é LOAD-BEARING, não otimização.** Sem ele, um `:cnpj`
alfanumérico **não lê o wire de 7 chars já emitido** — devolve o payload cru
(`'!)x+z:$'`) como se fosse o valor. **Corrupção silenciosa**, não erro alto. Com ele, um
único id lê tudo que existe.

Isso muda a natureza da decisão: o caso compacto não fica porque comprime melhor hoje; fica
porque é **o mecanismo de compatibilidade** que torna o "um `cnpj` só" possível. A compressão
é o bônus que decai.

## Decisão

**`SPEC_CNPJ` é o CNPJ da IN RFB nº 2.229/2024** — alfabeto `[0-9A-Z]` (36 símbolos), DV
decimal, `wire_id="cnpj"`:

```
corpo 100% decimal  → base 10, 7 chars   (payload byte-idêntico ao wire histórico)
corpo com letra     → base 36, 10 chars
```

O decode discrimina **pelo comprimento**. Não existe `SPEC_CNPJ_ALFA`, não existe `cnpja`,
não existe chooser — não há escolha a fazer, logo não há heurística com prazo de validade.

### O universo, confirmado na fonte

**`[0-9A-Z]{12}[0-9]{2}`** — 36 símbolos, todas as **26 letras maiúsculas**, sem exclusões no
formato (NT Conjunta 2025.001 / XSD da NF-e). A exclusão de `I,O,U,Q,F` que circula é, se
existir, estratégia de **emissão** — encolhe o subespaço ocupado, não o formato aceito.

### Minúscula fica fora — é classe CONTRATO (H-15-06)

Minúscula **não pertence ao domínio oficial**; é variante de **representação**. Como
*identificador* a caixa é irrelevante, mas aceitar minúscula canonizando a saída (`12.abc…`
entra, `12.ABC…` sai) **perde o RT byte-canonical** — constituição do formato. É a classe do
`sort_by`/`drop_names`: lossless como identificador, não como string. Medido: compraria
**−35,55%** numa coluna 100% minúscula. Aguarda `T-FMT-CONTRACT-SIGNATURE`. Hoje cai em
literal — não ganha, nunca corrompe.

## Consequências

- **Byte-neutro no domínio numérico**, provado por diferencial contra os parâmetros
  **históricos** (regex numérica, `encoded_length=7`, formatter decimal): **4 011 encodes e
  3 505 decodes (3 000 adulterados) — 0 divergências**. Um wire de coluna numérica sai
  idêntico ao de antes de todo este arco.

  As divergências de **status** (telemetria) existem e foram censadas em corpus amplo
  (10 008 valores, cobrindo de propósito as formas alfanuméricas que o diferencial numérico
  quase não tinha). São **3 classes, todas partindo de `format_mismatch`** — o catch-all que o
  spec histórico dava a qualquer valor com letra:
  
  | histórico → unificado | n | muda byte? |
  |---|---:|---|
  | `format_mismatch` → `compressible` | 3 017 | **sim — é a capacidade nova** (o alfanumérico deixa de ser literal) |
  | `format_mismatch` → `format_unmasked` | 2 002 | não (ambos literal) |
  | `format_mismatch` → `check_invalid` | 1 984 | não (ambos literal), e o rótulo novo é mais informativo |
  
  **Nenhum valor numérico diverge** — nem em byte nem em status. Roundtrip: 10 008/10 008.

  > A primeira redação deste ADR dizia "0 divergências, **inclusive de status**" sem
  > qualificar o domínio — afirmação larga demais para o corpus que eu tinha medido. A
  > revisão adversarial apontou; o censo acima é a correção, e é evidência melhor do que a
  > afirmação que ele substitui.
  > O primeiro diferencial que rodei estava **errado**: lia `spec.encoded_length` do spec
  > vivo (já 10) para simular o pré-weld, comparando "algoritmo antigo com parâmetro novo".
  > Ele acusou divergências que eram artefato do próprio script.
- **O custo honesto de reusar o id: incompatibilidade PARA A FRENTE.** A retro-compat é
  perfeita (leitor novo lê wire velho, provado acima), mas o inverso não: um decoder
  **pré-weld** lendo um wire novo com payload de 10 chars cai no ramo `return payload` e
  devolve `'$&KqK%ci}p'` **como se fosse o valor** — silencioso. Um `wire_id` novo teria feito
  esse leitor falhar **alto**; foi exatamente o desenho do ADR-0043 que esta decisão descarta.
  A troca é consciente: o owner pediu um id só, e pré-1.0 (ADR-0024) wire antigo se lê pelo
  git, com decoder e dado saindo da mesma versão do repo. **Fica registrado como o preço, não
  como surpresa.**
- **O registry volta a 5 specs** (`cpf`, `cnpj`, `ip`, `data-iso`, `int-pad`) — o `cnpja`
  existiu só dentro desta sessão e nunca foi publicado.
- **A DSL (`scripts/natures_compiler/`) não expressa alfabeto** e por isso só compila o
  subconjunto numérico. Lacuna **declarada**, não silenciosa: o teste de equivalência foi
  re-pinado para afirmar a equivalência que importa — **byte a byte no domínio numérico** —
  e documenta a limitação. É acessório, não core.
- Rótulo de telemetria: valor de dígitos unicode segue em `format_mismatch` (era
  `format_unmasked` antes do ADR-0042); bytes idênticos, pinado em teste.

## Alternativas rejeitadas

- **Dois `wire_id` (ADR-0043)** — complexidade nossa para um formato que a lei unificou.
- **Dropar o caso compacto** ("um algoritmo só, puro") — quebraria a leitura do wire
  histórico **em silêncio**, e perderia até 27,6% sem nada em troca.
- **Fail-loud em payload de 7 chars** em vez do compacto — quebra legado ruidosamente e
  ainda perde a compressão.

## Evidência

Labs do arco: [`2350`](../../experiments/lab/dirty/2026-08/2026-08-20/2026-08-20-2350-cnpj-alfanumerico/)
(descoberta) · [`0030`](../../experiments/lab/dirty/2026-08/2026-08-21/2026-08-21-0030-cnpj-alfa-controle/)
(controle) · [`0130`](../../experiments/lab/dirty/2026-08/2026-08-21/2026-08-21-0130-cnpj-um-so-compacto/)
(o compacto por valor) · [`0230`](../../experiments/lab/dirty/2026-08/2026-08-21/2026-08-21-0230-cnpj-unificado/)
(a unificação e o relatório de vantagem).

**Fontes**: [NT Conjunta 2025.001 / NT 2026.004 — NF-e](http://www.nfe.fazenda.gov.br/POrtal/exibirArquivo.aspx?conteudo=2%2FTP%2FAP+Pb4%3D) ·
[Receita — CNPJ alfanumérico](https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/acoes-e-programas/programas-e-atividades/cnpj-alfanumerico) ·
[regex `^[0-9A-Z]{12}[0-9]{2}$`](https://ramosdainformatica.com.br/cnpj-alfanumerico-implementacao/)

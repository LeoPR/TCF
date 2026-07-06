# Conclusão — teoria de cardinalidade (força + rápido-vs-pleno) [probatório]

Peça 8 do [grupo](../notas/estudo-tcf-hierarquico-mapa.md). Números: `artifacts/`. Teoria completa:
[notas/teoria-cardinalidade.md](../notas/teoria-cardinalidade.md).

- **O insight rápido-vs-pleno se sustenta — com nuance**: o pleno (OBAT/HCC) pega o **inter-item**
  (afixo `@empresa.com`) que o RLE-rápido perde (48B<67B). Mas **nem sempre o pleno ganha**: em alta
  entropia (ids opacos) o rápido é **menor** (30B<39B) — o OBAT super-tokeniza. Então "mais lento →
  mais compressão" **não é lei**; depende de haver inter-item.
- **ACHADO-CHAVE — cardinalidade ≠ compressibilidade (ortogonais)**: a cardinalidade (multiplicidade →
  normalização/RLE do valor-inteiro) e a compressibilidade (afixo/inter-item → OBAT/HCC) são **eixos
  independentes**. A coluna FRACA (`cliente_`, mult=1) não tem cardinalidade a explorar, mas comprime
  muito por afixo. O trade rápido↔pleno é **qual eixo explorar**, não a força.
- **Taxonomia de força**: FORTE (mult alta + valor largo) · FRACA (mult~1) · QUASE (g3>0, FD aproximada)
  · INDUZIDA (o JSON dita, g3=0 de graça). A força prevê o ganho de **normalização**, não o de compressão.
- **Duas estratégias, mesmo RT**: rápido (guiado-por-estrutura, RLE) e pleno (OBAT/HCC) reconstroem o
  mesmo dado; a escolha é velocidade × razão × qual redundância.

## Prior-art (survey — schema-guided vs data-driven, força, redundância)

Workflow `teoria-cardinalidade` (3 lentes + síntese). Enquadra a teoria (detalhe em
[notas/teoria-cardinalidade.md](../notas/teoria-cardinalidade.md)):

- **Avaliação parcial (Futamura)**: (a) rápida = (b) plena com a busca **restrita** ao que a cardinalidade
  prediz. Especializar preserva RT + melhora **velocidade**, não a **razão** → eixos separados.
- **Superconjunto + dominância fraca**: (b) contém (a) (só p/ coder ÓTIMO); OBAT/HCC são gulosos → (b)
  domina estritamente **só com 3 condições** (inter-item existe + guloso realiza + largura>overhead;
  senão o brotli come o ganho <1KB). (a) **Pareto-domina** em filhos únicos/opacos.
- **CASCADE (Parquet/ORC)**: as duas vias são **complementares** — encoding schema-aware primeiro, depois
  compressor geral. As duas coisas que o TCF dá são um cascade, não rivais.
- **Order Dependency**: descobrir a FD é necessário, não suficiente — o RLE exige o pai **agrupado**;
  ordem semântica paga permutação. Refs: TANE/HyFD, g3-error (Kivinen & Mannila 1995), Dremel rep/def.

## Hipóteses (H-CARD-01..07, registradas em roadmap-hipoteses)

Sete hipóteses no [roadmap-hipoteses](../notas/roadmap-hipoteses.md) + a teoria completa em
[notas/teoria-cardinalidade.md](../notas/teoria-cardinalidade.md): (01) fast/full coincidem em RT,
divergem em velocidade×razão · (02) dominância de full é fraca e falha no encoder guloso (medido +9B) ·
(03) força prevê ganho de NORMALIZAÇÃO, não de compressão · (04) sob QUASE (g3>0) a guiada exige
side-channel; plena é lossless de graça · (05) chave (d=n) ≠ grupo-coarse (d≪n) · (06) Order Dependency
gateia o custo da guiada · (07) o ganho inter-item pode não sobreviver ao brotli.

**Recomendação**: a teoria (taxonomia + ortogonalidade + trade + cascade) é o "material" pedido. Um dial
rápido/pleno seria um `PipelineConfig` opt-in (não muda o default; RT idêntico). Próximo: **voltar ao
plano geral (header-minimal)** + revisar tickets.

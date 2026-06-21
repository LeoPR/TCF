# Checkpoint 2026-06-21 — avaliação documental (Strata) + pausa

**Tipo**: ponto de pausa + avaliação de aderência ao método Strata (L0) da documentação produzida.
Disparado por: owner ("faça uma pausa para revisão commit e push; avaliação documental com Strata").
Protocolo: [[reference-strata-knowledge-architecture-review]] · gatilho L0 [[feedback-strata-l0-check-before-big-changes]].

## Higiene (commit/push)

- Árvore **limpa**, **0 commits sem push** (tudo no remoto até `e788f22`). Sessão: ~17 commits desde
  `6023c74` (F2 design → governança Strata → cheap-wins → V2-RLE → cross-dict/H-REF → lazy A1-A3 →
  header → transmissão). **`src/tcf` intocado** em toda a sessão (verificado por `git diff` a cada passo).

## Avaliação por princípio L0 (honesta, 0-4)

| § | princípio | estado | observação |
|---|---|---|---|
| §1 | separação física | **4** | notas=exploração, `tickets/`=trabalho, `docs/adr/`=decisão, labs=experimento. `src/tcf` não tocado. Limpo. |
| §2 | achabilidade | **3→4** | **Gap achado e fechado neste checkpoint**: MAP.md não listava 5 docs novos; STATUS parou no 06-19. Corrigidos (MAP + bloco SESSAO 06-21). Registry `roadmap-hipoteses` é o hub (Pacotes 11-bis/ter/quater). |
| §3 | rastreabilidade | **4** | achados ligados aos labs; status markers (CLOSED/ABERTO/REFUTADO/PARADO); superfície (STATUS) refrescada. Traço preservado (nada apagado; tickets fechados intactos). |
| §3-bis | força do artefato | **3** | tickets marcam [dispositivo]/[probatório]; **as notas novas em geral NÃO marcam** — gap menor (a maioria é probatório/exploração, dá pra inferir). |
| §4 | registro científico | **4** | **honestidade forte**: V2-RLE CLOSED, header row-count REFUTADO, transmissão nicho ~5-15%, e o **teste decisivo (NDJSON+brotli) declarado como não-feito**. Vocabulário sóbrio; refutações preservadas. |
| §5 | fonte única | **3** | números apontam pro lab (o teste mede); **mas** alguns % (venda 10/14%, byte-sizes) aparecem copiados em 2-3 docs → risco de deriva. Vigiar. |
| §6 | disciplina de fonte | **4** | pesquisa de transmissão citou fontes reais (RFC/AIP/big techs); mecânica (`^N`, header=bytes) **verificada empiricamente no encoder** antes de afirmar. |
| §7 | maturação | **4** | tudo no nível certo (exploração/nota em dirty); nada promovido cedo a `src/tcf`/ADR-accepted. 0.8-plano = a consolidação. Pendente owner: Pacote 1 (G-1). |
| §9 | economia do esforço | **3** | ~7 docs/labs novos na sessão. Cada um foi investigação pedida + registrada (diretiva cross-ref). **Borderline**: o cluster "compressão/transmissão" (rle-familia, dict-referencia, v2rle, header, transmissão) é grande — mitigado por cross-links + registry. Vigiar proliferação. |
| §10 | durabilidade | **4** | git + push (N cópias); caveat OneDrive (ADR-0021). OK. |

## Pontos honestos (o que NÃO está perfeito)

1. **§3-bis**: as notas novas não marcam dispositivo/probatório explicitamente. Baixo impacto; padronizar quando tocar cada uma.
2. **§5**: percentuais medidos copiados em múltiplos docs (venda, byte-sizes). Se um mudar, os outros derivam. Manter o **lab como fonte** e os demais como ponteiro.
3. **§9**: muitos pontos de entrada no tema compressão/transmissão. Se crescer mais, considerar **um índice único** do tema (ou consolidar em `rle-familia-estudo` como hub). Por ora, os cross-links seguram.
4. **Não é gap, é dívida sadia**: vários resultados são "exploração honesta que fechou" (refutados/nicho) — corretamente em dirty, não promovidos. Não formalizar (regra de três).

## Estado / retomada

- **Foco 0.8** (plano: [`v08-plano-etapas.md`](../v08-plano-etapas.md)). Workstream **A** (lazy) em
  **A1✅ A2✅ A3✅**; falta **A4** (promover → `tcf.view`, toca `src/tcf` aditivo → aprovação) + **A5**.
  Workstream **B** (cross-dict): **B1** caracterizar (não-feito). **T1** (TCF vs NDJSON+brotli) = teste
  decisivo de transmissão pendente.
- **Decisões pendentes do owner**: A4 (promover lazy), B1/cross-dict, V2-RLE nicho, Pacote 1 (data 08-18).
- **Sem nada bloqueado**; `src/tcf` estável; baselines intactos (381 passed).

> Avaliação geral: aderência Strata **boa** (média ~3,7/4). A documentação da sessão é rastreável,
> honesta e proporcional; os únicos ajustes são de achabilidade (feitos) e vigilância de §5/§9.

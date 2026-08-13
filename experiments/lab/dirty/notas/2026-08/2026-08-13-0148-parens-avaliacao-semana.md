# Poréns da avaliação da semana (2026-08-06 → 13) — para análise do owner

**Data**: 2026-08-13
**Tipo**: registro de sessão única (avaliação pedida pelo owner; **nada decidido aqui** —
cada item espera análise/veredito)
**Origem**: avaliação técnica da semana + enquadramento do owner na resposta (vetores
ortogonais, maleabilidade, CPU × latência).

---

## 0. Enquadramento do owner sobre CPU — registrar pra não reler como "problema"

O projeto **não é speed-first**: latência, memória, velocidade e compressão são vetores
ortogonais já discutidos, e o cobertor é curto — sempre se quer win-win, mas na falta dele
cada escolha é válida **como escolha**. Dois corolários que o owner fixou nesta sessão:

- **Maleabilidade é o critério de qualidade**: o algoritmo deve se adaptar a essas escolhas
  *profundamente no núcleo* (ajustável, matemático — o ideal) e **não** como um monte de
  `if`s escolhendo caminho.
- **CPU ≠ latência**: usar mais processamento não significa responder mais devagar — pode
  significar usar um algoritmo diferente. São íntimos, mas não são o mesmo eixo; precisam
  de análise separada de qualquer forma.

Lida assim, a penalidade de +35% de CPU do seq-RLE periódico (ADR-0040) **não é defeito**:
é o preço da opção latência que o mecanismo habilita. O que segue em aberto não é "reduzir
os 35%" e sim enquadrá-lo nos vetores.

---

## 1. CPU do periódico — de "preocupação" a "análise de vetor"

- Verificar se o **compartilhamento do array de deltas** com `detect_seq_runs` entrou no
  weld (ADR-0040 declara "é parte do weld"; é a maior fatia do custo restante: 6,8 ms
  contra 1,6 ms da lógica de período em corpo de 1200 linhas).
- Pergunta certa na análise: os +35% são custo **fixo do default** ou custo do **perfil
  latência**? Se o periódico é escolha de quem prioriza latência/memória, o default pode
  ter outro ponto de operação — e aí o número a cobrar não é 35%, é o custo do default.
- Conexão natural com `T-GATES-ANTES` e `T-SEQRLE-INCREMENTAL` (já vizinhos registrados).

## 2. Desempate do `min()` por ordem de argumento — frágil

- A ordem dos candidatos no `min()` é **load-bearing** pra byte-canonicidade (ADR-0040 §
  "Desempate"). Hoje está registrada em prosa no ADR; um próximo candidato pode inverter
  empate **silenciosamente**.
- Ação possível: pin explícito na suíte afirmando o desempate (empate → compactado), não
  só nota de ADR.

## 3. View: o bug nature+dict está fechado, a **classe** não

- Fix `6bea40ec` ficou bom: fonte única `_reverte_nature` nos dois caminhos + wrapper de
  módulo no `_col` (o `view.py:156` latente foi junto).
- Mas o bug era emissível no `.8` de produção e é a pior classe pela régua do projeto
  (errado, sem erro). Sugere que a matriz de testes do view **não cobre o produto cruzado
  nature × modo** (dict/split/run × com/sem nature).
- Ação possível: sweep paramétrico nature × modo no view, não só o caso que falhou.

## 4. ADR-0041 (spec em três planos) — em análise do owner

- Único item da rodada com **prazo real** (grafia congela no 1.0) — mas é a última
  instância do owner e é o que ele fará; **não é bloqueio externo**, não cobrar.
- Contexto acumulando enquanto espera: 14 `.tcf` commitados com `:data-iso`; o `view` sem
  a válvula out-of-band (documentado, não consertado).

## 5. "Guard vira amplificador" — padrão recorrente sem casa fixa

- Duas ocorrências na semana (auditoria bN; defeito #6 do periódico): validação que
  trabalha proporcional ao que o wire **declara** antes de validar o que ele declara.
- A lição ("ordem das condições é defesa, não estilo") está em prosa no ADR-0040. Falta
  virar **checklist obrigatório** de qualquer validação wire-facing futura — candidato a
  entrada no AGENTS.md §4 ou em template de weld.

## 6. `T-FLOOR-POS-POLARIDADE` — prioridade escondida

- O FLOOR é medido no corpo canônico, mas o que embarca é `polariza(corpo)`
  (`encoder.py:456`). Isso vale pro **core de hoje**, não só pro periódico — as rotas
  existentes podem estar escolhendo com régua errada já.
- Registrado no roadmap/STATUS (não tem arquivo de ticket próprio). Na triagem da semana
  saiu como o item que mais merece subir na fila depois do ADR-0041.

---

## Ordem sugerida pela avaliação (owner decide)

1. **ADR-0041** — já é a mesa atual do owner; decisão `dt` vs `dtiso` está medida
   (12 flips × 6).
2. **`T-NATURE-CANDIDATO-BN`** — ~5,7% real medido (EXP-017 §2), constraint de perfil
   batch já desenhada, conflito com pulso resolvido de graça.
3. **`T-FLOOR-POS-POLARIDADE`** — o único que fala do core que **já emite hoje**.
4. Itens 1, 2, 3 e 5 acima entram como análise/higiene, sem urgência de formato.

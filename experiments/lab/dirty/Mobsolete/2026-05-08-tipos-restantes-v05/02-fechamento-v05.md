# Fechamento da v0.5 — o que falta cobrir

Lista priorizada do que precisa ser fechado para v0.5 ser uma
especificação **completa e prática** (= cobre datasets reais sem
dependências externas).

---

## CRÍTICO 1 — NULL / missing values

### Problema

Datasets reais têm valores ausentes. TCF v0.4 não tem solução
canônica.

### Proposta

**Marcador `~` para NULL** em qualquer coluna. Reservado.

Comportamento:
- Linha contendo apenas `~` → valor NULL nessa posição
- Aplicação distingue de string literal contendo `~` por contexto
  (TCF não armazena valores que sejam `~` puro — colidiria; se a
  aplicação precisar, escapar como `\~`)
- RLE: `5*~` para 5 NULLs contíguos
- Dict: NULL pode receber idx 0 reservado, OU ser tratado como
  literal especial (proposta: literal especial — simples, sem caso
  especial no dict)

### Sintaxe

```
nome:
Ana
~
Beto
2*~
3
```

(`3` aqui é ref a Beto se a coluna for não-numérica.)

### Decisão de design

- Encoder usa `~` para NULL
- Decoder reconhece `~` como NULL em qualquer coluna
- Aplicações que precisam armazenar literalmente `~` devem escapar:
  `\~`. (raro, mas possível)
- RLE e dict trabalham normalmente sobre `~` como literal

### Ticket / Mesa

Mesa rápida `2026-05-08-null-marker/` para validar:
1. Marcador `~` não colide com casos comuns
2. RLE/dict comportam-se com NULL
3. Comportamento com flags δ, Q em coluna que tem NULL

→ Mesa simples, ~3 arquivos curtos.

---

## CRÍTICO 2 — Booleans

### Problema

Cardinalidade 2. Regra unificada funciona mas pode não ser ótima
(overhead do dict para 2 entradas).

### Análise

Para `true/false`:
- Literal: `true` (4) ou `false` (5) com \n = 5-6 chars cada
- Dict bare: declarações + refs `1`/`2` (2 chars cada com \n)
- Para N=100, 50/50: literal = ~550 chars; dict = 4+5+2 + 98×2 = 207
- Dict ganha grande quando valores são longos.

Para `0/1`:
- Literal: `0` ou `1` (2 chars com \n)
- Dict: declarações + refs (2 chars). Empate — dict não ajuda, pode
  até prejudicar pelo overhead semântico.

### Decisão

A regra unificada já decide certo na maioria. **Sem flag nova.**
Encoder com auto-discrim e cardinalidade detectada cobre.

Caso especial a considerar: para `0/1`, encoder pode forçar literal
(skip dict). Heurística: cardinalidade ≤ 2 e literal_len ≤ 2 chars →
literal.

### Ticket / Mesa

Não precisa mesa dedicada. Validar comportamento como **caso de teste**
no protótipo Python.

---

## CRÍTICO 3 — Times isolados (HH:MM:SS)

### Problema

Coluna com hora pura, sem data. Mesa de timestamps tratou casos com
data; este é caso ortogonal.

### Análise

ISO 8601 permite `14:30:00` ou `14:30:00.123`. Decoder reconhece pelo
shape (8 ou 12 chars).

δ multi-escala aplica diretamente: deltas em h/m/s/ms.

Diferença vs timestamp: não há overflow de dia. Se delta passar de
24h, opções:
- Tratar como overflow (volta a 00:00:01)
- Erro do encoder
- Ressetar para novo absoluto

**Decisão**: encoder responsabiliza-se por não emitir delta que
ultrapasse o ciclo. Se ultrapassar, emite novo absoluto. Decoder
trata `+25h` como erro estrito.

### Ticket / Mesa

Não precisa mesa nova. Documentar como caso particular do δ
multi-escala. Adicionar nota na gramática consolidada.

---

## DESEJÁVEL 1 — Quantização Q (floats com tolerância)

### Problema

Floats com precisão maior que necessária desperdiçam bytes. Aplicação
pode tolerar arredondamento.

### Status

Catalogada na mesa de pesquisa numérica. Flag `Q` proposta.

### Decisão para v0.5

**Incluir flag Q** com sintaxe simples:
```
# ext: <col>=quant:step=<step>
```

Encoder arredonda valores ao múltiplo de step. Decoder retorna
arredondados.

Sum-preserving fica para v0.6 (mais complexo, ticket separado).

### Ticket / Mesa

Mesa **T-N-IoT-baseline** já planejada cobre. Pode entrar em v0.5
com versão simples (sem sum-preserving).

---

## DESEJÁVEL 2 — Strings longas (documentar)

### Problema

Strings únicas e longas (descrições, comentários) não comprimem com
RLE/dict.

### Decisão para v0.5

**Não tentar otimizar.** Documentar:
> Para colunas com cardinalidade ≈ N (cada valor único e longo), TCF
> não comprime — o conteúdo é armazenado literalmente. Compressão de
> strings longas é responsabilidade do compressor downstream (gzip,
> zstd, etc.) ou de pipelines especializados.

Sem flag nova. Sem mesa nova.

---

## DEFERIR para v0.6+

| Tipo | Por que defere |
|---|---|
| Currency com unidade | Espera flag P (mesa P) |
| Coordenadas como tipo composto | OK como 2 colunas separadas |
| Versions semânticas | OK como literal |
| Sparse columns dedicado | RLE sobre NULL cobre parcialmente |
| Arrays / listas | Layout diferente, ticket grande |
| Nested JSON | Layout diferente, exige flatten antes |
| UUIDs | Sem padrão, literal aceitável |
| Hashes / blobs | Sem padrão, literal aceitável |
| URLs | Espera P |
| Emails | Espera P |
| Cross-column dict | Insight, não bloqueador |
| Sum-preserving (S3.1 da mesa numérica) | Pesquisa em andamento |
| Regressão linear | Pesquisa em andamento |
| Erro paralelo | Pesquisa em andamento |
| Compactos hex/base64 do índice | Etapa 2, ticket S aberto |
| Bit-packing | Etapa 2 |
| TCF-binary dialeto | Etapa 2 |

---

## Caminho final para v0.5

### Mesas restantes (curto prazo)

1. **`2026-05-08-null-marker/`** — fechar NULL com `~`. ~3 arquivos.
2. **T-N-IoT-baseline** (já planejada) — implementar Q (quantização
   simples).

### Validações no protótipo (paralelo)

3. Booleans (caso `0/1` e `true/false`) — testes de unidade.
4. Times isolados — testes de unidade.
5. Strings longas — caso negativo (literal aceito).

### Documentação

6. Atualizar gramática formal (`2026-05-09-gramatica-densidade/04-gramatica-formal.md`)
   com:
   - Marcador `~` para NULL
   - Sufixo `Q` na hierarquia Lxxx
7. Atualizar PROGRESSO geral com status atual.

### Após isso, v0.5 está fechado. Inicia-se:

8. **Protótipo Python** do encoder/decoder com flags `SRDMA + δ + Π +
   I + Q + ~null`.
9. **Validação em escala** com TPC-H ou similar.
10. **Voltar à mesa de transporte** (chunks/prioridade) — agora com
    base estável.

V0.6 começa com:
- Flag P (prefix elision)
- Flag L' (line-RLE)
- Sum-preserving (S3.1)
- Erro paralelo (E4.1)
- Cross-column dict
- TCF-binary dialeto (etapa 2)

---

## Estado da hierarquia Lxxx ao fechar v0.5

```
flags = SRDMAδΠIQ + (~null automático, sem flag)

S = sort multi-chave
R = RLE
D = dict implícito
M = auto-discriminador bare/marcado
A = alfabeto adaptativo
δ = delta como pré-transformação
Π = packed absolute
I = inline mode
Q = quantização explícita
```

**Default produção otimizada v0.5**: `SRDMAδΠIQ` (todas exceto K, P,
L' que ficam para v0.6).

**Default produção mínima v0.5**: `SRDMA` (5 flags, ganho ≥ 0
sempre).

NULL marker `~` é convenção universal, não flag (sempre disponível,
não-redundante).

---

## Como saber que v0.5 está fechado

Critérios:

- [ ] NULL implementado e testado
- [ ] Boolean validado em protótipo
- [ ] Times isolados testados
- [ ] Q (quantização simples) implementada
- [ ] Strings longas documentadas como caso negativo
- [ ] Gramática formal atualizada com tudo acima
- [ ] PROGRESSO geral atualizado
- [ ] Protótipo Python passa testes de roundtrip em todos os tipos
- [ ] Validação em escala em pelo menos 1 dataset real (TPC-H ou
      similar) com bytes proporcionais ao esperado
- [ ] Documento de migração v0.4 → v0.5

Quando todos esses estiverem ✓, **v0.5 está congelada** e começa-se
v0.6.

---

## Princípio que fechou esta mesa

> Algoritmo primeiro (Etapa 1), representação depois (Etapa 2).

A v0.5 é a **conclusão da Etapa 1**. Cobre todos os algoritmos de
compressão lógica em texto ASCII decimal, com pequenas concessões à
Etapa 2 (alfabeto adaptativo, packed absolute) que ganham muito sem
sacrificar legibilidade.

A Etapa 2 completa (bit-packing, binário, Gorilla XOR, etc) fica
para **TCF-binary** ou **v0.6+** — independente do trabalho de
fechamento de v0.5.

Esta separação dá clareza tanto para implementar quanto para
documentar e justificar academicamente.

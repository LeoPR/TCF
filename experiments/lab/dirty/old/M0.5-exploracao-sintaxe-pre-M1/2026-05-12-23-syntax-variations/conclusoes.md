# Conclusões — simplificações ortogonais, v3 vence em D2

Roundtrip 10/10 OK. Em D2-mini e D2-completo, **v3 (v2 sem
aspas) é a melhor sintaxe testada**, com 24-27% de redução
sobre v1 e 59-61% sobre verbose.

## Resposta à pergunta do user (por que v1 e v2 quebram diferente)

A "quebra diferente" entre v1 e v2 não é cálculo de ganho — é
**duas filosofias representando os mesmos tokens**:

- **v1**: a string da decl fica inteira. As "quebras" são
  invocadas por slice em cada ref (`@N<K` ou `@N>K`).
- **v2/v3**: a string da decl é **pré-fragmentada** exatamente
  nos pontos das refs futuras. Cada fragmento ganha idx.

Ambas codificam a mesma estrutura. O trade-off de bytes depende
de quantas refs distintas chegam ao nó:

- v1 paga K explícito por ref (4-5 chars / ref)
- v2/v3 paga 1 quebra no nó + idx por ref (1-3 chars / ref)

Em D2-mini (refs concentradas em poucos slices), v2/v3 ganha.
Em iso-N1000 do exp 22 (muitos slices sobrepostos), v1 ganha.

## As 3 simplificações são ortogonais

Cada uma ataca um custo diferente:

| Simplificação | Custo atacado | Economia em D2-mini |
|---|---|---|
| Sem `@N:` (v1→v1b) | Prefixo redundante de decl | 18 bytes (16%) |
| Quebras explícitas (v1→v2) | `@N<K` por ref | 19 bytes (16%) |
| Sem aspas (v2→v3) | `'...'` em literais | 12 bytes (12%) |

São combináveis. Existem versões "v2b" (idx por fragmento + sem
`@N:`) e "v3b" (sem aspas + sem `@N:`) — não implementadas mas
seguem o mesmo padrão.

## v3 vence mas tem teto de aplicabilidade

v3 só funciona em datasets onde **literais não contêm dígitos**.
Em D2-mini/D2-completo (emails sem números) cobre 100%. Em
regime A do exp 17 (urls, iso, ips, codigos), todos os literais
contêm dígitos.

Para escalar v3, precisa **v4** com 1 das 2 opções:

1. **Escape `\` antes de dígito no literal**: custa +1 byte por
   dígito no literal
2. **Aspas só quando ambíguo**: regra "se literal tem dígito,
   coloca aspas". Custo: 2 bytes por literal com dígito

Provavelmente opção 2 vence em literais com vários dígitos
consecutivos (uma única aspa cobre todos).

## v1b é uma melhoria barata sobre v1

v1b mantém a filosofia de v1 (quebras implícitas via length),
mas remove o prefixo `@N:` redundante. Ganho de 16% sem mexer
no modelo conceitual. **Aplicável a TODOS os 21 datasets** — não
tem a limitação de v3.

Para datasets com muitos slices sobrepostos (iso-N1000), v1b
provavelmente vence v2/v3 também — herda a robustez de v1.

## Insight de design para próximas sintaxes

O caminho até aqui mostra que cada **simplificação localizada**
reduz bytes de 15-30%. Combinadas, atingem 50-65% vs verbose
em datasets favoráveis.

O próximo grande salto **não** virá de mais simplificações
textuais. Possíveis caminhos:

- **Marcadores binários** (chars de controle ou unicode reservados
  para `@`, `<`, `>` etc.): cada marcador vira 1 byte. Pode
  reduzir mais 20-30%.
- **Codificação variable-length de idx** (base 64 ou base 94):
  idx 1-93 em 1 byte. Útil quando há muitos idx pequenos.
- **Híbrido v1/v2 por nó**: escolhe a sintaxe que tem menos bytes
  por nó, marcando com 1 byte no início. Pode dar ótimo
  universal.

## Pontos a registrar

1. **v3 vence em datasets sem dígitos em literais**: -27% vs v1
   em D2-mini, -24% em D2-completo
2. **v1b é barata e universal**: -16% sem perder aplicabilidade
3. **Simplificações são ortogonais e combináveis**
4. **Próximo passo natural**: v4 = v3 com aspas condicionais
   (cobre regime A) ou escalar v3 só nos datasets onde funciona
5. **Não confundir mecanismo com formato**: a filosofia v1 vs
   v2 é diferente; ambas têm vida em cenários diferentes

## O que este experimento não mostra

- Comportamento em datasets com dígitos em literais (urls, iso,
  ips, codigos)
- Comportamento em escala (N >> 12)
- Comparação com gzip — saber se ganho de bytes sobrevive
- Marcadores binários ou chars unicode reservados
- Híbrido v1/v2 por nó (escolha dinâmica)

## Próximos experimentos naturais

**Direção A — fechar a sintaxe textual**:
- v4 com aspas condicionais ou escape — cobre regime A
- Escalar v3 (sem mudança) só nos 2 datasets compatíveis

**Direção B — saltar para benchmark externo**:
- TCF (v1, v3) + gzip vs CSV + gzip vs HTFC
- Saber onde o TCF realmente compete

**Direção C — pular para binário**:
- Marcadores unicode reservados ou chars de controle
- 1 byte por marcador estrutural

Sugestão pessoal: **Direção B** antes das outras. Saber se TCF
compete externamente (depois de gzip) é input fundamental:
- Se compete: vale refinar mais sintaxes
- Se não compete (gzip apaga o ganho): TCF se posiciona como
  legível, não como denso, e mais sintaxes viram refinamento
  estético

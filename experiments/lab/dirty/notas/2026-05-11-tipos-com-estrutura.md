# Tipos com estrutura conhecida — nota conceitual para resgate

Data: 2026-05-11
Contexto: pedido do user após exp 17 mostrar que CPFs e UUIDs
ficaram 100% literais (algoritmo do exp 16 não detecta padrão).
Status: **direção futura**, não foco do ciclo atual.

---

## Observação que motivou a nota

O exp 17 mostrou cobertura 0% em CPFs e 0.7% em UUIDs. Não por
defeito do algoritmo — por limite estrutural: o método do exp 16
detecta "regiões de chars consecutivos iguais", e nestes tipos
os chars entre os separadores são pseudo-random.

Mas **a estrutura está lá** — só não é detectável por LCP/LCS
literal. Por exemplo:

- Um CPF tem **separadores fixos** (`.`, `.`, `-`) em posições
  conhecidas
- O 11º dígito (último) é **checksum** dos 10 anteriores —
  redundante
- Um UUID tem **separadores fixos** (`-` em posições 8, 13, 18, 23)
- Todo char de um UUID está no alfabeto hex (16 símbolos), não 256

Se o encoder reconhecer o tipo, pode armazenar **muito menos
informação** e reconstruir o original na decodificação.

## Lista de tipos candidatos

### CPF / CNPJ

Formato CPF: `XXX.XXX.XXX-XX` (14 chars, 11 dígitos significativos).

Reduções possíveis:

- **Separadores `.` `.` `-` em posições fixas** → dedutíveis pela
  posição do dígito decodificado
- **Checksum (2 últimos dígitos)** → calculáveis a partir dos 9
  primeiros via algoritmo CPF padrão. Pode ser omitido.
- Resultado: 14 chars → **9 dígitos** (-36% texto, sem perda)
- Validação implícita: se o checksum não bate, falhou a inferência

CNPJ análogo: 18 chars → 12 dígitos.

### UUID

Formato canônico: `8-4-4-4-12 hex` (36 chars, 32 hex significativos).

Reduções possíveis:

- **Separadores `-` em posições fixas** → dedutíveis
- **Alfabeto hex** (16 símbolos) → pode ser recodificado em
  base maior (base32, base64) reduzindo total de chars
- Resultado: 36 chars → 32 hex → 22 chars em base64 (-39%)
- Ou armazenar como 16 bytes binários e expor em texto só por
  ferramenta de inspeção

### IP v4

Formato: `XXX.XXX.XXX.XXX` (7-15 chars).

Reduções possíveis:

- **Separadores `.` em 3 posições** → dedutíveis
- **Cada octeto é 0-255** → cabe em 1 byte literal ou
  representação de 1-3 chars
- Resultado: 4 inteiros de 0-255 → 4 bytes textuais ou 3-12 chars

### ISO timestamps

Formato típico: `YYYY-MM-DDTHH:MM:SSZ` (20 chars).

Reduções possíveis:

- **Separadores `-` `T` `:` `Z`** → dedutíveis pela posição
- **Componentes têm range fixo**: ano 4 dígitos, mês 1-12, dia 1-31,
  etc.
- **Delta encoding** se ordenados: ver
  [`comparacoes-nao-literais.md`](2026-05-11-comparacoes-nao-literais.md)
- Em casos de mesmo dia: só horário muda (8-10 chars → 4 chars)

### Códigos estruturados (PED-2026-00001 etc.)

Formato típico: `<prefixo>-<ano>-<serial>`.

Reduções possíveis:

- **Prefixo + ano** se repetidos → ref a uma decl única (já feito
  pelo exp 16!)
- **Serial monotônico** → delta de +1 entre adjacentes (lossless,
  se ordenados)

### Datas brasileiras / americanas / europeias

`DD/MM/AAAA`, `MM/DD/AAAA`, `YYYY-MM-DD`. Análogo a ISO mas com
separador `/` e ordens diferentes.

### Telefones brasileiros

`(11) 98765-4321` (15 chars) → 11 dígitos significativos +
formato. Separadores `(`, `)`, ` `, `-` dedutíveis. DDD pode ser
agrupado entre múltiplas strings.

### Emails

Estrutura `local@dominio.tld`. O algoritmo do exp 16 **já captura
parcialmente** via LCP/LCS (foi onde exp 13-15 demonstraram).
Reduções adicionais:

- Domínios repetidos → dicionário implícito (já feito)
- TLDs comuns (`.com`, `.com.br`) → símbolos reservados

## Padrão geral

Cada tipo tem 3-4 elementos comuns que abrem espaço para
compressão estrutural:

1. **Separadores em posições fixas** — dedutíveis, não precisam
   ser armazenados
2. **Alfabeto restrito** — permite recodificação em base maior
3. **Redundância interna** (checksum, formato) — dedutível
4. **Ranges conhecidos** de cada componente — permite encoding
   binário compacto

## Trade-off

Ganhos:

- Compressão muito maior em tipos reconhecidos (UUID 36→22,
  CPF 14→9)
- Validação implícita (formato errado falha na inferência)
- Texto fica mais inspecionável (separadores não precisam estar lá)

Custos:

- Detector de tipo por coluna (regex ou heurística)
- Encoder/decoder específico por tipo
- Modo fallback se string não bater o formato exato
- Generalidade: cada tipo é caso especial
- Manutenção: novos formatos exigem novos handlers

## Como isso interage com o algoritmo atual

Modo de composição mais limpo: **tipos especiais como
pré-transformação por coluna**, similar a delta encoding (ver
[`comparacoes-nao-literais.md`](2026-05-11-comparacoes-nao-literais.md)).

```
Coluna bruta (CPFs)
    ↓ transformação por tipo (drop separadores + checksum)
Coluna em formato compactado (só 9 dígitos por linha)
    ↓ algoritmo do exp 16 (LCP/LCS)
Coluna codificada em TCF
    ↓ encode_online (sintaxe textual)
TCF final
```

O encoder do exp 16 não precisa saber que é CPF — ele recebe uma
coluna de strings transformadas. O decoder TCF reconstrói as
strings transformadas; uma camada acima reaplica
`separadores + checksum` para devolver o CPF original.

Composição limpa, ortogonal. Cada tipo é uma "pré-transformação".

## Quando retomar

Pré-condições para abrir experimento de tipos especiais:

- Algoritmo lossless estabilizado (exp 16 já está) ✓
- Comportamento mapeado em famílias variadas (exp 17) ✓
- Comportamento mapeado em escala (exp 18 próximo)
- Variantes algorítmicas exploradas (exps 19, 20, 21)
- Marcadores compactos investigados (ver
  [`marcadores-compactos.md`](2026-05-11-marcadores-compactos.md))

Tipos especiais entram **depois** porque:

- São casos particulares; cada um é um experimento
- A camada de pré-transformação é ortogonal — pode ser adicionada
  sem mudar o encoder principal
- O ganho real depende do tipo: testar 1 ou 2 primeiro (CPF e UUID
  são bons candidatos por serem extremos no exp 17)

## Estrutura possível dos experimentos por tipo

Cada tipo seria um experimento dedicado:

- `XX-cpf-estrutural/` — detecta CPF, drop separadores+checksum,
  passa para encoder
- `XX-uuid-estrutural/` — detecta UUID, recodifica em base maior
- `XX-ip-estrutural/` — IPs em 4 octetos
- `XX-iso-estrutural/` — timestamps com componentes separados

Roundtrip lossless **obrigatório** em todos.

## Arquivos relacionados

- [`comparacoes-nao-literais.md`](2026-05-11-comparacoes-nao-literais.md)
  — delta encoding como pré-transformação (mesma camada)
- [`marcadores-compactos.md`](2026-05-11-marcadores-compactos.md)
  — sintaxe compacta (camada de serialização, ortogonal a tipos)
- [`../old/2026-05-09-delta-datas/`](../old/2026-05-09-delta-datas/)
  — lab arquivado sobre delta em datas (re-verificar antes de
  citar)
- [`../../../docs/workbench/_archive/tickets/open/23-P-numeric-precision.md`](../../../docs/workbench/_archive/tickets/open/23-P-numeric-precision.md)
  — ticket arquivado sobre tratamento numérico
- [exp 17](../2026-05-11-17-familias-variadas/conclusoes.md) —
  onde ficou claro que CPF e UUID precisam de outra abordagem

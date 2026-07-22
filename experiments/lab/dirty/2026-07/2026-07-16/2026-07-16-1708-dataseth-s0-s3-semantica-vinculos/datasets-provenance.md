# Proveniência dos dados

**Natureza**: corpus sintético de design, construído em 2026-07-16 para falsificar distinções do contrato S0–S3. Não é evidência ecológica nem sustenta alegação de ganho de compressão.

## Entradas

- `inputs/01-corpus-json-completo.json`: vinte casos mínimos e compostos de JSON padrão: raízes arbitrárias, tipos escalares, Unicode, controles/newline, vazios, ausência versus null, arrays mistos, ragged, irmãos e estrutura sem folhas.
- `inputs/02-duplicate-key-invalid.json`: contraprova intencional; o contrato DatasetH rejeita nomes duplicados porque sua semântica seria dependente do parser de origem.

Não houve download, anonimização ou uso de dados externos. Progressão realista e real-world pertence a S4+, depois que o contrato e a álgebra sobreviverem a este corpus de design.

# Stream vs Standalone — verificacao em-processo + pendencias reais

## Contexto

EXP-003a mediu compressao gzip **standalone** (`gzip.compress(data)`).
User levantou questao valida: o comportamento em **canais stream**
(HTTP/1.x, /2, /3 com transfer-encoding) eh similar?

## Verificacao em-processo (2026-05-05)

Lab `experiments/lab/clean/EXP-003a-calibration/verify-stream.py`
mediu 3 modos sobre os mesmos 5 datasets:

| Modo | Descricao | Diff vs standalone |
|------|-----------|-------------------|
| M1 | `gzip.compress(data)` standalone | 0% (referencia) |
| M2 | `GzipFile.write()` em chunks, sem flush forcado | **0% — identico a M1** |
| M3 | `GzipFile.write()` em chunks com `Z_SYNC_FLUSH` a cada 1KB | **+5% a +22% (avg +10%)** |

**Conclusao em-processo**:
- HTTP/1.x+ com `Content-Encoding: gzip` aplicado a body completo
  → comportamento ≈ M2 ≈ M1. EXP-003a eh referencia valida.
- Cenarios com flush por mensagem (WebSocket per-message-deflate sem
  context_takeover, gRPC stream com small messages) → comportamento
  ≈ M3. Custa 5-22% adicional dependendo de chunk_size e estrutura.

## O que NAO foi testado (pendencia)

Verificacao foi puramente em-processo (Python `gzip` lib). Para teste
rigoroso, precisa servidor real. Pendencias:

| # | Cenario | Por que importa |
|---|---------|-----------------|
| P1 | HTTP/1.1 com Apache/Nginx + `Content-Encoding: gzip` | maioria dos APIs ainda usa |
| P2 | HTTP/2 com gzip body + hpack header | header compression diferente |
| P3 | HTTP/3 com QUIC + brotli streaming | proximo padrao moderno |
| P4 | WebSocket per-message-deflate | streams interativos |
| P5 | gRPC com gzip codec | RPC binario com compressao |
| P6 | Latencia (nao so bytes) | flush antes pode vencer se tempo importa |
| P7 | Brotli/zstd standalone vs streaming | brotli tem janela 16MB; pode mudar curva |

## Quando rodar P1-P7

Apos:
- M-chunks-v04 implementado (chunks reais existem)
- HP-T1 e HP-T2 validados em-processo
- Decisao de quais Propostas (E/H/I) entrarao no core

Setup proposto:
- Caddy ou Nginx local com configuracao minima
- Cliente: `curl --compressed` ou Python `requests`
- Mede: bytes na rede (tcpdump ou Content-Length header)
- Compara: TCF v0.4 modes × HTTP version × compressor

Custo estimado: 1-2 dias para infraestrutura + testes.

## Por que registrar agora se nao testar agora

Sem este documento, no futuro:
- Esquecemos que HP-T2 foi validada SO em-processo
- Decisoes baseadas em referencia incompleta
- Possivelmente publicar paper com claim "stream comprime igual standalone"
  sem prova real

Com este documento:
- Lembrete explicito de que precisa teste com servidor real
- Lista das 7 pendencias (P1-P7)
- Custo estimado

## Decisao se conflito aparecer

Caso resultado em-processo (M2≈M1) NAO se confirmar em servidor real:

- M2 era simulacao razoavel mas nao perfeita
- Re-rodar EXP-003a/003b com numeros corrigidos
- Possivel ajuste de defaults de chunk_size

Em qualquer caso, **a metodologia (medir bytes em datasets variados)
permanece valida**. So a referencia base muda.

## Status

- Verificacao em-processo: **OK** (M2 ≈ M1 confirmado)
- Pendencia P1-P7: **registrada**
- Bloqueia EXP-003b/EXP-007? **NAO** — referencia em-processo eh
  suficiente para decisoes iniciais
- Bloqueia release v0.4 publico? **SIM, ao menos P1+P3** —
  publicar reivindicando "comprime bem em stream" sem testar eh ruim

## Localizacao das saidas

- Codigo: `experiments/lab/clean/EXP-003a-calibration/verify-stream.py`
- Resultados: `experiments/lab/clean/EXP-003a-calibration/results/stream-verification.json`
- Esta nota: aqui

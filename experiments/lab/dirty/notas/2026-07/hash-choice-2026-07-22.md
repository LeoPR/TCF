# Escolha de hash — pesquisa (2026-07-22)

**Força**: referência/guia (não altera código). Motivado por pergunta do owner: "sha256 tem
intenção criptográfica que o torna mais lento; há hashes mais rápidos, menos colisões, sem
compromisso cripto (xxhash?)".

## Auditoria — onde há hash no repo

- **`src/tcf` (core): ZERO hash criptográfico.** A hot-path do encode não usa sha256/blake. O
  dedup de valores únicos usa o `dict`/`set` do Python (SipHash-1-3 interno, já rápido e
  DoS-resistente; randomizado por `PYTHONHASHSEED`, logo **não serve** como fingerprint estável).
- **`../scripts/bench_perf/manifest.py`**: `sha256` do `cases.json` (fingerprint da matriz p/ a
  guarda `.8`↔`.9`). **One-time, arquivo pequeno** — microssegundos num run de minutos.
- **`../scripts/bench_perf/calibrators.py`**: `C2_hash` = workload DELIBERADO (mede hash/s da
  máquina). Não deve ser otimizado — é referência estável de calibração.

**Conclusão: nenhum uso atual é crítico de performance.** Trocar o sha256 hoje economiza zero.

## Benchmark (esta máquina, 50 MB, min de N)

| algoritmo | MB/s | vs sha256 | cripto | dep |
|---|---:|---:|:--:|:--:|
| sha256 (atual) | 338 | 1,0× | sim | stdlib |
| blake2b | 406 | 1,2× | sim | **stdlib** |
| blake2s | 259 | 0,8× | sim | stdlib |
| md5 | 576 | 1,7× | não (colide) | stdlib |
| sha1 | 771 | 2,3× | quebrado | stdlib |
| xxh3_128 | *~15-50×* (típico) | — | não | terceiro |
| BLAKE3 | *~5-10×* (típico) | — | sim | terceiro |

**Nota**: CPUs modernas têm **SHA-NI** (aceleração de sha256 em hardware) — por isso o gap p/ o
blake2b é só 1,2×. O salto grande é só com não-cripto (xxHash) ou BLAKE3, ambos deps de terceiro.

## Guia de decisão (para quando importar — contrato/content-addressing, `.9`/1.0)

O lugar futuro onde a escolha pesa é a **assinatura de contrato** (`H-CONTRACT-EXTERN-01`) e
content-addressing, SE hashear payloads grandes ou por-valor:

- **Precisa de integridade (anti-adulteração)?**
  - zero-dep: **`hashlib.blake2b`** (stdlib, cripto, 1,2× mais rápido que sha256, saída de 512b
    truncável). Default pragmático.
  - máxima velocidade cripto + paralelismo: **BLAKE3** (dep `blake3`, SIMD + tree-hash).
- **É só fingerprint NÃO-cripto em escala (dedup, content-id, sem adversário)?**
  - **xxHash (xxh3_128)** (dep `xxhash`) — o mais rápido, ~GB/s, SMHasher-clean. É o que o owner
    lembrou. Alternativas de qualidade: wyhash, FarmHash, MetroHash, HighwayHash (SIMD, keyed).
- **Fingerprint estável, zero-dep, não-cripto, arquivo único** (ex.: um cheque de igualdade
  exato): `zlib.crc32`/`adler32` (stdlib, 32-bit) bastam quando não se busca num espaço — mas
  128-bit (blake2b truncado) é mais seguro como convenção.

## Recomendação

1. **Manter sha256** no manifesto/calibrador (custo zero; o calibrador PRECISA ser estável).
2. **Decidir de antemão** o hash do contrato quando construir a assinatura — não nascer com o
   hash errado. Requisito manda: integridade → blake2b (stdlib) ou BLAKE3 (dep); fingerprint puro
   → xxHash (dep).
3. Se um dia surgir hash na hot-path do TCF (content-addressing por-valor), medir com o
   `bench_perf` antes — o gap sha256→xxHash só compensa se o hash for fração relevante do encode.

Cross-ref: [`H-CONTRACT-EXTERN-01`](../2026-05/roadmap-hipoteses.md) (assinatura de contrato).

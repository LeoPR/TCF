# INDEX

| arquivo | o que e' |
|---|---|
| `intermediates/corte-fora-de-fase.json` | os 40 tamanhos de fatia (1..40) em dias uteis (periodo 5), com RT por tamanho — a prova da pergunta 2 |
| `intermediates/penhasco-por-tamanho-de-fatia.json` | bytes/valor por tamanho de fatia + se o marcador seq-RLE ativou — a prova da pergunta 4 |
| `outputs/<tipo>.inteiro.tcf` | o wire de 600 valores em UMA fatia |
| `outputs/<tipo>.8fatias.tcf` | os mesmos 600 em 8 fatias independentes (separadas por `=== FATIA ===`, que NAO faz parte do wire) |
| `outputs/<tipo>.*.roundtrip.json` | contra-prova: diff contra `inputs/<tipo>.entrada.json` |

Cada fatia de `*.8fatias.tcf` e' um wire COMPLETO e decodificavel sozinho — e' isso que 'responder em slices' quer dizer.

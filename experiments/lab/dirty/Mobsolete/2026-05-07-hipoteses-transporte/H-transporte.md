# Hipóteses: TCF chunked vs monolítico + camada de transporte inteligente

**Data:** 2026-05-07
**Status:** hipóteses abertas — sem experimento ainda

---

## Contexto

TCF pode descrever semanticamente seus dados (tipos de coluna, cardinalidade, order, RLE spans, dict references) de forma que uma camada acima use essa informação para otimizar o transporte. A questão central é: em que medida isso é necessário, ou se a camada de transporte consegue fazer o mesmo trabalho com um TCF monolítico opaco.

**Baseline de comparação:** camada de transporte que recebe um TCF monolítico e o fatiia/envia ela mesma, sem nenhum conhecimento semântico do formato.

---

## H0 — Hipótese nula

> Não existe cenário real onde TCF chunked/semântico oferece vantagem mensurável sobre TCF monolítico + camada de transporte genérica inteligente.

Se verdadeira: a complexidade de chunks no formato não se justifica; manter TCF simples e delegar tudo ao transportador.

---

## H1 — Latência percebida (time-to-first-useful-data)

> Em redes de alta latência, TCF com colunas ordenadas semanticamente (coluna-chave primeiro) reduz o tempo até o primeiro dado útil comparado a monolítico, porque a camada de transporte pode entregar o primeiro chunk já decodificável de forma independente.

**Condição de falha:** se o transportador conseguir identificar o início da primeira coluna no stream monolítico e entregar progressivamente, o ganho desaparece.

**Onde TCF ajuda:** o transportador só consegue fatiar corretamente se souber onde terminam as colunas — o que exige parsear o formato. Com chunks explícitos, ele não precisa parsear, só alinhar.

---

## H2 — Custo de retransmissão em redes com perda

> Chunks menores e autodescritivos reduzem o custo de retransmissão em redes com perda de pacotes: apenas o chunk corrompido precisa ser reenviado, não o arquivo inteiro.

**Condição de falha:** qualquer protocolo com checksums por segmento (TCP, QUIC) já faz isso ao nível de bytes — o transportador retransmite só o segmento perdido independentemente do TCF ser monolítico ou chunked.

**Onde TCF ajuda:** o chunk é a unidade de retransmissão *semanticamente significativa* — retransmitir meio-chunk não serve de nada para o decoder. Se o chunk coincide com a unidade de transporte, evita-se retransmissão de dados inúteis.

---

## H3 — Paralelismo real

> Chunks independentes (sem referências cruzadas — sem dict global) permitem que múltiplas conexões/workers decodifiquem em paralelo, coisa que monolítico não permite independentemente da inteligência do transportador.

**Condição de falha:** se o paralelismo for só de transferência (não de decodificação), o monolítico com HTTP range requests já resolve.

**Onde TCF ajuda:** o gargalo pode ser CPU de decodificação, não banda. Chunks autodescritivos permitem pipeline decode paralelo. Monolítico com dict global é inerentemente sequencial.

---

## H4 — Metadados semânticos como hint para o transportador

> Mesmo que o TCF permaneça monolítico, ter metadados no header (cardinalidade, tipos, tamanho estimado por coluna) permite que a camada de transporte tome decisões melhores (priorização, compressão seletiva, prefetch) do que com dados opacos.

**Esta hipótese é independente das outras:** TCF pode fornecer semântica sem ser chunked. O valor está nos metadados, não na topologia.

---

## H5 — Hipótese de inutilidade do chunking em LLM context

> Para o caso de uso primário do TCF (entrada de dados para LLMs via contexto), chunking e otimização de transporte são irrelevantes: o LLM recebe o contexto inteiro de uma vez, e a rede não é o gargalo.

Se verdadeira: a topologia de chunks só importa para casos de uso secundários (streaming de datasets grandes, APIs, pipelines de dados). O design de TCF não deve ser puxado por esses casos.

---

## Experimento proposto (quando chegar a hora)

**Setup mínimo:** servidor local simulando latência/perda com `tc netem` ou equivalente Windows. Duas condições:
- Condição A: TCF monolítico, transportador fatia por bytes fixos
- Condição B: TCF chunked, transportador alinha aos chunks

**Métricas:** time-to-first-decode, tempo total de decode, CPU de decode, bytes retransmitidos.

**Critério de decisão:** se nenhuma métrica em B supera A por >10% em algum cenário realista → H0 não rejeitada → simplificar TCF.

---

## Decisões abertas

1. Qual o cenário de rede "realista" para TCF? (LLM API call? dataset pipeline? real-time stream?)
2. O column ordering semântico fica no TCF ou é hint separado?
3. TCF chunked precisa proibir dict global, ou permite dict-por-chunk como compromisso?

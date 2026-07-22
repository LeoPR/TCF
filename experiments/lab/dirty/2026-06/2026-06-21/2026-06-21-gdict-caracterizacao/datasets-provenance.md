# Provenance — datasets same-domain-ref (B1 Etapa 5) [apontamento]

Dados efêmeros de caracterização. **Raw fica em `Z:/tcf-data/external/`**; aqui só o apontamento
(regra do projeto: dado baixado não se mistura ao repo). Regeneráveis pelos comandos abaixo.
NÃO são datasets canônicos (não têm metadata.json/hub) — são amostras de caracterização do B1.

## 1. OpenFlights routes (rotas aéreas — same-domain: aeroporto origem/destino)

- **Fonte**: https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat
- **Local**: `Z:/tcf-data/external/openflights/routes.dat` (~2.4 MB, 67663 linhas)
- **Licença**: OpenFlights, Open Database License (ODbL).
- **Formato** (CSV sem header): `airline, airline_id, source_airport, source_airport_id,
  dest_airport, dest_airport_id, codeshare, stops, equipment`.
- **Colunas same-domain**: `source_airport`~`dest_airport` (códigos IATA, K≈3425) e
  `source_airport_id`~`dest_airport_id` (ids, K≈3334).

## 2. SNAP ca-GrQc (grafo de colaboração — same-domain: nó from/to)

- **Fonte**: https://snap.stanford.edu/data/ca-GrQc.txt.gz
- **Local**: `Z:/tcf-data/external/snap-ca-grqc/ca-GrQc.txt` (descomprimido, ~0.35 MB, 28980 arestas)
- **Licença**: SNAP (Stanford), uso acadêmico.
- **Formato**: edge-list TSV `FromNodeId  ToNodeId` (4 linhas de comentário `#` no topo).
- **Colunas same-domain**: `from_node`~`to_node` (ids de nó, K≈5242, Jaccard 1.000).

## Regenerar

```python
import urllib.request, gzip, os
os.makedirs("Z:/tcf-data/external/openflights", exist_ok=True)
os.makedirs("Z:/tcf-data/external/snap-ca-grqc", exist_ok=True)
urllib.request.urlretrieve(
    "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat",
    "Z:/tcf-data/external/openflights/routes.dat")
raw = urllib.request.urlopen("https://snap.stanford.edu/data/ca-GrQc.txt.gz").read()
open("Z:/tcf-data/external/snap-ca-grqc/ca-GrQc.txt", "wb").write(gzip.decompress(raw))
```

Leitura na medição: [`etapa5_real_samedomain.py`](etapa5_real_samedomain.py) (lê direto de Z:).
Se virarem fixtures permanentes, promover a canônico (metadata.json + hub) — não necessário pro B1.

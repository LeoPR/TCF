# data-local/ — fallback storage

Esta pasta e um **fallback** usado por `scripts/_paths.py` quando voce
nao cria `config/storage.json`.

## Quando e usada

Se voce NAO tem `config/storage.json`, `_paths.py` coloca dados aqui
(dentro do projeto). Util para dev rapido sem precisar de disco extra.

## Quando NAO usar

- Se o projeto esta no **OneDrive** (caso do dev principal), use um
  disco externo via `config/storage.json` para **nao sincronizar gigas**.
- Se voce vai baixar datasets grandes (>100MB).

## Como configurar o disco externo

```bash
# Copiar template
cp config/storage.json.example config/storage.json

# Editar storage.json para apontar para seu disco
# Exemplo:
#   { "data_root": "Z:/tcf-data" }
#   { "data_root": "/mnt/data/tcf" }
#   { "data_root": "D:/datasets/tcf" }

# Verificar
python scripts/_paths.py
```

## O que fica nesta pasta

Se voce usar este fallback, eventualmente vai aparecer aqui:

```
data-local/
├── external/
├── interim/
├── processed/
└── archives/
```

**Nada disso vai para git.** O `.gitignore` exclui todo o conteudo
exceto este README e o `.gitkeep`.

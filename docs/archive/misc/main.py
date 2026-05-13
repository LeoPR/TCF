import os
import json
import pandas as pd

# Diretório e metadata fixos
cwd = os.getcwd()
metadata_path = os.path.join(cwd, "metadata.json")
if not os.path.isfile(metadata_path):
    print("metadata.json não encontrado no diretório atual.")
    exit(1)

with open(metadata_path, encoding="utf-8") as f:
    metadata = json.load(f)

# Leitura dos DataFrames e definição dos metadados
tables = {}
meta_info = {}
for tname, spec in metadata.items():
    file_part, pk, fks = None, None, {}
    v = str(spec).strip()
    if "#" in v:
        file_part, tail = v.split("#", 1)
        file_part = file_part.strip()
        if "=" in tail:
            for pair in tail.split(","):
                if "=" in pair:
                    k, col = pair.strip().split("=", 1)
                    fks[k.strip()] = col.strip()
        else:
            pk = tail.strip()
    else:
        file_part = v

    # Encontra o arquivo certo
    fpath = os.path.join(cwd, file_part)
    if not os.path.isfile(fpath):
        if os.path.isfile(file_part):
            fpath = file_part
        elif os.path.isfile(file_part + ".csv"):
            fpath = file_part + ".csv"
        elif os.path.isfile(file_part + ".json"):
            fpath = file_part + ".json"
        else:
            print(f"Arquivo para '{tname}' não encontrado: {file_part}")
            exit(1)
    if fpath.lower().endswith(".csv"):
        df = pd.read_csv(fpath, dtype=str, keep_default_na=False)
    elif fpath.lower().endswith(".json"):
        with open(fpath, encoding="utf-8") as fj:
            raw = json.load(fj)
            if isinstance(raw, list):
                df = pd.DataFrame(raw)
            elif isinstance(raw, dict) and "rows" in raw:
                df = pd.DataFrame(raw["rows"])
            else:
                print(f"{fpath} inválido. Deve ser lista ou dict com 'rows'.")
                exit(1)
    else:
        print(f"Extensão de arquivo não suportada: {fpath}")
        exit(1)
    tables[tname] = df
    meta_info[tname] = {"file": fpath, "pk": pk, "fks": fks}

# Processamento e JOINs
data_out = {}
referencias_faltantes = []
for tname, meta in meta_info.items():
    df = tables[tname]
    fks = meta["fks"]
    pk = meta["pk"]
    if not fks:
        data_out[tname] = df.fillna("").to_dict(orient="records")
        continue
    df_merged = df.copy()
    for alvo, col_fk in fks.items():
        alvo_pk = meta_info[alvo]["pk"]
        alvo_df = tables[alvo].copy()
        # Renomear apenas se houver conflito (exceto a PK)
        cols_a_renomear = [c for c in alvo_df.columns if c != alvo_pk and c in df_merged.columns]
        alvo_df_ren = alvo_df.rename(columns={c: f"{c}_{alvo}" for c in cols_a_renomear})
        # Realiza o merge
        merged = df_merged.merge(
            alvo_df_ren,
            how="left",
            left_on=col_fk,
            right_on=alvo_pk,
            suffixes=("", f"_{alvo}")
        )
        # Monta o objeto relacionado
        obj_cols = [c for c in alvo_df_ren.columns]
        def build_obj(row):
            refval = row[alvo_pk]
            if pd.isna(refval) or str(refval).strip() == "":
                referencias_faltantes.append(f"{tname}:{col_fk} => {alvo}({row.get(col_fk)})")
                return None
            return {c.replace(f"_{alvo}",""): row[c] for c in obj_cols}
        merged[alvo] = merged.apply(build_obj, axis=1)
        # Remove colunas extras do merge gerado (menos PK)
        dropcols = [c for c in merged.columns if c in obj_cols and c != alvo_pk]
        df_merged = merged.drop(columns=dropcols)
    data_out[tname] = df_merged.fillna("").to_dict(orient="records")

counts = {k: len(v) for k, v in data_out.items()}

consolidated = {
    "meta": meta_info,
    "counts": counts,
    "data": data_out,
    "avisos": referencias_faltantes
}
saida = os.path.join(cwd, "consolidated.json")
with open(saida, "w", encoding="utf-8") as f:
    json.dump(consolidated, f, indent=2, ensure_ascii=False)

print(f"OK: gravado {saida}")
if referencias_faltantes:
    print(f"Avisos: {len(referencias_faltantes)} referências não resolvidas.")
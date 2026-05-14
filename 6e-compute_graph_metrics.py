#!/usr/bin/env python3
"""Compute graph metrics per subject."""

import os

import numpy as np
import pandas as pd
import yaml
import networkx as nx

CONFIG_PATH = "configs/default.yaml"


def load_config(path: str = CONFIG_PATH) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def adjacency_to_nx(A: np.ndarray, threshold_percentile: float) -> nx.Graph:
    n = A.shape[0]
    A_thr = A.copy()
    np.fill_diagonal(A_thr, 0)
    upper = A_thr[np.triu_indices(n, k=1)]
    if len(upper) == 0:
        return nx.Graph()
    thr = np.percentile(upper, threshold_percentile)
    A_thr[A_thr < thr] = 0
    return nx.from_numpy_array(A_thr)


def graph_metrics(A: np.ndarray, threshold_percentile: float) -> dict:
    G = adjacency_to_nx(A, threshold_percentile)
    if G.number_of_nodes() == 0:
        return {
            "degree": 0.0,
            "clustering": 0.0,
            "path_length": 0.0,
            "global_eff": 0.0,
            "local_eff": 0.0,
        }
    try:
        Gc = G.subgraph(max(nx.connected_components(G), key=len)).copy()
        return {
            "degree": float(np.mean([d for _, d in Gc.degree()])),
            "clustering": float(nx.average_clustering(Gc)),
            "path_length": float(
                nx.average_shortest_path_length(Gc) if nx.is_connected(Gc) else 0.0
            ),
            "global_eff": float(nx.global_efficiency(Gc)),
            "local_eff": float(nx.local_efficiency(Gc)),
        }
    except Exception:
        return {
            "degree": 0.0,
            "clustering": 0.0,
            "path_length": 0.0,
            "global_eff": 0.0,
            "local_eff": 0.0,
        }


def main() -> None:
    cfg = load_config()
    meta = pd.read_csv(cfg["data"]["metadata"])

    processed_dir = cfg["data"]["processed_dir"]
    thr = float(cfg["graph_metrics"]["threshold_percentile"])
    rows = []

    for _, row in meta.iterrows():
        sid = row["subject_id"]
        proc_dir = os.path.join(processed_dir, sid)
        paths = {
            "mri": os.path.join(proc_dir, f"{sid}_A_mri.npy"),
            "pet": os.path.join(proc_dir, f"{sid}_A_pet.npy"),
            "fused": os.path.join(proc_dir, f"{sid}_A_fused.npy"),
        }

        if any(not os.path.isfile(p) for p in paths.values()):
            print(f"[SKIP] {sid} missing adjacency files")
            continue

        record = {"subject_id": sid, "label": row["label"]}
        for tag, path in paths.items():
            A = np.load(path)
            metrics = graph_metrics(A, thr)
            for k, v in metrics.items():
                record[f"{tag}_{k}"] = v

        rows.append(record)
        print(f"[OK] {sid}")

    df = pd.DataFrame(rows)
    df.to_csv(cfg["data"]["graph_metrics_csv"], index=False)
    print(f"Saved: {cfg['data']['graph_metrics_csv']} shape={df.shape}")


if __name__ == "__main__":
    main()

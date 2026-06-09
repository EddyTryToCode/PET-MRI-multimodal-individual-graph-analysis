#!/usr/bin/env python3
"""Build PET adjacency matrices using Wasserstein distances."""

import os
import pickle

import numpy as np
import pandas as pd
import yaml
from scipy.stats import wasserstein_distance

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CONFIG_PATH = "configs/default.yaml"


def load_config(path: str = CONFIG_PATH) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def compute_distance_matrix(
    roi_voxels: dict, roi_ids: list, min_voxels: int
) -> np.ndarray:
    n = len(roi_ids)
    D = np.full((n, n), np.inf, dtype=np.float32)
    np.fill_diagonal(D, 0.0)

    valid = {}
    for rid in roi_ids:
        vals = roi_voxels.get(rid)
        if vals is not None and len(vals) >= min_voxels and np.any(vals):
            valid[rid] = vals

    for a, rid_i in enumerate(roi_ids):
        if rid_i not in valid:
            continue
        for b in range(a + 1, n):
            rid_j = roi_ids[b]
            if rid_j not in valid:
                continue
            d = wasserstein_distance(valid[rid_i], valid[rid_j])
            D[a, b] = d
            D[b, a] = d

    return D


def resolve_sigma(D: np.ndarray, sigma_cfg) -> float:
    if isinstance(sigma_cfg, str) and sigma_cfg.lower() == "auto":
        vals = D[np.isfinite(D) & (D > 0)]
        return float(np.mean(vals)) if len(vals) else 1.0
    return float(sigma_cfg)


def distance_to_similarity(D: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0:
        sigma = 1.0
    A = np.zeros_like(D, dtype=np.float32)
    finite = np.isfinite(D)
    A[finite] = np.exp(-(D[finite] ** 2) / (2.0 * sigma ** 2))
    np.fill_diagonal(A, 1.0)
    A[~finite] = 0.0
    return A


def main() -> None:
    cfg = load_config()
    labels_df = pd.read_csv(cfg["data"]["atlas_labels"])
    roi_ids = labels_df["roi_id"].tolist()
    meta = pd.read_csv(cfg["data"]["metadata"])

    processed_dir = cfg["data"]["processed_dir"]
    min_voxels = int(cfg["roi_extraction"]["min_voxels"])
    sigma_cfg = cfg["graph_pet"]["sigma"]

    for _, row in meta.iterrows():
        sid = row["subject_id"]
        roi_path = os.path.join(
            processed_dir, sid, f"{sid}_PET_roi_voxels.pkl"
        )
        out_npy = os.path.join(processed_dir, sid, f"{sid}_A_pet.npy")
        out_qc = os.path.join(processed_dir, sid, f"{sid}_A_pet_heatmap.png")

        if os.path.exists(out_npy):
            print(f"[SKIP] {sid} already exists")
            continue
        if not os.path.isfile(roi_path):
            print(f"[SKIP] {sid} PET ROI voxels not found")
            continue

        with open(roi_path, "rb") as f:
            roi_voxels = pickle.load(f)

        D = compute_distance_matrix(roi_voxels, roi_ids, min_voxels)
        sigma = resolve_sigma(D, sigma_cfg)
        A = distance_to_similarity(D, sigma)
        np.save(out_npy, A)

        plt.figure(figsize=(8, 6))
        plt.imshow(A, cmap="hot", vmin=0, vmax=1)
        plt.colorbar(label=f"Similarity (sigma={sigma:.4f})")
        plt.title(f"{sid} PET graph")
        plt.tight_layout()
        plt.savefig(out_qc, dpi=100)
        plt.close()

        mean_val = A[np.triu_indices(len(roi_ids), k=1)].mean()
        print(f"[OK] {sid} mean_similarity={mean_val:.3f}")


if __name__ == "__main__":
    main()
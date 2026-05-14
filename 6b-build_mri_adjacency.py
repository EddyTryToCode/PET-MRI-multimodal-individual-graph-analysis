#!/usr/bin/env python3
"""Build MRI adjacency matrices using Jensen-Shannon similarity."""

import os
import pickle

import numpy as np
import pandas as pd
import yaml
from scipy.spatial.distance import jensenshannon

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CONFIG_PATH = "configs/default.yaml"


def load_config(path: str = CONFIG_PATH) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def compute_histogram(vals: np.ndarray, bins: int, epsilon: float) -> np.ndarray:
    h, _ = np.histogram(vals, bins=bins, density=False)
    h = h.astype(np.float32) + epsilon
    return h / h.sum()


def build_mri_adjacency(
    roi_voxels: dict,
    roi_ids: list,
    bins: int,
    epsilon: float,
) -> np.ndarray:
    n = len(roi_ids)
    histograms = {}
    for rid in roi_ids:
        histograms[rid] = compute_histogram(roi_voxels[rid], bins, epsilon)

    A = np.zeros((n, n), dtype=np.float32)
    for a, rid_i in enumerate(roi_ids):
        A[a, a] = 1.0
        for b in range(a + 1, n):
            rid_j = roi_ids[b]
            d = float(jensenshannon(histograms[rid_i], histograms[rid_j]))
            s = 1.0 - min(d, 1.0)
            A[a, b] = s
            A[b, a] = s
    return A


def main() -> None:
    cfg = load_config()
    labels_df = pd.read_csv(cfg["data"]["atlas_labels"])
    roi_ids = labels_df["roi_id"].tolist()
    meta = pd.read_csv(cfg["data"]["metadata"])

    processed_dir = cfg["data"]["processed_dir"]
    bins = int(cfg["graph_mri"]["bins"])
    epsilon = float(cfg["graph_mri"]["epsilon"])

    for _, row in meta.iterrows():
        sid = row["subject_id"]
        roi_path = os.path.join(
            processed_dir, sid, f"{sid}_MRI_roi_voxels.pkl"
        )
        out_npy = os.path.join(processed_dir, sid, f"{sid}_A_mri.npy")
        out_qc = os.path.join(processed_dir, sid, f"{sid}_A_mri_heatmap.png")

        if os.path.exists(out_npy):
            print(f"[SKIP] {sid} already exists")
            continue
        if not os.path.isfile(roi_path):
            print(f"[SKIP] {sid} MRI ROI voxels not found")
            continue

        with open(roi_path, "rb") as f:
            roi_voxels = pickle.load(f)

        A = build_mri_adjacency(roi_voxels, roi_ids, bins, epsilon)
        np.save(out_npy, A)

        plt.figure(figsize=(8, 6))
        plt.imshow(A, cmap="hot", vmin=0, vmax=1)
        plt.colorbar(label="JSD similarity")
        plt.title(f"{sid} MRI graph (JSD)")
        plt.tight_layout()
        plt.savefig(out_qc, dpi=100)
        plt.close()

        mean_val = A[np.triu_indices(len(roi_ids), k=1)].mean()
        print(f"[OK] {sid} mean_similarity={mean_val:.3f}")


if __name__ == "__main__":
    main()

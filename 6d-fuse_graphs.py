#!/usr/bin/env python3
"""Fuse MRI and PET adjacency matrices."""

import os

import numpy as np
import pandas as pd
import yaml

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CONFIG_PATH = "configs/default.yaml"


def load_config(path: str = CONFIG_PATH) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def fuse_adjacency(A_mri: np.ndarray, A_pet: np.ndarray, alpha: float) -> np.ndarray:
    if A_mri.shape != A_pet.shape:
        raise ValueError("Adjacency shapes do not match")
    return alpha * A_mri + (1.0 - alpha) * A_pet


def main() -> None:
    cfg = load_config()
    meta = pd.read_csv(cfg["data"]["metadata"])

    processed_dir = cfg["data"]["processed_dir"]
    alpha = float(cfg["fusion"]["alpha"])

    for _, row in meta.iterrows():
        sid = row["subject_id"]
        proc_dir = os.path.join(processed_dir, sid)
        a_mri_path = os.path.join(proc_dir, f"{sid}_A_mri.npy")
        a_pet_path = os.path.join(proc_dir, f"{sid}_A_pet.npy")
        out_path = os.path.join(proc_dir, f"{sid}_A_fused.npy")
        out_qc = os.path.join(proc_dir, f"{sid}_A_fused_heatmap.png")

        if os.path.exists(out_path):
            print(f"[SKIP] {sid} already exists")
            continue
        if not os.path.isfile(a_mri_path) or not os.path.isfile(a_pet_path):
            print(f"[SKIP] {sid} adjacency not found")
            continue

        A_mri = np.load(a_mri_path)
        A_pet = np.load(a_pet_path)
        A_fused = fuse_adjacency(A_mri, A_pet, alpha)
        np.save(out_path, A_fused)

        plt.figure(figsize=(8, 6))
        plt.imshow(A_fused, cmap="hot", vmin=0, vmax=1)
        plt.colorbar(label=f"Fused similarity (alpha={alpha})")
        plt.title(f"{sid} fused graph")
        plt.tight_layout()
        plt.savefig(out_qc, dpi=100)
        plt.close()

        n = A_fused.shape[0]
        mean_val = A_fused[np.triu_indices(n, k=1)].mean()
        print(f"[OK] {sid} mean_similarity={mean_val:.3f}")


if __name__ == "__main__":
    main()

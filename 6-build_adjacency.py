#!/usr/bin/env python3
"""
Wasserstein Distance Adjacency Matrix Builder
===============================================
Computes pairwise 1D Wasserstein (Earth Mover's) Distance between all ROI
FDG-PET voxel distributions, converts to a similarity-based adjacency matrix
via Gaussian kernel, and generates heatmap QC images.

Reference: EUSIPCO 2024 — Graph Neural Networks for Alzheimer's classification.

Input:
    ./Project_Data/sub-{id}/sub-{id}_PET_voxel_dict.pkl

Output:
    ./Project_Data/sub-{id}/sub-{id}_Adjacency_Matrix.npy
    ./QC_Adjacency/sub-{id}_Heatmap_QC.png

Dependencies:
    pip install numpy scipy matplotlib seaborn

Usage:
    python build_adjacency.py
"""

import os
import sys
import glob
import time
import pickle

import numpy as np
from scipy.stats import wasserstein_distance

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns


# ══════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════
PROJECT_DIR = "./Project_Data"
QC_DIR = "./QC_Adjacency"
N_ROIS = 100          # Number of parcels in the Schaefer Atlas
MIN_VOXELS = 10       # Minimum voxels required for a valid ROI


# ══════════════════════════════════════════════════════════════
# Core functions
# ══════════════════════════════════════════════════════════════

def load_voxel_dict(pkl_path: str) -> dict:
    """Load the ROI voxel dictionary from pickle."""
    with open(pkl_path, "rb") as f:
        return pickle.load(f)


def compute_distance_matrix(voxel_data: dict, n_rois: int) -> np.ndarray:
    """
    Compute the symmetric N×N Wasserstein distance matrix.

    ROIs are indexed 1..N in the dictionary (atlas labels).
    Matrix indices are 0..N-1.

    If an ROI is missing or has < MIN_VOXELS, its distances are set to inf.
    Diagonal is always 0.
    """
    D = np.full((n_rois, n_rois), np.inf)
    np.fill_diagonal(D, 0.0)

    # Identify valid ROIs
    valid = {}
    for roi in range(1, n_rois + 1):
        if roi in voxel_data and len(voxel_data[roi]) >= MIN_VOXELS:
            valid[roi] = voxel_data[roi]

    valid_labels = sorted(valid.keys())

    # Compute pairwise distances (upper triangle, then mirror)
    for a_idx, roi_i in enumerate(valid_labels):
        for roi_j in valid_labels[a_idx + 1:]:
            i = roi_i - 1  # 0-indexed
            j = roi_j - 1
            d = wasserstein_distance(valid[roi_i], valid[roi_j])
            D[i, j] = d
            D[j, i] = d

    return D


def distance_to_adjacency(D: np.ndarray) -> np.ndarray:
    """
    Convert distance matrix to adjacency matrix using Gaussian kernel:
        A_ij = exp(-gamma * D_ij)
    where gamma = 1 / median(valid non-zero distances).

    - If D_ij == inf  →  A_ij = 0 (no edge)
    - Diagonal A_ii = 1.0 (self-loops)
    """
    # Compute gamma from median of valid, finite, non-zero distances
    mask = np.isfinite(D) & (D > 0)
    if mask.any():
        gamma = 1.0 / np.median(D[mask])
    else:
        gamma = 1.0  # fallback

    A = np.zeros_like(D)

    finite_mask = np.isfinite(D)
    A[finite_mask] = np.exp(-gamma * D[finite_mask])

    # Ensure diagonal is 1.0 (self-loops)
    np.fill_diagonal(A, 1.0)

    # Ensure inf distances → 0 (already handled, but explicit)
    A[~finite_mask] = 0.0

    return A, gamma


def generate_heatmap(A: np.ndarray, output_path: str, title: str) -> None:
    """Generate and save a heatmap of the adjacency matrix."""
    fig, ax = plt.subplots(figsize=(8, 7))

    sns.heatmap(
        A,
        ax=ax,
        cmap="viridis",
        square=True,
        cbar=True,
        cbar_kws={"label": "Similarity (Gaussian kernel)"},
        xticklabels=False,
        yticklabels=False,
        vmin=0,
        vmax=1,
    )

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel("ROI", fontsize=10)
    ax.set_ylabel("ROI", fontsize=10)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


# ══════════════════════════════════════════════════════════════
# Main pipeline
# ══════════════════════════════════════════════════════════════

def main():
    sub_dirs = sorted(glob.glob(os.path.join(PROJECT_DIR, "sub-*")))
    total = len(sub_dirs)

    if total == 0:
        print(f"[ERROR] No sub-* folders found in {os.path.abspath(PROJECT_DIR)}")
        sys.exit(1)

    os.makedirs(QC_DIR, exist_ok=True)

    print("=" * 60)
    print("  Wasserstein Adjacency Matrix Builder")
    print(f"  Subjects  : {total}")
    print(f"  ROIs      : {N_ROIS}")
    print(f"  Min voxels: {MIN_VOXELS}")
    print("=" * 60)

    success = 0
    skipped = 0
    errors = 0
    t_start = time.time()

    for idx, sub_dir in enumerate(sub_dirs, start=1):
        sub_label = os.path.basename(sub_dir)
        pkl_path = os.path.join(sub_dir, f"{sub_label}_PET_voxel_dict.pkl")
        npy_path = os.path.join(sub_dir, f"{sub_label}_Adjacency_Matrix.npy")
        qc_path = os.path.join(QC_DIR, f"{sub_label}_Heatmap_QC.png")

        if not os.path.isfile(pkl_path):
            print(f"  [{idx}/{total}] SKIP {sub_label} — .pkl not found")
            skipped += 1
            continue

        t0 = time.time()

        try:
            # 1. Load voxel distributions
            voxel_data = load_voxel_dict(pkl_path)

            if not voxel_data:
                print(f"  [{idx}/{total}] SKIP {sub_label} — empty voxel dict")
                skipped += 1
                continue

            # 2. Compute Wasserstein distance matrix
            D = compute_distance_matrix(voxel_data, N_ROIS)

            # 3. Convert to adjacency (Gaussian kernel)
            A, gamma = distance_to_adjacency(D)

            # 4. Save adjacency matrix
            np.save(npy_path, A)

            # 5. Generate heatmap QC
            generate_heatmap(A, qc_path, title=f"{sub_label}  (γ={gamma:.4f})")

            elapsed = time.time() - t0
            n_valid = int(np.sum(np.diag(A) == 1.0))
            n_edges = int(np.sum(A > 0) - n_valid)  # off-diagonal non-zero
            print(
                f"  [{idx}/{total}] ✓ {sub_label}  "
                f"({n_valid} valid ROIs, {n_edges:,} edges, γ={gamma:.4f}, "
                f"{elapsed:.1f}s)"
            )
            success += 1

        except Exception as e:
            print(f"  [{idx}/{total}] ✗ {sub_label} FAILED: {e}")
            errors += 1

    total_time = time.time() - t_start
    print("\n" + "=" * 60)
    print(f"  Done in {total_time / 60:.1f} min")
    print(f"  Success : {success}/{total}")
    print(f"  Skipped : {skipped}/{total}")
    print(f"  Errors  : {errors}/{total}")
    print("=" * 60)


if __name__ == "__main__":
    main()

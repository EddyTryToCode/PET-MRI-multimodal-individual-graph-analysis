#!/usr/bin/env python3
"""
ADNI Schaefer Atlas Parcellation & Voxel Extraction Pipeline
==============================================================
Aligns a Schaefer Atlas to each subject's preprocessed PET space,
extracts per-ROI FDG-PET voxel intensity distributions, and generates
visual QC images of the parcellation overlay.

Input:
    ./Project_Data/sub-{id}/sub-{id}_MRI_preprocessed.nii.gz
    ./Project_Data/sub-{id}/sub-{id}_PET_preprocessed.nii.gz
    Atlas NIfTI (configured below)

Output:
    ./Project_Data/sub-{id}/sub-{id}_PET_voxel_dict.pkl
    ./QC_Parcellation/sub-{id}_Atlas_QC.png

Dependencies:
    pip install nilearn nibabel matplotlib numpy

Usage:
    python extract_roi_voxels.py
"""

import os
import sys
import glob
import time
import pickle

import numpy as np
import nibabel as nib

# Use non-interactive backend before importing pyplot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from nilearn import image as nli_image
from nilearn import plotting


# ══════════════════════════════════════════════════════════════
# Configuration — EDIT THESE PATHS
# ══════════════════════════════════════════════════════════════
PROJECT_DIR = "./Project_Data"
ATLAS_PATH = "./Atlas/schaefer_2018/Schaefer2018_100Parcels_7Networks_order_FSLMNI152_2mm.nii.gz"
QC_DIR = "./QC_Parcellation"


# ══════════════════════════════════════════════════════════════
# Core functions
# ══════════════════════════════════════════════════════════════

def resample_atlas_to_subject(atlas_img, pet_img):
    """
    Resample the atlas into the subject's PET space using nearest-neighbor
    interpolation to preserve integer ROI labels.
    """
    resampled = nli_image.resample_to_img(
        source_img=atlas_img,
        target_img=pet_img,
        interpolation="nearest",
    )
    return resampled


def extract_roi_voxels(atlas_array: np.ndarray,
                       pet_array: np.ndarray) -> dict:
    """
    For each ROI label in the atlas, extract all valid PET voxel intensities.

    Returns:
        dict  {roi_label (int): np.ndarray of voxel values}
    """
    # All unique ROI labels, excluding background (0)
    labels = np.unique(atlas_array)
    labels = labels[labels != 0]

    voxel_data = {}
    for label in labels:
        label_int = int(label)
        # Get all PET values within this ROI
        roi_mask = atlas_array == label
        values = pet_array[roi_mask]

        # Filter out zeros and NaNs
        values = values[~np.isnan(values)]
        values = values[values != 0]

        if len(values) > 0:
            voxel_data[label_int] = values

    return voxel_data


def save_voxel_dict(voxel_data: dict, output_path: str) -> None:
    """Save the ROI voxel dictionary as a pickle file."""
    with open(output_path, "wb") as f:
        pickle.dump(voxel_data, f, protocol=pickle.HIGHEST_PROTOCOL)


def generate_parcellation_qc(resampled_atlas,
                             mri_path: str,
                             output_path: str,
                             title: str) -> None:
    """
    Generate a QC image: atlas parcellation overlaid on anatomical MRI.
    """
    display = plotting.plot_roi(
        roi_img=resampled_atlas,
        bg_img=mri_path,
        display_mode="ortho",
        alpha=0.5,
        cmap="tab20",
        title=title,
        draw_cross=True,
    )
    display.savefig(output_path, dpi=150)
    display.close()
    plt.close("all")


# ══════════════════════════════════════════════════════════════
# Main pipeline
# ══════════════════════════════════════════════════════════════

def main():
    # Validate atlas
    if not os.path.isfile(ATLAS_PATH):
        print(f"[ERROR] Atlas file not found: {os.path.abspath(ATLAS_PATH)}")
        print("        Please set ATLAS_PATH at the top of this script.")
        sys.exit(1)

    # Discover subjects
    sub_dirs = sorted(glob.glob(os.path.join(PROJECT_DIR, "sub-*")))
    total = len(sub_dirs)

    if total == 0:
        print(f"[ERROR] No sub-* folders found in {os.path.abspath(PROJECT_DIR)}")
        sys.exit(1)

    # Create output directories
    os.makedirs(QC_DIR, exist_ok=True)

    print("=" * 60)
    print("  Schaefer Atlas Parcellation & Voxel Extraction")
    print(f"  Subjects : {total}")
    print(f"  Atlas    : {ATLAS_PATH}")
    print(f"  QC dir   : {os.path.abspath(QC_DIR)}")
    print("=" * 60)

    # Load atlas once (shared across all subjects)
    print("[INFO] Loading atlas ...")
    atlas_img = nib.load(ATLAS_PATH)
    n_labels = len(np.unique(atlas_img.get_fdata().astype(int))) - 1  # exclude 0
    print(f"[INFO] Atlas has {n_labels} ROI labels\n")

    success = 0
    skipped = 0
    errors = 0
    t_start = time.time()

    for idx, sub_dir in enumerate(sub_dirs, start=1):
        sub_label = os.path.basename(sub_dir)
        mri_path = os.path.join(sub_dir, f"{sub_label}_MRI_preprocessed.nii.gz")
        pet_path = os.path.join(sub_dir, f"{sub_label}_PET_preprocessed.nii.gz")
        pkl_path = os.path.join(sub_dir, f"{sub_label}_PET_voxel_dict.pkl")
        qc_path = os.path.join(QC_DIR, f"{sub_label}_Atlas_QC.png")

        # Validate inputs
        if not os.path.isfile(pet_path):
            print(f"  [{idx}/{total}] SKIP {sub_label} — PET not found")
            skipped += 1
            continue
        if not os.path.isfile(mri_path):
            print(f"  [{idx}/{total}] SKIP {sub_label} — MRI not found")
            skipped += 1
            continue

        t0 = time.time()

        try:
            # 1. Load subject PET
            pet_img = nib.load(pet_path)

            # 2. Resample atlas → subject PET space
            resampled_atlas = resample_atlas_to_subject(atlas_img, pet_img)

            # 3. Extract voxel distributions per ROI
            atlas_array = resampled_atlas.get_fdata().astype(int)
            pet_array = pet_img.get_fdata().astype(np.float32)

            voxel_data = extract_roi_voxels(atlas_array, pet_array)

            # 4. Save voxel dictionary
            save_voxel_dict(voxel_data, pkl_path)

            # 5. Generate QC image
            generate_parcellation_qc(
                resampled_atlas, mri_path, qc_path, title=sub_label
            )

            elapsed = time.time() - t0
            n_rois = len(voxel_data)
            total_voxels = sum(len(v) for v in voxel_data.values())
            print(
                f"  [{idx}/{total}] ✓ {sub_label}  "
                f"({n_rois} ROIs, {total_voxels:,} voxels, {elapsed:.1f}s)"
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

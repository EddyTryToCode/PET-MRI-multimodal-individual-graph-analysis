#!/usr/bin/env python3
"""
ADNI Quality Control Snapshot Generator
=========================================
Generates 2D ortho-view QC images overlaying preprocessed PET on MRI
for visual inspection of coregistration and skull-stripping quality.

Input:
    ./Project_Data/sub-{id}/sub-{id}_MRI_preprocessed.nii.gz
    ./Project_Data/sub-{id}/sub-{id}_PET_preprocessed.nii.gz

Output:
    ./QC_Snapshots/sub-{id}_QC.png

Dependencies:
    pip install nilearn matplotlib nibabel

Usage:
    python generate_qc.py
"""

import os
import sys
import glob
import time

# Use non-interactive backend to prevent display and memory leaks
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from nilearn import plotting


# ══════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════
PROJECT_DIR = "./Project_Data"
OUTPUT_DIR = "./QC_Snapshots"


def generate_qc_snapshot(mri_path: str,
                         pet_path: str,
                         output_path: str,
                         title: str) -> None:
    """
    Generate a single QC snapshot: PET overlaid on MRI in ortho view
    (axial + sagittal + coronal).
    """
    display = plotting.plot_stat_map(
        stat_map_img=pet_path,
        bg_img=mri_path,
        display_mode="ortho",
        alpha=0.6,
        cmap="hot",
        title=title,
        colorbar=True,
        draw_cross=True,
    )
    display.savefig(output_path, dpi=150)
    display.close()
    plt.close("all")  # Extra safety against memory leaks


def main():
    # Discover subject folders
    sub_dirs = sorted(glob.glob(os.path.join(PROJECT_DIR, "sub-*")))
    total = len(sub_dirs)

    if total == 0:
        print(f"[ERROR] No sub-* folders found in {os.path.abspath(PROJECT_DIR)}")
        sys.exit(1)

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("  ADNI QC Snapshot Generator")
    print(f"  Subjects found : {total}")
    print(f"  Output folder  : {os.path.abspath(OUTPUT_DIR)}")
    print("=" * 60)

    success = 0
    skipped = 0
    errors = 0

    t_start = time.time()

    for idx, sub_dir in enumerate(sub_dirs, start=1):
        sub_label = os.path.basename(sub_dir)
        mri_path = os.path.join(sub_dir, f"{sub_label}_MRI_preprocessed.nii.gz")
        pet_path = os.path.join(sub_dir, f"{sub_label}_PET_preprocessed.nii.gz")
        out_path = os.path.join(OUTPUT_DIR, f"{sub_label}_QC.png")

        # Check input files exist
        if not os.path.isfile(mri_path):
            print(f"  [{idx}/{total}] SKIP {sub_label} — MRI not found")
            skipped += 1
            continue
        if not os.path.isfile(pet_path):
            print(f"  [{idx}/{total}] SKIP {sub_label} — PET not found")
            skipped += 1
            continue

        try:
            generate_qc_snapshot(mri_path, pet_path, out_path, title=sub_label)
            print(f"  [{idx}/{total}] ✓ Generated QC for {sub_label}")
            success += 1
        except Exception as e:
            print(f"  [{idx}/{total}] ✗ ERROR {sub_label}: {e}")
            errors += 1

    elapsed = time.time() - t_start
    print("\n" + "=" * 60)
    print(f"  Done in {elapsed:.1f}s")
    print(f"  Success : {success}/{total}")
    print(f"  Skipped : {skipped}/{total}")
    print(f"  Errors  : {errors}/{total}")
    print(f"  Output  : {os.path.abspath(OUTPUT_DIR)}")
    print("=" * 60)


if __name__ == "__main__":
    main()

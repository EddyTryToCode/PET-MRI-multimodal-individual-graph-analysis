#!/usr/bin/env python3
"""
ADNI Quality Control Snapshot Generator
========================================
Generates QC images overlaying preprocessed PET on MRI for each subject.

Input:
  {processed_dir}/sub-*/sub-*_MRI_preprocessed.nii.gz
  {processed_dir}/sub-*/sub-*_PET_preprocessed.nii.gz

Output:
  qc/pet_over_mri/sub-*_QC.png

Dependencies:
  nilearn
  matplotlib
  pyyaml
"""

import os
import sys
import glob
import time

import yaml

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from nilearn import plotting

CONFIG_PATH = "configs/default.yaml"


def load_config(path: str = CONFIG_PATH) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def generate_qc_snapshot(
    mri_path: str, pet_path: str, output_path: str, title: str
) -> None:
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
    plt.close("all")


def main() -> None:
    cfg = load_config()
    processed_dir = cfg["data"]["processed_dir"]
    output_dir = os.path.join("qc", "pet_over_mri")

    sub_dirs = sorted(glob.glob(os.path.join(processed_dir, "sub-*")))
    total = len(sub_dirs)
    if total == 0:
        print(f"No sub-* folders found in {os.path.abspath(processed_dir)}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("ADNI QC snapshot generator")
    print(f"Subjects found: {total}")
    print(f"Output folder: {os.path.abspath(output_dir)}")
    print("=" * 60)

    success = 0
    skipped = 0
    errors = 0
    t_start = time.time()

    for idx, sub_dir in enumerate(sub_dirs, start=1):
        sub_label = os.path.basename(sub_dir)
        mri_path = os.path.join(sub_dir, f"{sub_label}_MRI_preprocessed.nii.gz")
        pet_path = os.path.join(sub_dir, f"{sub_label}_PET_preprocessed.nii.gz")
        out_path = os.path.join(output_dir, f"{sub_label}_QC.png")

        if not os.path.isfile(mri_path):
            print(f"[{idx}/{total}] SKIP {sub_label} MRI not found")
            skipped += 1
            continue
        if not os.path.isfile(pet_path):
            print(f"[{idx}/{total}] SKIP {sub_label} PET not found")
            skipped += 1
            continue

        try:
            generate_qc_snapshot(mri_path, pet_path, out_path, title=sub_label)
            print(f"[{idx}/{total}] OK {sub_label}")
            success += 1
        except Exception as e:
            print(f"[{idx}/{total}] ERROR {sub_label}: {e}")
            errors += 1

    elapsed = time.time() - t_start
    print("=" * 60)
    print(f"Done in {elapsed:.1f}s")
    print(f"Success: {success}/{total}")
    print(f"Skipped: {skipped}/{total}")
    print(f"Errors: {errors}/{total}")
    print("=" * 60)


if __name__ == "__main__":
    main()
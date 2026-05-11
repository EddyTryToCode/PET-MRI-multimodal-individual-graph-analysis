#!/usr/bin/env python3
"""
ADNI Data Restructuring Pipeline
=================================
Reads a metadata CSV (data.csv) and reorganizes raw ADNI download files into
a clean, subject-centric directory structure with NIfTI outputs.

Output structure:
    ./Project_Data/
        sub-{subject}/
            sub-{subject}_PET.nii.gz
            sub-{subject}_MRI.nii.gz

Dependencies (pip install):
    pandas
    dicom2nifti
    pydicom          (required by dicom2nifti)

Usage:
    python restructure_adni.py
"""

import os
import glob
import shutil
import gzip
import pandas as pd
import dicom2nifti

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
CSV_PATH = "./data_balanced.csv"
RAW_DATA_DIR = "./data"          # Root of the unzipped ADNI download
OUTPUT_DIR = "./Project_Data"

# ──────────────────────────────────────────────
# Step 1 – Build a lookup: img_id -> folder path
# ──────────────────────────────────────────────
def build_image_id_index(raw_dir: str) -> dict:
    """
    Walk the raw ADNI directory tree once and map every folder whose name
    starts with 'I' (image-ID folders like I224368) to its full path.
    This avoids repeated os.walk calls for each CSV row.
    """
    index = {}
    for dirpath, dirnames, _ in os.walk(raw_dir):
        for d in dirnames:
            if d.startswith("I"):
                index[d] = os.path.join(dirpath, d)
    return index


# ──────────────────────────────────────────────
# Step 2 – Processing helpers
# ──────────────────────────────────────────────
def convert_pet_dicom(src_folder: str, dest_path: str) -> None:
    """Convert a folder of DICOM slices to a single compressed NIfTI."""
    # dicom2nifti.convert_directory writes into an *output directory*,
    # so we use a temporary subfolder and then rename.
    tmp_dir = dest_path + "_tmp_dcm2nii"
    os.makedirs(tmp_dir, exist_ok=True)

    dicom2nifti.convert_directory(src_folder, tmp_dir)

    # Grab the first .nii or .nii.gz that was produced
    nii_files = glob.glob(os.path.join(tmp_dir, "*.nii.gz")) + \
                glob.glob(os.path.join(tmp_dir, "*.nii"))

    if not nii_files:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise FileNotFoundError("dicom2nifti produced no NIfTI output")

    src_nii = nii_files[0]

    if src_nii.endswith(".nii.gz"):
        shutil.move(src_nii, dest_path)
    else:
        # Compress .nii → .nii.gz
        with open(src_nii, "rb") as f_in, gzip.open(dest_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    shutil.rmtree(tmp_dir, ignore_errors=True)


def copy_mri_nifti(src_folder: str, dest_path: str) -> None:
    """Find the .nii/.nii.gz inside src_folder and copy it to dest_path."""
    nii_files = glob.glob(os.path.join(src_folder, "*.nii.gz")) + \
                glob.glob(os.path.join(src_folder, "*.nii"))

    if not nii_files:
        raise FileNotFoundError(f"No NIfTI file found in {src_folder}")

    src_nii = nii_files[0]

    if src_nii.endswith(".nii.gz"):
        shutil.copy(src_nii, dest_path)
    else:
        # Compress .nii → .nii.gz
        with open(src_nii, "rb") as f_in, gzip.open(dest_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)


# ──────────────────────────────────────────────
# Main pipeline
# ──────────────────────────────────────────────
def main():
    # Read metadata CSV
    df = pd.read_csv(CSV_PATH)
    total = len(df)
    print(f"[INFO] Loaded {total} rows from {CSV_PATH}")

    # Create output root
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Build image-ID index (single walk over the raw tree)
    print(f"[INFO] Indexing raw ADNI folders under {RAW_DATA_DIR} ...")
    img_index = build_image_id_index(RAW_DATA_DIR)
    print(f"[INFO] Found {len(img_index)} image-ID folders")

    # Counters
    success = 0
    skipped = 0
    errors  = 0

    for idx, row in df.iterrows():
        subject      = row["Subject"]
        modality     = row["Modality"]
        img_id       = row["Image Data ID"]
        file_format  = row["Format"]

        sub_label = f"sub-{subject}"
        sub_dir   = os.path.join(OUTPUT_DIR, sub_label)
        os.makedirs(sub_dir, exist_ok=True)

        # Locate the image-ID folder
        src_folder = img_index.get(img_id)
        if src_folder is None:
            print(f"  [{idx+1}/{total}] SKIP  {img_id} — folder not found in {RAW_DATA_DIR}")
            skipped += 1
            continue

        try:
            if modality == "PET" and file_format == "DCM":
                dest = os.path.join(sub_dir, f"{sub_label}_PET.nii.gz")
                convert_pet_dicom(src_folder, dest)
                print(f"  [{idx+1}/{total}] ✓ Converted PET for {sub_label}  ({img_id})")

            elif modality == "MRI" and file_format == "NiFTI":
                dest = os.path.join(sub_dir, f"{sub_label}_MRI.nii.gz")
                copy_mri_nifti(src_folder, dest)
                print(f"  [{idx+1}/{total}] ✓ Copied   MRI for {sub_label}  ({img_id})")

            else:
                print(f"  [{idx+1}/{total}] SKIP  {img_id} — unhandled modality/format "
                      f"({modality}/{file_format})")
                skipped += 1
                continue

            success += 1

        except Exception as e:
            print(f"  [{idx+1}/{total}] ERROR {img_id} ({sub_label}): {e}")
            errors += 1

    # Summary
    print("\n" + "=" * 50)
    print(f"Done!  Success: {success}  |  Skipped: {skipped}  |  Errors: {errors}")
    print(f"Output directory: {os.path.abspath(OUTPUT_DIR)}")
    print("=" * 50)


if __name__ == "__main__":
    main()

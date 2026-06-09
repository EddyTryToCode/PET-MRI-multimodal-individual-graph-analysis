#!/usr/bin/env python3
"""
ADNI Data Restructuring Pipeline
================================
Reads an ADNI metadata CSV and reorganizes raw downloads into a
subject-centric directory layout with NIfTI outputs.

Input:
    CSV: ./data_balanced.csv (columns: Subject, Modality, Image Data ID, Format)
    Raw ADNI download root: ./data

Output:
    {raw_dir}/sub-*/sub-*_PET.nii.gz
    {raw_dir}/sub-*/sub-*_MRI.nii.gz
    {metadata} (generated from data_balanced.csv)

Dependencies:
  pandas
  dicom2nifti
  pydicom
  pyyaml
"""

import os
import glob
import shutil
import gzip
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import dicom2nifti
import yaml

CONFIG_PATH = "configs/default.yaml"
CSV_PATH = "./data_balanced.csv"
CSV_PATH_ALT = "./data/data_balanced.csv"
RAW_DATA_DIR = "./data"
RAW_DATA_DIR_ALT = "./data/ADNI"


def load_config(path: str = CONFIG_PATH) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def build_image_id_index(raw_dir: str) -> dict:
    index = {}
    for dirpath, dirnames, _ in os.walk(raw_dir):
        for d in dirnames:
            if d.startswith("I"):
                index[d] = os.path.join(dirpath, d)
    return index


def normalize_modality(value: str) -> str:
    return str(value).strip().upper()


def normalize_format(value: str) -> str:
    return str(value).strip().lower()


def convert_pet_dicom(src_folder: str, dest_path: str) -> None:
    tmp_dir = dest_path + "_tmp_dcm2nii"
    os.makedirs(tmp_dir, exist_ok=True)

    dicom2nifti.convert_directory(src_folder, tmp_dir)

    nii_files = glob.glob(os.path.join(tmp_dir, "*.nii.gz")) + glob.glob(
        os.path.join(tmp_dir, "*.nii")
    )
    if not nii_files:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise FileNotFoundError("dicom2nifti produced no NIfTI output")

    src_nii = nii_files[0]
    if src_nii.endswith(".nii.gz"):
        shutil.move(src_nii, dest_path)
    else:
        with open(src_nii, "rb") as f_in, gzip.open(dest_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    shutil.rmtree(tmp_dir, ignore_errors=True)


def copy_mri_nifti(src_folder: str, dest_path: str) -> None:
    nii_files = glob.glob(os.path.join(src_folder, "*.nii.gz")) + glob.glob(
        os.path.join(src_folder, "*.nii")
    )
    if not nii_files:
        raise FileNotFoundError(f"No NIfTI file found in {src_folder}")

    src_nii = nii_files[0]
    if src_nii.endswith(".nii.gz"):
        shutil.copy(src_nii, dest_path)
    else:
        with open(src_nii, "rb") as f_in, gzip.open(dest_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)


def build_metadata_from_balanced(df: pd.DataFrame, out_path: str) -> None:
    required = {"Subject", "Group", "Sex", "Age"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"data_balanced.csv missing columns: {sorted(missing)}")

    work = df[df["Group"].isin(["AD", "CN"])].copy()
    if work.empty:
        print("No AD/CN rows found for metadata.csv")
        return

    work = work.drop_duplicates(subset=["Subject"], keep="first")

    site_value = "ADNI"
    if "Site" in work.columns:
        site_value = work["Site"].fillna("ADNI")

    meta_df = pd.DataFrame(
        {
            "subject_id": "sub-" + work["Subject"].astype(str),
            "label": work["Group"].astype(str),
            "age": work["Age"],
            "sex": work["Sex"].astype(str),
            "site": site_value,
        }
    )

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    meta_df.to_csv(out_path, index=False)
    print(f"Saved metadata: {out_path} ({len(meta_df)} subjects)")


def process_task(task: dict) -> tuple:
    try:
        if task["kind"] == "PET":
            convert_pet_dicom(task["src"], task["dest"])
        else:
            copy_mri_nifti(task["src"], task["dest"])
        return ("ok", task, None)
    except Exception as e:
        return ("error", task, str(e))


def main() -> None:
    cfg = load_config()
    output_dir = Path(cfg["data"]["raw_dir"])

    csv_path = CSV_PATH_ALT if os.path.isfile(CSV_PATH_ALT) else CSV_PATH
    raw_dir = RAW_DATA_DIR_ALT if os.path.isdir(RAW_DATA_DIR_ALT) else RAW_DATA_DIR

    df = pd.read_csv(csv_path)
    total = len(df)
    print(f"Loaded {total} rows from {csv_path}")

    metadata_path = cfg["data"]["metadata"]
    build_metadata_from_balanced(df, metadata_path)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Indexing raw ADNI folders under {raw_dir}")
    img_index = build_image_id_index(raw_dir)
    print(f"Found {len(img_index)} image-ID folders")

    num_workers = cfg.get("restructure", {}).get("num_workers", 1)
    if isinstance(num_workers, str) and num_workers.lower() == "auto":
        num_workers = os.cpu_count() or 1
    num_workers = int(num_workers) if int(num_workers) > 0 else 1

    tasks = []
    seen = set()
    skipped = 0

    for idx, row in df.iterrows():
        subject = row["Subject"]
        modality = normalize_modality(row["Modality"])
        file_format = normalize_format(row["Format"])
        img_id = row["Image Data ID"]

        if modality not in {"PET", "MRI"}:
            skipped += 1
            continue

        if modality == "PET" and file_format != "dcm":
            skipped += 1
            continue
        if modality == "MRI" and file_format not in {"nifti", "nii"}:
            skipped += 1
            continue

        key = (subject, modality)
        if key in seen:
            continue

        src_folder = img_index.get(img_id)
        if src_folder is None:
            print(f"[{idx+1}/{total}] SKIP {img_id} folder not found")
            skipped += 1
            continue

        sub_label = f"sub-{subject}"
        sub_dir = output_dir / sub_label
        sub_dir.mkdir(parents=True, exist_ok=True)

        dest = sub_dir / f"{sub_label}_{modality}.nii.gz"
        if dest.exists():
            skipped += 1
            continue

        tasks.append(
            {
                "idx": idx + 1,
                "subject": subject,
                "modality": modality,
                "img_id": img_id,
                "src": src_folder,
                "dest": str(dest),
                "kind": modality,
            }
        )
        seen.add(key)

    success = 0
    errors = 0

    if num_workers == 1:
        for task in tasks:
            status, info, err = process_task(task)
            if status == "ok":
                success += 1
                print(
                    f"[{info['idx']}/{total}] OK {info['kind']} sub-{info['subject']} ({info['img_id']})"
                )
            else:
                errors += 1
                print(
                    f"[{info['idx']}/{total}] ERROR {info['img_id']} (sub-{info['subject']}): {err}"
                )
    else:
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {executor.submit(process_task, task): task for task in tasks}
            for future in as_completed(futures):
                task = futures[future]
                status, info, err = future.result()
                if status == "ok":
                    success += 1
                    print(
                        f"[{info['idx']}/{total}] OK {info['kind']} sub-{info['subject']} ({info['img_id']})"
                    )
                else:
                    errors += 1
                    print(
                        f"[{info['idx']}/{total}] ERROR {info['img_id']} (sub-{info['subject']}): {err}"
                    )

    print("=" * 50)
    print(f"Done. Success: {success} Skipped: {skipped} Errors: {errors}")
    print(f"Output directory: {output_dir.resolve()}")
    print("=" * 50)


if __name__ == "__main__":
    main()
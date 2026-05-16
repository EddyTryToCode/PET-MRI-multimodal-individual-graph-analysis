#!/usr/bin/env python3
"""Extract MRI voxel values per ROI using the AAL atlas."""

import os
import pickle

import numpy as np
import nibabel as nib
import pandas as pd
import yaml
from nilearn.image import resample_to_img

CONFIG_PATH = "configs/default.yaml"


def load_config(path: str = CONFIG_PATH) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def extract_roi_voxels(
    img_data: np.ndarray,
    atlas_data: np.ndarray,
    roi_ids: list,
    min_voxels: int,
) -> dict:
    """
    Extract voxel values per ROI for MRI T1 images.
    NOTE: Unlike PET, MRI intensity is NOT filtered to > 0 because T1 signal
    can legitimately be near zero (dark GM/WM regions) after bias correction.
    We only discard non-finite values (NaN/Inf).
    """
    roi_voxels = {}
    for rid in roi_ids:
        vals = img_data[atlas_data == rid].astype(np.float32)
        vals = vals[np.isfinite(vals)]
        # Keep all finite values — do NOT filter by > 0 for MRI
        if len(vals) < min_voxels:
            vals = np.zeros(min_voxels, dtype=np.float32)
        roi_voxels[rid] = vals
    return roi_voxels


def main() -> None:
    cfg = load_config()
    atlas_img = nib.load(cfg["data"]["atlas_nii"])
    labels_df = pd.read_csv(cfg["data"]["atlas_labels"])
    roi_ids = labels_df["roi_id"].tolist()
    meta = pd.read_csv(cfg["data"]["metadata"])

    processed_dir = cfg["data"]["processed_dir"]
    min_voxels = int(cfg["roi_extraction"]["min_voxels"])
    # NOTE: filter_positive intentionally NOT used for MRI (it is only for PET)

    for _, row in meta.iterrows():
        sid = row["subject_id"]
        mri_path = os.path.join(
            processed_dir, sid, f"{sid}_MRI_preprocessed.nii.gz"
        )
        out_path = os.path.join(
            processed_dir, sid, f"{sid}_MRI_roi_voxels.pkl"
        )

        if os.path.exists(out_path):
            print(f"[SKIP] {sid} already exists")
            continue
        if not os.path.isfile(mri_path):
            print(f"[SKIP] {sid} MRI not found")
            continue

        mri_img = nib.load(mri_path)
        atlas_mri = resample_to_img(
            atlas_img, mri_img, interpolation="nearest", copy=True
        )

        mri_data = mri_img.get_fdata().astype(np.float32)
        atlas_data = atlas_mri.get_fdata().astype(np.int32)

        roi_voxels = extract_roi_voxels(
            mri_data, atlas_data, roi_ids, min_voxels
        )

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as f:
            pickle.dump(roi_voxels, f, protocol=pickle.HIGHEST_PROTOCOL)

        n_valid = sum(1 for v in roi_voxels.values() if np.any(v))
        print(f"[OK] {sid} valid_rois={n_valid}/{len(roi_ids)}")


if __name__ == "__main__":
    main()

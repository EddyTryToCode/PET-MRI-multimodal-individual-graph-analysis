#!/usr/bin/env python3
"""Extract PET voxel values per ROI using the AAL atlas.

The atlas lives in MNI standard space whereas the preprocessed PET images
are in subject-native space (coregistered to MRI in step 2).  We therefore
use ANTs SyN registration to warp the atlas into each subject's native
space before extracting per-ROI voxel distributions.
"""

import os
import pickle

import numpy as np
import nibabel as nib
import pandas as pd
import yaml

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from nilearn.image import resample_to_img
from nilearn import plotting

from atlas_registration import warp_atlas_to_native

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
    filter_positive: bool,
) -> dict:
    roi_voxels = {}
    for rid in roi_ids:
        vals = img_data[atlas_data == rid].astype(np.float32)
        vals = vals[np.isfinite(vals)]
        if filter_positive:
            vals = vals[vals > 0]
        if len(vals) < min_voxels:
            vals = np.zeros(min_voxels, dtype=np.float32)
        roi_voxels[rid] = vals
    return roi_voxels


def generate_parcellation_qc(
    resampled_atlas: nib.Nifti1Image,
    mri_path: str,
    output_path: str,
    title: str,
) -> None:
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


def main() -> None:
    cfg = load_config()
    atlas_path = cfg["data"]["atlas_nii"]
    labels_df = pd.read_csv(cfg["data"]["atlas_labels"])
    roi_ids = labels_df["roi_id"].tolist()
    meta = pd.read_csv(cfg["data"]["metadata"])

    processed_dir = cfg["data"]["processed_dir"]
    min_voxels = int(cfg["roi_extraction"]["min_voxels"])
    filter_positive = bool(cfg["roi_extraction"]["filter_positive"])

    # Registration config (defaults to SyN if section absent)
    reg_cfg = cfg.get("registration", {})
    reg_type = reg_cfg.get("type", "SyN")

    qc_dir = os.path.join("qc", "parcellation_overlay")
    os.makedirs(qc_dir, exist_ok=True)

    if not os.path.isfile(atlas_path):
        raise FileNotFoundError(f"Atlas not found: {atlas_path}")

    for _, row in meta.iterrows():
        sid = row["subject_id"]
        pet_path = os.path.join(
            processed_dir, sid, f"{sid}_PET_preprocessed.nii.gz"
        )
        mri_path = os.path.join(
            processed_dir, sid, f"{sid}_MRI_preprocessed.nii.gz"
        )
        out_path = os.path.join(
            processed_dir, sid, f"{sid}_PET_roi_voxels.pkl"
        )
        qc_path = os.path.join(qc_dir, f"{sid}_atlas_qc.png")

        if os.path.exists(out_path):
            print(f"[SKIP] {sid} already exists")
            continue
        if not os.path.isfile(pet_path):
            print(f"[SKIP] {sid} PET not found")
            continue
        if not os.path.isfile(mri_path):
            print(f"[SKIP] {sid} MRI not found")
            continue

        print(f"[RUN] {sid}")

        # ---------------------------------------------------------------
        # 1.  Warp atlas from MNI → subject native space (cached)
        # ---------------------------------------------------------------
        atlas_native_path = os.path.join(
            processed_dir, sid, f"{sid}_atlas_native.nii.gz"
        )
        transform_dir = os.path.join(processed_dir, sid, "transforms")

        warped_atlas_nib = warp_atlas_to_native(
            mri_path, atlas_path, atlas_native_path, transform_dir,
            reg_type=reg_type,
        )

        # ---------------------------------------------------------------
        # 2.  Resample warped atlas to PET voxel grid
        #     (atlas is now spatially correct; this only adjusts the grid)
        # ---------------------------------------------------------------
        pet_img = nib.load(pet_path)
        resampled_atlas = resample_to_img(
            warped_atlas_nib, pet_img, interpolation="nearest", copy=True
        )

        atlas_data = resampled_atlas.get_fdata().astype(np.int32)
        pet_data = pet_img.get_fdata().astype(np.float32)

        # ---------------------------------------------------------------
        # 3.  Extract ROI voxels
        # ---------------------------------------------------------------
        roi_voxels = extract_roi_voxels(
            pet_data, atlas_data, roi_ids, min_voxels, filter_positive
        )

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as f:
            pickle.dump(roi_voxels, f, protocol=pickle.HIGHEST_PROTOCOL)

        # ---------------------------------------------------------------
        # 4.  QC overlay (use MRI-resolution warped atlas for cleaner vis)
        # ---------------------------------------------------------------
        generate_parcellation_qc(warped_atlas_nib, mri_path, qc_path, title=sid)

        n_valid = sum(1 for v in roi_voxels.values() if np.any(v))
        print(f"[OK] {sid} valid_rois={n_valid}/{len(roi_ids)}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""Download AAL3 atlas via nilearn."""

import os
import shutil

import numpy as np
import nibabel as nib
import pandas as pd
import yaml
from nilearn import datasets

CONFIG_PATH = "configs/default.yaml"


def load_config(path: str = CONFIG_PATH) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def main() -> None:
    cfg = load_config()
    os.makedirs("data/atlas", exist_ok=True)

    out_nii = cfg["data"]["atlas_nii"]
    out_csv = cfg["data"]["atlas_labels"]

    if os.path.exists(out_nii) and os.path.exists(out_csv):
        print("AAL3 atlas already downloaded")
        return

    print("Downloading AAL atlas via nilearn")
    aal = datasets.fetch_atlas_aal(version="SPM12")

    shutil.copy(aal.maps, out_nii)

    labels_df = pd.DataFrame(
        {
            "roi_id": [int(i) for i in aal.indices],
            "roi_name": aal.labels,
        }
    )
    labels_df.to_csv(out_csv, index=False)

    img = nib.load(out_nii)
    unique_ids = np.unique(img.get_fdata().astype(int))
    unique_ids = unique_ids[unique_ids > 0]
    print(f"AAL3 atlas: {img.shape}, {len(unique_ids)} ROIs")
    print(f"Saved: {out_nii}")
    print(f"Labels: {out_csv}")


if __name__ == "__main__":
    main()
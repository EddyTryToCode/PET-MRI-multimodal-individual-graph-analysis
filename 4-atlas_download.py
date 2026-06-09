#!/usr/bin/env python3
"""Download AAL atlas via nilearn, with a direct-download fallback."""

import os
import tarfile
import tempfile
import xml.etree.ElementTree as ET

import numpy as np
import nibabel as nib
import pandas as pd
import requests
import urllib3
import yaml
from nilearn import datasets

CONFIG_PATH = "configs/default.yaml"
AAL_URL = "https://www.gin.cnrs.fr/AAL_files/aal_for_SPM12.tar.gz"


def _parse_aal_labels(xml_text: str) -> pd.DataFrame:
    root = ET.fromstring(xml_text)
    labels = []

    for label in root.findall(".//label"):
        index_text = label.findtext("index")
        name_text = label.findtext("name")
        if not index_text or not name_text:
            continue
        labels.append({"roi_id": int(index_text), "roi_name": name_text})

    return pd.DataFrame(labels)


def _download_aal_fallback(out_nii: str, out_csv: str) -> None:
    print("Nilearn download failed; retrying with a direct download fallback")
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    with requests.get(AAL_URL, stream=True, timeout=120, verify=False) as response:
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp_file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    tmp_file.write(chunk)
            tar_path = tmp_file.name

    try:
        with tarfile.open(tar_path, mode="r:gz") as tar_file:
            nii_member = tar_file.getmember("aal/ROI_MNI_V4.nii")
            xml_member = tar_file.getmember("aal/ROI_MNI_V4.xml")

            nii_bytes = tar_file.extractfile(nii_member).read()
            xml_text = tar_file.extractfile(xml_member).read().decode("utf-8")

        with tempfile.NamedTemporaryFile(suffix=".nii", delete=False) as nii_file:
            nii_file.write(nii_bytes)
            nii_path = nii_file.name

        try:
            img = nib.load(nii_path)
            nib.save(img, out_nii)
        finally:
            if os.path.exists(nii_path):
                os.remove(nii_path)

        labels_df = _parse_aal_labels(xml_text)
        labels_df.to_csv(out_csv, index=False)
    finally:
        if os.path.exists(tar_path):
            os.remove(tar_path)


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
    try:
        aal = datasets.fetch_atlas_aal(version="SPM12")

        img = nib.load(aal.maps)
        nib.save(img, out_nii)

        labels_df = pd.DataFrame(
            {
                "roi_id": [int(i) for i in aal.indices],
                "roi_name": aal.labels,
            }
        )
        labels_df.to_csv(out_csv, index=False)
    except Exception:
        _download_aal_fallback(out_nii, out_csv)

    img = nib.load(out_nii)
    unique_ids = np.unique(img.get_fdata().astype(int))
    unique_ids = unique_ids[unique_ids > 0]
    print(f"AAL3 atlas: {img.shape}, {len(unique_ids)} ROIs")
    print(f"Saved: {out_nii}")
    print(f"Labels: {out_csv}")


if __name__ == "__main__":
    main()
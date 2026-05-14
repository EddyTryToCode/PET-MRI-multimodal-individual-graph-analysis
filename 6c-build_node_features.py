#!/usr/bin/env python3
"""Build node feature matrices per subject."""

import os
import pickle

import numpy as np
import pandas as pd
import yaml

CONFIG_PATH = "configs/default.yaml"


def load_config(path: str = CONFIG_PATH) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def roi_stats(vals: np.ndarray) -> np.ndarray:
    if len(vals) == 0 or np.sum(vals) == 0:
        return np.zeros(6, dtype=np.float32)
    return np.array(
        [
            np.mean(vals),
            np.std(vals),
            np.percentile(vals, 10),
            np.percentile(vals, 50),
            np.percentile(vals, 90),
            float(len(vals)),
        ],
        dtype=np.float32,
    )


def build_node_features(roi_mri: dict, roi_pet: dict, roi_ids: list) -> np.ndarray:
    rows = []
    for rid in roi_ids:
        fm = roi_stats(roi_mri.get(rid, np.array([])))
        fp = roi_stats(roi_pet.get(rid, np.array([])))
        rows.append(np.concatenate([fm, fp]))
    return np.stack(rows, axis=0)


def main() -> None:
    cfg = load_config()
    labels_df = pd.read_csv(cfg["data"]["atlas_labels"])
    roi_ids = labels_df["roi_id"].tolist()
    meta = pd.read_csv(cfg["data"]["metadata"])

    processed_dir = cfg["data"]["processed_dir"]

    for _, row in meta.iterrows():
        sid = row["subject_id"]
        proc_dir = os.path.join(processed_dir, sid)
        mri_pkl = os.path.join(proc_dir, f"{sid}_MRI_roi_voxels.pkl")
        pet_pkl = os.path.join(proc_dir, f"{sid}_PET_roi_voxels.pkl")
        out_npy = os.path.join(proc_dir, f"{sid}_node_features.npy")

        if os.path.exists(out_npy):
            print(f"[SKIP] {sid} already exists")
            continue
        if not os.path.isfile(mri_pkl) or not os.path.isfile(pet_pkl):
            print(f"[SKIP] {sid} ROI voxels not found")
            continue

        with open(mri_pkl, "rb") as f:
            roi_mri = pickle.load(f)
        with open(pet_pkl, "rb") as f:
            roi_pet = pickle.load(f)

        X = build_node_features(roi_mri, roi_pet, roi_ids)
        np.save(out_npy, X)
        print(f"[OK] {sid} X shape={X.shape}")


if __name__ == "__main__":
    main()

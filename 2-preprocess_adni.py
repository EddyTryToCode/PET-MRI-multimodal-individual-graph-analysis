#!/usr/bin/env python3
"""
ADNI Neuroimaging Preprocessing Pipeline
========================================
Preprocesses paired MRI (T1) and PET (FDG) NIfTI files using ANTsPy and HD-BET.

Pipeline per subject:
  1. MRI N4 bias field correction
  2. Skull stripping (HD-BET)
  3. PET to MRI coregistration (affine)
  4. PET brain masking
  5. PET normalization and clipping
  6. Save outputs

Input:
  {raw_dir}/sub-*/sub-*_MRI.nii.gz
  {raw_dir}/sub-*/sub-*_PET.nii.gz

Output:
  {processed_dir}/sub-*/sub-*_MRI_preprocessed.nii.gz
  {processed_dir}/sub-*/sub-*_PET_preprocessed.nii.gz

Dependencies:
  antspyx
  hd-bet
  pyyaml
"""

import os
import sys
import glob
import time
import shutil
import tempfile
import subprocess
from pathlib import Path

import numpy as np
import ants
import yaml

CONFIG_PATH = "configs/default.yaml"


def load_config(path: str = CONFIG_PATH) -> dict:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r") as f:
        return yaml.safe_load(f)


def elapsed(start: float) -> str:
    secs = time.time() - start
    if secs < 60:
        return f"{secs:.1f}s"
    return f"{secs / 60:.1f}min"


def detect_hdbet_device() -> str:
    try:
        import torch

        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            print(f"GPU detected: {name}")
            return "cuda"
    except ImportError:
        pass
    print("GPU not available. HD-BET will run on CPU")
    return "cpu"


def step1_n4_correction(mri_path: str) -> "ants.ANTsImage":
    print("Step 1: N4 bias field correction")
    t0 = time.time()
    mri = ants.image_read(mri_path)
    mri_n4 = ants.n4_bias_field_correction(mri)
    print(f"Step 1 done ({elapsed(t0)})")
    return mri_n4


def step2_skull_strip(
    mri_n4: "ants.ANTsImage", tmp_dir: str, device: str
) -> tuple:
    print("Step 2: Skull stripping (HD-BET)")
    t0 = time.time()

    tmp_input = os.path.join(tmp_dir, "mri_n4.nii.gz")
    tmp_output = os.path.join(tmp_dir, "mri_brain.nii.gz")
    ants.image_write(mri_n4, tmp_input)

    cmd = [
        "hd-bet",
        "-i",
        tmp_input,
        "-o",
        tmp_output,
        "-device",
        device,
        "--disable_tta",
        "--save_bet_mask",
    ]

    env = os.environ.copy()
    env["MKL_THREADING_LAYER"] = "GNU"
    env["MKL_SERVICE_FORCE_INTEL"] = "1"

    result = subprocess.run(cmd, env=env)
    if result.returncode != 0 and device != "cpu":
        print("HD-BET GPU failed, retrying on CPU")
        cmd[cmd.index(device)] = "cpu"
        result = subprocess.run(cmd, env=env)

    if result.returncode != 0:
        raise RuntimeError(f"HD-BET failed with exit code {result.returncode}")

    # Locate HD-BET outputs: expected names are mri_brain.nii.gz + mri_brain_mask.nii.gz
    # We explicitly look for each to avoid any ambiguity.
    all_nii = glob.glob(os.path.join(tmp_dir, "*.nii.gz"))

    # Separate mask files from brain image files
    mask_candidates = [f for f in all_nii if "mask" in os.path.basename(f).lower()]
    brain_candidates = [
        f for f in all_nii
        if "mask" not in os.path.basename(f).lower()
        and os.path.basename(f) != "mri_n4.nii.gz"
    ]

    if not brain_candidates:
        raise FileNotFoundError(
            f"HD-BET brain output not found in {tmp_dir}. Files: {os.listdir(tmp_dir)}"
        )

    # Sort by size as extra safety: brain image > binary mask in bytes
    brain_candidates.sort(key=lambda x: os.path.getsize(x), reverse=True)
    mri_brain = ants.image_read(brain_candidates[0])

    # Prefer the HD-BET neural-network mask over intensity thresholding.
    # HD-BET mask is binary {0,1} and correctly handles dark GM voxels near zero.
    if mask_candidates:
        mask_candidates.sort(key=lambda x: os.path.getsize(x))
        mask_img = ants.image_read(mask_candidates[0])
        mask_array = (mask_img.numpy() > 0).astype(np.float32)
    else:
        # Fallback: derive from brain image (less accurate, but safe)
        print("[WARN] HD-BET mask file not found, falling back to intensity threshold")
        mask_array = (mri_brain.numpy() > 0).astype(np.float32)

    mri_mask = mri_brain.new_image_like(mask_array)

    print(f"Step 2 done ({elapsed(t0)})")
    return mri_brain, mri_mask


def step3_pet_coregistration(
    pet_path: str, mri_n4: "ants.ANTsImage"
) -> "ants.ANTsImage":
    print("Step 3: PET to MRI coregistration")
    t0 = time.time()

    pet = ants.image_read(pet_path)
    reg = ants.registration(fixed=mri_n4, moving=pet, type_of_transform="AffineFast")
    pet_coreg = reg["warpedmovout"]

    print(f"Step 3 done ({elapsed(t0)})")
    return pet_coreg


def step4_pet_brain_mask(
    pet_coreg: "ants.ANTsImage", mri_mask: "ants.ANTsImage"
) -> "ants.ANTsImage":
    print("Step 4: PET brain masking")
    t0 = time.time()

    mask_array = mri_mask.numpy().astype(float)
    mask_array[mask_array > 0] = 1.0

    pet_array = pet_coreg.numpy()
    pet_masked = pet_array * mask_array
    pet_brain = pet_coreg.new_image_like(pet_masked)

    print(f"Step 4 done ({elapsed(t0)})")
    return pet_brain


def normalize_pet_mean_brain(pet_data: np.ndarray, brain_mask: np.ndarray) -> np.ndarray:
    valid = pet_data[(brain_mask > 0) & (pet_data > 0)]
    if len(valid) == 0:
        return pet_data
    return pet_data / (valid.mean() + 1e-8)


def clip_percentile(
    data: np.ndarray, mask: np.ndarray, low: float, high: float
) -> np.ndarray:
    valid = data[mask > 0]
    if len(valid) == 0:
        return data
    lo, hi = np.percentile(valid, [low, high])
    out = data.copy()
    out[mask > 0] = np.clip(out[mask > 0], lo, hi)
    return out


def step5_save(
    out_dir: str,
    sub_label: str,
    mri_brain: "ants.ANTsImage",
    pet_brain: "ants.ANTsImage",
) -> None:
    print("Step 5: Saving outputs")

    mri_out = os.path.join(out_dir, f"{sub_label}_MRI_preprocessed.nii.gz")
    pet_out = os.path.join(out_dir, f"{sub_label}_PET_preprocessed.nii.gz")

    ants.image_write(mri_brain, mri_out)
    ants.image_write(pet_brain, pet_out)

    print(f"Saved: {os.path.basename(mri_out)}")
    print(f"Saved: {os.path.basename(pet_out)}")


def main() -> None:
    cfg = load_config()
    raw_dir = Path(cfg["data"]["raw_dir"])
    processed_dir = Path(cfg["data"]["processed_dir"])

    normalize_mode = cfg["preprocessing"]["pet_normalize"]
    clip_low, clip_high = cfg["preprocessing"]["clip_percentile"]

    sub_dirs = sorted(glob.glob(str(raw_dir / "sub-*")))
    total = len(sub_dirs)
    if total == 0:
        print(f"No sub-* folders found in {raw_dir.resolve()}")
        sys.exit(1)

    processed_dir.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print("ADNI preprocessing pipeline")
    print(f"Subjects found: {total}")
    print("=" * 60)

    device = detect_hdbet_device()
    success = 0
    errors = 0

    for idx, sub_dir in enumerate(sub_dirs, start=1):
        sub_label = os.path.basename(sub_dir)
        mri_path = os.path.join(sub_dir, f"{sub_label}_MRI.nii.gz")
        pet_path = os.path.join(sub_dir, f"{sub_label}_PET.nii.gz")

        print(f"[{idx}/{total}] Processing {sub_label}")

        out_dir = processed_dir / sub_label
        mri_out = out_dir / f"{sub_label}_MRI_preprocessed.nii.gz"
        pet_out = out_dir / f"{sub_label}_PET_preprocessed.nii.gz"

        if mri_out.exists() and pet_out.exists():
            print(f"SKIP {sub_label} (already processed)")
            success += 1
            continue

        if not os.path.isfile(mri_path):
            print(f"SKIP MRI not found: {mri_path}")
            errors += 1
            continue
        if not os.path.isfile(pet_path):
            print(f"SKIP PET not found: {pet_path}")
            errors += 1
            continue

        t_subject = time.time()
        tmp_dir = tempfile.mkdtemp(prefix=f"hdbet_{sub_label}_")

        try:
            mri_n4 = step1_n4_correction(mri_path)
            mri_brain, mri_mask = step2_skull_strip(mri_n4, tmp_dir, device)
            pet_coreg = step3_pet_coregistration(pet_path, mri_n4)
            pet_brain = step4_pet_brain_mask(pet_coreg, mri_mask)

            mask_array = (mri_mask.numpy() > 0).astype(np.float32)
            pet_array = pet_brain.numpy()

            if normalize_mode == "mean_brain":
                pet_array = normalize_pet_mean_brain(pet_array, mask_array)
            pet_array = clip_percentile(pet_array, mask_array, clip_low, clip_high)
            pet_brain = pet_brain.new_image_like(pet_array)

            out_dir = processed_dir / sub_label
            out_dir.mkdir(parents=True, exist_ok=True)
            step5_save(str(out_dir), sub_label, mri_brain, pet_brain)

            print(f"OK {sub_label} completed in {elapsed(t_subject)}")
            success += 1

        except Exception as e:
            print(f"ERROR {sub_label}: {e}")
            errors += 1

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    print("=" * 60)
    print("Pipeline finished")
    print(f"Success: {success}/{total}")
    print(f"Errors: {errors}/{total}")
    print("=" * 60)


if __name__ == "__main__":
    main()
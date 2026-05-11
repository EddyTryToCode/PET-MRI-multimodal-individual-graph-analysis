#!/usr/bin/env python3
"""
ADNI Neuroimaging Preprocessing Pipeline
==========================================
Preprocesses paired MRI (T1) and PET (FDG) NIfTI files using ANTsPy and HD-BET.

Pipeline per subject:
    1. MRI N4 Bias Field Correction  (ANTsPy)
    2. Skull Stripping               (HD-BET, GPU → CPU fallback)
    3. PET → MRI Coregistration      (ANTsPy, Affine)
    4. PET Brain Masking             (apply MRI brain mask to PET)
    5. Save outputs

Input structure:
    ./Project_Data/sub-{id}/sub-{id}_MRI.nii.gz
    ./Project_Data/sub-{id}/sub-{id}_PET.nii.gz

Output (saved in the same subject folder):
    sub-{id}_MRI_preprocessed.nii.gz   (N4-corrected, skull-stripped MRI)
    sub-{id}_PET_preprocessed.nii.gz   (coregistered, skull-stripped PET)

Dependencies:
    pip install antspyx hd-bet

Usage:
    python preprocess_adni.py
"""

import os
import sys
import glob
import time
import shutil
import tempfile
import subprocess
from pathlib import Path

import ants


# ══════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════
PROJECT_DIR = Path("./Project_Data")


# ══════════════════════════════════════════════════════════════
# Utility helpers
# ══════════════════════════════════════════════════════════════
def _elapsed(start: float) -> str:
    """Return a human-readable elapsed time string."""
    secs = time.time() - start
    if secs < 60:
        return f"{secs:.1f}s"
    return f"{secs / 60:.1f}min"


def _detect_hdbet_device() -> str:
    """
    Probe for a CUDA-capable GPU.  Returns 'cuda' if available,
    otherwise 'cpu'.  (HD-BET v2 uses 'cuda'/'cpu', not '0'/'cpu'.)
    """
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            print(f"  [GPU] Detected: {name}")
            return "cuda"
    except ImportError:
        pass
    print("  [GPU] Not available — HD-BET will run on CPU")
    return "cpu"


# ══════════════════════════════════════════════════════════════
# Pipeline steps
# ══════════════════════════════════════════════════════════════

def step1_n4_correction(mri_path: str) -> "ants.ANTsImage":
    """
    Step 1 — N4 Bias Field Correction.
    Reads the raw MRI and returns the corrected image.
    """
    print("  [Step 1] N4 Bias Field Correction ...")
    t0 = time.time()

    mri = ants.image_read(mri_path)
    mri_n4 = ants.n4_bias_field_correction(mri)

    print(f"  [Step 1] Done ({_elapsed(t0)})")
    return mri_n4


def step2_skull_strip(mri_n4: "ants.ANTsImage",
                      tmp_dir: str,
                      device: str) -> tuple:
    """
    Step 2 — Skull Stripping via HD-BET.
    Saves mri_n4 to a temp file, runs HD-BET, reads back the brain
    image and the binary mask.

    Returns:
        (mri_brain, mri_mask)  — both as ants.ANTsImage
    """
    print("  [Step 2] Skull Stripping (HD-BET) ...")
    t0 = time.time()

    # Write the N4-corrected MRI to a temp NIfTI
    tmp_input = os.path.join(tmp_dir, "mri_n4.nii.gz")
    tmp_output = os.path.join(tmp_dir, "mri_brain.nii.gz")
    ants.image_write(mri_n4, tmp_input)

    # Build HD-BET v2 command
    # --save_bet_mask  →  also save the binary brain mask
    # --disable_tta   →  faster inference (slight quality trade-off)
    cmd = [
        "hd-bet",
        "-i", tmp_input,
        "-o", tmp_output,
        "-device", device,
        "--disable_tta",
        "--save_bet_mask",
    ]

    # Fix MKL threading conflict (conda MKL vs PyTorch's libgomp)
    env = os.environ.copy()
    env["MKL_THREADING_LAYER"] = "GNU"
    env["MKL_SERVICE_FORCE_INTEL"] = "1"

    # Stream output in real-time (HD-BET downloads models on first run)
    result = subprocess.run(cmd, env=env)

    if result.returncode != 0:
        # If GPU failed, retry on CPU
        if device != "cpu":
            print("  [Step 2] GPU run failed — retrying on CPU ...")
            cmd[cmd.index(device)] = "cpu"
            result = subprocess.run(cmd, env=env)

        if result.returncode != 0:
            raise RuntimeError(f"HD-BET failed with exit code {result.returncode}")

    # HD-BET v2 appends '_bet' to output names:
    #   mri_brain_bet.nii.gz  — skull-stripped brain
    brain_candidates = glob.glob(os.path.join(tmp_dir, "*_bet.nii.gz"))

    if not brain_candidates:
        raise FileNotFoundError(
            f"HD-BET brain output not found in {tmp_dir}. "
            f"Files present: {os.listdir(tmp_dir)}"
        )

    mri_brain = ants.image_read(brain_candidates[0])

    # Derive binary brain mask from the skull-stripped output
    # (more robust than relying on HD-BET's mask file naming)
    import numpy as np
    mask_array = (mri_brain.numpy() > 0).astype(np.float32)
    mri_mask = mri_brain.new_image_like(mask_array)

    print(f"  [Step 2] Done ({_elapsed(t0)})")
    return mri_brain, mri_mask


def step3_pet_coregistration(pet_path: str,
                             mri_n4: "ants.ANTsImage") -> "ants.ANTsImage":
    """
    Step 3 — Register PET → MRI (intra-subject, affine).
    Returns the warped (coregistered) PET image.
    """
    print("  [Step 3] PET → MRI Coregistration ...")
    t0 = time.time()

    pet = ants.image_read(pet_path)

    reg = ants.registration(
        fixed=mri_n4,
        moving=pet,
        type_of_transform="AffineFast",
    )

    pet_coreg = reg["warpedmovout"]

    print(f"  [Step 3] Done ({_elapsed(t0)})")
    return pet_coreg


def step4_pet_brain_mask(pet_coreg: "ants.ANTsImage",
                         mri_mask: "ants.ANTsImage") -> "ants.ANTsImage":
    """
    Step 4 — Apply the binary brain mask to the coregistered PET.
    Removes extra-cranial signal (skull, eyes, etc.).
    """
    print("  [Step 4] PET Brain Masking ...")
    t0 = time.time()

    # Ensure mask is binary (0/1) and in the same space
    mask_array = mri_mask.numpy().astype(float)
    mask_array[mask_array > 0] = 1.0

    pet_array = pet_coreg.numpy()
    pet_masked = pet_array * mask_array

    pet_brain = pet_coreg.new_image_like(pet_masked)

    print(f"  [Step 4] Done ({_elapsed(t0)})")
    return pet_brain


def step5_save(sub_dir: str,
               sub_label: str,
               mri_brain: "ants.ANTsImage",
               pet_brain: "ants.ANTsImage") -> None:
    """
    Step 5 — Write final preprocessed files to the subject directory.
    """
    print("  [Step 5] Saving outputs ...")

    mri_out = os.path.join(sub_dir, f"{sub_label}_MRI_preprocessed.nii.gz")
    pet_out = os.path.join(sub_dir, f"{sub_label}_PET_preprocessed.nii.gz")

    ants.image_write(mri_brain, mri_out)
    ants.image_write(pet_brain, pet_out)

    print(f"           → {os.path.basename(mri_out)}")
    print(f"           → {os.path.basename(pet_out)}")


# ══════════════════════════════════════════════════════════════
# Main orchestrator
# ══════════════════════════════════════════════════════════════

def main():
    # Discover subject folders
    sub_dirs = sorted(glob.glob(str(PROJECT_DIR / "sub-*")))
    total = len(sub_dirs)

    if total == 0:
        print(f"[ERROR] No sub-* folders found in {PROJECT_DIR.resolve()}")
        sys.exit(1)

    print("=" * 60)
    print(f"  ADNI Preprocessing Pipeline")
    print(f"  Subjects found: {total}")
    print("=" * 60)

    # Detect GPU once for all subjects
    device = _detect_hdbet_device()

    success = 0
    errors = 0

    for idx, sub_dir in enumerate(sub_dirs, start=1):
        sub_label = os.path.basename(sub_dir)   # e.g. sub-941_S_1195
        mri_path = os.path.join(sub_dir, f"{sub_label}_MRI.nii.gz")
        pet_path = os.path.join(sub_dir, f"{sub_label}_PET.nii.gz")

        print(f"\n[{idx}/{total}] Processing {sub_label}")
        print("-" * 50)

        # Validate inputs
        if not os.path.isfile(mri_path):
            print(f"  [SKIP] MRI not found: {mri_path}")
            errors += 1
            continue
        if not os.path.isfile(pet_path):
            print(f"  [SKIP] PET not found: {pet_path}")
            errors += 1
            continue

        t_subject = time.time()

        # Use a temporary directory for HD-BET intermediates
        tmp_dir = tempfile.mkdtemp(prefix=f"hdbet_{sub_label}_")

        try:
            # Step 1 — N4 Bias Field Correction
            mri_n4 = step1_n4_correction(mri_path)

            # Step 2 — Skull Stripping
            mri_brain, mri_mask = step2_skull_strip(mri_n4, tmp_dir, device)

            # Step 3 — PET Coregistration
            pet_coreg = step3_pet_coregistration(pet_path, mri_n4)

            # Step 4 — PET Brain Masking
            pet_brain = step4_pet_brain_mask(pet_coreg, mri_mask)

            # Step 5 — Save
            step5_save(sub_dir, sub_label, mri_brain, pet_brain)

            print(f"  [✓] {sub_label} completed in {_elapsed(t_subject)}")
            success += 1

        except Exception as e:
            print(f"  [✗] {sub_label} FAILED: {e}")
            errors += 1

        finally:
            # Clean up temporary files
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # Final summary
    print("\n" + "=" * 60)
    print(f"  Pipeline finished!")
    print(f"  Success : {success}/{total}")
    print(f"  Errors  : {errors}/{total}")
    print("=" * 60)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Warp an MNI-space atlas to subject native space using ANTs registration.

This module is shared by step 5 (PET ROI extraction) and step 5b (MRI ROI
extraction).  It registers the MNI152 template to each subject's MRI and
applies the resulting transforms to the atlas with nearest-neighbour
interpolation so that integer ROI labels are preserved.

The warped atlas and transform files are cached on disk so that the
(expensive) registration only runs once per subject.
"""

import os
import shutil
import glob

import ants
import nibabel as nib
import numpy as np


# ---------------------------------------------------------------------------
# MNI template helpers
# ---------------------------------------------------------------------------

def _get_mni_template() -> "ants.ANTsImage":
    """Return the MNI152 T1 1 mm template shipped with ANTsPy."""
    mni_path = ants.get_ants_data("mni")
    return ants.image_read(mni_path)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def warp_atlas_to_native(
    mri_path: str,
    atlas_path: str,
    output_atlas_path: str,
    transform_dir: str,
    reg_type: str = "SyN",
) -> nib.Nifti1Image:
    """Warp *atlas_path* (MNI space) into the native space of *mri_path*.

    Parameters
    ----------
    mri_path : str
        Path to the subject's preprocessed MRI NIfTI (native space).
    atlas_path : str
        Path to the AAL atlas NIfTI in MNI space.
    output_atlas_path : str
        Where to save the warped atlas NIfTI.  If this file already exists
        the function loads it from disk (cache hit) and returns immediately.
    transform_dir : str
        Directory for caching ANTs transform files.
    reg_type : str
        ANTs transform type – ``"SyN"`` (default, accurate, ~5-10 min) or
        ``"Affine"`` (fast, ~1 min).

    Returns
    -------
    nibabel.Nifti1Image
        The atlas resampled in the subject's native MRI space.
    """

    # ------------------------------------------------------------------
    # Cache hit – warped atlas already exists
    # ------------------------------------------------------------------
    if os.path.isfile(output_atlas_path):
        return nib.load(output_atlas_path)

    os.makedirs(os.path.dirname(output_atlas_path), exist_ok=True)
    os.makedirs(transform_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Load images
    # ------------------------------------------------------------------
    mri_ants = ants.image_read(mri_path)
    mni_template = _get_mni_template()
    atlas_ants = ants.image_read(atlas_path)

    # ------------------------------------------------------------------
    # Register MNI template → subject native MRI
    #   fixed  = subject MRI  (native space)
    #   moving = MNI template
    #   fwdtransforms map MNI → native  (what we need for the atlas)
    # ------------------------------------------------------------------
    print(f"  [REG] Registering MNI → native ({reg_type}) ...")
    reg = ants.registration(
        fixed=mri_ants,
        moving=mni_template,
        type_of_transform=reg_type,
    )

    # Cache transforms for potential reuse
    for i, tf in enumerate(reg["fwdtransforms"]):
        ext = os.path.splitext(tf)[1]
        dst = os.path.join(transform_dir, f"mni_to_native_{i}{ext}")
        shutil.copy2(tf, dst)

    # ------------------------------------------------------------------
    # Apply transforms to atlas (nearest-neighbour keeps integer labels)
    # ------------------------------------------------------------------
    atlas_native = ants.apply_transforms(
        fixed=mri_ants,
        moving=atlas_ants,
        transformlist=reg["fwdtransforms"],
        interpolator="nearestNeighbor",
    )

    # ------------------------------------------------------------------
    # Convert ANTs image to nibabel and save
    # ------------------------------------------------------------------
    # ANTs/ITK uses LPS coordinates; NIfTI uses RAS.
    # We must negate the first two axes (L→R, P→A) during conversion.
    direction = np.array(atlas_native.direction)
    spacing = np.array(atlas_native.spacing)
    origin = np.array(atlas_native.origin)

    # LPS → RAS: flip L and P axes
    lps_to_ras = np.diag([-1.0, -1.0, 1.0])

    affine = np.eye(4)
    affine[:3, :3] = lps_to_ras @ direction @ np.diag(spacing)
    affine[:3, 3] = lps_to_ras @ origin

    atlas_nib = nib.Nifti1Image(
        atlas_native.numpy().astype(np.int32), affine=affine
    )
    nib.save(atlas_nib, output_atlas_path)
    print(f"  [REG] Saved warped atlas → {output_atlas_path}")

    return atlas_nib

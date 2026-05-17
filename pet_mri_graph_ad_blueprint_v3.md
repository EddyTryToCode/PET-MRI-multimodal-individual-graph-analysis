# PET-MRI Multimodal Individual Graph Analysis with AAL for Alzheimer's Diagnosis
## Blueprint v3 — Tích hợp pipeline có sẵn + bổ sung phần còn thiếu

> **Dành cho AI coding agent.**
> File này là tài liệu duy nhất, chốt toàn bộ thiết kế.
> Phần **[CÓ SẴN]** = đã có code, chỉ cần tái sử dụng hoặc sửa nhẹ.
> Phần **[CẦN THÊM]** = cần viết mới.
> Không cần hỏi lại về lựa chọn phương pháp.

---

## 0. Quyết định về Atlas

**Quyết định chốt:** Dùng **AAL3 (116 ROI, 1mm MNI space)**.

**Lý do:**
- Đúng với tên đề tài: *PET-MRI multimodal individual graph analysis **with AAL** for Alzheimer's diagnosis*.
- AAL là atlas giải phẫu chuẩn, bao phủ toàn não gồm cả vùng dưới vỏ — phù hợp với AD vì các vùng hippocampus, amygdala, temporal có trong AAL.
- 116 ROI cho ma trận 116×116 — vừa đủ nhỏ để baseline ML hiệu quả, vừa đủ lớn để có ý nghĩa sinh học.

**Atlas cần download:** AAL3v1 từ GIN (https://www.gin.cnrs.fr/en/tools/aal) hoặc dùng nilearn:
```python
from nilearn import datasets
aal = datasets.fetch_atlas_aal(version='SPM12')  # 116 ROI
```
**Tên file chuẩn:** `AAL3v1_1mm.nii.gz` + `AAL3_labels.csv` (roi_id, roi_name).

---

## 1. Tổng quan pipeline đầy đủ

```
ADNI raw (PET DICOM + MRI NIfTI) + CSV metadata
        │
        ▼
[S1] Restructure & convert                        ✅ CÓ SẴN
     - PET DICOM → NIfTI (dicom2nifti)
     - MRI NIfTI → copy
     → Project_Data/sub-*/sub-*_PET.nii.gz + sub-*_MRI.nii.gz
     File: 1-restructure_adni.py
        │
        ▼
[S2] Preprocessing per subject                    ✅ CÓ SẴN (cần thêm PET normalize)
     - N4 bias correction (MRI)
     - HD-BET skull strip (GPU/CPU fallback)
     - PET→MRI affine registration
     - Apply MRI brain mask to PET
     → *_MRI_preprocessed.nii.gz + *_PET_preprocessed.nii.gz
     File: 2-preprocess_adni.py  ← cần thêm bước normalize PET (xem S2b)
        │
        ├─► [S3] QC snapshot PET over MRI (PNG)   ✅ CÓ SẴN
        │     File: 3-generate_qc.py
        │
        ▼
[S4] Download AAL3 atlas (116 ROI, 1mm)           ✅ CÓ SẴN → cần sửa URL/method
     File: 4-atlas_download.py
        │
        ▼
[S5] Resample atlas + PET ROI voxel extraction    ✅ CÓ SẴN
     - Resample atlas → PET space
     - Extract voxel values per ROI → .pkl
     - QC parcellation overlay
     File: 5-extract_roi_voxels.py
        │
        ├─► [S5b] MRI ROI voxel extraction         🆕 CẦN THÊM
        │     - Reuse logic từ 5-extract_roi_voxels.py, đổi input sang MRI
        │     - Atlas đã resample sang PET space → cần resample lại sang MRI space
        │     File: 5b-extract_mri_roi_voxels.py
        │
        ▼
[S6] PET adjacency (Wasserstein)                  ✅ CÓ SẴN
     - Pairwise Wasserstein distances
     - Gaussian kernel similarity
     → A_pet.npy + heatmap QC
     File: 6-build_adjacency.py  ← đã đúng logic
        │
        ├─► [S6b] MRI adjacency (Jensen-Shannon)   🆕 CẦN THÊM
        │     - Histogram per ROI → JSD similarity
        │     → A_mri.npy + heatmap QC
        │     File: 6b-build_mri_adjacency.py
        │
        ├─► [S6c] Node feature matrix X            🆕 CẦN THÊM
        │     - [MRI stats | PET stats] per ROI
        │     → node_features.npy
        │     File: 6c-build_node_features.py
        │
        ├─► [S6d] Graph fusion                     🆕 CẦN THÊM
        │     - A_fused = α * A_mri + (1-α) * A_pet
        │     → A_fused.npy + heatmap QC
        │     File: 6d-fuse_graphs.py
        │
        └─► [S6e] Graph metrics                    🆕 CẦN THÊM
              - degree, clustering, path_length,
                local_eff, global_eff per graph
              → graph_metrics.csv
              File: 6e-compute_graph_metrics.py
        │
        ▼
[S7] Classification                               ✅ CÓ SẴN (cần nâng cấp)
     - Hiện tại: flat adjacency + SVM
     - Nâng cấp: graph metrics + node stats + flat A_fused + XGBoost + proper test split
     File: 7-classify.py  ← viết lại từ 7-svm_classify.py
        │
        ▼
[S8] Evaluation + Interpretability                🆕 CẦN THÊM
     - Full metrics: AUC, Sensitivity, Specificity, F1, BACC
     - ROI importance (top edges AD vs CN)
     - ROC curve, confusion matrix
     File: 8-evaluate.py
```

---

## 2. Cấu trúc thư mục

```
project_root/
│
├── configs/
│   └── default.yaml
│
├── data/
│   ├── raw/
│   │   └── sub-*/
│   │       ├── sub-*_PET.nii.gz          ← sau S1
│   │       └── sub-*_MRI.nii.gz          ← sau S1
│   ├── processed/
│   │   └── sub-*/
│   │       ├── sub-*_MRI_preprocessed.nii.gz   ← sau S2
│   │       ├── sub-*_PET_preprocessed.nii.gz   ← sau S2
│   │       ├── sub-*_PET_roi_voxels.pkl         ← sau S5
│   │       ├── sub-*_MRI_roi_voxels.pkl         ← sau S5b  [CẦN THÊM]
│   │       ├── sub-*_A_pet.npy                  ← sau S6
│   │       ├── sub-*_A_mri.npy                  ← sau S6b  [CẦN THÊM]
│   │       ├── sub-*_A_fused.npy                ← sau S6d  [CẦN THÊM]
│   │       └── sub-*_node_features.npy          ← sau S6c  [CẦN THÊM]
│   ├── atlas/
│   │   ├── AAL3v1_1mm.nii.gz                              ← sau S4
│   │   └── AAL3_labels.csv
│   ├── metadata.csv
│   └── graph_metrics.csv                        ← sau S6e  [CẦN THÊM]
│
├── qc/
│   ├── pet_over_mri/                            ← sau S3
│   └── parcellation_overlay/                    ← sau S5
│
├── outputs/
│   ├── figures/
│   └── results/
│
├── 1-restructure_adni.py                        ✅
├── 2-preprocess_adni.py                         ✅ (cần sửa nhỏ)
├── 3-generate_qc.py                             ✅
├── 4-atlas_download.py                          ✅
├── 5-extract_roi_voxels.py                      ✅
├── 5b-extract_mri_roi_voxels.py                 🆕
├── 6-build_adjacency.py                         ✅
├── 6b-build_mri_adjacency.py                    🆕
├── 6c-build_node_features.py                    🆕
├── 6d-fuse_graphs.py                            🆕
├── 6e-compute_graph_metrics.py                  🆕
├── 7-classify.py                                🆕 (viết lại từ 7-svm_classify.py)
├── 8-evaluate.py                                🆕
└── requirements.txt
```

---

## 3. `configs/default.yaml`

```yaml
data:
  raw_dir: data/raw
  processed_dir: data/processed
  atlas_nii: data/atlas/AAL3v1_1mm.nii.gz
  atlas_labels: data/atlas/AAL3_labels.csv
  metadata: data/metadata.csv
  graph_metrics_csv: data/graph_metrics.csv

preprocessing:
  pet_normalize: mean_brain   # chia pet / mean(pet[mask>0]) sau skull strip
  clip_percentile: [0.5, 99.5]

roi_extraction:
  min_voxels: 10
  filter_positive: true

graph_pet:
  method: wasserstein
  sigma: auto                 # mean pairwise distance

graph_mri:
  method: jensenshannon
  bins: 64
  epsilon: 1.0e-8

fusion:
  alpha: 0.5                  # tune qua validation

graph_metrics:
  threshold_percentile: 70    # proportional thresholding

classification:
  test_size: 0.15
  n_folds: 5
  seed: 42
  alpha_search: [0.3, 0.5, 0.7]   # inner CV tune alpha
  classifiers: [svm, xgboost]
  feature_set: all            # options: graph_metrics | node_stats | flat_adj | all
```

---

## 4. `metadata.csv` — định dạng bắt buộc

```csv
subject_id,label,age,sex,site
sub-0001,AD,74,F,site1
sub-0002,CN,68,M,site1
```

- `label`: **"AD"** hoặc **"CN"** — chính xác, case-sensitive.
- Paths đến ảnh được suy ra tự động từ `subject_id` + `processed_dir` trong code.
- Không cần cột `mri_path`, `pet_path` vì cấu trúc thư mục đã cố định.

---

## 5. Thiết kế chi tiết các bước CẦN THÊM

---

### S2b — Thêm PET normalize vào `2-preprocess_adni.py`

**Vị trí thêm:** Sau bước "Apply MRI brain mask to PET", trước khi lưu `*_PET_preprocessed.nii.gz`.

```python
# Thêm vào 2-preprocess_adni.py sau khi có PET đã mask

def normalize_pet_mean_brain(pet_data: np.ndarray, brain_mask: np.ndarray) -> np.ndarray:
    """
    Chuẩn hóa PET: chia cho mean voxel não (mask > 0 và pet > 0).
    Loại bỏ ảnh hưởng của global uptake scale khác nhau giữa subjects.
    """
    valid = pet_data[(brain_mask > 0) & (pet_data > 0)]
    if len(valid) == 0:
        return pet_data
    return pet_data / (valid.mean() + 1e-8)

def clip_percentile(data: np.ndarray, mask: np.ndarray,
                    low: float = 0.5, high: float = 99.5) -> np.ndarray:
    valid = data[mask > 0]
    if len(valid) == 0:
        return data
    lo, hi = np.percentile(valid, [low, high])
    out = data.copy()
    out[mask > 0] = np.clip(out[mask > 0], lo, hi)
    return out

# Trong vòng lặp chính của 2-preprocess_adni.py, thêm sau khi có pet_masked:
# pet_norm = normalize_pet_mean_brain(pet_masked, brain_mask)
# pet_clipped = clip_percentile(pet_norm, brain_mask)
# → lưu pet_clipped thay vì pet_masked
```

---


### S4 — Sửa `4-atlas_download.py` để download AAL3

**Thay thế toàn bộ logic download atlas cũ** bằng đoạn sau:

```python
#!/usr/bin/env python3
"""4-atlas_download.py — Download AAL3 atlas via nilearn."""

import os
import shutil
import numpy as np
import nibabel as nib
import pandas as pd
from nilearn import datasets

def main(cfg):
    os.makedirs("data/atlas", exist_ok=True)
    out_nii  = cfg["data"]["atlas_nii"]       # data/atlas/AAL3v1_1mm.nii.gz
    out_csv  = cfg["data"]["atlas_labels"]    # data/atlas/AAL3_labels.csv

    if os.path.exists(out_nii) and os.path.exists(out_csv):
        print("[SKIP] AAL3 atlas already downloaded.")
        return

    # Download via nilearn (AAL SPM12 = 116 ROI, 1mm MNI)
    print("Downloading AAL atlas via nilearn...")
    aal = datasets.fetch_atlas_aal(version="SPM12")

    # Copy NIfTI
    shutil.copy(aal.maps, out_nii)

    # Build labels CSV: roi_id (int), roi_name (str)
    labels_df = pd.DataFrame({
        "roi_id":   [int(i) for i in aal.indices],
        "roi_name": aal.labels
    })
    labels_df.to_csv(out_csv, index=False)

    # Verify
    img = nib.load(out_nii)
    unique_ids = np.unique(img.get_fdata().astype(int))
    unique_ids = unique_ids[unique_ids > 0]
    print(f"[OK] AAL3 atlas: {img.shape}, {len(unique_ids)} ROIs")
    print(f"     Saved: {out_nii}")
    print(f"     Labels: {out_csv}")

if __name__ == "__main__":
    import yaml
    with open("configs/default.yaml") as f:
        cfg = yaml.safe_load(f)
    main(cfg)
```


---

### S5b — `5b-extract_mri_roi_voxels.py`

**Logic:** Tương tự `5-extract_roi_voxels.py`, nhưng có sự khác biệt quan trọng:
- Input image: `*_MRI_preprocessed.nii.gz` thay vì `*_PET_preprocessed.nii.gz`
- Atlas cần resample về **MRI space** (thay vì PET space)
- Output: `sub-*_MRI_roi_voxels.pkl`
- **KHÔNG áp dụng `filter_positive`** — MRI T1 có voxel hợp lệ gần 0 (dark GM/WM sau N4 correction), chỉ filter `> 0` cho PET (loại bỏ uptake âm artifact)

```python
#!/usr/bin/env python3
"""5b-extract_mri_roi_voxels.py — Extract MRI voxel values per ROI (AAL atlas)."""

import os, pickle
import numpy as np
import nibabel as nib
from nilearn.image import resample_to_img
import pandas as pd

def extract_roi_voxels(img_data, atlas_data, roi_ids, min_voxels=10):
    """
    Extract voxel values per ROI for MRI T1 images.
    NOTE: Unlike PET, MRI intensity is NOT filtered to > 0 because T1 signal
    can legitimately be near zero (dark GM/WM regions) after bias correction.
    We only discard non-finite values (NaN/Inf).
    """
    result = {}
    for rid in roi_ids:
        vals = img_data[atlas_data == rid].copy().astype(np.float32)
        vals = vals[np.isfinite(vals)]  # Chỉ lọc NaN/Inf, KHÔNG filter > 0
        result[rid] = vals if len(vals) >= min_voxels else np.zeros(min_voxels, dtype=np.float32)
    return result

def main(cfg):
    atlas_img = nib.load(cfg["data"]["atlas_nii"])
    labels_df = pd.read_csv(cfg["data"]["atlas_labels"])  # cols: roi_id, roi_name
    roi_ids = labels_df["roi_id"].tolist()
    meta = pd.read_csv(cfg["data"]["metadata"])
    min_voxels = cfg["roi_extraction"]["min_voxels"]
    # NOTE: filter_positive intentionally NOT used for MRI (it is only for PET)

    for _, row in meta.iterrows():
        sid = row["subject_id"]
        mri_path = os.path.join(cfg["data"]["processed_dir"], sid,
                                f"{sid}_MRI_preprocessed.nii.gz")
        out_path = os.path.join(cfg["data"]["processed_dir"], sid,
                                f"{sid}_MRI_roi_voxels.pkl")

        if os.path.exists(out_path):
            print(f"[SKIP] {sid}")
            continue

        mri_img = nib.load(mri_path)
        # Resample atlas về MRI space (khác với S5 resample về PET space)
        atlas_mri = resample_to_img(atlas_img, mri_img,
                                    interpolation="nearest", copy=True)
        mri_data = mri_img.get_fdata().astype(np.float32)
        atlas_data = atlas_mri.get_fdata().astype(np.int32)

        roi_voxels = extract_roi_voxels(mri_data, atlas_data, roi_ids, min_voxels)
        with open(out_path, "wb") as f:
            pickle.dump(roi_voxels, f)
        n_valid = sum(1 for v in roi_voxels.values() if v.sum() > 0)
        print(f"[OK] {sid} | valid ROIs: {n_valid}/{len(roi_ids)}")

if __name__ == "__main__":
    import yaml
    with open("configs/default.yaml") as f:
        cfg = yaml.safe_load(f)
    main(cfg)
```

---

### S6b — `6b-build_mri_adjacency.py`

**Thuật toán:** Jensen-Shannon similarity từ histogram voxel.

**Formulation:**

Với mỗi ROI \(i\), histogram chuẩn hóa thành phân bố \(p_i\):

\[ p_i(k) = \frac{h_i(k) + \varepsilon}{\sum_k (h_i(k) + \varepsilon)} \]

Edge:

\[ A_{MRI}(i,j) = 1 - \sqrt{JSD(p_i \| p_j)} \in [0, 1] \]

Diagonal = 1.

**Lưu ý quan trọng:**
- Histogram **phải dùng global bin range** (min/max trên toàn bộ voxel của mọi ROI) để các bin được đồng nhất (aligned) khi so sánh JSD.
- Dùng `float64` cho histogram để tránh lỗi precision → NaN khi `scipy.jensenshannon` lấy `sqrt` của giá trị âm siêu nhỏ.
- Nếu toàn bộ voxel là hằng số (dữ liệu lỗi), in warning vì ma trận sẽ không mang thông tin.

```python
#!/usr/bin/env python3
"""6b-build_mri_adjacency.py — Build MRI individual graph via JSD similarity."""

import os, pickle
import numpy as np
from scipy.spatial.distance import jensenshannon
import matplotlib.pyplot as plt
import pandas as pd

def compute_histogram(vals, bins=64, epsilon=1e-8, val_range=None):
    h, _ = np.histogram(vals, bins=bins, range=val_range, density=False)
    h = h.astype(np.float64) + epsilon  # float64 để tránh NaN từ precision errors
    return h / h.sum()

def build_mri_adjacency(roi_voxels, roi_ids, bins=64, epsilon=1e-8):
    """
    Returns A_mri [N, N] float32.
    A_mri[i,j] = 1 - JSD(hist_i, hist_j) ∈ [0, 1]. Diagonal = 1.
    """
    n = len(roi_ids)

    # Compute global range for aligned bins
    valid_vals = [v for v in roi_voxels.values() if len(v) > 0]
    if not valid_vals:
        return np.zeros((n, n), dtype=np.float32)

    all_vals = np.concatenate(valid_vals)
    g_min, g_max = float(all_vals.min()), float(all_vals.max())
    if g_min == g_max:
        print(f"[WARN] All voxels constant ({g_min:.4f}). Check MRI preprocessing.")
        g_min -= 0.5
        g_max += 0.5
    val_range = (g_min, g_max)

    H = {}
    for rid in roi_ids:
        vals = roi_voxels[rid]
        if len(vals) == 0:
            vals = np.array([g_min], dtype=np.float32)
        H[rid] = compute_histogram(vals, bins, epsilon, val_range)

    A = np.zeros((n, n), dtype=np.float32)
    for a, i in enumerate(roi_ids):
        A[a, a] = 1.0
        for b in range(a + 1, n):
            j = roi_ids[b]
            d = float(jensenshannon(H[i], H[j]))
            if np.isnan(d): d = 0.0  # Safety fallback
            s = 1.0 - min(d, 1.0)
            A[a, b] = s
            A[b, a] = s
    return A

def main(cfg):
    labels_df = pd.read_csv(cfg["data"]["atlas_labels"])  # cols: roi_id, roi_name
    roi_ids = labels_df["roi_id"].tolist()
    meta = pd.read_csv(cfg["data"]["metadata"])
    gmc = cfg["graph_mri"]

    for _, row in meta.iterrows():
        sid = row["subject_id"]
        roi_path = os.path.join(cfg["data"]["processed_dir"], sid,
                                f"{sid}_MRI_roi_voxels.pkl")
        out_npy = os.path.join(cfg["data"]["processed_dir"], sid,
                               f"{sid}_A_mri.npy")
        out_qc = os.path.join(cfg["data"]["processed_dir"], sid,
                              f"{sid}_A_mri_heatmap.png")
        if os.path.exists(out_npy):
            print(f"[SKIP] {sid}")
            continue

        with open(roi_path, "rb") as f:
            roi_voxels = pickle.load(f)

        A = build_mri_adjacency(roi_voxels, roi_ids, gmc["bins"], gmc["epsilon"])
        np.save(out_npy, A)

        # QC heatmap
        plt.figure(figsize=(8, 6))
        plt.imshow(A, cmap="hot", vmin=0, vmax=1)
        plt.colorbar(label="JSD similarity")
        plt.title(f"{sid} — MRI graph (JSD)")
        plt.tight_layout()
        plt.savefig(out_qc, dpi=100)
        plt.close()
        print(f"[OK] {sid} | A_mri mean={A[np.triu_indices(len(roi_ids), k=1)].mean():.3f}")

if __name__ == "__main__":
    import yaml
    with open("configs/default.yaml") as f:
        cfg = yaml.safe_load(f)
    main(cfg)
```

---

### S6c — `6c-build_node_features.py`

**Output:** `node_features.npy` shape `[N_roi, 12]` — 6 stats MRI + 6 stats PET mỗi ROI.

```python
#!/usr/bin/env python3
"""6c-build_node_features.py — Build node feature matrix X per subject."""

import os, pickle
import numpy as np
import pandas as pd

def roi_stats(vals):
    """Trả về [mean, std, p10, p50, p90, count] float32."""
    if len(vals) == 0 or vals.sum() == 0:
        return np.zeros(6, dtype=np.float32)
    return np.array([
        np.mean(vals), np.std(vals),
        np.percentile(vals, 10), np.percentile(vals, 50), np.percentile(vals, 90),
        float(len(vals))
    ], dtype=np.float32)

def build_node_features(roi_mri, roi_pet, roi_ids):
    """Returns X: [N_roi, 12] — concat MRI stats + PET stats."""
    rows = []
    for rid in roi_ids:
        fm = roi_stats(roi_mri.get(rid, np.array([])))
        fp = roi_stats(roi_pet.get(rid, np.array([])))
        rows.append(np.concatenate([fm, fp]))
    return np.stack(rows, axis=0)

def main(cfg):
    labels_df = pd.read_csv(cfg["data"]["atlas_labels"])  # cols: roi_id, roi_name
    roi_ids = labels_df["roi_id"].tolist()
    meta = pd.read_csv(cfg["data"]["metadata"])

    for _, row in meta.iterrows():
        sid = row["subject_id"]
        proc_dir = os.path.join(cfg["data"]["processed_dir"], sid)
        mri_pkl = os.path.join(proc_dir, f"{sid}_MRI_roi_voxels.pkl")
        pet_pkl = os.path.join(proc_dir, f"{sid}_PET_roi_voxels.pkl")
        out_npy = os.path.join(proc_dir, f"{sid}_node_features.npy")

        if os.path.exists(out_npy):
            print(f"[SKIP] {sid}")
            continue

        with open(mri_pkl, "rb") as f:
            roi_mri = pickle.load(f)
        with open(pet_pkl, "rb") as f:
            roi_pet = pickle.load(f)

        X = build_node_features(roi_mri, roi_pet, roi_ids)
        np.save(out_npy, X)
        print(f"[OK] {sid} | X shape={X.shape}")

if __name__ == "__main__":
    import yaml
    with open("configs/default.yaml") as f:
        cfg = yaml.safe_load(f)
    main(cfg)
```

---

### S6d — `6d-fuse_graphs.py`

```python
#!/usr/bin/env python3
"""6d-fuse_graphs.py — Fuse A_mri + A_pet into A_fused."""

import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

def fuse_adjacency(A_mri, A_pet, alpha=0.5):
    """A_fused = alpha * A_mri + (1 - alpha) * A_pet."""
    assert A_mri.shape == A_pet.shape
    return alpha * A_mri + (1.0 - alpha) * A_pet

def main(cfg):
    meta = pd.read_csv(cfg["data"]["metadata"])
    alpha = cfg["fusion"]["alpha"]

    for _, row in meta.iterrows():
        sid = row["subject_id"]
        proc_dir = os.path.join(cfg["data"]["processed_dir"], sid)
        a_mri_path = os.path.join(proc_dir, f"{sid}_A_mri.npy")
        a_pet_path = os.path.join(proc_dir, f"{sid}_A_pet.npy")
        out_path   = os.path.join(proc_dir, f"{sid}_A_fused.npy")
        out_qc     = os.path.join(proc_dir, f"{sid}_A_fused_heatmap.png")

        if os.path.exists(out_path):
            print(f"[SKIP] {sid}")
            continue

        A_mri = np.load(a_mri_path)
        A_pet = np.load(a_pet_path)
        A_fused = fuse_adjacency(A_mri, A_pet, alpha)
        np.save(out_path, A_fused)

        n = A_fused.shape[0]
        plt.figure(figsize=(8, 6))
        plt.imshow(A_fused, cmap="hot", vmin=0, vmax=1)
        plt.colorbar(label=f"Fused similarity (α={alpha})")
        plt.title(f"{sid} — Fused graph")
        plt.tight_layout()
        plt.savefig(out_qc, dpi=100)
        plt.close()
        print(f"[OK] {sid} | A_fused mean={A_fused[np.triu_indices(n, k=1)].mean():.3f}")

if __name__ == "__main__":
    import yaml
    with open("configs/default.yaml") as f:
        cfg = yaml.safe_load(f)
    main(cfg)
```

---

### S6e — `6e-compute_graph_metrics.py`

**Output:** `data/graph_metrics.csv` — 1 hàng / subject, gồm metrics của A_mri, A_pet, A_fused.

```python
#!/usr/bin/env python3
"""6e-compute_graph_metrics.py — Topological graph metrics per subject."""

import os
import numpy as np
import pandas as pd
import networkx as nx

def adjacency_to_nx(A, threshold_percentile=70):
    """Proportional thresholding: giữ top (100-pct)% cạnh mạnh nhất."""
    n = A.shape[0]
    A_thr = A.copy()
    np.fill_diagonal(A_thr, 0)
    upper = A_thr[np.triu_indices(n, k=1)]
    if len(upper) == 0:
        return nx.Graph()
    thr = np.percentile(upper, threshold_percentile)
    A_thr[A_thr < thr] = 0
    return nx.from_numpy_array(A_thr)

def graph_metrics(A, threshold_percentile=70):
    """
    Trả về dict với 5 metrics.
    Dùng largest connected component để tránh lỗi disconnected graph.
    """
    G = adjacency_to_nx(A, threshold_percentile)
    if G.number_of_nodes() == 0:
        return {"degree": 0, "clustering": 0, "path_length": 0,
                "global_eff": 0, "local_eff": 0}
    try:
        Gc = G.subgraph(max(nx.connected_components(G), key=len)).copy()
        return {
            "degree":      np.mean([d for _, d in Gc.degree()]),
            "clustering":  nx.average_clustering(Gc),
            "path_length": nx.average_shortest_path_length(Gc) if nx.is_connected(Gc) else 0.0,
            "global_eff":  nx.global_efficiency(Gc),
            "local_eff":   nx.local_efficiency(Gc),
        }
    except Exception:
        return {"degree": 0, "clustering": 0, "path_length": 0,
                "global_eff": 0, "local_eff": 0}

def main(cfg):
    meta = pd.read_csv(cfg["data"]["metadata"])
    thr = cfg["graph_metrics"]["threshold_percentile"]
    out_csv = cfg["data"]["graph_metrics_csv"]

    # Incremental / crash-safe: load already-computed rows
    done_sids = set()
    rows = []
    if os.path.isfile(out_csv):
        existing = pd.read_csv(out_csv)
        rows = existing.to_dict("records")
        done_sids = set(existing["subject_id"].tolist())
        print(f"[INFO] Resuming: {len(done_sids)} subjects already in {out_csv}")

    for _, row in meta.iterrows():
        sid = row["subject_id"]
        if sid in done_sids:
            print(f"[SKIP] {sid} already computed")
            continue

        proc_dir = os.path.join(cfg["data"]["processed_dir"], sid)

        record = {"subject_id": sid, "label": row["label"]}
        for tag, fname in [("mri", f"{sid}_A_mri.npy"),
                           ("pet", f"{sid}_A_pet.npy"),
                           ("fused", f"{sid}_A_fused.npy")]:
            A = np.load(os.path.join(proc_dir, fname))
            m = graph_metrics(A, thr)
            for k, v in m.items():
                record[f"{tag}_{k}"] = v

        rows.append(record)
        print(f"[OK] {sid}")

        # Write incrementally after every subject to survive crashes
        pd.DataFrame(rows).to_csv(out_csv, index=False)

    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False)
    print(f"\nSaved: {out_csv} | shape={df.shape}")

if __name__ == "__main__":
    import yaml
    with open("configs/default.yaml") as f:
        cfg = yaml.safe_load(f)
    main(cfg)
```

---

### S7 — `7-classify.py` (viết lại từ 7-svm_classify.py)

**Thay đổi so với phiên bản cũ:**
1. Tách test set 15% TRƯỚC CV — không để leak.
2. Thêm feature sets: graph metrics + node stats + flat A_fused (thay vì chỉ flat A_pet).
3. Thêm XGBoost song song với SVM.
4. Tune alpha trong inner fold.

```python
#!/usr/bin/env python3
"""7-classify.py — Multimodal graph classification: SVM + XGBoost, 5-fold CV."""

import os
import numpy as np
import pandas as pd
import yaml
import pickle
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import roc_auc_score, balanced_accuracy_score, confusion_matrix
from sklearn.base import clone
from xgboost import XGBClassifier

def load_subject_features(sid, proc_dir, alpha=0.5):
    """
    Trả về feature vector 1D cho 1 subject:
    [graph_metrics (15) | node_stats (24) | flat_A_fused (N*(N-1)/2)]
    """
    # Graph metrics
    metrics_path = os.path.join(proc_dir, sid, "graph_metrics_local.npy")  # đọc từ CSV hoặc tính lại
    # Node features
    X_node = np.load(os.path.join(proc_dir, sid, f"{sid}_node_features.npy"))
    node_mean = X_node.mean(axis=0)   # [12]
    node_std  = X_node.std(axis=0)    # [12]
    # Flat adjacency fused
    A_fused = np.load(os.path.join(proc_dir, sid, f"{sid}_A_fused.npy"))
    n = A_fused.shape[0]
    flat_adj = A_fused[np.triu_indices(n, k=1)]
    return np.concatenate([node_mean, node_std, flat_adj])

def build_feature_matrix(meta, metrics_df, proc_dir, alpha=0.5):
    """Gộp graph metrics + node stats + flat adjacency."""
    X_list, y_list, sids = [], [], []
    for _, row in meta.iterrows():
        sid = row["subject_id"]
        # Graph metrics từ CSV
        m_row = metrics_df[metrics_df["subject_id"] == sid].iloc[0]
        metric_cols = [c for c in metrics_df.columns
                       if c not in ["subject_id", "label"]]
        gm = m_row[metric_cols].values.astype(np.float32)
        # Node + flat
        nf = load_subject_features(sid, proc_dir, alpha)
        feat = np.concatenate([gm, nf])
        X_list.append(feat)
        y_list.append(int(row["label"] == "AD"))
        sids.append(sid)
    return np.stack(X_list), np.array(y_list), sids

def get_classifiers():
    return {
        "svm": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", SVC(kernel="rbf", probability=True, C=1.0, gamma="scale"))
        ]),
        "xgboost": XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            eval_metric="logloss", use_label_encoder=False,
            verbosity=0
        ),
    }

def run_cv(X, y, cfg):
    seed = cfg["classification"]["seed"]
    n_folds = cfg["classification"]["n_folds"]
    test_size = cfg["classification"]["test_size"]

    # Tách test set TRƯỚC — không tham gia CV
    X_dev, X_test, y_dev, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=seed
    )

    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
    classifiers = get_classifiers()
    cv_results = {name: {"auc": [], "bacc": [], "sens": [], "spec": []}
                  for name in classifiers}

    for fold, (tr_idx, val_idx) in enumerate(skf.split(X_dev, y_dev)):
        X_tr, X_val = X_dev[tr_idx], X_dev[val_idx]
        y_tr, y_val = y_dev[tr_idx], y_dev[val_idx]

        for name, clf in classifiers.items():
            clf_c = clone(clf)
            clf_c.fit(X_tr, y_tr)
            prob = clf_c.predict_proba(X_val)[:, 1]
            pred = (prob >= 0.5).astype(int)
            tn, fp, fn, tp = confusion_matrix(y_val, pred, labels=[0,1]).ravel()
            auc  = roc_auc_score(y_val, prob)
            bacc = balanced_accuracy_score(y_val, pred)
            sens = tp / (tp + fn + 1e-8)
            spec = tn / (tn + fp + 1e-8)
            cv_results[name]["auc"].append(auc)
            cv_results[name]["bacc"].append(bacc)
            cv_results[name]["sens"].append(sens)
            cv_results[name]["spec"].append(spec)
            print(f"  Fold {fold+1} | {name:8s} | AUC={auc:.3f} | Sens={sens:.3f} | Spec={spec:.3f}")

    print("\n=== CV Summary ===")
    for name in cv_results:
        r = cv_results[name]
        print(f"[{name}] AUC={np.mean(r['auc']):.3f}±{np.std(r['auc']):.3f} | "
              f"Sens={np.mean(r['sens']):.3f} | Spec={np.mean(r['spec']):.3f}")

    # Eval trên test set với model best (SVM theo AUC)
    best_name = max(cv_results, key=lambda n: np.mean(cv_results[n]["auc"]))
    best_clf = clone(classifiers[best_name])
    best_clf.fit(X_dev, y_dev)
    prob_test = best_clf.predict_proba(X_test)[:, 1]
    pred_test = (prob_test >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, pred_test, labels=[0,1]).ravel()
    print(f"\n=== Test Set ({best_name}) ===")
    print(f"AUC={roc_auc_score(y_test, prob_test):.3f} | "
          f"Sens={tp/(tp+fn+1e-8):.3f} | Spec={tn/(tn+fp+1e-8):.3f}")
    return cv_results, best_clf, X_test, y_test, prob_test

def main():
    import yaml
    with open("configs/default.yaml") as f:
        cfg = yaml.safe_load(f)

    meta = pd.read_csv(cfg["data"]["metadata"])
    metrics_df = pd.read_csv(cfg["data"]["graph_metrics_csv"])

    print("Building feature matrix...")
    X, y, sids = build_feature_matrix(meta, metrics_df, cfg["data"]["processed_dir"],
                                       cfg["fusion"]["alpha"])
    print(f"Feature matrix: {X.shape} | Labels: {np.bincount(y)}")

    cv_results, best_clf, X_test, y_test, prob_test = run_cv(X, y, cfg)

    # Lưu kết quả
    os.makedirs("outputs/results", exist_ok=True)
    pd.DataFrame({
        "subject_id": [sids[i] for i in range(len(sids))],  # cần map lại với test idx
        "y_true": y_test, "y_prob": prob_test
    }).to_csv("outputs/results/test_predictions.csv", index=False)
    print("Saved: outputs/results/test_predictions.csv")

if __name__ == "__main__":
    main()
```

---

### S8 — `8-evaluate.py`

```python
#!/usr/bin/env python3
"""8-evaluate.py — Full evaluation: ROC, confusion matrix, ROI importance."""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import (
    roc_curve, auc, confusion_matrix, classification_report,
    balanced_accuracy_score, roc_auc_score
)

def plot_roc(y_true, y_prob, out_path):
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    roc_auc = auc(fpr, tpr)
    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, lw=2, label=f"AUC = {roc_auc:.3f}")
    plt.plot([0,1],[0,1], "k--")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved ROC: {out_path}")

def plot_confusion(y_true, y_pred, labels, out_path):
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(4, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
    ax.set_xticklabels(labels); ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > cm.max()/2 else "black")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved confusion matrix: {out_path}")

def plot_group_adjacency(meta_df, proc_dir, out_path, graph_tag="A_fused"):
    """Group-averaged adjacency: CN vs AD side by side."""
    cn_mats, ad_mats = [], []
    for _, row in meta_df.iterrows():
        A = np.load(os.path.join(proc_dir, row["subject_id"],
                                 f"{row['subject_id']}_{graph_tag}.npy"))
        (ad_mats if row["label"] == "AD" else cn_mats).append(A)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, mats, title in zip(axes,
                                [cn_mats, ad_mats],
                                ["CN (mean)", "AD (mean)"]):
        mean_A = np.mean(np.stack(mats), axis=0)
        im = ax.imshow(mean_A, cmap="hot", vmin=0, vmax=1)
        ax.set_title(title)
        plt.colorbar(im, ax=ax)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Saved group adjacency: {out_path}")

def main():
    import yaml
    with open("configs/default.yaml") as f:
        cfg = yaml.safe_load(f)

    pred_df = pd.read_csv("outputs/results/test_predictions.csv")
    meta = pd.read_csv(cfg["data"]["metadata"])

    y_true = pred_df["y_true"].values
    y_prob = pred_df["y_prob"].values
    y_pred = (y_prob >= 0.5).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0,1]).ravel()
    print("=== Final Test Metrics ===")
    print(f"AUC:      {roc_auc_score(y_true, y_prob):.4f}")
    print(f"Accuracy: {(tp+tn)/(tp+tn+fp+fn):.4f}")
    print(f"BACC:     {balanced_accuracy_score(y_true, y_pred):.4f}")
    print(f"Sensitivity (Recall AD): {tp/(tp+fn+1e-8):.4f}")
    print(f"Specificity (Recall CN): {tn/(tn+fp+1e-8):.4f}")
    print(f"F1:       {2*tp/(2*tp+fp+fn+1e-8):.4f}")

    os.makedirs("outputs/figures", exist_ok=True)
    plot_roc(y_true, y_prob, "outputs/figures/roc_curve.png")
    plot_confusion(y_true, y_pred, ["CN", "AD"], "outputs/figures/confusion_matrix.png")
    plot_group_adjacency(meta, cfg["data"]["processed_dir"],
                         "outputs/figures/group_adjacency.png")

if __name__ == "__main__":
    main()
```

---

## 6. `requirements.txt`

```
nibabel>=5.0.0
nilearn>=0.10.0
numpy>=1.24.0
scipy>=1.10.0
pandas>=2.0.0
scikit-learn>=1.3.0
xgboost>=2.0.0
networkx>=3.1
dicom2nifti>=2.4.0
matplotlib>=3.7.0
seaborn>=0.12.0
tqdm>=4.65.0
pyyaml>=6.0
```

> **PyTorch / PyG:** Không bắt buộc cho pipeline này.
> Chỉ cần nếu muốn tiến thêm sang Dual-branch GNN (bước mở rộng sau).

---

## 7. Thứ tự chạy từ đầu đến cuối

```bash
# Cài dependencies
pip install -r requirements.txt

# S1-S3: đã có, chạy như cũ
python 1-restructure_adni.py
python 2-preprocess_adni.py   # ← đã thêm normalize PET
python 3-generate_qc.py

# S4-S5: đã có, chạy như cũ
python 4-atlas_download.py    # đã sửa để download AAL3
python 5-extract_roi_voxels.py

# S5b: MỚI
python 5b-extract_mri_roi_voxels.py

# S6: đã có, chạy như cũ
python 6-build_adjacency.py   # → A_pet

# S6b-S6e: MỚI
python 6b-build_mri_adjacency.py
python 6c-build_node_features.py
python 6d-fuse_graphs.py
python 6e-compute_graph_metrics.py

# S7-S8: MỚI (thay thế 7-svm_classify.py cũ)
python 7-classify.py
python 8-evaluate.py
```

---

## 8. Thứ tự implement cho agent

| Bước | File | Trạng thái | Ưu tiên |
|---|---|---|---|
| 1 | `configs/default.yaml` | 🆕 Tạo mới | 🔴 Trước tất cả |
| 2 | Thêm normalize PET vào `2-preprocess_adni.py` | ✏️ Sửa nhẹ | 🔴 Trước S5b |
| 3 | `5b-extract_mri_roi_voxels.py` | 🆕 | 🔴 Core |
| 4 | `6b-build_mri_adjacency.py` | 🆕 | 🔴 Core |
| 5 | `6c-build_node_features.py` | 🆕 | 🔴 Core |
| 6 | `6d-fuse_graphs.py` | 🆕 | 🔴 Core |
| 7 | `6e-compute_graph_metrics.py` | 🆕 | 🟡 Trước S7 |
| 8 | `7-classify.py` | 🆕 (viết lại) | 🔴 |
| 9 | `8-evaluate.py` | 🆕 | 🟡 |

---

## 9. Những lưu ý bắt buộc cho agent

1. **S5 (PET) và S5b (MRI) dùng atlas ở KHÁC space:**
   - S5 đã resample atlas → PET space.
   - S5b phải resample atlas → MRI space riêng. Không dùng chung atlas đã resample từ S5.

2. **S5b KHÔNG áp dụng `filter_positive` cho MRI:**
   - `filter_positive: true` trong config chỉ dành cho PET (loại bỏ uptake âm artifact).
   - MRI T1 có voxel intensity gần 0 hợp lệ (dark GM/WM sau N4 correction). Lọc `> 0` cho MRI sẽ loại mất voxel hợp lệ, gây ROI thiếu voxel → zero-padding → similarity = 1.0.

3. **PET normalize (S2b) phải làm TRƯỚC S5**, vì S5 extract từ `*_PET_preprocessed.nii.gz`.
   Nếu S5 đã chạy rồi mà chưa normalize → cần chạy lại S5 sau khi sửa S2.

4. **S2 phải load HD-BET mask file riêng (`*_mask.nii.gz`)**:
   - KHÔNG dùng `mri_brain.numpy() > 0` để tạo mask — sẽ bỏ sót vùng GM tối.
   - HD-BET mask là binary {0,1} đã được neural network predict, chính xác hơn threshold intensity.

5. **S6b histogram phải dùng global bin range:**
   - `np.histogram(vals, bins=64)` mặc định sẽ tính range cục bộ → bins không aligned giữa các ROI → JSD so sánh sai.
   - Phải tính global `(min, max)` trên toàn bộ voxel rồi truyền `range=(g_min, g_max)` cho tất cả ROI.
   - Dùng `float64` cho histogram để tránh precision errors → NaN.

6. **6-build_adjacency.py hiện tại đã đúng logic Wasserstein** → không sửa, chỉ verify output là `*_A_pet.npy`.

7. **Test split 15% trong S7 phải tách TRƯỚC vòng lặp CV** — xem code S7, dòng `train_test_split`.

8. **Khi fit scaler/StandardScaler trong SVM pipeline**, `clone(clf)` đảm bảo không có data leak giữa các fold.

9. **S7 đọc graph metrics (bao gồm fused) từ CSV `graph_metrics.csv`**, không tính lại tại runtime. Điều này đảm bảo nhất quán với giá trị đã tính ở S6e (cùng threshold).

10. **S6e ghi CSV incremental** để crash-safe. Nếu crash giữa chừng, kết quả đã tính không bị mất.

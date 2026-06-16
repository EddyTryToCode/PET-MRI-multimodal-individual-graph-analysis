# 📋 Pipeline Chi Tiết: Phân Tích Đồ Thị Não Cá Nhân Đa Phương Thức PET-MRI cho Chẩn Đoán Alzheimer

> **Tài liệu này giải thích từng bước trong pipeline một cách chi tiết nhất có thể**, bao gồm kiến thức y tế nền tảng, lý do chọn phương pháp, cách hoạt động, đầu vào/đầu ra, và kết quả được lưu ở đâu. Dù bạn không có kiến thức chuyên sâu về hình ảnh thần kinh (neuroimaging), bạn vẫn có thể hiểu toàn bộ pipeline sau khi đọc tài liệu này.

---

## 🧠 Kiến Thức Nền Tảng

### Bệnh Alzheimer (AD) là gì?

**Bệnh Alzheimer (Alzheimer's Disease — AD)** là dạng sa sút trí tuệ (dementia) phổ biến nhất, chiếm khoảng 60–80% các ca sa sút trí tuệ. Bệnh gây thoái hóa thần kinh tiến triển, dẫn đến mất trí nhớ, suy giảm nhận thức, và cuối cùng mất khả năng tự chăm sóc.

**Những thay đổi sinh lý bệnh chính trong não AD:**

| Đặc điểm | Mô tả |
|:---|:---|
| **Teo não (Brain atrophy)** | Mất thể tích chất xám (gray matter), đặc biệt ở thùy thái dương (temporal lobe), hippocampus, và vỏ não vùng liên hợp |
| **Mảng Amyloid (Amyloid plaques)** | Sự tích tụ protein beta-amyloid ngoại bào, đóng vai trò khởi phát bệnh |
| **Đám rối sợi Tau (Neurofibrillary tangles)** | Protein Tau bất thường tạo đám rối bên trong tế bào thần kinh |
| **Giảm chuyển hóa glucose (Hypometabolism)** | Giảm tiêu thụ glucose ở các vùng não bị ảnh hưởng — đây là dấu hiệu phát hiện bằng PET |
| **Mất kết nối mạng lưới não (Network disruption)** | Các mạng lưới não bình thường (đặc biệt Default Mode Network) bị phá vỡ |

### Hai phương thức hình ảnh: MRI và PET

#### 🔵 MRI (Magnetic Resonance Imaging — Chụp Cộng Hưởng Từ)

**MRI cấu trúc T1-weighted** cho hình ảnh giải phẫu não với độ phân giải cao (thường 1mm³/voxel). MRI T1 cho phép phân biệt rõ ràng:

- **Chất xám (Gray Matter — GM):** Chứa thân tế bào thần kinh, synapse — hiện sáng vừa trên T1
- **Chất trắng (White Matter — WM):** Chứa sợi trục myelin hóa — hiện sáng nhất trên T1
- **Dịch não tủy (CSF):** Lỏng — hiện tối trên T1

**Vai trò trong dự án:** MRI cung cấp thông tin **hình thái cấu trúc (morphological/structural)** — cho biết vùng nào bị teo, mất thể tích. Trong bệnh Alzheimer, hippocampus và thùy thái dương là những vùng teo sớm nhất. Bằng cách so sánh **phân bố cường độ voxel (voxel intensity distribution)** của các vùng não (ROI), ta có thể phát hiện sự thay đổi cấu trúc mô não.

#### 🟠 PET (Positron Emission Tomography — Chụp Cắt Lớp Phát Xạ Positron)

**FDG-PET (¹⁸F-Fluorodeoxyglucose PET)** đo mức tiêu thụ glucose của não. Glucose là nguồn năng lượng chính của tế bào thần kinh, nên mức FDG uptake phản ánh mức độ hoạt động synapse.

- **Vùng hoạt động mạnh** → hấp thu nhiều FDG → tín hiệu cao (sáng)
- **Vùng thoái hóa** → giảm hấp thu FDG → tín hiệu thấp (tối) = **hypometabolism**

**Vai trò trong dự án:** PET cung cấp thông tin **chức năng chuyển hóa (metabolic/functional)** — cho biết vùng nào đang hoạt động kém. Trong AD, hypometabolism thường xuất hiện ở:
- Posterior cingulate cortex (vỏ đai sau)
- Precuneus
- Parietal cortex (vỏ đỉnh)
- Temporal cortex (vỏ thái dương)

#### 🟢 Tại sao kết hợp cả hai? (Multimodal)

MRI và PET cung cấp **thông tin bổ sung (complementary information):**

| | MRI | PET |
|:---|:---|:---|
| **Đo gì** | Cấu trúc giải phẫu | Chuyển hóa glucose |
| **Phát hiện** | Teo não, mất thể tích | Giảm chuyển hóa |
| **Thời điểm** | Muộn hơn trong tiến trình bệnh | Sớm hơn — hypometabolism xảy ra trước khi teo rõ |
| **Độ phân giải** | Cao (1mm) | Thấp hơn (2-4mm) |

**Kết hợp cả hai** cho phép phát hiện bệnh chính xác hơn so với chỉ dùng một phương thức duy nhất.

### Atlas AAL3 (Automated Anatomical Labeling)

**AAL3** là một bản đồ phân vùng não (brain parcellation atlas) chia toàn bộ não thành **116 vùng giải phẫu (ROI — Region of Interest)**, bao gồm:

- **Vùng vỏ não (Cortical regions):** Frontal, parietal, temporal, occipital lobes
- **Vùng dưới vỏ (Subcortical regions):** Hippocampus, amygdala, caudate, putamen, thalamus
- **Tiểu não (Cerebellum):** Các thùy và vermis

Atlas được định nghĩa trong **không gian MNI152 chuẩn (standard MNI space)** — một mẫu não trung bình được tạo từ 152 bộ não khỏe mạnh. Mọi não cá nhân đều cần được **đăng ký (register)** vào không gian này, hoặc ngược lại đưa atlas về không gian cá nhân.

**Tại sao chọn AAL3?**
- Đúng với tên đề tài: "*... with AAL for Alzheimer's diagnosis*"
- 116 ROI là kích thước phù hợp — đủ nhỏ cho machine learning hiệu quả, đủ lớn để có ý nghĩa sinh học
- Bao phủ hippocampus, amygdala, temporal — các vùng quan trọng nhất cho AD

### Đồ thị não cá nhân (Individual Brain Graph) là gì?

Thay vì nhìn não như một tập hợp vùng riêng lẻ, ta mô hình hóa não như một **đồ thị (graph/network):**

- **Nút (Node):** Mỗi vùng não (ROI) trong atlas AAL3 = 1 nút. Có 116 nút.
- **Cạnh (Edge):** Mức độ "giống nhau" (similarity) giữa hai vùng não. Nếu phân bố voxel của hai vùng giống nhau → edge weight cao → chúng có "kết nối" mạnh.

**"Cá nhân" (Individual)** nghĩa là mỗi bệnh nhân có **một đồ thị riêng**, được xây dựng từ chính dữ liệu hình ảnh của họ — không phải dùng dữ liệu trung bình nhóm.

**Ma trận kề (Adjacency Matrix):** Đồ thị được biểu diễn dưới dạng ma trận vuông `116 × 116`, trong đó phần tử `A[i,j]` là trọng số cạnh giữa vùng i và vùng j.

---

## 📊 Tổng Quan Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DỮ LIỆU THÔ ADNI                           │
│  PET (DICOM) + MRI (NIfTI) + CSV metadata                         │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│  BƯỚC 1: Restructure — Sắp xếp lại dữ liệu thô                   │
│  Script: 1-restructure_adni.py                                     │
│  Output: data/raw/sub-*/sub-*_{PET,MRI}.nii.gz                    │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│  BƯỚC 2: Preprocessing — Tiền xử lý hình ảnh                      │
│  Script: 2-preprocess_adni.py                                      │
│  Output: data/processed/sub-*/*_preprocessed.nii.gz                │
└──────────┬─────────────────┬───────────────────────────────────────┘
           │                 │
           ▼                 ▼
┌──────────────────┐  ┌──────────────────────────────────────────────┐
│ BƯỚC 3: QC       │  │  BƯỚC 4: Download Atlas AAL3                 │
│ 3-generate_qc.py │  │  4-atlas_download.py                         │
│ Output: qc/*.png │  │  Output: data/atlas/AAL3v1_1mm.nii.gz        │
└──────────────────┘  └────────────────┬─────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────┐
│  BƯỚC 5 & 5b: Đăng ký Atlas + Trích xuất Voxel theo ROI           │
│  Scripts: atlas_registration.py, 5-extract_roi_voxels.py,          │
│           5b-extract_mri_roi_voxels.py                             │
│  Output: *_PET_roi_voxels.pkl, *_MRI_roi_voxels.pkl               │
└──────────┬─────────────────┬───────────────┬───────────────────────┘
           │                 │               │
           ▼                 ▼               ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────────────────┐
│ BƯỚC 6: PET      │ │ BƯỚC 6b: MRI │ │ BƯỚC 6c: Node Features       │
│ Adjacency        │ │ Adjacency    │ │ 6c-build_node_features.py    │
│ (Wasserstein)    │ │ (JSD)        │ │ Output: *_node_features.npy  │
│ Output: A_pet.npy│ │ Output:      │ └──────────────────────────────┘
└────────┬─────────┘ │ A_mri.npy    │
         │           └──────┬───────┘
         │                  │
         └────────┬─────────┘
                  ▼
┌────────────────────────────────────────────────────────────────────┐
│  BƯỚC 6d: Fusion — Kết hợp đồ thị PET + MRI                      │
│  Script: 6d-fuse_graphs.py                                         │
│  Output: *_A_fused.npy                                             │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│  BƯỚC 6e: Tính Graph Metrics — Đặc trưng topo đồ thị             │
│  Script: 6e-compute_graph_metrics.py                               │
│  Output: data/graph_metrics.csv                                    │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│  BƯỚC 7: Classification — Phân loại AD vs CN                       │
│  Script: 7-classify.py                                             │
│  Output: outputs/results/classification_summary.csv                │
│          outputs/results/test_predictions.csv                      │
└────────────────────────────┬───────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│  BƯỚC 8: Evaluation — Đánh giá & Trực quan hóa                    │
│  Script: 8-evaluate.py                                             │
│  Output: outputs/figures/*.png, outputs/results/roi_importance.csv │
└────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Cấu Trúc Thư Mục Dự Án

```
project_root/
│
├── configs/
│   └── default.yaml                    ← File cấu hình trung tâm
│
├── data/
│   ├── raw/                            ← Dữ liệu thô sau Bước 1
│   │   └── sub-*/
│   │       ├── sub-*_PET.nii.gz
│   │       └── sub-*_MRI.nii.gz
│   │
│   ├── processed/                      ← Dữ liệu đã xử lý (Bước 2–6e)
│   │   └── sub-*/
│   │       ├── sub-*_MRI_preprocessed.nii.gz    ← Bước 2
│   │       ├── sub-*_PET_preprocessed.nii.gz    ← Bước 2
│   │       ├── sub-*_atlas_native.nii.gz        ← Bước 5 (atlas đã warp)
│   │       ├── transforms/                       ← Bước 5 (ANTs transforms)
│   │       ├── sub-*_PET_roi_voxels.pkl         ← Bước 5
│   │       ├── sub-*_MRI_roi_voxels.pkl         ← Bước 5b
│   │       ├── sub-*_A_pet.npy                  ← Bước 6
│   │       ├── sub-*_A_mri.npy                  ← Bước 6b
│   │       ├── sub-*_node_features.npy          ← Bước 6c
│   │       ├── sub-*_A_fused.npy                ← Bước 6d
│   │       ├── sub-*_A_pet_heatmap.png          ← QC Bước 6
│   │       ├── sub-*_A_mri_heatmap.png          ← QC Bước 6b
│   │       └── sub-*_A_fused_heatmap.png        ← QC Bước 6d
│   │
│   ├── atlas/
│   │   ├── AAL3v1_1mm.nii.gz                   ← Bước 4
│   │   └── AAL3_labels.csv                      ← Bước 4
│   │
│   ├── metadata.csv                             ← Bước 1
│   └── graph_metrics.csv                        ← Bước 6e
│
├── qc/
│   ├── pet_over_mri/                            ← Bước 3
│   │   └── sub-*_QC.png
│   └── parcellation_overlay/                    ← Bước 5
│       └── sub-*_atlas_qc.png
│
├── outputs/
│   ├── figures/                                 ← Bước 8
│   │   ├── roc_curve.png
│   │   ├── confusion_matrix.png
│   │   ├── group_adjacency_pet.png
│   │   ├── group_adjacency_mri.png
│   │   └── group_adjacency_fused.png
│   └── results/                                 ← Bước 7 + 8
│       ├── classification_summary.csv
│       ├── test_predictions.csv
│       └── roi_importance.csv
│
├── 1-restructure_adni.py
├── 2-preprocess_adni.py
├── 3-generate_qc.py
├── 4-atlas_download.py
├── 5-extract_roi_voxels.py
├── 5b-extract_mri_roi_voxels.py
├── atlas_registration.py
├── 6-build_adjacency.py
├── 6b-build_mri_adjacency.py
├── 6c-build_node_features.py
├── 6d-fuse_graphs.py
├── 6e-compute_graph_metrics.py
├── 7-classify.py
├── 7-svm_classify.py                           ← Script SVM cũ (tham khảo)
├── 8-evaluate.py
├── configs/default.yaml
└── requirements.txt
```

---

## ⚙️ File Cấu Hình: `configs/default.yaml`

Toàn bộ pipeline đều đọc tham số từ file cấu hình duy nhất này. Dưới đây là giải thích từng tham số:

```yaml
data:
  raw_dir: data/raw                          # Thư mục chứa dữ liệu thô sau restructure
  processed_dir: data/processed              # Thư mục chứa dữ liệu đã xử lý
  atlas_nii: data/atlas/AAL3v1_1mm.nii.gz    # File NIfTI atlas AAL3
  atlas_labels: data/atlas/AAL3_labels.csv   # Bảng tên 116 ROI
  metadata: data/metadata.csv               # Bảng thông tin bệnh nhân
  graph_metrics_csv: data/graph_metrics.csv  # Kết quả graph metrics

restructure:
  num_workers: 4                             # Số luồng chuyển đổi song song

preprocessing:
  pet_normalize: mean_brain                  # Chuẩn hóa PET: chia cho mean uptake toàn não
  clip_percentile: [0.5, 99.5]               # Cắt giá trị ngoại lai ở percentile 0.5 và 99.5

roi_extraction:
  min_voxels: 10                             # Số voxel tối thiểu mỗi ROI (dưới ngưỡng = padding zeros)
  filter_positive: true                      # Chỉ giữ voxel > 0 cho PET (không áp dụng cho MRI)

registration:
  type: SyN                                  # Loại đăng ký: SyN (chính xác, ~5-10 phút) hoặc Affine (nhanh, ~1 phút)

graph_pet:
  method: wasserstein                        # Phương pháp đo khoảng cách cho PET
  sigma: auto                                # Gaussian kernel sigma: "auto" = mean khoảng cách pairwise

graph_mri:
  method: jensenshannon                      # Phương pháp đo tương tự cho MRI
  bins: 64                                   # Số bin histogram
  epsilon: 1.0e-8                            # Smoothing factor cho histogram

fusion:
  alpha: 0.5                                 # Trọng số mặc định cho fusion: 0.5 = cân bằng MRI/PET

graph_metrics:
  threshold_percentile: 70                   # Giữ top 30% cạnh mạnh nhất (ngưỡng tại percentile 70)

classification:
  test_size: 0.15                            # 15% dữ liệu dành cho test set
  n_folds: 5                                 # 5-fold cross-validation
  seed: 42                                   # Random seed cho tái lập kết quả
  alpha_search: [0.3, 0.5, 0.7]             # Các giá trị alpha cần thử khi grid search
  classifiers: [svm, xgboost]                # Các bộ phân loại sử dụng
  feature_set: all                           # Loại feature: graph_metrics | node_stats | flat_adj | all
```

---

## 🔬 CHI TIẾT TỪNG BƯỚC

---

### BƯỚC 1: Restructure Dữ Liệu Thô

| | |
|:---|:---|
| **Script** | `1-restructure_adni.py` |
| **Mục đích** | Chuyển đổi dữ liệu ADNI thô (DICOM + NIfTI rời rạc) thành cấu trúc thư mục chuẩn, theo từng bệnh nhân |
| **Thời gian** | ~5–15 phút (tùy số lượng subjects) |

#### Kiến thức nền

**ADNI (Alzheimer's Disease Neuroimaging Initiative)** là cơ sở dữ liệu nghiên cứu lớn nhất thế giới về hình ảnh não AD. Khi tải dữ liệu từ ADNI, các file được tổ chức theo cách phức tạp (theo ngày chụp, protocol, image ID...), không theo bệnh nhân.

**DICOM** là định dạng hình ảnh y khoa chuẩn — mỗi lát cắt não là một file riêng. Ảnh PET thường là DICOM.

**NIfTI (.nii.gz)** là định dạng hình ảnh 3D — cả khối não 3D trong một file duy nhất. Tiện lợi hơn DICOM cho phân tích.

#### Bước 1 làm gì?

1. **Đọc CSV metadata (`data_balanced.csv`):** File này chứa thông tin về mỗi bệnh nhân gồm: Subject ID, nhóm bệnh (AD/CN/MCI), tuổi, giới tính, modality (PET/MRI), Image Data ID, định dạng file (DCM/NIfTI).

2. **Xây dựng index folder:** Duyệt qua toàn bộ thư mục `data/` để tìm tất cả folder có tên bắt đầu bằng `I` (Image ID từ ADNI, ví dụ `I123456`), lập bảng ánh xạ `Image ID → đường dẫn folder`.

3. **Xử lý từng bệnh nhân:**
   - **PET (DICOM → NIfTI):** Dùng thư viện `dicom2nifti` để chuyển đổi folder DICOM thành file `.nii.gz` duy nhất
   - **MRI (NIfTI → Copy):** Copy trực tiếp file NIfTI có sẵn
   - Tạo thư mục riêng cho mỗi bệnh nhân: `data/raw/sub-{ID}/`

4. **Tạo metadata.csv:** Trích xuất thông tin (subject_id, label AD/CN, tuổi, giới tính) và lưu vào `data/metadata.csv`

#### Đầu vào (Input)

| File | Mô tả |
|:---|:---|
| `data_balanced.csv` | Bảng CSV từ ADNI chứa thông tin subjects |
| `data/` hoặc `data/ADNI/` | Thư mục chứa dữ liệu thô ADNI đã tải |

#### Đầu ra (Output)

| File | Mô tả |
|:---|:---|
| `data/raw/sub-{ID}/sub-{ID}_PET.nii.gz` | Ảnh PET 3D dạng NIfTI cho mỗi bệnh nhân |
| `data/raw/sub-{ID}/sub-{ID}_MRI.nii.gz` | Ảnh MRI T1 3D dạng NIfTI cho mỗi bệnh nhân |
| `data/metadata.csv` | Bảng thông tin: subject_id, label, age, sex, site |

#### Lưu ý kỹ thuật

- Hỗ trợ xử lý **đa luồng** (multi-threaded) với số workers cấu hình trong `default.yaml`
- Tự động bỏ qua subjects đã xử lý (idempotent)
- Chỉ xử lý PET dạng DICOM và MRI dạng NIfTI (bỏ qua các định dạng khác)
- Chỉ giữ subjects thuộc nhóm AD hoặc CN

---

### BƯỚC 2: Tiền Xử Lý Hình Ảnh (Preprocessing)

| | |
|:---|:---|
| **Script** | `2-preprocess_adni.py` |
| **Mục đích** | Chuẩn hóa và làm sạch ảnh MRI + PET để chuẩn bị cho phân tích |
| **Thời gian** | ~3–10 phút/bệnh nhân (phụ thuộc GPU/CPU) |
| **Phụ thuộc** | ANTsPy, HD-BET, PyTorch |

#### Kiến thức nền

Ảnh MRI và PET thô không thể dùng trực tiếp cho phân tích vì nhiều lý do:
- MRI bị méo cường độ do từ trường không đều (bias field)
- Ảnh chứa hộp sọ, da, mỡ — không phải mô não
- PET và MRI chụp ở thời điểm khác nhau → vị trí não khác nhau
- Cường độ PET khác nhau giữa các lần chụp (do liều FDG khác nhau)

#### Bước 2 làm gì? (5 bước con cho mỗi bệnh nhân)

##### Bước 2.1: N4 Bias Field Correction (Hiệu chỉnh từ trường)

**Vấn đề:** Cuộn dây thu sóng MRI tạo ra từ trường không hoàn toàn đồng nhất → cùng một loại mô nhưng ở các vị trí khác nhau có cường độ khác nhau. Ví dụ, chất xám ở giữa não có thể sáng hơn chất xám ở rìa não.

**Giải pháp:** Thuật toán **N4ITK** (cải tiến từ N3) ước lượng bias field (trường nhiễu) dạng đa thức trơn, rồi chia ảnh cho bias field đó để triệt tiêu hiệu ứng.

**Công cụ:** `ants.n4_bias_field_correction(mri_image)`

**Kết quả:** Ảnh MRI có cường độ đồng nhất hơn trong cùng loại mô.

##### Bước 2.2: Skull Stripping (Loại bỏ hộp sọ)

**Vấn đề:** Ảnh MRI ban đầu chứa cả hộp sọ (bone), da đầu (scalp), mỡ, và cơ — các mô không phải não. Nếu không loại bỏ, chúng sẽ ảnh hưởng đến kết quả phân tích.

**Giải pháp:** Dùng **HD-BET (High-Definition Brain Extraction Tool)** — một deep learning model (dựa trên U-Net) được huấn luyện để tách não ra khỏi hộp sọ. HD-BET hoạt động tốt trên nhiều loại ảnh MRI và PET.

**Công cụ:** `hd-bet -i input.nii.gz -o brain.nii.gz`

**Kết quả:**
- `mri_brain`: Ảnh MRI chỉ chứa mô não (vùng ngoài não = 0)
- `mri_mask`: Mặt nạ nhị phân (binary mask) — 1 = vùng não, 0 = vùng ngoài não

**Lưu ý:** HD-BET ưu tiên chạy trên GPU (nhanh hơn ~10x). Nếu GPU không khả dụng, tự động fallback về CPU.

##### Bước 2.3: PET → MRI Co-registration (Đồng đăng ký)

**Vấn đề:** Ảnh PET và MRI được chụp ở các thời điểm khác nhau, với máy quét khác nhau. Dù cùng một người, vị trí đầu trong máy khác nhau → não ở các tọa độ khác nhau trong hai ảnh. Cần "xếp chồng" (align) chúng lên nhau.

**Giải pháp:** Dùng **Affine registration** (phép biến đổi affine — xoay, dịch, co giãn, nghiêng) để đưa PET về cùng không gian tọa độ với MRI. Affine registration đủ chính xác vì PET và MRI cùng một bệnh nhân → hình dạng não giống nhau, chỉ khác vị trí/hướng.

**Công cụ:** `ants.registration(fixed=mri, moving=pet, type_of_transform="AffineFast")`

- `fixed = MRI` (ảnh tham chiếu, giữ nguyên)
- `moving = PET` (ảnh cần di chuyển để khớp với MRI)

**Kết quả:** Ảnh PET đã được xoay/dịch/co giãn để khớp hoàn hảo với ảnh MRI.

##### Bước 2.4: PET Brain Masking (Áp dụng mặt nạ não)

**Mục đích:** Áp dụng brain mask từ MRI (Bước 2.2) lên ảnh PET đã co-registered (Bước 2.3) để loại bỏ tín hiệu PET ngoài não.

**Cách làm:** Nhân (element-wise multiplication) ảnh PET với brain mask:
```
PET_brain = PET_coregistered × brain_mask
```
Vùng ngoài não (mask = 0) → PET = 0. Vùng trong não (mask = 1) → PET giữ nguyên.

##### Bước 2.5: PET Normalization & Intensity Clipping

**Chuẩn hóa PET (Mean Brain Normalization):**

**Vấn đề:** Liều FDG tiêm cho mỗi bệnh nhân khác nhau, cân nặng/BMI khác nhau → giá trị tuyệt đối PET khác nhau. Không thể so sánh trực tiếp giữa các bệnh nhân.

**Giải pháp:** Chia mỗi voxel PET cho **giá trị trung bình** toàn bộ voxel não (chỉ tính voxel > 0 trong brain mask):
```
PET_normalized = PET / mean(PET[brain_mask > 0 & PET > 0])
```
Sau chuẩn hóa, giá trị PET thể hiện **tỷ lệ tương đối** so với toàn não: vùng > 1.0 = chuyển hóa cao hơn trung bình, vùng < 1.0 = chuyển hóa thấp hơn trung bình.

**Cắt giá trị ngoại lai (Percentile Clipping):**

Cắt giá trị cực đoan ở percentile 0.5 và 99.5 để loại bỏ outlier (artifact).

#### Đầu vào (Input)

| File | Mô tả |
|:---|:---|
| `data/raw/sub-*/sub-*_MRI.nii.gz` | Ảnh MRI thô |
| `data/raw/sub-*/sub-*_PET.nii.gz` | Ảnh PET thô |

#### Đầu ra (Output)

| File | Mô tả |
|:---|:---|
| `data/processed/sub-*/sub-*_MRI_preprocessed.nii.gz` | Ảnh MRI đã: N4 corrected + skull stripped |
| `data/processed/sub-*/sub-*_PET_preprocessed.nii.gz` | Ảnh PET đã: co-registered + masked + normalized + clipped |

---

### BƯỚC 3: Kiểm Soát Chất Lượng (Quality Control — QC)

| | |
|:---|:---|
| **Script** | `3-generate_qc.py` |
| **Mục đích** | Tạo ảnh xác minh trực quan để kiểm tra kết quả preprocessing |
| **Thời gian** | ~5–10 giây/bệnh nhân |

#### Bước 3 làm gì?

Tạo ảnh QC overlay: **PET chồng lên MRI** trong 3 mặt cắt orthogonal (sagittal, coronal, axial) để kiểm tra:
- MRI skull stripping có tốt không (có mất mô não hay giữ lại hộp sọ?)
- PET co-registration có chính xác không (PET hot spot có trùng với vùng não trên MRI?)

Dùng thư viện `nilearn.plotting.plot_stat_map` với colormap "hot" (PET) phủ lên nền MRI xám.

#### Đầu vào (Input)

| File | Mô tả |
|:---|:---|
| `data/processed/sub-*/sub-*_MRI_preprocessed.nii.gz` | MRI đã xử lý |
| `data/processed/sub-*/sub-*_PET_preprocessed.nii.gz` | PET đã xử lý |

#### Đầu ra (Output)

| File | Mô tả |
|:---|:---|
| `qc/pet_over_mri/sub-*_QC.png` | Ảnh PNG overlay PET trên MRI |

#### Cách đánh giá QC

Người dùng cần **kiểm tra bằng mắt** từng ảnh QC:
- ✅ **Tốt:** PET hotspot (vùng sáng) nằm đúng trong vùng chất xám trên MRI
- ❌ **Xấu — Skull stripping lỗi:** Thấy hộp sọ/da đầu trong ảnh MRI, hoặc mất mô não
- ❌ **Xấu — Co-registration lỗi:** PET lệch khỏi MRI, hotspot nằm ngoài não

Nếu phát hiện lỗi → cần loại bỏ bệnh nhân đó hoặc điều chỉnh tham số preprocessing.

---

### BƯỚC 4: Tải Atlas AAL3

| | |
|:---|:---|
| **Script** | `4-atlas_download.py` |
| **Mục đích** | Tải bản đồ phân vùng não AAL3 (116 ROI) từ internet |
| **Thời gian** | ~10–30 giây (tải từ mạng) |

#### Bước 4 làm gì?

1. **Ưu tiên tải qua `nilearn`:** Thư viện `nilearn` có hàm `datasets.fetch_atlas_aal(version="SPM12")` tự động tải atlas AAL chuẩn từ server nghiên cứu.

2. **Fallback:** Nếu nilearn thất bại (do lỗi mạng), tải trực tiếp file `.tar.gz` từ website GIN (https://www.gin.cnrs.fr/AAL_files/aal_for_SPM12.tar.gz) rồi giải nén.

3. **Tạo 2 file:**
   - **`AAL3v1_1mm.nii.gz`:** File NIfTI 3D — mỗi voxel chứa giá trị integer là ROI ID (1–116). Voxel ngoài não = 0.
   - **`AAL3_labels.csv`:** Bảng ánh xạ `roi_id → roi_name`, ví dụ: `2001 → Precentral_L` (hồi trước trung tâm trái).

4. **Xác minh:** Đếm số ROI unique (phải = 116), in kích thước ảnh.

#### Đầu vào (Input)

Không cần input từ pipeline — tải từ internet.

#### Đầu ra (Output)

| File | Mô tả |
|:---|:---|
| `data/atlas/AAL3v1_1mm.nii.gz` | Atlas AAL3 dạng NIfTI, 1mm resolution, không gian MNI152 |
| `data/atlas/AAL3_labels.csv` | Bảng tên 116 ROI: roi_id, roi_name |

#### Một số ROI quan trọng trong AD

| ROI ID | Tên | Vùng giải phẫu | Ý nghĩa trong AD |
|:---|:---|:---|:---|
| 37–38 | Hippocampus_L/R | Hippocampus | Teo sớm nhất — liên quan trí nhớ |
| 41–42 | Amygdala_L/R | Hạch hạnh nhân | Xử lý cảm xúc, teo sớm |
| 35–36 | ParaHippocampal_L/R | Vùng cạnh hippocampus | Hỗ trợ trí nhớ, teo sớm |
| 65–66 | Angular_L/R | Hồi góc | Hub mạng lưới DMN |
| 67–68 | Precuneus_L/R | Precuneus | Hub chính DMN, hypometabolism sớm |
| 35–36 | Cingulum_Post_L/R | Vỏ đai sau | Hypometabolism mạnh nhất trong AD |
| 81–82 | Temporal_Inf_L/R | Thùy thái dương dưới | Teo chất xám |

---

### BƯỚC 5: Đăng Ký Atlas + Trích Xuất Voxel PET theo ROI

| | |
|:---|:---|
| **Scripts** | `atlas_registration.py` (module chung) + `5-extract_roi_voxels.py` |
| **Mục đích** | Đưa atlas AAL3 từ không gian MNI về không gian não cá nhân, rồi trích xuất giá trị PET cho mỗi vùng não |
| **Thời gian** | ~5–10 phút/bệnh nhân (SyN), ~1 phút (Affine) |
| **Phụ thuộc** | ANTsPy, nibabel, nilearn |

#### Kiến thức nền

**Vấn đề không gian tọa độ (Coordinate Space Problem):**

Atlas AAL3 được tạo trong **không gian MNI152** — một não "trung bình" chuẩn. Nhưng mỗi bệnh nhân có não riêng (kích thước, hình dạng, nếp gấp khác nhau) — gọi là **không gian native**. 

Ảnh PET và MRI đã preprocessed nằm trong không gian native → không thể áp atlas MNI trực tiếp vì vị trí các vùng não sẽ lệch.

**Hai cách tiếp cận:**
1. Đưa ảnh bệnh nhân → MNI (normalization): Biến dạng ảnh bệnh nhân → mất thông tin
2. ✅ **Đưa atlas MNI → native (inverse approach):** Giữ nguyên ảnh bệnh nhân, chỉ biến dạng atlas → tốt hơn cho phân tích cá nhân

**Dự án này chọn cách 2**: Warp atlas từ MNI → native.

#### Bước 5 làm gì?

##### 5.1: ANTs Registration — MNI Template → Subject Native

**Module `atlas_registration.py`** thực hiện:

1. **Load ảnh:**
   - `fixed = subject MRI` (ảnh MRI preprocessed, không gian native)
   - `moving = MNI152 template` (template não chuẩn từ ANTsPy)

2. **Registration (Đăng ký hình ảnh):**
   Dùng `ants.registration()` để tìm phép biến đổi đưa MNI template khớp với MRI cá nhân:
   
   - **SyN (Symmetric Normalization):** Đăng ký phi tuyến tính — cho phép biến dạng cục bộ (nếp gấp não, khe, rãnh khác nhau). Chính xác nhất nhưng chậm (~5-10 phút/subject).
   - **Affine:** Chỉ xoay, dịch, co giãn — nhanh (~1 phút) nhưng kém chính xác hơn cho não teo.

3. **Apply transforms lên atlas:**
   Áp dụng phép biến đổi đã tính (forward transforms từ MNI → native) lên atlas AAL3:
   ```python
   atlas_native = ants.apply_transforms(
       fixed=subject_mri,
       moving=atlas_aal3,
       transformlist=forward_transforms,
       interpolator="nearestNeighbor"  # Giữ nguyên số integer ROI ID
   )
   ```
   
   **Nearest Neighbor interpolation** là bắt buộc vì atlas chứa integer label (1–116). Nếu dùng linear interpolation, sẽ tạo ra giá trị trung gian vô nghĩa (ví dụ 45.7 — không phải ROI nào cả).

4. **Chuyển đổi hệ tọa độ LPS → RAS:**
   ANTs sử dụng hệ tọa độ **LPS** (Left-Posterior-Superior), nhưng NIfTI dùng **RAS** (Right-Anterior-Superior). Cần đảo dấu 2 trục đầu tiên khi lưu file.

5. **Cache:** Lưu atlas đã warp (`sub-*_atlas_native.nii.gz`) và transforms (`transforms/`) để tái sử dụng cho Bước 5b.

##### 5.2: Resample Atlas → PET Grid

Dù atlas đã ở không gian native, lưới voxel (voxel grid) của atlas và PET có thể khác nhau (MRI 1mm vs PET 2-4mm). Dùng `nilearn.image.resample_to_img` với nearest-neighbor để đưa atlas về đúng grid voxel của PET.

##### 5.3: Trích xuất voxel PET theo ROI

Với mỗi ROI (1–116), trích xuất tất cả giá trị voxel PET nằm trong ROI đó:
```python
for roi_id in [1, 2, ..., 116]:
    vals = pet_data[atlas_data == roi_id]  # Array 1D chứa giá trị PET của tất cả voxel trong ROI
    roi_voxels[roi_id] = vals
```

**Lọc:**
- Chỉ giữ giá trị > 0 cho PET (`filter_positive: true`) — loại bỏ artifact âm
- ROI có ít hơn `min_voxels` (10) voxel → padding bằng zeros
- Loại bỏ NaN/Inf

##### 5.4: QC Parcellation Overlay

Tạo ảnh QC hiển thị atlas đã warp phủ lên MRI để xác minh parcellation đúng vị trí.

#### Đầu vào (Input)

| File | Mô tả |
|:---|:---|
| `data/processed/sub-*/sub-*_MRI_preprocessed.nii.gz` | MRI preprocessed (reference cho registration) |
| `data/processed/sub-*/sub-*_PET_preprocessed.nii.gz` | PET preprocessed (nguồn voxel) |
| `data/atlas/AAL3v1_1mm.nii.gz` | Atlas AAL3 trong không gian MNI |
| `data/metadata.csv` | Danh sách subjects |

#### Đầu ra (Output)

| File | Mô tả |
|:---|:---|
| `data/processed/sub-*/sub-*_atlas_native.nii.gz` | Atlas AAL3 đã warp về không gian native |
| `data/processed/sub-*/transforms/mni_to_native_*.mat/.nii.gz` | ANTs transform files (cached) |
| `data/processed/sub-*/sub-*_PET_roi_voxels.pkl` | Dictionary Python: `{roi_id: array of PET voxel values}` |
| `qc/parcellation_overlay/sub-*_atlas_qc.png` | Ảnh QC atlas overlay |

---

### BƯỚC 5b: Trích Xuất Voxel MRI theo ROI

| | |
|:---|:---|
| **Script** | `5b-extract_mri_roi_voxels.py` |
| **Mục đích** | Trích xuất giá trị voxel MRI T1 cho mỗi ROI, tái sử dụng atlas đã warp từ Bước 5 |
| **Thời gian** | ~10–30 giây/bệnh nhân (cache hit — không cần re-registration) |

#### Khác biệt so với Bước 5

| | Bước 5 (PET) | Bước 5b (MRI) |
|:---|:---|:---|
| **Input image** | `*_PET_preprocessed.nii.gz` | `*_MRI_preprocessed.nii.gz` |
| **Filter positive** | ✅ Có — loại voxel ≤ 0 (PET artifact) | ❌ Không — MRI T1 có giá trị gần 0 hợp lệ (vùng GM tối sau N4) |
| **Registration** | Chạy đầy đủ (SyN/Affine) | Tái sử dụng cache — **tức thì** |
| **Output** | `*_PET_roi_voxels.pkl` | `*_MRI_roi_voxels.pkl` |

**Tại sao không filter positive cho MRI?** Sau N4 bias correction, một số vùng chất xám (gray matter) có cường độ T1 rất thấp, gần 0 — nhưng đây là giá trị hợp lệ, phản ánh đặc tính mô thực tế. Chỉ lọc NaN/Inf, không lọc theo dấu.

#### Đầu vào (Input)

| File | Mô tả |
|:---|:---|
| `data/processed/sub-*/sub-*_MRI_preprocessed.nii.gz` | MRI preprocessed |
| `data/processed/sub-*/sub-*_atlas_native.nii.gz` | Atlas đã warp (từ Bước 5) |
| `data/atlas/AAL3v1_1mm.nii.gz` | Atlas gốc (fallback nếu chưa warp) |

#### Đầu ra (Output)

| File | Mô tả |
|:---|:---|
| `data/processed/sub-*/sub-*_MRI_roi_voxels.pkl` | Dictionary: `{roi_id: array of MRI voxel values}` |

---

### BƯỚC 6: Xây Dựng Đồ Thị PET (Ma Trận Kề — Wasserstein Distance)

| | |
|:---|:---|
| **Script** | `6-build_adjacency.py` |
| **Mục đích** | Xây dựng đồ thị mạng lưới chuyển hóa PET cho mỗi bệnh nhân |
| **Thời gian** | ~30 giây/bệnh nhân |

#### Kiến thức nền — Wasserstein Distance

**Wasserstein distance** (còn gọi là **Earth Mover's Distance — EMD**) đo "chi phí" để biến đổi một phân bố xác suất thành phân bố khác. Hình tượng: nếu mỗi phân bố là một đống đất, Wasserstein distance là lượng công (mass × khoảng cách) tối thiểu cần di chuyển đất từ đống này thành đống kia.

**Tại sao chọn Wasserstein cho PET?**
- PET voxel values là giá trị liên tục (continuous) — Wasserstein xử lý trực tiếp trên giá trị, không cần histogram hóa
- Wasserstein nhạy cảm với cả hình dạng và vị trí (shift) của phân bố — quan trọng vì hypometabolism AD dịch chuyển cả phân bố sang trái
- Không yêu cầu phân bố dương chuẩn hóa (normalization)

#### Bước 6 làm gì?

1. **Tính ma trận khoảng cách D:**
   Với mỗi cặp ROI (i, j), tính Wasserstein distance giữa phân bố voxel PET:
   ```
   D[i,j] = wasserstein_distance(PET_voxels_ROI_i, PET_voxels_ROI_j)
   ```
   Ma trận D có kích thước `116 × 116`, đối xứng, đường chéo = 0.

2. **Chuyển khoảng cách → tương tự (Gaussian kernel):**
   Khoảng cách nhỏ → tương tự cao, khoảng cách lớn → tương tự thấp:
   ```
   A[i,j] = exp(-D[i,j]² / (2σ²))
   ```
   Trong đó σ (sigma) được tính tự động bằng **giá trị trung bình** của tất cả khoảng cách hữu hạn (`sigma: auto`). Gaussian kernel đảm bảo giá trị similarity nằm trong [0, 1].

3. **Lưu & QC:**
   - Lưu ma trận kề `A_pet.npy`
   - Tạo heatmap trực quan (`A_pet_heatmap.png`)

#### Đầu vào (Input)

| File | Mô tả |
|:---|:---|
| `data/processed/sub-*/sub-*_PET_roi_voxels.pkl` | Phân bố voxel PET mỗi ROI |
| `data/atlas/AAL3_labels.csv` | Danh sách 116 ROI |

#### Đầu ra (Output)

| File | Mô tả |
|:---|:---|
| `data/processed/sub-*/sub-*_A_pet.npy` | Ma trận kề PET `116×116` (Wasserstein similarity) |
| `data/processed/sub-*/sub-*_A_pet_heatmap.png` | Heatmap trực quan |

#### Ý nghĩa kết quả

- `A_pet[i,j] ≈ 1.0`: ROI i và j có phân bố chuyển hóa PET rất giống nhau → "kết nối chuyển hóa" mạnh
- `A_pet[i,j] ≈ 0.0`: ROI i và j có phân bố chuyển hóa rất khác nhau
- Trong bệnh nhân AD, các vùng bị hypometabolism sẽ có pattern kết nối **khác biệt rõ rệt** so với người khỏe mạnh

---

### BƯỚC 6b: Xây Dựng Đồ Thị MRI (Ma Trận Kề — Jensen-Shannon Divergence)

| | |
|:---|:---|
| **Script** | `6b-build_mri_adjacency.py` |
| **Mục đích** | Xây dựng đồ thị mạng lưới cấu trúc MRI cho mỗi bệnh nhân |
| **Thời gian** | ~30 giây/bệnh nhân |

#### Kiến thức nền — Jensen-Shannon Divergence (JSD)

**Jensen-Shannon Divergence (JSD)** là phiên bản đối xứng và bounded của Kullback-Leibler Divergence (KL), đo sự khác biệt giữa hai phân bố xác suất.

**Công thức:**
```
JSD(P || Q) = ½ KL(P || M) + ½ KL(Q || M),   trong đó M = ½(P + Q)
```

JSD nằm trong khoảng [0, 1] (khi dùng log₂), với:
- JSD = 0: Hai phân bố giống hệt nhau
- JSD = 1: Hai phân bố hoàn toàn khác nhau

**Tại sao dùng JSD cho MRI (thay vì Wasserstein)?**
- MRI cần so sánh **hình dạng phân bố** (distribution shape) hơn là vị trí — vì cường độ T1 tuyệt đối ít ý nghĩa
- JSD yêu cầu histogram → phù hợp khi muốn so sánh "dạng" (bimodal/unimodal, narrow/wide) của phân bố cường độ mô
- JSD bounded [0,1] → không cần Gaussian kernel, trực tiếp chuyển thành similarity: `s = 1 - JSD`

#### Bước 6b làm gì?

1. **Tính global bin range:**
   Tìm min/max của **tất cả** voxel MRI trên mọi ROI → đảm bảo histogram của các ROI được so sánh trên cùng thang đo (aligned bins).

2. **Tạo histogram cho mỗi ROI:**
   ```python
   hist[roi] = histogram(mri_voxels[roi], bins=64, range=(global_min, global_max))
   hist[roi] = (hist[roi] + epsilon) / sum(hist[roi])  # Chuẩn hóa + Laplace smoothing
   ```
   `epsilon = 1e-8` tránh bin = 0 → phòng chia cho 0 khi tính KL Divergence.

3. **Tính JSD similarity:**
   ```
   A_mri[i,j] = 1 - JSD(hist_ROI_i, hist_ROI_j)
   ```
   - Hai ROI có phân bố cường độ MRI giống nhau → JSD thấp → similarity cao
   - Đường chéo = 1.0 (ROI giống chính nó)

4. **Lưu & QC:** Tương tự Bước 6.

#### Đầu vào (Input)

| File | Mô tả |
|:---|:---|
| `data/processed/sub-*/sub-*_MRI_roi_voxels.pkl` | Phân bố voxel MRI mỗi ROI |

#### Đầu ra (Output)

| File | Mô tả |
|:---|:---|
| `data/processed/sub-*/sub-*_A_mri.npy` | Ma trận kề MRI `116×116` (JSD similarity) |
| `data/processed/sub-*/sub-*_A_mri_heatmap.png` | Heatmap trực quan |

---

### BƯỚC 6c: Trích Xuất Đặc Trưng Nút (Node Features)

| | |
|:---|:---|
| **Script** | `6c-build_node_features.py` |
| **Mục đích** | Tính toán thống kê mô tả cho mỗi ROI, kết hợp cả MRI và PET |
| **Thời gian** | ~10 giây/bệnh nhân |

#### Bước 6c làm gì?

Với mỗi ROI, tính **6 thống kê mô tả** cho MRI và **6 thống kê mô tả** cho PET:

| Chỉ số | Ý nghĩa | Liên quan AD |
|:---|:---|:---|
| **Mean** | Giá trị trung bình | PET mean thấp = hypometabolism; MRI mean thấp = mất mô |
| **Std** | Độ lệch chuẩn | Std cao = mô không đồng nhất (mixed healthy/atrophied tissue) |
| **Percentile 10** | Giá trị tại 10% thấp nhất | Phát hiện phần "xấu nhất" của ROI |
| **Percentile 50 (Median)** | Giá trị trung vị | Robust hơn mean, ít bị ảnh hưởng outlier |
| **Percentile 90** | Giá trị tại 90% cao nhất | Phát hiện phần "tốt nhất" của ROI |
| **Count** | Số voxel trong ROI | ROI nhỏ hơn có thể do teo não |

**Ma trận node features:** `[116 ROI × 12 features]` = 6 MRI stats + 6 PET stats cho mỗi ROI.

#### Đầu vào (Input)

| File | Mô tả |
|:---|:---|
| `data/processed/sub-*/sub-*_MRI_roi_voxels.pkl` | Voxel MRI mỗi ROI |
| `data/processed/sub-*/sub-*_PET_roi_voxels.pkl` | Voxel PET mỗi ROI |

#### Đầu ra (Output)

| File | Mô tả |
|:---|:---|
| `data/processed/sub-*/sub-*_node_features.npy` | Ma trận `116 × 12` (6 MRI stats + 6 PET stats) |

---

### BƯỚC 6d: Fusion — Kết Hợp Đồ Thị PET + MRI

| | |
|:---|:---|
| **Script** | `6d-fuse_graphs.py` |
| **Mục đích** | Kết hợp thông tin chuyển hóa (PET) và cấu trúc (MRI) thành một đồ thị thống nhất |
| **Thời gian** | ~5 giây/bệnh nhân |

#### Kiến thức nền — Graph Fusion

Mỗi bệnh nhân giờ có hai đồ thị:
- `A_pet`: Mạng lưới chuyển hóa — phản ánh **chức năng**
- `A_mri`: Mạng lưới cấu trúc — phản ánh **hình thái**

**Fusion** kết hợp chúng thành một đồ thị duy nhất chứa **cả hai loại thông tin:**

```
A_fused = α × A_mri + (1 - α) × A_pet
```

Trong đó `α` (alpha) là trọng số điều khiển tỷ lệ đóng góp:
- `α = 0.0`: Chỉ dùng PET (100% chuyển hóa)
- `α = 0.5`: Cân bằng 50/50
- `α = 1.0`: Chỉ dùng MRI (100% cấu trúc)
- `α = 0.3`: 30% MRI + 70% PET (PET chiếm ưu thế)
- `α = 0.7`: 70% MRI + 30% PET (MRI chiếm ưu thế)

**Kết quả thực nghiệm cho thấy `α = 0.3` (70% MRI + 30% PET) cho hiệu quả tốt nhất** — nghĩa là thông tin cấu trúc MRI đóng vai trò quan trọng hơn trong phân loại AD, nhưng PET bổ sung thông tin chuyển hóa giá trị.

#### Đầu vào (Input)

| File | Mô tả |
|:---|:---|
| `data/processed/sub-*/sub-*_A_mri.npy` | Ma trận kề MRI |
| `data/processed/sub-*/sub-*_A_pet.npy` | Ma trận kề PET |

#### Đầu ra (Output)

| File | Mô tả |
|:---|:---|
| `data/processed/sub-*/sub-*_A_fused.npy` | Ma trận kề fused `116×116` |
| `data/processed/sub-*/sub-*_A_fused_heatmap.png` | Heatmap trực quan |

---

### BƯỚC 6e: Tính Toán Graph Metrics — Đặc Trưng Topology Đồ Thị

| | |
|:---|:---|
| **Script** | `6e-compute_graph_metrics.py` |
| **Mục đích** | Trích xuất đặc trưng cấu trúc mạng lưới (topology) từ đồ thị não |
| **Thời gian** | ~1–2 phút cho toàn bộ subjects |
| **Phụ thuộc** | NetworkX |

#### Kiến thức nền — Lý thuyết đồ thị trong thần kinh học

Não được mô hình hóa như một mạng lưới phức hợp (complex network). Các chỉ số topology cho biết **cách tổ chức** của mạng lưới — liệu nó hiệu quả, tích hợp tốt, hay bị phân mảnh.

#### Bước 6e làm gì?

1. **Proportional Thresholding:**
   Ma trận kề dày đặc (dense) — mọi cặp ROI đều có edge. Cần loại bỏ edge yếu để giữ lại mạng lưới có ý nghĩa. Dùng **percentile thresholding** tại 70% — chỉ giữ **top 30% edge mạnh nhất**.

2. **Chuyển đổi sang đồ thị NetworkX:**
   `nx.from_numpy_array(A_thresholded)` → đối tượng đồ thị

3. **Tính 5 metrics cho mỗi đồ thị (A_mri, A_pet, A_fused):**

| Metric | Tên tiếng Việt | Công thức/Ý nghĩa | Liên quan AD |
|:---|:---|:---|:---|
| **Degree** | Bậc trung bình | Số cạnh trung bình mỗi nút | Thấp hơn ở AD → mất kết nối |
| **Clustering Coefficient** | Hệ số phân cụm | Tỷ lệ tam giác (hàng xóm của i cũng kết nối với nhau) | Cho biết mức độ "nhóm" cục bộ |
| **Path Length** | Chiều dài đường đi TB | Số bước trung bình giữa 2 nút bất kỳ | Dài hơn ở AD → truyền tin kém hiệu quả |
| **Global Efficiency** | Hiệu quả toàn cục | 1/path_length trung bình | Thấp hơn ở AD → mất tích hợp toàn não |
| **Local Efficiency** | Hiệu quả cục bộ | Hiệu quả của mạng cục bộ quanh mỗi nút | Thấp hơn ở AD → mất khả năng xử lý cục bộ |

4. **Tính cho cả 3 loại đồ thị** (MRI, PET, Fused) → tổng cộng **15 features** mỗi subject.

5. **Lưu incremental:** Ghi file CSV sau mỗi subject để chống crash.

#### Đầu vào (Input)

| File | Mô tả |
|:---|:---|
| `data/processed/sub-*/sub-*_A_mri.npy` | Ma trận kề MRI |
| `data/processed/sub-*/sub-*_A_pet.npy` | Ma trận kề PET |
| `data/processed/sub-*/sub-*_A_fused.npy` | Ma trận kề Fused |

#### Đầu ra (Output)

| File | Mô tả |
|:---|:---|
| `data/graph_metrics.csv` | CSV với mỗi hàng = 1 subject, cột gồm: subject_id, label, + 15 metrics (5 metrics × 3 graphs) |

**Cấu trúc cột `graph_metrics.csv`:**
```
subject_id, label, mri_degree, mri_clustering, mri_path_length, mri_global_eff, mri_local_eff,
                   pet_degree, pet_clustering, pet_path_length, pet_global_eff, pet_local_eff,
                   fused_degree, fused_clustering, fused_path_length, fused_global_eff, fused_local_eff
```

---

### BƯỚC 7: Phân Loại AD vs CN (Classification)

| | |
|:---|:---|
| **Script** | `7-classify.py` |
| **Mục đích** | Huấn luyện mô hình machine learning để phân biệt bệnh nhân AD và người khỏe mạnh CN |
| **Thời gian** | ~5–15 phút |
| **Phụ thuộc** | scikit-learn, XGBoost |

#### Kiến thức nền — Phân loại nhị phân

**Bài toán:** Cho các đặc trưng đồ thị não của một bệnh nhân, dự đoán họ thuộc nhóm **AD (Alzheimer's Disease)** hay **CN (Cognitively Normal — người nhận thức bình thường)**.

#### Bước 7 làm gì?

##### 7.1: Chia dữ liệu

```
Toàn bộ subjects
    ├── 85% → Development set (dùng cho cross-validation + training)
    └── 15% → Holdout test set (KHÔNG ĐỤNG cho đến evaluation cuối cùng)
```

**Stratified split:** Đảm bảo tỷ lệ AD:CN giống nhau trong cả 2 tập.

##### 7.2: Xây dựng vector đặc trưng (Feature Vector)

Mỗi bệnh nhân được biểu diễn bằng một vector số, ghép nối từ nhiều nguồn:

| Thành phần | Kích thước | Nguồn |
|:---|:---|:---|
| **Graph metrics** | 15 | Từ `graph_metrics.csv` (5 metrics × 3 graphs) |
| **Node statistics** | 24 | Từ `node_features.npy`: mean + std của 12 features qua 116 ROI |
| **Flat adjacency (upper triangle)** | 6,670 | Tam giác trên của `A_fused` (116×115/2) |
| **Tổng** | **~6,709** | Kết hợp tất cả |

**Tại sao kết hợp nhiều loại feature (feature_set: "all")?**
- Graph metrics: Thông tin macro về tổ chức mạng lưới
- Node stats: Thông tin micro về đặc tính mỗi vùng
- Flat adjacency: Thông tin chi tiết về mọi kết nối
- Kết hợp cho mô hình cái nhìn đa góc độ → phân loại chính xác hơn

##### 7.3: Grid Search Alpha

Pipeline thử **3 giá trị alpha** khi tính `A_fused`:
- α = 0.3 (PET trọng số 0.3, MRI trọng số 0.7)
- α = 0.5 (cân bằng)
- α = 0.7 (PET trọng số 0.7, MRI trọng số 0.3)

Với mỗi alpha, chạy cross-validation để tìm alpha tốt nhất cho mỗi classifier.

##### 7.4: Cross-Validation (5-Fold Stratified)

Development set được chia thành 5 fold:
```
Fold 1: [──train──] [val]
Fold 2: [──train──] [val]
Fold 3: [──train──] [val]
Fold 4: [──train──] [val]
Fold 5: [──train──] [val]
```

Mỗi fold: train trên 4 phần, validate trên 1 phần. Lặp 5 lần → trung bình kết quả.

##### 7.5: Hai Bộ Phân Loại

**SVM (Support Vector Machine):**
- Kernel: RBF (Radial Basis Function)
- Pipeline: StandardScaler → SVC(probability=True)
- Ưu điểm: Tốt cho dữ liệu chiều cao (high-dimensional), ít overfitting với regularization

**XGBoost (Extreme Gradient Boosting):**
- 200 decision trees, max depth 4
- Learning rate 0.05, subsample 0.8
- Ưu điểm: Xử lý tốt dữ liệu tabular, feature interaction, robust với outlier

##### 7.6: Evaluation trên Holdout Test Set

Sau khi chọn alpha tốt nhất, train model trên toàn bộ development set → predict trên test set.

#### Đầu vào (Input)

| File | Mô tả |
|:---|:---|
| `data/metadata.csv` | Labels (AD/CN) |
| `data/graph_metrics.csv` | 15 graph metrics mỗi subject |
| `data/processed/sub-*/sub-*_node_features.npy` | Node features |
| `data/processed/sub-*/sub-*_A_mri.npy` | Ma trận kề MRI (cho fusion dynamic) |
| `data/processed/sub-*/sub-*_A_pet.npy` | Ma trận kề PET (cho fusion dynamic) |

#### Đầu ra (Output)

| File | Mô tả |
|:---|:---|
| `outputs/results/classification_summary.csv` | Bảng tóm tắt: classifier, alpha, CV AUC, test AUC, test BACC, sensitivity, specificity |
| `outputs/results/test_predictions.csv` | Dự đoán chi tiết: subject_id, y_true, y_pred, y_prob, classifier, alpha |

#### Metrics đánh giá

| Metric | Ý nghĩa | Công thức |
|:---|:---|:---|
| **AUC (Area Under ROC Curve)** | Khả năng phân biệt AD vs CN tổng thể | Diện tích dưới đường ROC |
| **BACC (Balanced Accuracy)** | Accuracy cân bằng giữa 2 lớp | (Sensitivity + Specificity) / 2 |
| **Sensitivity (Recall, True Positive Rate)** | Tỷ lệ phát hiện đúng bệnh nhân AD | TP / (TP + FN) |
| **Specificity (True Negative Rate)** | Tỷ lệ xác nhận đúng người khỏe CN | TN / (TN + FP) |

---

### BƯỚC 8: Đánh Giá & Trực Quan Hóa (Evaluation)

| | |
|:---|:---|
| **Script** | `8-evaluate.py` |
| **Mục đích** | Tạo báo cáo đánh giá toàn diện + visualization cho kết quả phân loại |
| **Thời gian** | ~1–2 phút |

#### Bước 8 làm gì?

##### 8.1: Đọc kết quả & Tính metrics

Đọc `test_predictions.csv` (từ Bước 7), tính:
- ROC AUC
- Accuracy, Balanced Accuracy
- Sensitivity, Specificity
- F1-Score

##### 8.2: ROC Curve

**ROC (Receiver Operating Characteristic) Curve** thể hiện trade-off giữa True Positive Rate (sensitivity) và False Positive Rate khi thay đổi ngưỡng phân loại.

- Đường chéo = random guess (AUC = 0.5)
- Càng gần góc trái trên = càng tốt (AUC → 1.0)

##### 8.3: Confusion Matrix

Ma trận nhầm lẫn hiển thị 4 ô: TP, FP, FN, TN — cho biết mô hình nhầm loại nào.

##### 8.4: Group Adjacency Heatmaps

Tính **ma trận kề trung bình** cho nhóm AD và nhóm CN, rồi hiển thị cạnh nhau để so sánh trực quan pattern kết nối. Tạo cho cả 3 loại đồ thị (PET, MRI, Fused).

##### 8.5: ROI Importance — Biomarker Analysis

**Phân tích biomarker quan trọng nhất:**

1. Tính ma trận kề trung bình cho nhóm AD và CN
2. Tính **chênh lệch tuyệt đối** cho mỗi cạnh: `|AD_mean[i,j] - CN_mean[i,j]|`
3. Xếp hạng top 30 cạnh có chênh lệch lớn nhất
4. Các vùng não liên quan → **biomarker tiềm năng** cho AD

**Kết quả thực nghiệm cho thấy các vùng biomarker hàng đầu:**
- **Posterior Cingulate Gyrus (Vỏ đai sau):** Kết nối thay đổi mạnh nhất — đúng với y văn (hub chính của DMN)
- **Angular Gyrus (Hồi góc):** Thay đổi cả chuyển hóa và cấu trúc
- **Precuneus:** Hub DMN, hypometabolism sớm
- **Inferior Temporal Gyrus (Hồi thái dương dưới):** Phân bố voxel khác biệt rõ

#### Đầu vào (Input)

| File | Mô tả |
|:---|:---|
| `outputs/results/test_predictions.csv` | Dự đoán trên test set |
| `data/metadata.csv` | Labels |
| `data/atlas/AAL3_labels.csv` | Tên ROI |
| `data/processed/sub-*/sub-*_A_{pet,mri,fused}.npy` | Ma trận kề tất cả subjects |

#### Đầu ra (Output)

| File | Mô tả |
|:---|:---|
| `outputs/figures/roc_curve.png` | Đường cong ROC |
| `outputs/figures/confusion_matrix.png` | Ma trận nhầm lẫn |
| `outputs/figures/group_adjacency_pet.png` | Heatmap trung bình PET: CN vs AD |
| `outputs/figures/group_adjacency_mri.png` | Heatmap trung bình MRI: CN vs AD |
| `outputs/figures/group_adjacency_fused.png` | Heatmap trung bình Fused: CN vs AD |
| `outputs/results/roi_importance.csv` | Top 30 cạnh biomarker: roi_i, roi_j, tên ROI, AD_mean, CN_mean, diff |

---

## 📈 Kết Quả Thực Nghiệm

### Cross-Validation Grid Search (trên Development Set)

| Classifier | α (PET weight) | AUC | BACC |
|:---|:---|:---|:---|
| **XGBoost** | **0.3** | **0.909** 🏆 | **0.845** |
| XGBoost | 0.5 | 0.907 | 0.831 |
| SVM | 0.3 | 0.890 | 0.801 |
| SVM | 0.5 | 0.886 | 0.810 |
| XGBoost | 0.7 | 0.887 | 0.811 |

**Nhận xét:** α = 0.3 (MRI chiếm 70%, PET chiếm 30%) cho kết quả tốt nhất → MRI cung cấp nhiều thông tin phân loại hơn, nhưng PET bổ sung giá trị.

### Holdout Test Set (XGBoost, α = 0.3)

| Metric | Score |
|:---|:---|
| **ROC AUC** | **0.878** |
| **Accuracy** | **84.2%** |
| **Balanced Accuracy** | **84.2%** |
| **Sensitivity** | **84.2%** |
| **Specificity** | **84.2%** |
| **F1-Score** | **84.2%** |

---

## 🔧 Hướng Dẫn Chạy Pipeline

### Yêu cầu hệ thống

| Thành phần | Yêu cầu |
|:---|:---|
| **Python** | ≥ 3.8 |
| **RAM** | ≥ 16 GB (SyN registration cần nhiều RAM) |
| **GPU** | Khuyến khích (cho HD-BET), không bắt buộc |
| **Disk** | ~50 GB cho dữ liệu ADNI |

### Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### Chạy tuần tự

```bash
# Giai đoạn 1: Dữ liệu
python 1-restructure_adni.py
python 2-preprocess_adni.py
python 3-generate_qc.py           # Kiểm tra QC trước khi tiếp tục!
python 4-atlas_download.py

# Giai đoạn 2: Atlas Registration + ROI
python 5-extract_roi_voxels.py     # Bước nặng nhất (SyN registration)
python 5b-extract_mri_roi_voxels.py

# Giai đoạn 3: Graph Construction
python 6-build_adjacency.py
python 6b-build_mri_adjacency.py
python 6c-build_node_features.py

# Giai đoạn 4: Fusion + Metrics
python 6d-fuse_graphs.py
python 6e-compute_graph_metrics.py

# Giai đoạn 5: Classification + Evaluation
python 7-classify.py
python 8-evaluate.py
```

### Lưu ý quan trọng

1. **Tất cả scripts đều idempotent:** Tự động bỏ qua subjects đã xử lý → có thể chạy lại an toàn nếu bị gián đoạn
2. **Bước 5 là nặng nhất:** SyN registration ~5-10 phút/subject. Dùng `registration.type: Affine` trong config nếu muốn nhanh hơn (nhưng kém chính xác)
3. **Bước 5b tái sử dụng cache:** Nếu đã chạy Bước 5, Bước 5b sẽ chạy gần như tức thì
4. **Kiểm tra QC sau Bước 3:** Xem `qc/pet_over_mri/` để phát hiện lỗi preprocessing sớm
5. **Kiểm tra QC sau Bước 5:** Xem `qc/parcellation_overlay/` để xác minh atlas registration

---

## 📚 Tham Khảo Thuật Ngữ

| Thuật ngữ | Tiếng Việt | Giải thích |
|:---|:---|:---|
| ADNI | Sáng kiến hình ảnh thần kinh AD | Cơ sở dữ liệu nghiên cứu quốc tế |
| ROI | Vùng quan tâm | Một vùng não trong atlas |
| Adjacency Matrix | Ma trận kề | Biểu diễn đồ thị dạng ma trận |
| Voxel | Pixel 3D | Đơn vị nhỏ nhất trong ảnh 3D |
| NIfTI | Định dạng ảnh não 3D | File .nii.gz |
| DICOM | Định dạng ảnh y khoa | File .dcm (mỗi lát = 1 file) |
| MNI Space | Không gian MNI | Hệ tọa độ não chuẩn quốc tế |
| Native Space | Không gian cá nhân | Hệ tọa độ não riêng mỗi người |
| Warp | Biến dạng | Biến đổi phi tuyến tính |
| Registration | Đăng ký hình ảnh | Xếp chồng 2 ảnh lên nhau |
| Skull Stripping | Loại bỏ hộp sọ | Tách não ra khỏi xương sọ |
| Bias Field | Trường nhiễu | Hiệu ứng cường độ không đều trong MRI |
| Hypometabolism | Giảm chuyển hóa | Giảm tiêu thụ glucose — dấu hiệu AD |
| DMN | Mạng chế độ mặc định | Mạng lưới não hoạt động khi nghỉ |
| Cross-Validation | Xác thực chéo | Phương pháp đánh giá model robust |
| AUC | Diện tích dưới ROC | Metric đánh giá phân loại tổng thể |
| Sensitivity | Độ nhạy | Tỷ lệ phát hiện đúng AD |
| Specificity | Độ đặc hiệu | Tỷ lệ xác nhận đúng CN |

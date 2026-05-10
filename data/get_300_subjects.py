import pandas as pd

# --- CẤU HÌNH TÊN FILE ---
PET_CSV = 'PET_list.csv' # File chứa FDG
MRI_CSV = 'MRI_list.csv' # File chứa MPRAGE

def score_mri_pre(desc):
    d = str(desc).lower()
    # Mức độ tiền xử lý MRI (Số càng nhỏ càng xịn)
    if 'scaled' in d: return 1           # Đã chuẩn hóa cường độ (Cao nhất)
    if 'n3' in d: return 2               # Đã khử nhiễu Bias field
    if 'b1 correction' in d: return 3    # Đã hiệu chỉnh B1
    if 'gradwarp' in d: return 4         # Đã nắn méo hình học
    return 5

def score_pet_pre(desc):
    d = str(desc).lower()
    # Mức độ tiền xử lý PET (Số càng nhỏ càng xịn)
    if 'uniform 6mm' in d or 'uniform resolution' in d: return 1 # Chuẩn hóa Voxel (Cao nhất)
    if 'standardized image' in d or 'std img' in d: return 2
    if 'averaged' in d or 'avg' in d: return 3
    if 'co-registered' in d or 'coreg' in d: return 4
    return 5

print("Đang đọc dữ liệu Preprocessed...")
pet_df = pd.read_csv(PET_CSV)
mri_df = pd.read_csv(MRI_CSV)

# Tính điểm chất lượng cho từng file
mri_df['MRI_Tier'] = mri_df['Description'].apply(score_mri_pre)
pet_df['PET_Tier'] = pet_df['Description'].apply(score_pet_pre)

# Xóa các dòng lỗi thiếu dữ liệu
mri_df['Age'] = pd.to_numeric(mri_df['Age'], errors='coerce')
pet_df['Age'] = pd.to_numeric(pet_df['Age'], errors='coerce')
mri_df = mri_df.dropna(subset=['Age', 'Subject ID', 'Image ID'])
pet_df = pet_df.dropna(subset=['Age', 'Subject ID', 'Image ID'])

common_subjects = set(mri_df['Subject ID']).intersection(set(pet_df['Subject ID']))

best_pairs = []

# Ghép cặp
for subj in common_subjects:
    # Lấy toàn bộ PET của bệnh nhân, ưu tiên Baseline (tuổi nhỏ nhất) và Xịn nhất
    subj_pet = pet_df[pet_df['Subject ID'] == subj].sort_values(by=['Age', 'PET_Tier'])
    subj_mri = mri_df[mri_df['Subject ID'] == subj]
    
    if subj_pet.empty or subj_mri.empty:
        continue
        
    baseline_pet = subj_pet.iloc[0]
    baseline_pet_age = baseline_pet['Age']
    
    # Tính khoảng cách ngày với MRI
    subj_mri_copy = subj_mri.copy()
    subj_mri_copy['Time_Diff'] = (subj_mri_copy['Age'] - baseline_pet_age).abs() * 365.25
    
    # Lấy MRI gần ngày nhất, nếu trùng ngày thì lấy MRI xịn nhất
    best_mri = subj_mri_copy.sort_values(by=['Time_Diff', 'MRI_Tier']).iloc[0]
    
    # Ràng buộc <= 365 ngày
    if best_mri['Time_Diff'] <= 365:
        best_pairs.append({
            'Subject': subj,
            'PET_ID': baseline_pet['Image ID'],
            'PET_Tier': baseline_pet['PET_Tier'],
            'MRI_ID': best_mri['Image ID'],
            'MRI_Tier': best_mri['MRI_Tier'],
            'Time_Diff': best_mri['Time_Diff']
        })

# Sắp xếp để chọn 300 cặp tinh hoa nhất
best_df = pd.DataFrame(best_pairs)
best_df = best_df.sort_values(by=['PET_Tier', 'MRI_Tier', 'Time_Diff'])
top_300 = best_df.head(300)

print("\n--- THỐNG KÊ CHẤT LƯỢNG TOP 300 ---")
print("Tổng số bệnh nhân hợp lệ:", len(best_df))
print("Số lượng Top 300 phân theo Hạng (PET_Tier, MRI_Tier):")
print(top_300.groupby(['PET_Tier', 'MRI_Tier']).size())

# Trích xuất 600 Image ID
final_image_ids = top_300['PET_ID'].tolist() + top_300['MRI_ID'].tolist()
clean_ids = [str(i).strip() if str(i).strip().startswith('I') else f"I{str(i).strip()}" for i in final_image_ids]

print(f"\n--- CHUỖI {len(clean_ids)} IMAGE ID ĐỂ TẢI TRÊN ADNI ---")
print(", ".join(clean_ids))
print("------------------------------------------------------------\n")
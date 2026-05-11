import os
from nilearn import datasets

# Tạo thư mục chứa Atlas
os.makedirs('./Atlas', exist_ok=True)

print("Đang kết nối đến kho dữ liệu thần kinh học để tải Schaefer Atlas...")

# Tải Schaefer Atlas (Bản 100 vùng - 100 Parcellations)
# Hệ tọa độ: MNI152 (Chuẩn quốc tế), độ phân giải 2mm
schaefer = datasets.fetch_atlas_schaefer_2018(
    n_rois=100, 
    yeo_networks=7, 
    resolution_mm=2, 
    data_dir='./Atlas'
)

# Đường dẫn file NIfTI sau khi tải về
atlas_path = schaefer.maps
print(f"✅ Đã tải thành công!")
print(f"File Atlas NIfTI của bạn đang nằm ở: {atlas_path}")

# In ra thử tên của vài vùng não
print("\nTên của 5 vùng não đầu tiên:")
for i in range(5):
    print(f"Vùng {i+1}: {schaefer.labels[i].decode('utf-8')}")
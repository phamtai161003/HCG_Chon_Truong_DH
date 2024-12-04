from flask import Flask, render_template, request, url_for
import pandas as pd
import math
import requests

app = Flask(__name__)

# Load dữ liệu từ file CSV
data = pd.read_csv('universities_cau_giay_geo_1000_records.csv')

# Hàm tính khoảng cách Haversine giữa hai điểm tọa độ
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Bán kính Trái Đất (km)
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c  # khoảng cách tính bằng km

# Hàm chuyển địa chỉ thành tọa độ sử dụng Nominatim API của OpenStreetMap
def geocode_address(address):
    url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json&limit=1"
    headers = {
        "User-Agent": "MyUniversityAdvisorApp/1.0 (phamductai2710@gmail.com)"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        results = response.json()
        if results:
            location = results[0]
            return float(location["lat"]), float(location["lon"])
    return None, None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Lấy điểm thi của người dùng
        diem_toan = float(request.form.get('diem_toan', 0))
        diem_ly = float(request.form.get('diem_ly', 0))
        diem_hoa = float(request.form.get('diem_hoa', 0))
        tong_diem = diem_toan + diem_ly + diem_hoa

        # Lấy địa chỉ nhà của người dùng
        address = request.form.get("address")
        user_lat, user_lon = geocode_address(address)

        if user_lat is None or user_lon is None:
            return "Không thể tìm thấy tọa độ cho địa chỉ này. Vui lòng thử lại."

        # Các tùy chọn lọc khác
        chat_luong = request.form.get('chat_luong')
        hoc_phi = request.form.get('hoc_phi')
        linh_vuc = request.form.get('linh_vuc')
        canh_tranh = request.form.get('canh_tranh')
        co_hoi_viec_lam = request.form.get('co_hoi_viec_lam')
        hoc_bong = request.form.get('hoc_bong')
        chuong_trinh_lien_ket = request.form.get('chuong_trinh_lien_ket')

        # Lọc trường phù hợp với lĩnh vực đã chọn và các tiêu chí đầu vào
        # Chỉ lấy những ngành có điểm chuẩn không quá cao so với `tong_diem`
        ket_qua = data[
            (data['diem_chuan'] <= tong_diem + 1) &  # Điểm chuẩn không quá 2 điểm cao hơn tổng điểm của người dùng
            (data['diem_chuan'] >= tong_diem - 2) &  # Điểm chuẩn không quá thấp hơn nhiều
            (data['linh_vuc'] == linh_vuc)
        ]

        # Nếu không có kết quả phù hợp, trả về thông báo không có ngành phù hợp
        if ket_qua.empty:
            return render_template(
                'results.html', 
                results=[], 
                tong_diem=tong_diem,
                linh_vuc=linh_vuc,
                ten_nganh=request.args.get('ten_nganh', '')
            )

        # Tạo bản sao của ket_qua để tránh cảnh báo SettingWithCopyWarning
        ket_qua = ket_qua.copy()
        
        # Tính khoảng cách từ nhà của người dùng đến từng trường
        ket_qua['distance'] = ket_qua.apply(
            lambda row: haversine(user_lat, user_lon, row['latitude'], row['longitude']), axis=1
        )

        # Sắp xếp theo điểm chuẩn giảm dần và khoảng cách gần nhất, hiển thị tối đa 100 kết quả
        ket_qua = ket_qua.sort_values(
            by=['diem_chuan', 'distance'], 
            ascending=[False, True]
        ).head(100)  # Hiển thị tối đa 100 kết quả

        return render_template(
            'results.html', 
            results=ket_qua.to_dict(orient='records'), 
            tong_diem=tong_diem,
            linh_vuc=linh_vuc,
            ten_nganh=request.args.get('ten_nganh', '')
        )
    
    return render_template('index.html')



@app.route('/filter_results', methods=['GET'])
def filter_results():
    # Lấy từ khóa ngành học người dùng nhập
    ten_nganh = request.args.get('ten_nganh', '').lower()
    tong_diem = request.args.get('tong_diem', type=float, default=0)

    # Lọc các ngành theo từ khóa nhập vào từ dữ liệu gốc
    filtered_results = data[(data['ten_nganh'].str.lower().str.contains(ten_nganh, na=False)) &
                            (data['diem_chuan'] <= tong_diem + 1)]

    # Tính khoảng cách cho từng kết quả lọc (sử dụng tọa độ mặc định nếu cần)
    user_lat, user_lon = 21.0285, 105.8542  # Toạ độ ví dụ (Hà Nội)
    filtered_results = filtered_results.copy()
    filtered_results['distance'] = filtered_results.apply(
        lambda row: haversine(user_lat, user_lon, row['latitude'], row['longitude']), axis=1
    )

    # Sắp xếp kết quả theo điểm chuẩn giảm dần và khoảng cách gần nhất, giới hạn 100 kết quả
    filtered_results = filtered_results.sort_values(by=['diem_chuan', 'distance'], ascending=[False, True]).head(100)

    return render_template(
        'results.html', 
        results=filtered_results.to_dict(orient='records'), 
        tong_diem=tong_diem, 
        ten_nganh=ten_nganh
    )

if __name__ == '__main__':
    app.run(debug=True)

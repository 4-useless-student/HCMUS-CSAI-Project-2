Hướng dẫn chi tiết cách chạy và cài đặt

1. Cài đặt
B1: git clone thư mục source code về(nếu chưa có)
Link repo: https://github.com/4-useless-student/HCMUS-CSAI-Project-2.git
B2: Cài đặt môi trường(sử dụng conda)
Lần lượt nhập các lệnh sau:
- conda create --name csai-proj2 python==3.10(có thể sử dụng phiên bản khác đều được)
- conda activate csai-proj2
B3: Cài đặt thư viện
- pip install -r requirements.txt

2. Chạy
Ở đây nhóm sẽ có 2 file để mà Chạy
2.1 main.py
File này được sử dụng để test nhanh nên có thể tùy chỉnh input và solver
Các tham số tùy chỉnh:
+ TIME_OUT = 120 # Có thể chỉnh xuống thấp để chạy nhanh hơn
+ solvers_to_run # list chứa các solver muốn chạy. Muốn tắt solver nào thì chỉ cần comment là tên là được hoặc ngược lại
+ input_ids_to_run # list chứa các index của input muốn chạy. Muốn chạy input nào chỉ cần thêm số index tương ứng là được
Nhập lệnh để chạy: python main.py

2.2 benchmark.py
file này được sử dụng để đánh giá, so sánh giữa các solver với nhau nên sẽ
chạy đầy đủ các input
Các tham số tùy chỉnh:
+ TIMEOUT = 120 # Có thể chỉnh xuống thấp để chạy nhanh hơn
+ SKIP_BRUTEFORCE_LARGE = True # Bật tắt cơ chế skip brute-force solver
+ LARGE_MAP_THRESHOLD = 12 # Chỉnh map size để skip brute-force
Nhập lệnh để chạy: python benchmark.py 

Kết quả có thể quan sát trong folder Outputs hoặc images hoặc benchmark_reports.csv
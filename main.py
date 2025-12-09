import os
import time
from algs_helper import AStarSolver, CNFSolver, BacktrackingSolver 



def main():
    # 1. Cấu hình đường dẫn
    input_folder = "Inputs"   
    output_folder = "Outputs"

    # Tạo thư mục Output nếu chưa có
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 2. Lấy danh sách file input và sắp xếp
    try:
        files = [f for f in os.listdir(input_folder) if f.endswith('.txt')]
        files.sort() # Sắp xếp để chạy từ input-01 -> input-10
    except FileNotFoundError:
        print(f"Lỗi: Không tìm thấy thư mục '{input_folder}'. Hãy kiểm tra lại đường dẫn.")
        return

    print(f"Tìm thấy {len(files)} file input. Bắt đầu chạy...\n")
    print("-" * 60)
    print(f"{'Input File':<15} | {'Algorithm':<15} | {'Time (s)':<10} | {'Status'}")
    print("-" * 60)

    # 3. Duyệt qua từng file input
    for filename in files:
        input_path = os.path.join(input_folder, filename)
        
        # --- Thêm thuật toán muốn chạy vào đây ---
        solver_classes = [
            AStarSolver,
            # CNFSolver, 
            # BacktrackingSolver
        ]
        
        for SolverClass in solver_classes:
            algo_name = SolverClass.__name__
            
            try:
                # Khởi tạo solver
                solver = SolverClass(input_path)
                
                # Chạy thuật toán và đo giờ
                exec_time = solver.run()
                
                # Tạo tên file output: input-01.txt -> output-01_AStarSolver.txt
                output_filename = filename.replace('input', 'output').replace('.txt', f'_{algo_name}.txt')
                output_path = os.path.join(output_folder, output_filename)
                
                # Lưu kết quả
                solver.save_output(output_path)
                
                print(f"{filename:<15} | {algo_name:<15} | {exec_time:.4f}     | Done")

            except Exception as e:
                print(f"{filename:<15} | {algo_name:<15} | ERROR      | {str(e)}")

    print("-" * 60)
    print("Hoàn tất xử lý tất cả file.")

if __name__ == "__main__":
    main()
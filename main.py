import os
import time
import threading
from solver import AStarSolver, BacktrackingSolver, BruteForceSolver, PySATSolver

INPUT_DIR = "Inputs"  
OUTPUT_DIR = "Outputs"
TIME_OUT = 120

def main(solvers, input_idx):
    # 1. Tạo thư mục Output nếu chưa có
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # Kiểm tra thư mục Input
    if not os.path.exists(INPUT_DIR):
        print(f"Lỗi: Không tìm thấy thư mục '{INPUT_DIR}'. Hãy kiểm tra lại đường dẫn.")
        return

    print(f"Bắt đầu chạy với các input ID: {input_idx}")
    print(f"Các thuật toán: {[s.__name__ for s in solvers]}\n")

    # 2. Duyệt qua từng ID trong danh sách input_idx
    for idx in input_idx:
        # Định dạng tên file: 5 -> input-05.txt, 10 -> input-10.txt
        filename = f"input-{idx:02d}.txt"
        input_path = os.path.join(INPUT_DIR, filename)
        
        # Kiểm tra file input có tồn tại không
        if not os.path.exists(input_path):
            print(f"{filename} | {'---'} | {'---'} | File not found")
            continue
        
        # 3. Chạy từng thuật toán cho file input hiện tại
        for SolverClass in solvers:
            algo_name = SolverClass.__name__
            
            try:
                print(f"Run {algo_name} solver for {filename}")
                # Khởi tạo solver
                solver = SolverClass(input_path)
        
                thread_result = {"exec_time": None, "error": None}
                
                # Hàm wrapper để chạy trong thread
                def run_solver_wrapper():
                    try:
                        thread_result["exec_time"] = solver.run()
                    except Exception as e:
                        thread_result["error"] = e

                # Tạo và chạy thread
                solver_thread = threading.Thread(target=run_solver_wrapper)
                solver_thread.daemon = True
                solver_thread.start()
                
                # Chờ thread chạy trong khoảng TIME_OUT
                solver_thread.join(timeout=TIME_OUT)

                if solver_thread.is_alive():
                    print(f"{filename} | {algo_name} | > {TIME_OUT} | Time Limit Exceeded")
                    continue

                if thread_result["error"]:
                    # Trường hợp code solver bị lỗi
                    raise thread_result["error"]
                
                exec_time = thread_result["exec_time"]

                # Kiểm tra solution
                if solver.solution is None:
                    print(f"{filename} | {algo_name} | {exec_time:<10.4f} | No Solution")
                    continue
                
                # Lưu output
                output_filename = filename.replace('input', 'output').replace('.txt', f'_{algo_name}.txt')
                output_path = os.path.join(OUTPUT_DIR, output_filename)
                solver.save_output(output_path)
                
                print(f"{filename} | {algo_name} | {exec_time:<10.4f} | Done")

            except Exception as e:
                # In lỗi nếu có vấn đề trong quá trình chạy
                print(f"{filename} | {algo_name} | ERROR | {str(e)}")
            
            print()
        print()

    print("Hoàn tất xử lý.")

if __name__ == "__main__":
    # Danh sách các thuật toán muốn chạy
    solvers_to_run = [
        PySATSolver, 
        AStarSolver,
        BacktrackingSolver
        #BruteForceSolver
    ]
    
    # Danh sách các ID của file input muốn chạy (Ví dụ: input-01.txt, input-05.txt)
<<<<<<< HEAD
    input_ids_to_run = [2] 
=======
    input_ids_to_run = [1,2,3,4,5,6,7,8,9,10] 
>>>>>>> 76963715dc60eb11b9d064b8e91adf79a7a1cdaf
    
    # Gọi hàm main với tham số
    main(solvers=solvers_to_run, input_idx=input_ids_to_run)
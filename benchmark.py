import os
import time
import pandas as pd
import tracemalloc
import multiprocessing
from solver import AStarSolver, BacktrackingSolver, BruteForceSolver, PySATSolver
from utils import plot_benchmark

# --- CẤU HÌNH ---
INPUT_FOLDER = "Inputs"
OUTPUT_REPORT = "benchmark_report.csv"
IMAGE_DIR = "images"
OUTPUT_DIR = "Outputs"

# THIẾT LẬP TIMEOUT
TIMEOUT_LIMIT = 60  # Giây. Nếu chạy quá 60s sẽ bị kill.
SKIP_BRUTEFORCE_LARGE = True 
LARGE_MAP_THRESHOLD = 12 # Size >= 12 sẽ auto skip BruteForce (đỡ tốn công tạo process)

def run_wrapper(SolverClass, input_path, output_path, queue):
    """
    Hàm wrapper chạy trong một process con.
    Nhiệm vụ: Chạy thuật toán, đo RAM, lưu file, gửi kết quả về process cha.
    """
    try:
        # Bắt đầu đo RAM
        tracemalloc.start()
        start_time = time.time()
        
        # 1. Khởi tạo và chạy
        solver = SolverClass(input_path)
        solver.run() 
        
        # 2. Đo đạc kết thúc
        end_time = time.time()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        exec_time = end_time - start_time
        peak_mb = peak / (1024 * 1024)
        
        # 3. Kiểm tra kết quả
        has_solution = solver.solution is not None
        
        # 4. Lưu output nếu có lời giải
        if has_solution:
            solver.save_output(output_path)
            
        # 5. Gửi kết quả về
        queue.put({
            "status": "Success" if has_solution else "No Solution",
            "time": exec_time,
            "memory": peak_mb
        })
        
    except Exception as e:
        queue.put({
            "status": "Error",
            "error_msg": str(e)
        })

def main():
    if not os.path.exists(INPUT_FOLDER):
        print(f"Lỗi: Không tìm thấy thư mục '{INPUT_FOLDER}'")
        return
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith('.txt')]
    files.sort()
    
    results_data = []
    
    # Danh sách thuật toán
    solver_classes = [
        #PySATSolver,
        AStarSolver,
        BacktrackingSolver,
        BruteForceSolver
    ]

    print(f"{'Input':<15} | {'Size':<8} | {'Algorithm':<20} | {'Time (s)':<10} | {'Status'}")
    print("-" * 80)

    for filename in files:
        input_path = os.path.join(INPUT_FOLDER, filename)
        
        # Lấy size nhanh để check điều kiện skip
        temp_solver = AStarSolver(input_path) # Dùng class nào cũng được để parse
        temp_solver.parse_input()
        map_size = max(temp_solver.rows, temp_solver.cols)
        size_str = f"{temp_solver.rows}x{temp_solver.cols}"

        for SolverClass in solver_classes:
            algo_name = SolverClass.__name__
            
            # Logic Skip BruteForce map lớn (để đỡ tốn resource tạo process)
            if SKIP_BRUTEFORCE_LARGE and algo_name == "BruteForceSolver" and map_size >= LARGE_MAP_THRESHOLD:
                print(f"{filename:<15} | {size_str:<8} | {algo_name:<20} | {'-':<10} | SKIPPED (Too Large)")
                results_data.append({
                    "Input": filename, "Size": map_size, "Algorithm": algo_name,
                    "Time": None, "Memory_MB": None, "Status": "Skipped"
                })
                continue

            # Chuẩn bị Output path
            output_filename = filename.replace('input', 'output').replace('.txt', f'_{algo_name}.txt')
            output_path = os.path.join(OUTPUT_DIR, output_filename)

            # --- CƠ CHẾ TIMEOUT DÙNG MULTIPROCESSING ---
            queue = multiprocessing.Queue()
            p = multiprocessing.Process(target=run_wrapper, args=(SolverClass, input_path, output_path, queue))
            
            p.start() # Bắt đầu chạy process con
            p.join(timeout=TIMEOUT_LIMIT) # Chờ tối đa TIMEOUT_LIMIT giây

            if p.is_alive():
                # Nếu vẫn còn sống sau timeout -> Kill
                p.terminate()
                p.join() # Clean up
                
                print(f"{filename:<15} | {size_str:<8} | {algo_name:<20} | {'> ' + str(TIMEOUT_LIMIT) + 's':<10} | TIMEOUT")
                results_data.append({
                    "Input": filename, "Size": map_size, "Algorithm": algo_name,
                    "Time": TIMEOUT_LIMIT, "Memory_MB": None, "Status": "Timeout"
                })
            else:
                # Nếu chạy xong trước timeout -> Lấy kết quả từ Queue
                if not queue.empty():
                    result = queue.get()
                    if result["status"] == "Error":
                        print(f"{filename:<15} | {size_str:<8} | {algo_name:<20} | {'ERROR':<10} | {result['error_msg']}")
                    else:
                        print(f"{filename:<15} | {size_str:<8} | {algo_name:<20} | {result['time']:<10.4f} | {result['status']}")
                        
                    results_data.append({
                        "Input": filename, "Size": map_size, "Algorithm": algo_name,
                        "Time": result.get("time"),
                        "Memory_MB": result.get("memory"),
                        "Status": result["status"]
                    })
                else:
                    # Trường hợp crash mà không gửi được dữ liệu
                    print(f"{filename:<15} | {size_str:<8} | {algo_name:<20} | {'CRASH':<10} | Process died unexpectedly")

    # --- LƯU VÀ VẼ ---
    if results_data:
        df = pd.DataFrame(results_data)
        df.to_csv(OUTPUT_REPORT, index=False)
        print("\n" + "-" * 80)
        print(f"Đã lưu benchmark report vào: {OUTPUT_REPORT}")
        plot_benchmark(df, IMAGE_DIR, TIMEOUT_LIMIT)


if __name__ == "__main__":
    # Bắt buộc phải có dòng này khi dùng multiprocessing trên Windows
    multiprocessing.freeze_support() 
    main()
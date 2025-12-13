import heapq
import pandas as pd
import matplotlib.pyplot as plt
import os

def get_map_size(input_path):
    with open(input_path, 'r') as f:
        lines = f.readlines()
    
    # Đếm số dòng (rows)
    rows = len([line for line in lines if line.strip()])
    
    # Đếm số cột (cols) từ dòng đầu tiên
    if rows > 0:
        first_line = lines[0].strip()
        # Tách theo dấu phẩy và đếm
        cols = len([x.strip() for x in first_line.split(',') if x.strip()])
    else:
        cols = 0
    
    return rows, cols, max(rows, cols)

class AStarNode:
    """Node class for A* search with better comparison"""
    def __init__(self, f_value, g_value, assignment, var_id=None):
        self.f_value = f_value
        self.g_value = g_value
        self.assignment = assignment
        self.var_id = var_id  # Variable that was just assigned
        
    def __lt__(self, other):
        # Primary: f_value, Secondary: g_value (prefer deeper nodes when tie)
        if self.f_value != other.f_value:
            return self.f_value < other.f_value
        return self.g_value > other.g_value
    
    def __eq__(self, other):
        return self.f_value == other.f_value and self.assignment == other.assignment
    
    def __repr__(self):
        return f"Node(f={self.f_value}, g={self.g_value}, vars={len(self.assignment)})"


def unit_propagation(assignment, cnf_clauses):
    """
    Áp dụng Unit Propagation: Nếu clause chỉ còn 1 literal chưa gán, buộc gán nó.
    Trả về (success, new_assignment) hoặc (False, None) nếu conflict.
    """
    assignment = assignment.copy()
    changed = True
    
    while changed:
        changed = False
        for clause in cnf_clauses:
            unassigned = []
            satisfied = False
            
            for lit in clause:
                var_id = abs(lit)
                
                if var_id in assignment:
                    val = assignment[var_id]
                    # Check if literal is satisfied
                    if (lit > 0 and val == True) or (lit < 0 and val == False):
                        satisfied = True
                        break
                else:
                    unassigned.append(lit)
            
            if satisfied:
                continue
            
            # Conflict: clause is false
            if not unassigned:
                return False, None
            
            # Unit clause: force assignment
            if len(unassigned) == 1:
                lit = unassigned[0]
                var_id = abs(lit)
                new_val = True if lit > 0 else False
                
                if var_id in assignment:
                    if assignment[var_id] != new_val:
                        return False, None  # Conflict
                else:
                    assignment[var_id] = new_val
                    changed = True
    
    return True, assignment


def pure_literal_elimination(assignment, cnf_clauses, all_vars):
    """
    Tìm các biến chỉ xuất hiện với 1 polarity (chỉ dương hoặc chỉ âm).
    Gán chúng theo polarity đó.
    """
    assignment = assignment.copy()
    literal_polarity = {}  # var_id -> set of polarities
    
    for clause in cnf_clauses:
        for lit in clause:
            var_id = abs(lit)
            if var_id not in assignment:
                if var_id not in literal_polarity:
                    literal_polarity[var_id] = set()
                literal_polarity[var_id].add(lit > 0)
    
    # Assign pure literals
    for var_id, polarities in literal_polarity.items():
        if len(polarities) == 1 and var_id not in assignment:
            assignment[var_id] = True if True in polarities else False
    
    return assignment


def check_all_clauses_satisfied(assignment, cnf_clauses):
    """Kiểm tra xem tất cả các clause có được thỏa mãn không"""
    for clause in cnf_clauses:
        satisfied = False
        for lit in clause:
            var_id = abs(lit)
            if var_id in assignment:
                val = assignment[var_id]
                if (lit > 0 and val == True) or (lit < 0 and val == False):
                    satisfied = True
                    break
        
        if not satisfied:
            return False
    
    return True


def count_unsatisfied_clauses(assignment, cnf_clauses):
    """Đếm số clause chưa được thỏa mãn (dùng cho heuristic)"""
    unsatisfied = 0
    
    for clause in cnf_clauses:
        satisfied = False
        all_assigned = True
        
        for lit in clause:
            var_id = abs(lit)
            if var_id not in assignment:
                all_assigned = False
            elif (lit > 0 and assignment[var_id] == True) or \
                 (lit < 0 and assignment[var_id] == False):
                satisfied = True
                break
        
        if all_assigned and not satisfied:
            unsatisfied += 1
    
    return unsatisfied


def select_variable_vsids(assignment, cnf_clauses, var_scores):
    """
    Variable State Independent Decaying Sum (VSIDS) heuristic.
    Chọn biến xuất hiện nhiều trong các clause gần đây.
    """
    best_var = None
    best_score = -1
    
    for clause in cnf_clauses:
        clause_satisfied = False
        for lit in clause:
            var_id = abs(lit)
            if var_id in assignment:
                val = assignment[var_id]
                if (lit > 0 and val == True) or (lit < 0 and val == False):
                    clause_satisfied = True
                    break
        
        if not clause_satisfied:
            for lit in clause:
                var_id = abs(lit)
                if var_id not in assignment:
                    score = var_scores.get(var_id, 0)
                    if score > best_score:
                        best_score = score
                        best_var = var_id
    
    return best_var


def compute_variable_scores(cnf_clauses):
    """Tính điểm cho mỗi biến dựa trên tần suất xuất hiện"""
    scores = {}
    for clause in cnf_clauses:
        for lit in clause:
            var_id = abs(lit)
            scores[var_id] = scores.get(var_id, 0) + 1
    return scores


def plot_benchmark(df, image_dir, TIMEOUT_LIMIT):
    """
    Vẽ 2 biểu đồ tổng hợp (Line Chart):
    1. benchmark_chart_time.png: So sánh thời gian chạy.
    2. benchmark_chart_memory.png: So sánh bộ nhớ tiêu thụ.
    """
    # Định nghĩa cấu hình cho 2 biểu đồ
    metrics = [
        {
            "col": "Time",
            "ylabel": "Time (seconds)",
            "title": "Performance Comparison: Execution Time",
            "filename": "benchmark_chart_time.png",
            "is_time": True
        },
        {
            "col": "Memory_MB",
            "ylabel": "Peak Memory (MB)",
            "title": "Performance Comparison: Memory Usage",
            "filename": "benchmark_chart_memory.png",
            "is_time": False
        }
    ]

    for metric in metrics:
        plt.figure(figsize=(12, 7)) # Khung hình rộng hơn chút cho dễ nhìn
        
        # 1. Chuẩn bị dữ liệu
        df_plot = df.copy()
        
        if metric["is_time"]:
            # Với biểu đồ Time: Fill giá trị Timeout bằng giới hạn để vẽ đường chạm trần
            df_plot.loc[df_plot["Status"] == "Timeout", "Time"] = TIMEOUT_LIMIT
            # Chỉ lấy các trạng thái có ý nghĩa để vẽ
            valid_statuses = ["Success", "Timeout", "No Solution"]
            df_plot = df_plot[df_plot["Status"].isin(valid_statuses)]
        else:
            # Với biểu đồ Memory: Bỏ qua các dòng không có dữ liệu Memory (Timeout/Skipped/Error)
            df_plot = df_plot[df_plot["Memory_MB"].notna()]

        # 2. Vẽ từng đường (mỗi thuật toán 1 đường)
        algorithms = df_plot["Algorithm"].unique()
        
        for algo in algorithms:
            # Sắp xếp theo Size để đường vẽ đi từ trái sang phải hợp lý
            subset = df_plot[df_plot["Algorithm"] == algo].sort_values(by="Size")
            
            if not subset.empty:
                plt.plot(subset["Input"], subset[metric["col"]], 
                         marker='o', linewidth=2, markersize=6, label=algo)

        # 3. Trang trí biểu đồ
        # Nếu là biểu đồ Time, vẽ thêm đường kẻ ngang Timeout màu đỏ
        if metric["is_time"]:
            plt.axhline(y=TIMEOUT_LIMIT, color='r', linestyle='--', alpha=0.7, label=f'Timeout ({TIMEOUT_LIMIT}s)')

        plt.xlabel("Input Files (Ordered by Map Size)")
        plt.ylabel(metric["ylabel"])
        plt.title(metric["title"])
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.5) # Lưới mờ
        plt.xticks(rotation=45) # Xoay nhãn trục X cho đỡ chồng chéo
        plt.tight_layout()

        # 4. Lưu file
        # Nếu biến OUTPUT_DIR có trong scope global thì dùng, không thì lưu thư mục hiện tại
        save_path = os.path.join(image_dir, metric["filename"])
        
        plt.savefig(save_path)
        plt.close() # Đóng plot để giải phóng RAM
        
        print(f"Đã lưu biểu đồ: {save_path}")

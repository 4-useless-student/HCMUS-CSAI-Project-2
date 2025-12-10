import heapq
import time
import itertools

class BaseSolver:
    def __init__(self, input_file):
        self.input_file = input_file
        self.output_file = None
        self.grid = []
        self.rows = 0
        self.cols = 0
        self.islands = []       # List of (row, col, value)
        
        # Cấu trúc lưu trữ cầu tiềm năng và biến logic
        # potential_bridges = [ {'u': (r1,c1), 'v': (r2,c2), 'dir': 'H'/'V', 'id': index}, ... ]
        self.potential_bridges = [] 
        
        # Mapping biến logic cho CNF
        # Mỗi cầu i sẽ có 2 biến: 
        #   vars[i]['1']: Biến đại diện cho "có ít nhất 1 cầu"
        #   vars[i]['2']: Biến đại diện cho "có 2 cầu"
        self.bridge_vars = [] 
        self.cnf_clauses = [] # Danh sách các mệnh đề CNF: [[1, -2], ...]
        self.num_vars = 0
        
        self.solution = None
        self.execution_time = 0

    def parse_input(self):
        """Đọc file và xác định các thành phần cơ bản."""
        try:
            with open(self.input_file, 'r') as f:
                lines = f.readlines()
            self.grid = []
            for line in lines:
                row = [int(x) for x in line.replace(',', ' ').split()]
                if row: self.grid.append(row)
            
            self.rows = len(self.grid)
            self.cols = len(self.grid[0]) if self.rows else 0
            
            # Tìm các đảo
            for r in range(self.rows):
                for c in range(self.cols):
                    if self.grid[r][c] > 0:
                        self.islands.append((r, c, self.grid[r][c]))
            
            # Bước 1: Tìm tất cả cầu tiềm năng
            self._identify_potential_bridges()
            
            # Bước 2: Gán ID biến cho CNF
            self._assign_variables()
            
            print(f"Parsed: {len(self.islands)} islands, {len(self.potential_bridges)} potential bridges.")
            
        except FileNotFoundError:
            print(f"File {self.input_file} not found.")

    def _identify_potential_bridges(self):
        """Tìm tất cả các cặp đảo có thể nối với nhau."""
        self.potential_bridges = []
        bridge_id = 0
        
        # Duyệt qua từng đảo để tìm hàng xóm bên phải và bên dưới
        for i, (r1, c1, val1) in enumerate(self.islands):
            # 1. Tìm sang phải (Horizontal)
            for c2 in range(c1 + 1, self.cols):
                cell_val = self.grid[r1][c2]
                if cell_val > 0: # Gặp đảo khác
                    self.potential_bridges.append({
                        'u': (r1, c1), 'v': (r1, c2), 
                        'dir': 'H', 'id': bridge_id,
                        'u_idx': i, 'v_idx': self._get_island_index(r1, c2)
                    })
                    bridge_id += 1
                    break
                # Nếu muốn check xem có cầu khác chắn ngang không thì logic phức tạp hơn, 
                # nhưng ở bước khởi tạo ta giả sử chưa có cầu nào.
        
        # Tương tự tìm xuống dưới (Vertical) - Tách ra loop để dễ quản lý
        for i, (r1, c1, val1) in enumerate(self.islands):
            for r2 in range(r1 + 1, self.rows):
                cell_val = self.grid[r2][c1]
                if cell_val > 0:
                    self.potential_bridges.append({
                        'u': (r1, c1), 'v': (r2, c1), 
                        'dir': 'V', 'id': bridge_id,
                        'u_idx': i, 'v_idx': self._get_island_index(r2, c1)
                    })
                    bridge_id += 1
                    break

    def _get_island_index(self, r, c):
        for idx, isl in enumerate(self.islands):
            if isl[0] == r and isl[1] == c:
                return idx
        return -1

    def _assign_variables(self):
        """Gán số nguyên đại diện cho biến logic."""
        self.bridge_vars = []
        current_var = 1
        
        for b in self.potential_bridges:
            # Var_1: Có ít nhất 1 cầu
            # Var_2: Có 2 cầu
            self.bridge_vars.append({
                '1': current_var,
                '2': current_var + 1
            })
            current_var += 2
        self.num_vars = current_var - 1

    def generate_cnf(self):
        """
        Sinh các mệnh đề CNF mô tả luật chơi.
        """
        self.cnf_clauses = []
        
        # 1. Ràng buộc cơ bản: Var_2 -> Var_1 (Nếu có 2 cầu thì phải có 1 cầu)
        # Logic: NOT(Var_2) OR Var_1
        for i in range(len(self.potential_bridges)):
            v1 = self.bridge_vars[i]['1']
            v2 = self.bridge_vars[i]['2']
            self.cnf_clauses.append([-v2, v1])

        # 2. Ràng buộc: Cầu không cắt nhau
        # Chỉ xét cặp (Ngang, Dọc) có giao điểm
        horizontals = [b for b in self.potential_bridges if b['dir'] == 'H']
        verticals = [b for b in self.potential_bridges if b['dir'] == 'V']
        
        for h in horizontals:
            for v in verticals:
                # Kiểm tra giao nhau: Row của H nằm giữa Row đầu/cuối của V
                # và Col của V nằm giữa Col đầu/cuối của H
                if (v['u'][0] < h['u'][0] < v['v'][0]) and \
                   (h['u'][1] < v['u'][1] < h['v'][1]):
                    # Nếu cắt nhau, không thể cùng tồn tại
                    # Cấm: H có cầu (>=1) VÀ V có cầu (>=1)
                    # CNF: NOT(H_1) OR NOT(V_1)
                    idx_h = h['id']
                    idx_v = v['id']
                    self.cnf_clauses.append([-self.bridge_vars[idx_h]['1'], -self.bridge_vars[idx_v]['1']])

        # 3. Ràng buộc: Tổng số cầu quanh đảo == Giá trị đảo
        # Đây là phần phức tạp nhất. Ta sẽ dùng phương pháp liệt kê các cấu hình HỢP LỆ.
        for idx, (r, c, val) in enumerate(self.islands):
            # Lấy tất cả cầu nối vào đảo này
            connected_bridges = []
            for b in self.potential_bridges:
                if b['u_idx'] == idx or b['v_idx'] == idx:
                    connected_bridges.append(b['id'])
            
            # Sinh tất cả các tổ hợp số lượng cầu (0, 1, 2) cho các cạnh nối
            # Ví dụ: Đảo nối với 3 cầu (b1, b2, b3). Cần tổng = val.
            valid_configs = []
            # Mỗi cầu có thể là 0, 1 hoặc 2
            for config in itertools.product([0, 1, 2], repeat=len(connected_bridges)):
                if sum(config) == val:
                    valid_configs.append(config)
            
            # Nếu không có config nào thỏa mãn -> Vô nghiệm (thêm clause rỗng để fail ngay)
            if not valid_configs:
                self.cnf_clauses.append([]) 
                continue
            pass
        
        print(f"Generated {len(self.cnf_clauses)} basic CNF clauses.")

    def run(self):
        self.parse_input()
        start = time.time()
        self.solve()
        self.execution_time = time.time() - start
        print(f"Finished in {self.execution_time:.4f}s")
        if self.output_file:
            self.save_output(self.output_file)

    def save_output(self, output_file):
        # Implementation for saving output format
        pass


class AStarSolver(BaseSolver):
    def __init__(self, input_file):
        super().__init__(input_file)
    
    def heuristic(self, assignment, approach=1):
        """
        Tính toán giá trị Heuristic h(n).
        assignment: dict {var_id: bool}
        """
        if approach == 1:
            h_score = 0
            
            # --- Ý tưởng 1: Số lượng đảo chưa thỏa mãn điều kiện số cầu ---
            # Cần tính lại tổng số cầu hiện tại cho mỗi đảo dựa trên assignment
            current_island_sums = {i: 0 for i in range(len(self.islands))}
            
            for b_idx, var_map in enumerate(self.bridge_vars):
                v1 = var_map['1']
                v2 = var_map['2']
                
                val = 0
                # Kiểm tra assignment có gán True cho các biến này không
                if assignment.get(v2, False): 
                    val = 2
                elif assignment.get(v1, False): 
                    val = 1
                
                if val > 0:
                    b_info = self.potential_bridges[b_idx]
                    current_island_sums[b_info['u_idx']] += val
                    current_island_sums[b_info['v_idx']] += val
            
            unsatisfied_islands = 0
            for i, (r, c, target_val) in enumerate(self.islands):
                if current_island_sums[i] != target_val:
                    # Có thể cải tiến: cộng thêm độ chênh lệch abs(target - current)
                    unsatisfied_islands += 1 # Hoặc += abs(target_val - current_island_sums[i])
            
            h_score += unsatisfied_islands * 10 # Trọng số cao cho đảo

        elif approach == 2:
            # --- Ý tưởng 2: Số lượng mệnh đề (Clauses) bị vi phạm ---
            violated_clauses = 0
            for clause in self.cnf_clauses:
                # Clause là list các literal (VD: [-1, 2] nghĩa là NOT 1 OR 2)
                # Clause vi phạm khi TẤT CẢ literal đều False
                is_clause_satisfied = False
                is_clause_undetermined = False
                
                for lit in clause:
                    var_id = abs(lit)
                    is_pos = (lit > 0)
                    
                    # Nếu biến chưa được gán -> Clause chưa xác định (chưa vi phạm)
                    if var_id not in assignment:
                        is_clause_undetermined = True
                        break # Chưa thể kết luận clause này False
                    
                    val = assignment[var_id]
                    # Nếu literal là True (VD: lit=1, val=True HOẶC lit=-1, val=False)
                    if (is_pos and val) or (not is_pos and not val):
                        is_clause_satisfied = True
                        break
                
                if not is_clause_satisfied and not is_clause_undetermined:
                    violated_clauses += 1
        
            h_score += violated_clauses * 100 # Vi phạm luật là rất tệ
        
        return h_score

    def solve(self):
        """Thực thi thuật toán A*"""
        self.generate_cnf() # Sinh các ràng buộc trước
        
        # Priority Queue: (f, g, assignment_dict)
        # assignment lưu {var_id: True/False}
        # Lưu ý: A* trên không gian biến CNF rất lớn, ta chỉ duyệt biến Var_1, Var_2 cho mỗi cầu
        
        start_assignment = {}
        g = 0
        h = self.heuristic(start_assignment)
        f = g + h
        
        # Counter để break tie trong heap
        count = 0 
        open_set = []
        heapq.heappush(open_set, (f, g, count, start_assignment))
        
        print("Starting A*...")
        
        # Để tối ưu, cần xác định thứ tự gán biến (Variable Ordering)
        # Sắp xếp biến theo cầu nối vào đảo nhỏ nhất trước (Most Constrained)
        ordered_vars = []
        for b in self.potential_bridges:
            ordered_vars.append(self.bridge_vars[b['id']]['1'])
            ordered_vars.append(self.bridge_vars[b['id']]['2'])
            
        while open_set:
            current_f, current_g, _, current_assignment = heapq.heappop(open_set)
            
            # Kiểm tra Goal: Đã gán hết biến và H_score = 0 (thỏa mãn hết)
            # (Hoặc logic check goal riêng)
            if len(current_assignment) == self.num_vars:
                if self.heuristic(current_assignment) == 0:
                    self.reconstruct_solution(current_assignment)
                    return
                else:
                    continue # Nhánh này sai, bỏ qua

            # Chọn biến chưa gán tiếp theo
            # Đơn giản nhất: Lấy biến có ID nhỏ nhất chưa có trong assignment
            var_to_assign = -1
            for var_id in range(1, self.num_vars + 1):
                if var_id not in current_assignment:
                    var_to_assign = var_id
                    break
            
            if var_to_assign == -1: continue

            # Sinh trạng thái con: Gán True / False
            for val in [True, False]:
                new_assign = current_assignment.copy()
                new_assign[var_to_assign] = val
                
                # Pruning cơ bản: Check nhanh xem gán xong có vi phạm CNF Crossing không?
                # (Đã tích hợp trong heuristic phần violated_clauses, nếu > 0 thì f sẽ rất lớn)
                
                new_g = current_g + 1
                new_h = self.heuristic(new_assign)
                
                # Nếu heuristic quá lớn (vi phạm ràng buộc cứng), cắt tỉa luôn
                if new_h >= 1000: 
                    continue
                    
                new_f = new_g + new_h
                count += 1
                heapq.heappush(open_set, (new_f, new_g, count, new_assign))

        print("No solution found by A*.")

    def reconstruct_solution(self, assignment):
        print("Solution found!")
        self.solution = []
        # Convert assignment back to bridge format for output
        for i, b in enumerate(self.potential_bridges):
            v1 = self.bridge_vars[i]['1']
            v2 = self.bridge_vars[i]['2']
            
            count = 0
            if assignment.get(v2, False): count = 2
            elif assignment.get(v1, False): count = 1
            
            if count > 0:
                # Lưu cầu vào danh sách lời giải để hàm format_solution vẽ
                self.solution.append({
                    'u': b['u'], 'v': b['v'], 'val': count, 'dir': b['dir']
                })
    
    def format_solution(self):
        # Override hàm format để vẽ ra ma trận string
        if not self.solution: return []
        
        # Copy grid gốc
        res_grid = [['0' if x==0 else str(x) for x in row] for row in self.grid]
        
        for bridge in self.solution:
            r1, c1 = bridge['u']
            r2, c2 = bridge['v']
            val = bridge['val']
            direction = bridge['dir']
            
            symbol = ''
            if direction == 'H':
                symbol = '-' if val == 1 else '='
                for c in range(c1 + 1, c2):
                    res_grid[r1][c] = symbol
            else: # Vertical
                symbol = '|' if val == 1 else '$' # $ đại diện 2 cầu dọc như đề bài ví dụ
                for r in range(r1 + 1, r2):
                    res_grid[r][c1] = symbol
                    
        return [str(row).replace("'", '"') for row in res_grid]

# Helper test
if __name__ == "__main__":
    # Tạo file giả lập để test
    with open("input-test.txt", "w") as f:
        f.write("2 0 4 0 2\n0 0 0 0 0\n1 0 3 0 1")
    
    solver = AStarSolver("input-test.txt")
    solver.run()


class CNFSolver(BaseSolver):
    def __init__():
        pass
    def solve():
        pass
class BacktrackingSolver(BaseSolver):
    def __init__():
        pass
    def solve():
        pass

class BruteForceSolver(BaseSolver):
    def __init__():
        pass
    def solve():
        pass
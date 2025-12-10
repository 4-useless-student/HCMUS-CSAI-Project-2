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
            
            #print(f"Parsed: {len(self.islands)} islands, {len(self.potential_bridges)} potential bridges.")
            
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
        #print(f"Finished in {self.execution_time:.4f}s")
        return self.execution_time

    def save_output(self, output_file):
        # Implementation for saving output format
        if self.solution is None:
            # Nếu không có solution, không lưu file
            return
        
        # Tạo output format
        output_lines = self.format_solution()
        with open(output_file, 'w') as f:
            for line in output_lines:
                f.write(line + '\n')


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
    """
    Thuật toán Backtracking (DPLL - Davis-Putnam-Logemann-Loveland) để giải CNF.
    Các kỹ thuật chính:
    1. Unit Propagation: Tự động gán giá trị cho biến trong mệnh đề đơn vị
    2. Pure Literal Elimination: Loại bỏ literal chỉ xuất hiện dưới 1 dạng
    3. Decision: Chọn biến chưa gán và thử True/False
    4. Backtracking: Quay lui nếu gặp mâu thuẫn
    """
    def __init__(self, input_file):
        super().__init__(input_file)
    
    def solve(self):
        """Thực thi thuật toán DPLL Backtracking"""
        # Sinh CNF
        self.generate_cnf()
        
        if not self.cnf_clauses:
            print("No CNF clauses generated.")
            return
        
        # Thu thập tất cả biến từ CNF
        all_vars = set()
        for clause in self.cnf_clauses:
            for lit in clause:
                all_vars.add(abs(lit))
        
        # Sắp xếp biến theo thứ tự xuất hiện giảm dần trong CNF (heuristic)
        var_count = {}
        for clause in self.cnf_clauses:
            for lit in clause:
                var_count[abs(lit)] = var_count.get(abs(lit), 0) + 1
        self.ordered_vars = sorted(all_vars, key=lambda x: -var_count.get(x, 0))
        
        # Gọi DPLL
        assignment = {}
        result = self._dpll(self.cnf_clauses.copy(), assignment)
        
        if result is not None:
            self._reconstruct_solution_from_cnf(result)
            print("Solution found by Backtracking (DPLL)!")
        else:
            print("No solution found by Backtracking.")
    
    def _dpll(self, clauses, assignment):
        """
        Thuật toán DPLL đệ quy.
        Trả về assignment nếu SAT, None nếu UNSAT.
        """
        # 1. Unit Propagation
        clauses, assignment = self._unit_propagation(clauses, assignment)
        if clauses is None:
            return None  # Mâu thuẫn
        
        # 2. Pure Literal Elimination
        clauses, assignment = self._pure_literal_elimination(clauses, assignment)
        if clauses is None:
            return None
        
        # 3. Kiểm tra điều kiện dừng
        if len(clauses) == 0:
            return assignment  # Tất cả mệnh đề đã thỏa mãn
        
        # Kiểm tra mệnh đề rỗng (mâu thuẫn)
        for clause in clauses:
            if len(clause) == 0:
                return None
        
        # 4. Chọn biến chưa gán (Decision)
        unassigned_var = self._choose_variable(clauses, assignment)
        if unassigned_var is None:
            return None
        
        # 5. Thử gán True
        new_assignment = assignment.copy()
        new_assignment[unassigned_var] = True
        new_clauses = self._simplify(clauses, unassigned_var, True)
        
        result = self._dpll(new_clauses, new_assignment)
        if result is not None:
            return result
        
        # 6. Thử gán False (Backtrack)
        new_assignment = assignment.copy()
        new_assignment[unassigned_var] = False
        new_clauses = self._simplify(clauses, unassigned_var, False)
        
        return self._dpll(new_clauses, new_assignment)
    
    def _unit_propagation(self, clauses, assignment):
        """
        Unit Propagation: Tìm mệnh đề đơn vị và gán giá trị bắt buộc.
        Mệnh đề đơn vị là mệnh đề chỉ còn 1 literal chưa gán.
        """
        changed = True
        while changed:
            changed = False
            for clause in clauses:
                if len(clause) == 1:
                    lit = clause[0]
                    var = abs(lit)
                    value = lit > 0
                    
                    if var in assignment:
                        if assignment[var] != value:
                            return None, assignment  # Mâu thuẫn
                    else:
                        assignment[var] = value
                        clauses = self._simplify(clauses, var, value)
                        changed = True
                        break
                        
                if len(clause) == 0:
                    return None, assignment  # Mâu thuẫn
        
        return clauses, assignment
    
    def _pure_literal_elimination(self, clauses, assignment):
        """
        Pure Literal Elimination: Tìm literal chỉ xuất hiện dưới 1 dạng (toàn dương hoặc toàn âm).
        """
        # Đếm số lần xuất hiện dạng dương và âm của mỗi biến
        pos_count = {}
        neg_count = {}
        
        for clause in clauses:
            for lit in clause:
                var = abs(lit)
                if var not in assignment:
                    if lit > 0:
                        pos_count[var] = pos_count.get(var, 0) + 1
                    else:
                        neg_count[var] = neg_count.get(var, 0) + 1
        
        # Tìm pure literals
        for var in set(pos_count.keys()) | set(neg_count.keys()):
            if var in assignment:
                continue
            
            pos = pos_count.get(var, 0)
            neg = neg_count.get(var, 0)
            
            if pos > 0 and neg == 0:
                # Chỉ xuất hiện dạng dương -> gán True
                assignment[var] = True
                clauses = self._simplify(clauses, var, True)
            elif neg > 0 and pos == 0:
                # Chỉ xuất hiện dạng âm -> gán False
                assignment[var] = False
                clauses = self._simplify(clauses, var, False)
        
        return clauses, assignment
    
    def _simplify(self, clauses, var, value):
        """
        Đơn giản hóa công thức CNF sau khi gán var = value.
        - Loại bỏ mệnh đề được thỏa mãn
        - Loại bỏ literal sai trong các mệnh đề còn lại
        """
        new_clauses = []
        for clause in clauses:
            # Kiểm tra xem mệnh đề có được thỏa mãn không
            satisfied = False
            new_clause = []
            
            for lit in clause:
                lit_var = abs(lit)
                if lit_var == var:
                    if (lit > 0 and value) or (lit < 0 and not value):
                        satisfied = True
                        break
                    # Literal sai, không thêm vào
                else:
                    new_clause.append(lit)
            
            if not satisfied:
                new_clauses.append(new_clause)
        
        return new_clauses
    
    def _choose_variable(self, clauses, assignment):
        """Chọn biến chưa gán để quyết định (theo thứ tự xuất hiện nhiều nhất)"""
        for var in self.ordered_vars:
            if var not in assignment:
                return var
        return None
    
    def _reconstruct_solution_from_cnf(self, assignment):
        """Chuyển CNF assignment thành bridge solution"""
        self.solution = []
        
        for i, bridge in enumerate(self.potential_bridges):
            var1 = self.bridge_vars[i]['1']  # Có ít nhất 1 cầu
            var2 = self.bridge_vars[i]['2']  # Có 2 cầu
            
            has_one = assignment.get(var1, False)
            has_two = assignment.get(var2, False)
            
            if has_two:
                count = 2
            elif has_one:
                count = 1
            else:
                count = 0
            
            if count > 0:
                self.solution.append({
                    'u': bridge['u'],
                    'v': bridge['v'],
                    'val': count,
                    'dir': bridge['dir']
                })
    
    def format_solution(self):
        """Vẽ ma trận kết quả"""
        if not self.solution:
            return []
        
        res_grid = [['0' if x == 0 else str(x) for x in row] for row in self.grid]
        
        for bridge in self.solution:
            r1, c1 = bridge['u']
            r2, c2 = bridge['v']
            val = bridge['val']
            direction = bridge['dir']
            
            if direction == 'H':
                symbol = '-' if val == 1 else '='
                for c in range(c1 + 1, c2):
                    res_grid[r1][c] = symbol
            else:
                symbol = '|' if val == 1 else '$'
                for r in range(r1 + 1, r2):
                    res_grid[r][c1] = symbol
        
        return [str(row).replace("'", '"') for row in res_grid]


class BruteForceSolver(BaseSolver):
    """
    Thuật toán Brute Force để giải CNF.
    Các bước thực hiện:
    1. Thu thập tất cả biến xuất hiện trong CNF
    2. Sinh tất cả phép gán (True/False) với itertools.product
    3. Áp dụng Unit Propagation và Pure Literal Elimination để tối ưu
    4. Kiểm tra tính thỏa mãn của CNF với mỗi phép gán
    """
    def __init__(self, input_file):
        super().__init__(input_file)
    
    def solve(self):
        """Thực thi thuật toán Brute Force"""
        # Sinh CNF
        self.generate_cnf()
        
        if not self.cnf_clauses:
            print("No CNF clauses generated.")
            return
        
        # Thu thập tất cả biến từ CNF (dùng abs để lấy biến, không phân biệt dương/âm)
        all_vars = sorted(set(abs(lit) for clause in self.cnf_clauses for lit in clause))
        n = len(all_vars)
        
        print(f"Brute Force: {n} variables, {2**n} combinations to check")
        
        # Sinh tất cả phép gán (1 = True, -1 = False)
        checked = 0
        for values in itertools.product([1, -1], repeat=n):
            checked += 1
            
            # Tạo assignment: {var_id: True/False}
            assignment = {}
            for i, var in enumerate(all_vars):
                assignment[var] = (values[i] == 1)
            
            # Áp dụng Unit Propagation để suy diễn thêm
            clauses_copy = [clause.copy() for clause in self.cnf_clauses]
            assignment, is_valid = self._apply_propagation(clauses_copy, assignment)
            
            if not is_valid:
                continue
            
            # Kiểm tra tính thỏa mãn của CNF
            if self._check_cnf_satisfaction(assignment):
                self._reconstruct_solution_from_cnf(assignment)
                print(f"Solution found by Brute Force! (Checked {checked} combinations)")
                return
        
        print(f"No solution found by Brute Force. (Checked {checked} combinations)")
    
    def _apply_propagation(self, clauses, assignment):
        """Áp dụng Unit Propagation để phát hiện mâu thuẫn sớm"""
        changed = True
        while changed:
            changed = False
            new_clauses = []
            
            for clause in clauses:
                # Kiểm tra mệnh đề
                satisfied = False
                remaining = []
                
                for lit in clause:
                    var = abs(lit)
                    expected = lit > 0
                    
                    if var in assignment:
                        if assignment[var] == expected:
                            satisfied = True
                            break
                        # Literal sai, bỏ qua
                    else:
                        remaining.append(lit)
                
                if satisfied:
                    continue
                
                if len(remaining) == 0:
                    return assignment, False  # Mâu thuẫn
                
                if len(remaining) == 1:
                    # Unit clause - gán bắt buộc
                    lit = remaining[0]
                    var = abs(lit)
                    value = lit > 0
                    
                    if var in assignment:
                        if assignment[var] != value:
                            return assignment, False
                    else:
                        assignment[var] = value
                        changed = True
                
                new_clauses.append(remaining)
            
            clauses = new_clauses
        
        return assignment, True
    
    def _check_cnf_satisfaction(self, assignment):
        """
        Kiểm tra tính thỏa mãn của CNF với phép gán hiện tại.
        Mỗi mệnh đề phải có ít nhất 1 literal được thỏa mãn.
        """
        for clause in self.cnf_clauses:
            clause_satisfied = False
            
            for lit in clause:
                var = abs(lit)
                expected_value = lit > 0  # lit > 0 -> True, lit < 0 -> False
                
                if var in assignment:
                    if assignment[var] == expected_value:
                        clause_satisfied = True
                        break
            
            if not clause_satisfied:
                return False
        
        return True
    
    def _reconstruct_solution_from_cnf(self, assignment):
        """Chuyển CNF assignment thành bridge solution"""
        self.solution = []
        
        for i, bridge in enumerate(self.potential_bridges):
            var1 = self.bridge_vars[i]['1']
            var2 = self.bridge_vars[i]['2']
            
            has_one = assignment.get(var1, False)
            has_two = assignment.get(var2, False)
            
            if has_two:
                count = 2
            elif has_one:
                count = 1
            else:
                count = 0
            
            if count > 0:
                self.solution.append({
                    'u': bridge['u'],
                    'v': bridge['v'],
                    'val': count,
                    'dir': bridge['dir']
                })
    
    def format_solution(self):
        """Vẽ ma trận kết quả"""
        if not self.solution:
            return []
        
        res_grid = [['0' if x == 0 else str(x) for x in row] for row in self.grid]
        
        for bridge in self.solution:
            r1, c1 = bridge['u']
            r2, c2 = bridge['v']
            val = bridge['val']
            direction = bridge['dir']
            
            if direction == 'H':
                symbol = '-' if val == 1 else '='
                for c in range(c1 + 1, c2):
                    res_grid[r1][c] = symbol
            else:
                symbol = '|' if val == 1 else '$'
                for r in range(r1 + 1, r2):
                    res_grid[r][c1] = symbol
        
        return [str(row).replace("'", '"') for row in res_grid]
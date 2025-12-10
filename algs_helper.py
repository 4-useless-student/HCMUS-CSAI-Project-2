import heapq
import time
import itertools
from utils import (
    AStarNode, 
    unit_propagation, 
    pure_literal_elimination,
    check_all_clauses_satisfied,
    count_unsatisfied_clauses,
    select_variable_vsids,
    compute_variable_scores
)

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
        Sinh các mệnh đề CNF mô tả luật chơi - Improved version.
        """
        self.cnf_clauses = []
        
        # 1. Ràng buộc cơ bản: Var_2 -> Var_1 (Nếu có 2 cầu thì phải có 1 cầu)
        # Logic: NOT(Var_2) OR Var_1
        for i in range(len(self.potential_bridges)):
            v1 = self.bridge_vars[i]['1']
            v2 = self.bridge_vars[i]['2']
            self.cnf_clauses.append([-v2, v1])
            # Thêm ràng buộc: Nếu x1 sai thì x2 phải sai
            self.cnf_clauses.append([v1, -v2])

        # 2. Ràng buộc: Cầu không cắt nhau
        horizontals = [b for b in self.potential_bridges if b['dir'] == 'H']
        verticals = [b for b in self.potential_bridges if b['dir'] == 'V']
        
        for h in horizontals:
            for v in verticals:
                if (v['u'][0] < h['u'][0] < v['v'][0]) and \
                   (h['u'][1] < v['u'][1] < h['v'][1]):
                    idx_h = h['id']
                    idx_v = v['id']
                    self.cnf_clauses.append([-self.bridge_vars[idx_h]['1'], -self.bridge_vars[idx_v]['1']])

        # 3. Ràng buộc: Tổng số cầu quanh đảo == Giá trị đảo
        # Sử dụng encoding cardinality constraint
        for idx, (r, c, val) in enumerate(self.islands):
            # Lấy tất cả cầu nối vào đảo này
            connected_bridge_vars = []
            
            for b in self.potential_bridges:
                if b['u_idx'] == idx or b['v_idx'] == idx:
                    b_id = b['id']
                    # Thêm cả x1 và x2 vào list (x1 đóng góp 1, x2 đóng góp thêm 1 nữa)
                    connected_bridge_vars.append(self.bridge_vars[b_id]['1'])
                    connected_bridge_vars.append(self.bridge_vars[b_id]['2'])
            
            if not connected_bridge_vars:
                if val != 0:
                    self.cnf_clauses.append([])  # UNSAT
                continue
            
            # Encode exactly-k constraint bằng cách kết hợp at-least-k và at-most-k
            # Đây là version đơn giản hóa, chỉ xử lý các case phổ biến
            self._encode_exactly_k(connected_bridge_vars, val)
        
        # 4. Ràng buộc: Kết nối liên thông
        N = len(self.islands)
        min_bridges = N - 1
        
        if N > 1 and len(self.potential_bridges) >= min_bridges:
            bridge_v1_vars = [self.bridge_vars[i]['1'] for i in range(len(self.potential_bridges))]
            
            M = len(self.potential_bridges)
            max_false = M - min_bridges
            
            # At-least-K encoding: Trong mọi tập (max_false + 1) biến, ít nhất 1 phải True
            if max_false >= 0 and max_false < M and max_false < 10:  # Giới hạn để tránh explosion
                from itertools import combinations
                for subset in combinations(range(M), min(max_false + 1, M)):
                    clause = [bridge_v1_vars[i] for i in subset]
                    self.cnf_clauses.append(clause)
        
        print(f"Generated {len(self.cnf_clauses)} CNF clauses.")
    
    def _encode_exactly_k(self, variables, k):
        """
        Encode exactly-k constraint: Đúng k biến trong list phải là True
        Sử dụng phương pháp đơn giản cho các giá trị k nhỏ
        """
        n = len(variables)
        
        # At-least-k: Cấm tất cả tổ hợp có nhiều hơn (n-k) biến False
        if k > 0:
            max_false = n - k
            if max_false >= 0 and max_false < n:
                from itertools import combinations
                # Nếu có nhiều hơn max_false biến False -> vi phạm
                if max_false + 1 <= min(n, 15):  # Giới hạn để tránh quá nhiều clause
                    for subset in combinations(range(n), max_false + 1):
                        # Ít nhất 1 trong subset phải True
                        clause = [variables[i] for i in subset]
                        self.cnf_clauses.append(clause)
        
        # At-most-k: Cấm tất cả tổ hợp có nhiều hơn k biến True
        if k < n:
            if k + 1 <= min(n, 15):  # Giới hạn
                from itertools import combinations
                for subset in combinations(range(n), k + 1):
                    # Không được tất cả đều True
                    clause = [-variables[i] for i in subset]
                    self.cnf_clauses.append(clause)

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
        self.visited_states = set()
        self.var_scores = {}
    
    def _state_key(self, assignment):
        """Tạo key duy nhất cho trạng thái"""
        return tuple(sorted(assignment.items()))
    
    def _early_pruning(self, assignment):
        """Kiểm tra sớm các ràng buộc vi phạm"""
        # 1. Kiểm tra vi phạm số cầu tại mỗi đảo
        current_island_sums = {i: 0 for i in range(len(self.islands))}
        potential_island_sums = {i: 0 for i in range(len(self.islands))}
        
        for b_idx, var_map in enumerate(self.bridge_vars):
            v1 = var_map['1']
            v2 = var_map['2']
            
            val = 0
            max_potential = 2
            
            if v2 in assignment:
                if assignment[v2]:
                    val = 2
                    max_potential = 2
                else:
                    max_potential = 1 if v1 not in assignment or assignment.get(v1, False) else 0
            elif v1 in assignment:
                if assignment[v1]:
                    val = 1
                    max_potential = 2
                else:
                    val = 0
                    max_potential = 0
            
            b_info = self.potential_bridges[b_idx]
            current_island_sums[b_info['u_idx']] += val
            current_island_sums[b_info['v_idx']] += val
            potential_island_sums[b_info['u_idx']] += max_potential
            potential_island_sums[b_info['v_idx']] += max_potential
        
        for i, (r, c, target_val) in enumerate(self.islands):
            current = current_island_sums[i]
            potential = potential_island_sums[i]
            
            if current > target_val or potential < target_val:
                return False
        
        # 2. Kiểm tra vi phạm cầu cắt nhau
        for clause in self.cnf_clauses:
            if len(clause) == 2 and clause[0] < 0 and clause[1] < 0:
                var1 = abs(clause[0])
                var2 = abs(clause[1])
                if assignment.get(var1, False) and assignment.get(var2, False):
                    return False
        
        return True
    
    def _select_next_variable_improved(self, assignment):
        """
        Kết hợp VSIDS với Most Constrained Variable heuristic
        """
        # Tính toán trạng thái hiện tại của các đảo
        current_island_sums = {i: 0 for i in range(len(self.islands))}
        
        for b_idx, var_map in enumerate(self.bridge_vars):
            v1 = var_map['1']
            v2 = var_map['2']
            
            val = 0
            if assignment.get(v2, False):
                val = 2
            elif assignment.get(v1, False):
                val = 1
            
            if val > 0:
                b_info = self.potential_bridges[b_idx]
                current_island_sums[b_info['u_idx']] += val
                current_island_sums[b_info['v_idx']] += val
        
        # Tìm biến có impact cao nhất
        best_var = None
        best_score = -float('inf')
        
        for b_idx, var_map in enumerate(self.bridge_vars):
            v1 = var_map['1']
            v2 = var_map['2']
            
            if v1 not in assignment:
                b_info = self.potential_bridges[b_idx]
                u_idx = b_info['u_idx']
                v_idx = b_info['v_idx']
                
                # Điểm dựa trên mức độ cấp thiết của đảo
                u_needed = abs(self.islands[u_idx][2] - current_island_sums[u_idx])
                v_needed = abs(self.islands[v_idx][2] - current_island_sums[v_idx])
                urgency_score = -(u_needed + v_needed)  # Negative because we want minimum
                
                # Điểm VSIDS
                vsids_score = self.var_scores.get(v1, 0)
                
                # Kết hợp
                combined_score = urgency_score * 10 + vsids_score
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_var = v1
                    
            elif v2 not in assignment and assignment.get(v1, False):
                # Ưu tiên cao nếu v1 đã True
                return v2
        
        if best_var is None:
            # Fallback: lấy biến đầu tiên chưa gán
            for var_id in range(1, self.num_vars + 1):
                if var_id not in assignment:
                    return var_id
        
        return best_var
    
    def heuristic(self, assignment):
        """
        Admissible heuristic: Tổng độ chênh lệch số cầu của các đảo
        """
        h_score = 0
        current_island_sums = {i: 0 for i in range(len(self.islands))}
        
        for b_idx, var_map in enumerate(self.bridge_vars):
            v1 = var_map['1']
            v2 = var_map['2']
            
            val = 0
            if assignment.get(v2, False): 
                val = 2
            elif assignment.get(v1, False): 
                val = 1
            
            if val > 0:
                b_info = self.potential_bridges[b_idx]
                current_island_sums[b_info['u_idx']] += val
                current_island_sums[b_info['v_idx']] += val
        
        for i, (r, c, target_val) in enumerate(self.islands):
            diff = abs(target_val - current_island_sums[i])
            h_score += diff
        
        return h_score

    def solve(self):
        """A* với Unit Propagation và Pure Literal Elimination"""
        self.generate_cnf()
        
        # Tính VSIDS scores
        self.var_scores = compute_variable_scores(self.cnf_clauses)
        
        # Khởi tạo
        start_assignment = {}
        
        # Áp dụng Pure Literal Elimination ngay từ đầu
        start_assignment = pure_literal_elimination(start_assignment, self.cnf_clauses, 
                                                   list(range(1, self.num_vars + 1)))
        
        # Áp dụng Unit Propagation
        success, start_assignment = unit_propagation(start_assignment, self.cnf_clauses)
        if not success:
            print("No solution found!")
            return
        
        g = len(start_assignment)
        h = self.heuristic(start_assignment)
        f = g + h
        
        open_set = []
        initial_node = AStarNode(f, g, start_assignment)
        heapq.heappush(open_set, initial_node)
        
        best_f_score = {self._state_key(start_assignment): f}
        
        iterations = 0
        
        while open_set:
            iterations += 1
            
            current_node = heapq.heappop(open_set)
            current_assignment = current_node.assignment
            
            state_key = self._state_key(current_assignment)
            if state_key in self.visited_states:
                continue
            self.visited_states.add(state_key)
            
            # Goal test
            if len(current_assignment) == self.num_vars:
                if check_all_clauses_satisfied(current_assignment, self.cnf_clauses):
                    if self._early_pruning(current_assignment):
                        self.reconstruct_solution(current_assignment)
                        print("Solution found!")
                        return
                continue
            
            # Early pruning
            if not self._early_pruning(current_assignment):
                continue
            
            # Select variable
            var_to_assign = self._select_next_variable_improved(current_assignment)
            if var_to_assign is None:
                continue
            
            # Try both values
            for val in [True, False]:
                new_assign = current_assignment.copy()
                new_assign[var_to_assign] = val
                
                # Unit Propagation
                success, propagated_assign = unit_propagation(new_assign, self.cnf_clauses)
                if not success:
                    continue
                
                new_state_key = self._state_key(propagated_assign)
                if new_state_key in self.visited_states:
                    continue
                
                # Early pruning
                if not self._early_pruning(propagated_assign):
                    continue
                
                new_g = len(propagated_assign)
                new_h = self.heuristic(propagated_assign)
                new_f = new_g + new_h
                
                # Add to queue if better
                if new_state_key not in best_f_score or new_f < best_f_score[new_state_key]:
                    best_f_score[new_state_key] = new_f
                    new_node = AStarNode(new_f, new_g, propagated_assign, var_to_assign)
                    heapq.heappush(open_set, new_node)
        
        print("No solution found!")

    def reconstruct_solution(self, assignment):
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
        f.write("2 0 0 0 2\n0 0 0 0 0\n0 0 0 0 0")
    
    solver = AStarSolver("input-test.txt")
    solver.run()


class CNFSolver(BaseSolver):
    def __init__(self, input_file):
        super().__init__(input_file)
    
    def solve(self):
        pass


class BacktrackingSolver(BaseSolver):
    def __init__(self, input_file):
        super().__init__(input_file)
    
    def solve(self):
        pass


class BruteForceSolver(BaseSolver):
    def __init__(self, input_file):
        super().__init__(input_file)
    
    def solve(self):
        pass
from .base_solver import BaseSolver

from utils import (
    AStarNode, 
    unit_propagation, 
    pure_literal_elimination,
    check_all_clauses_satisfied,
    count_unsatisfied_clauses,
    select_variable_vsids,
    compute_variable_scores
)

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

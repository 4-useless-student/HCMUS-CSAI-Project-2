import itertools
from .base_solver import BaseSolver


class BruteForceSolver(BaseSolver):
    def __init__(self, input_file):
        super().__init__(input_file)
    
    def solve(self):
        # Sinh CNF
        self.generate_cnf()
        
        if not self.cnf_clauses:
            return
        
        # Thu thập tất cả biến từ CNF (dùng abs để lấy biến, không phân biệt dương/âm)
        all_vars = sorted(set(abs(lit) for clause in self.cnf_clauses for lit in clause))
        n = len(all_vars)
        
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
                return
    
    def _apply_propagation(self, clauses, assignment):
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


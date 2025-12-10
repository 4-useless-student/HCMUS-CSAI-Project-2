from .base_solver import BaseSolver

class BacktrackingSolver(BaseSolver):
    def __init__(self, input_file):
        super().__init__(input_file)
    
    def solve(self):
        # Sinh CNF
        self.generate_cnf()
        
        if not self.cnf_clauses:
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
    
    def _dpll(self, clauses, assignment):
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
        for var in self.ordered_vars:
            if var not in assignment:
                return var
        return None
    
    def _reconstruct_solution_from_cnf(self, assignment):
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

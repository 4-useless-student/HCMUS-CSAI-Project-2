import heapq

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

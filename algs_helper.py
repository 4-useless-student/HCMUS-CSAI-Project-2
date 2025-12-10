
from utils import (
    AStarNode, 
    unit_propagation, 
    pure_literal_elimination,
    check_all_clauses_satisfied,
    count_unsatisfied_clauses,
    select_variable_vsids,
    compute_variable_scores
)


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
from pysat.solvers import Glucose4
from .base_solver import BaseSolver

class PySATSolver(BaseSolver):
    def __init__(self, input_file):
        super().__init__(input_file)

    def solve(self):
        """
        Giải quyết bài toán sử dụng thư viện PySAT (Glucose4).
        """
        # 1. Sinh các mệnh đề CNF (kế thừa từ BaseSolver đã tối ưu)
        print("Đang sinh CNF...")
        self.generate_cnf()
        
        if not self.cnf_clauses:
            print("Cảnh báo: Không sinh được mệnh đề CNF nào.")
            return

        print(f"Bắt đầu giải với Glucose4 (Số biến: {self.num_vars}, Số mệnh đề: {len(self.cnf_clauses)})...")

        # 2. Khởi tạo solver và nạp mệnh đề
        # bootstrap_with giúp nạp nhanh toàn bộ clauses vào solver
        with Glucose4(bootstrap_with=self.cnf_clauses) as solver:
            # 3. Gọi hàm giải
            is_sat = solver.solve()
            
            if is_sat:
                # 4. Lấy model (danh sách các biến True/False)
                # Model trả về list các số nguyên (dương là True, âm là False)
                model = solver.get_model()
                
                # Chuyển model list thành dictionary {id_biến: True/False} để BaseSolver hiểu
                assignment = {abs(var): (var > 0) for var in model}
                
                # 5. Tái tạo lại lời giải (hàm này có sẵn ở BaseSolver)
                self._reconstruct_solution_from_cnf(assignment)
                print("PySAT: Đã tìm thấy lời giải! (SAT)")
            else:
                print("PySAT: Không tìm thấy lời giải (UNSAT).")
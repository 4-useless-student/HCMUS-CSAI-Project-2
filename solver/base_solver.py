import time

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
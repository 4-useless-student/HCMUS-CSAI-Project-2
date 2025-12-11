import time
from pysat.card import CardEnc

class BaseSolver:
    def __init__(self, input_file):
        self.input_file = input_file
        self.output_file = None
        self.grid = []
        self.rows = 0
        self.cols = 0
        self.islands = []       # List of (row, col, value)
        
        # Dict mapping từ tọa độ (r, c) -> index trong self.islands
        self.island_map = {}    
        # Map island_index -> list các bridge_id kết nối với nó
        self.island_bridges = {} 

        # Cấu trúc lưu trữ cầu tiềm năng
        self.potential_bridges = [] 
        
        # Mapping biến logic cho CNF
        self.bridge_vars = [] 
        self.cnf_clauses = [] 
        self.num_vars = 0
        
        self.solution = None
        self.execution_time = 0

    def parse_input(self):
        """Đọc file, xác định đảo và các cầu tiềm năng."""
        try:
            with open(self.input_file, 'r') as f:
                lines = f.readlines()
            
            self.grid = []
            for line in lines:
                clean_line = line.replace(',', ' ').strip()
                if not clean_line: continue
                row = [int(x) for x in clean_line.split()]
                self.grid.append(row)
            
            self.rows = len(self.grid)
            self.cols = len(self.grid[0]) if self.rows else 0
            
            self.islands = []
            self.island_map = {}
            idx_counter = 0
            for r in range(self.rows):
                for c in range(self.cols):
                    if self.grid[r][c] > 0:
                        self.islands.append((r, c, self.grid[r][c]))
                        self.island_map[(r, c)] = idx_counter
                        self.island_bridges[idx_counter] = []
                        idx_counter += 1
            
            self._identify_potential_bridges()
            self._assign_variables()
            
            print(f"Parsed: {len(self.islands)} islands, {len(self.potential_bridges)} potential bridges.")
            
        except FileNotFoundError:
            print(f"File {self.input_file} not found.")
        except ValueError:
            print("Error parsing input file format.")

    def _identify_potential_bridges(self):
        self.potential_bridges = []
        bridge_id = 0
        
        def add_bridge(u_idx, v_idx, r1, c1, r2, c2, direction):
            nonlocal bridge_id
            bridge = {
                'u': (r1, c1), 'v': (r2, c2),
                'dir': direction, 'id': bridge_id,
                'u_idx': u_idx, 'v_idx': v_idx
            }
            self.potential_bridges.append(bridge)
            self.island_bridges[u_idx].append(bridge_id)
            self.island_bridges[v_idx].append(bridge_id)
            bridge_id += 1

        # Duyệt ngang
        for r in range(self.rows):
            last_island_idx = -1
            for c in range(self.cols):
                if self.grid[r][c] > 0:
                    curr_idx = self.island_map[(r, c)]
                    if last_island_idx != -1:
                        prev_r, prev_c, _ = self.islands[last_island_idx]
                        add_bridge(last_island_idx, curr_idx, prev_r, prev_c, r, c, 'H')
                    last_island_idx = curr_idx

        # Duyệt dọc
        for c in range(self.cols):
            last_island_idx = -1
            for r in range(self.rows):
                if self.grid[r][c] > 0:
                    curr_idx = self.island_map[(r, c)]
                    if last_island_idx != -1:
                        prev_r, prev_c, _ = self.islands[last_island_idx]
                        add_bridge(last_island_idx, curr_idx, prev_r, prev_c, r, c, 'V')
                    last_island_idx = curr_idx

    def _assign_variables(self):
        self.bridge_vars = []
        current_var = 1
        for _ in self.potential_bridges:
            self.bridge_vars.append({'1': current_var, '2': current_var + 1})
            current_var += 2
        self.num_vars = current_var - 1

    def generate_cnf(self):
        self.cnf_clauses = []
        
        # 1. Var_2 -> Var_1
        for i in range(len(self.potential_bridges)):
            v1 = self.bridge_vars[i]['1']
            v2 = self.bridge_vars[i]['2']
            self.cnf_clauses.append([-v2, v1]) 

        # 2. Cầu không cắt nhau
        horizontals = [b for b in self.potential_bridges if b['dir'] == 'H']
        verticals = [b for b in self.potential_bridges if b['dir'] == 'V']
        for h in horizontals:
            for v in verticals:
                if (v['u'][0] < h['u'][0] < v['v'][0]) and (h['u'][1] < v['u'][1] < h['v'][1]):
                    self.cnf_clauses.append([-self.bridge_vars[h['id']]['1'], -self.bridge_vars[v['id']]['1']])

        # 3. Tổng số cầu quanh đảo == Giá trị đảo
        for idx, (r, c, val) in enumerate(self.islands):
            connected_vars = []
            for b_id in self.island_bridges[idx]:
                connected_vars.append(self.bridge_vars[b_id]['1'])
                connected_vars.append(self.bridge_vars[b_id]['2'])
            
            if not connected_vars:
                if val != 0: self.cnf_clauses.append([1, -1])
                continue
            
            cnf_obj = CardEnc.equals(lits=connected_vars, bound=val, encoding=1, top_id=self.num_vars)
            if cnf_obj.nv > self.num_vars: self.num_vars = cnf_obj.nv
            self.cnf_clauses.extend(cnf_obj.clauses)
        
        # 4. Liên thông yếu (>= N-1 cạnh)
        N = len(self.islands)
        if N > 1:
            all_v1_vars = [self.bridge_vars[i]['1'] for i in range(len(self.potential_bridges))]
            if len(all_v1_vars) >= N - 1:
                cnf_obj = CardEnc.atleast(lits=all_v1_vars, bound=N - 1, encoding=1, top_id=self.num_vars)
                if cnf_obj.nv > self.num_vars: self.num_vars = cnf_obj.nv
                self.cnf_clauses.extend(cnf_obj.clauses)
            else:
                 self.cnf_clauses.append([1, -1])
        
        print(f"Generated {len(self.cnf_clauses)} CNF clauses. Max Var: {self.num_vars}")

    def _reconstruct_solution_from_cnf(self, assignment):
        """Dịch kết quả từ Pysat sang danh sách cầu để vẽ."""
        self.solution = []
        for i, bridge in enumerate(self.potential_bridges):
            v1 = self.bridge_vars[i]['1']
            v2 = self.bridge_vars[i]['2']
            
            count = 0
            if assignment.get(v2, False): count = 2
            elif assignment.get(v1, False): count = 1
            
            if count > 0:
                self.solution.append({
                    'u': bridge['u'], 'v': bridge['v'],
                    'val': count, 'dir': bridge['dir']
                })

    def format_solution(self):
        """Vẽ ma trận kết quả (String grid)."""
        if not self.solution: return []
        
        # Copy grid gốc
        res_grid = [['0' if x==0 else str(x) for x in row] for row in self.grid]
        
        for bridge in self.solution:
            r1, c1 = bridge['u']
            r2, c2 = bridge['v']
            val = bridge['val']
            direction = bridge['dir']
            
            if direction == 'H':
                symbol = '-' if val == 1 else '='
                for c in range(c1 + 1, c2):
                    res_grid[r1][c] = symbol
            else: # Vertical
                symbol = '|' if val == 1 else '$' # $ cho cầu đôi dọc
                for r in range(r1 + 1, r2):
                    res_grid[r][c1] = symbol
                    
        return [str(row).replace("'", '"') for row in res_grid]

    def run(self):
        self.parse_input()
        start = time.time()
        self.solve() # Lớp con override hàm này
        self.execution_time = time.time() - start
        print(f"Finished in {self.execution_time:.4f}s")
        if self.output_file:
            self.save_output(self.output_file)
        return self.execution_time

    def solve(self):
        raise NotImplementedError("Subclasses must implement solve()")

    def save_output(self, output_file):
        if self.solution is None: return
        output_lines = self.format_solution()
        with open(output_file, 'w') as f:
            for line in output_lines:
                f.write(line + '\n')
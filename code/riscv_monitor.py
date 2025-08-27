import tkinter as tk
from tkinter import ttk
import threading
import time
import struct

# 개선된 메모리 모델
class Memory:
    def __init__(self, size_bytes):
        self.data = bytearray(size_bytes)  # 바이트 단위
    
    def read_byte(self, addr):
        if addr < len(self.data):
            return self.data[addr]
        return 0
    
    def read_half(self, addr):
        if addr + 1 < len(self.data):
            return self.data[addr] | (self.data[addr+1] << 8)  # 리틀 엔디안
        return 0
    
    def read_word(self, addr):
        if addr + 3 < len(self.data):
            return (self.data[addr] | 
                    (self.data[addr+1] << 8) | 
                    (self.data[addr+2] << 16) | 
                    (self.data[addr+3] << 24))
        return 0
    
    def write_byte(self, addr, value):
        if addr < len(self.data):
            self.data[addr] = value & 0xFF
    
    def write_half(self, addr, value):
        if addr + 1 < len(self.data):
            self.data[addr] = value & 0xFF
            self.data[addr+1] = (value >> 8) & 0xFF
    
    def write_word(self, addr, value):
        if addr + 3 < len(self.data):
            self.data[addr] = value & 0xFF
            self.data[addr+1] = (value >> 8) & 0xFF
            self.data[addr+2] = (value >> 16) & 0xFF
            self.data[addr+3] = (value >> 24) & 0xFF
    
    def clear(self):
        self.data = bytearray(len(self.data))

class RISCVMemoryMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("RISC-V 멀티사이클 파이프라인 시뮬레이터")
        self.root.geometry("1400x900")
        
        # 메모리 상태 (시뮬레이션용)
        self.regfile = [0] * 32  # x0-x31 레지스터 (각 32비트)
        self.ram = Memory(1024)  # 1024바이트 RAM (바이트 어드레서블)
        self.rom = Memory(1024)  # 1024바이트 ROM (바이트 어드레서블)
        
        # 멀티사이클 파이프라인 상태
        self.cycle_count = 0
        self.instruction_count = 0
        self.current_instruction = 0
        self.control_state = 'FETCH'
        
        # 파이프라인 레지스터 (하드웨어와 동일)
        self.pipeline_registers = {
            'PCOutData': 0x00000000,  # PC 출력
            'DecReg_RFData1': 0,      # Decode 단계 RF Data1
            'DecReg_RFData2': 0,      # Decode 단계 RF Data2
            'DecReg_immExt': 0,       # Decode 단계 Immediate
            'ExeReg_RFData2': 0,      # Execute 단계 RF Data2
            'ExeReg_aluResult': 0,    # Execute 단계 ALU 결과
            'ExeReg_PCSrcMuxOut': 0,  # Execute 단계 PC 소스
            'MemAccReg_busRData': 0,  # Memory 단계 버스 읽기 데이터
            'MemAccReg_busAddr': 0,   # Memory 단계 버스 주소
            'MemAccReg_busWData': 0   # Memory 단계 버스 쓰기 데이터
        }
        
        # 제어 신호 (하드웨어와 동일)
        self.control_signals = {
            'PCEn': 0,           # PC Enable
            'regFileWe': 0,      # Register File Write Enable
            'aluSrcMuxSel': 0,   # ALU Source Mux Select
            'busWe': 0,          # Bus Write Enable
            'RFWDSrcMuxSel': 0,  # RF Write Data Source Mux Select
            'branch': 0,         # Branch
            'jal': 0,            # JAL
            'jalr': 0            # JALR
        }
        
        # ALU 및 메모리 제어
        self.aluControl = 0
        self.ramControl = 0
        
        # 실행 히스토리 (되돌리기 기능용)
        self.history = []  # (regfile, ram, pc, cycle_count) 튜플들의 리스트
        self.max_history = 100  # 최대 히스토리 개수     
        
        # 로그 파일 핸들
        self.log_file = None
        
        self.setup_gui()
        self.start_monitoring()
        
        # 초기화 실행
        self.reset_system()
    
    def setup_gui(self):
        # 메인 프레임
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 상단 정보 패널
        info_frame = ttk.LabelFrame(main_frame, text="파이프라인 상태")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 사이클 및 상태 정보
        status_frame = ttk.Frame(info_frame)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(status_frame, text="사이클:").pack(side=tk.LEFT, padx=(0, 5))
        self.cycle_label = ttk.Label(status_frame, text="0", font=("Consolas", 12, "bold"))
        self.cycle_label.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(status_frame, text="명령어:").pack(side=tk.LEFT, padx=(0, 5))
        self.instruction_label = ttk.Label(status_frame, text="0", font=("Consolas", 12, "bold"))
        self.instruction_label.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(status_frame, text="상태:").pack(side=tk.LEFT, padx=(0, 5))
        self.state_label = ttk.Label(status_frame, text="FETCH", font=("Consolas", 12, "bold"))
        self.state_label.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(status_frame, text="PC:").pack(side=tk.LEFT, padx=(0, 5))
        self.pc_label = ttk.Label(status_frame, text="0x00000000", font=("Consolas", 12, "bold"))
        self.pc_label.pack(side=tk.LEFT)
        
        # 파이프라인 레지스터 표시
        pipeline_frame = ttk.LabelFrame(main_frame, text="파이프라인 레지스터")
        pipeline_frame.pack(fill=tk.X, pady=(0, 10))
        
        pipeline_text_frame = ttk.Frame(pipeline_frame)
        pipeline_text_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.pipeline_text = tk.Text(pipeline_text_frame, height=6, font=("Consolas", 9))
        pipeline_scroll = ttk.Scrollbar(pipeline_text_frame, orient=tk.HORIZONTAL, command=self.pipeline_text.xview)
        self.pipeline_text.configure(xscrollcommand=pipeline_scroll.set)
        self.pipeline_text.pack(side=tk.TOP, fill=tk.X)
        pipeline_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 메인 디스플레이 프레임
        display_frame = ttk.Frame(main_frame)
        display_frame.pack(fill=tk.BOTH, expand=True)
        
        # 레지스터 파일 표시
        reg_frame = ttk.LabelFrame(display_frame, text="레지스터 파일 (x0-x31)")
        reg_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.reg_text = tk.Text(reg_frame, width=35, height=15, font=("Consolas", 9))
        reg_scroll = ttk.Scrollbar(reg_frame, orient=tk.VERTICAL, command=self.reg_text.yview)
        self.reg_text.configure(yscrollcommand=reg_scroll.set)
        self.reg_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        reg_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # RAM 메모리 표시
        ram_frame = ttk.LabelFrame(display_frame, text="RAM 메모리 (0x000-0x3FF)")
        ram_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.ram_text = tk.Text(ram_frame, width=35, height=15, font=("Consolas", 9))
        ram_scroll = ttk.Scrollbar(ram_frame, orient=tk.VERTICAL, command=self.ram_text.yview)
        self.ram_text.configure(yscrollcommand=ram_scroll.set)
        self.ram_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ram_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # ROM 메모리 표시
        rom_frame = ttk.LabelFrame(display_frame, text="ROM 메모리 (0x000-0x3FF)")
        rom_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        self.rom_text = tk.Text(rom_frame, width=35, height=15, font=("Consolas", 9))
        rom_scroll = ttk.Scrollbar(rom_frame, orient=tk.VERTICAL, command=self.rom_text.yview)
        self.rom_text.configure(yscrollcommand=rom_scroll.set)
        self.rom_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        rom_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 컨트롤 패널
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(control_frame, text="코드 로드", command=self.load_code).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="초기화", command=self.reset_system).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="시뮬레이션 시작", command=self.start_simulation).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="시뮬레이션 정지", command=self.stop_simulation).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="단계 실행", command=self.step_execution).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="되돌리기", command=self.undo_step).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="로그 시작", command=self.start_logging).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="로그 정지", command=self.stop_logging).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Vivado 로그 읽기", command=self.read_vivado_log).pack(side=tk.LEFT, padx=5)
        
        # 상태 표시
        self.status_label = ttk.Label(control_frame, text="대기 중...")
        self.status_label.pack(side=tk.RIGHT, padx=5)
        
        self.simulation_running = False
    
    def reset_system(self):
        """시스템 초기화"""
        # 시뮬레이션 정지
        self.simulation_running = False
        
        # 카운터 초기화
        self.cycle_count = 0
        self.instruction_count = 0
        
        # 레지스터 파일 초기화
        self.regfile = [0] * 32
        self.regfile[0] = 0  # x0는 항상 0
        self.regfile[1] = 0x64  # ra = 0x64
        
        # 메모리 초기화
        self.ram = Memory(1024)
        self.rom = Memory(1024)
        
        # 파이프라인 레지스터 초기화
        self.pipeline_registers = {
            'PCOutData': 0x00000000,
            'DecReg_RFData1': 0,
            'DecReg_RFData2': 0,
            'DecReg_immExt': 0,
            'ExeReg_RFData2': 0,
            'ExeReg_aluResult': 0,
            'ExeReg_PCSrcMuxOut': 0,
            'MemAccReg_busRData': 0,
            'MemAccReg_busAddr': 0,
            'MemAccReg_busWData': 0
        }
        
        # 제어 신호 초기화
        self.control_signals = {
            'PCEn': 0, 'regFileWe': 0, 'aluSrcMuxSel': 0, 'busWe': 0,
            'RFWDSrcMuxSel': 0, 'branch': 0, 'jal': 0, 'jalr': 0
        }
        
        # 상태 초기화
        self.control_state = 'FETCH'
        self.current_instruction = 0
        self.aluControl = 0
        self.ramControl = 0
        
        # 히스토리 초기화
        self.history.clear()
        
        # 디스플레이 업데이트
        self.update_displays()
        
        # 상태 메시지 업데이트
        self.status_label.config(text="시스템 초기화 완료")
        
        print("멀티사이클 파이프라인 시뮬레이터 초기화 완료")
        
        # 로그 파일 초기화
        if self.log_file:
            self.log_file.close()
            self.log_file = None
    
    def load_code(self):
        try:
            with open("code.mem", "r", encoding="utf-8") as f:
                lines = f.readlines()
                rom_index = 0
                for line in lines:
                    line = line.strip()
                    # 주석이나 빈 줄 건너뛰기
                    if line.startswith('#') or not line:
                        continue
                    # 16진수 기계어 코드만 처리
                    if line and rom_index < 256:  # 256 워드 = 1024바이트
                        try:
                            instruction = int(line, 16)
                            # 4바이트씩 ROM에 저장 (리틀 엔디안)
                            addr = rom_index * 4
                            self.rom.write_word(addr, instruction)
                            rom_index += 1
                        except ValueError:
                            continue  # 잘못된 형식의 라인 무시
            self.status_label.config(text=f"코드 로드 완료 ({rom_index}개 명령어)")
            self.update_displays()
        except FileNotFoundError:
            self.status_label.config(text="코드 파일을 찾을 수 없습니다")
        except Exception as e:
            self.status_label.config(text=f"코드 로드 오류: {str(e)}")
    
    def load_test_code(self):
        """테스트 코드 로드"""
        try:
            with open("test_code.mem", "r", encoding="utf-8") as f:
                lines = f.readlines()
                rom_index = 0
                for line in lines:
                    line = line.strip()
                    # 주석이나 빈 줄 건너뛰기
                    if line.startswith('#') or not line:
                        continue
                    # 16진수 기계어 코드만 처리
                    if line and rom_index < 256:  # 256 워드 = 1024바이트
                        try:
                            instruction = int(line, 16)
                            # 4바이트씩 ROM에 저장 (리틀 엔디안)
                            addr = rom_index * 4
                            self.rom.write_word(addr, instruction)
                            rom_index += 1
                        except ValueError:
                            continue  # 잘못된 형식의 라인 무시
            self.status_label.config(text=f"테스트 코드 로드 완료 ({rom_index}개 명령어)")
            self.update_displays()
        except FileNotFoundError:
            self.status_label.config(text="test_code.mem 파일을 찾을 수 없습니다")
        except Exception as e:
            self.status_label.config(text=f"테스트 코드 로드 오류: {str(e)}")
    
    def start_simulation(self):
        self.simulation_running = True
        self.status_label.config(text="시뮬레이션 실행 중...")
    
    def stop_simulation(self):
        self.simulation_running = False
        self.status_label.config(text="시뮬레이션 정지됨")
    
    def step_execution(self):
        """멀티사이클 파이프라인 단계 실행"""
        try:
            # 현재 상태를 히스토리에 저장
            self.save_state()
            
            # 사이클 카운터 증가
            self.cycle_count += 1
            
            # ROM 범위 체크 - PC가 ROM 범위를 벗어나면 시뮬레이션 정지
            rom_addr = self.pipeline_registers['PCOutData']
            
            # 디버그 출력 (처음 10사이클만)
            if self.cycle_count <= 10:
                print(f"사이클 {self.cycle_count}: PC=0x{rom_addr:08X}, 상태={self.control_state}")
            
            # PC가 유효한 ROM 주소인지 확인 (0x00000000 ~ 0x000003FC)
            if rom_addr > 0x3FC:  # 1024 bytes - 4 = 0x3FC
                self.simulation_running = False
                self.status_label.config(text=f"ROM 범위 초과 - 시뮬레이션 종료 (PC: 0x{rom_addr:08X})")
                print(f"ROM 범위 초과로 시뮬레이션 종료: PC=0x{rom_addr:08X}")
                return
            
            # 무한 루프 방지 - 같은 PC에서 너무 오래 머물면 정지
            if hasattr(self, '_last_pc'):
                if self._last_pc == rom_addr:
                    self._pc_stall_count += 1
                    if self._pc_stall_count > 100:  # 100사이클 이상 같은 PC에 머물면 정지
                        self.simulation_running = False
                        self.status_label.config(text=f"무한 루프 감지 - 시뮬레이션 종료 (PC: 0x{rom_addr:08X})")
                        print(f"무한 루프 감지로 시뮬레이션 종료: PC=0x{rom_addr:08X}")
                        return
                else:
                    self._pc_stall_count = 0
            else:
                self._last_pc = rom_addr
                self._pc_stall_count = 0
            
            # Control Unit 상태 머신 실행
            self.execute_control_unit_state()
            
            # DataPath 실행
            self.execute_datapath()
            
            # 명령어 완료 체크 (FETCH로 돌아왔을 때)
            if self.control_state == 'FETCH' and hasattr(self, '_instruction_completed'):
                self.instruction_count += 1
                delattr(self, '_instruction_completed')
            
            # 로그 기록
            self.write_log(self.cycle_count, self.pipeline_registers['PCOutData'], 
                          self.current_instruction, self.pipeline_registers['MemAccReg_busAddr'],
                          self.pipeline_registers['MemAccReg_busWData'], 
                          self.pipeline_registers['MemAccReg_busRData'], 
                          self.control_signals['busWe'])
            
            # 디스플레이 업데이트
            self.update_displays()
            
            # 상태 메시지 업데이트
            if rom_addr <= 0x3FC:
                instruction = self.rom.read_word(rom_addr)
                self.status_label.config(text=f"사이클 {self.cycle_count}: {self.control_state} - PC: 0x{rom_addr:04X}")
            else:
                self.status_label.config(text=f"사이클 {self.cycle_count}: {self.control_state} - PC: 0x{rom_addr:04X} (ROM 범위 초과)")
            
            # 최대 사이클 수 제한 (안전장치)
            if self.cycle_count > 1000:
                self.simulation_running = False
                self.status_label.config(text="최대 사이클 수 도달 - 시뮬레이션 종료")
                print("최대 사이클 수(1000) 도달로 시뮬레이션 종료")
                return
                
        except Exception as e:
            print(f"시뮬레이션 오류 발생: {e}")
            self.simulation_running = False
            self.status_label.config(text=f"시뮬레이션 오류: {str(e)}")
            return
    
    def execute_control_unit_state(self):
        """Control Unit 상태 머신 실행"""
        opcode = self.current_instruction & 0x7F
        operator = ((self.current_instruction >> 30) & 0x1) << 3 | ((self.current_instruction >> 12) & 0x7)
        func3 = (self.current_instruction >> 12) & 0x7
        
        # 제어 신호 초기화
        self.control_signals = {
            'PCEn': 0, 'regFileWe': 0, 'aluSrcMuxSel': 0, 'busWe': 0,
            'RFWDSrcMuxSel': 0, 'branch': 0, 'jal': 0, 'jalr': 0
        }
        self.aluControl = 0
        self.ramControl = 0
        
        if self.control_state == 'FETCH':
            # PC Enable - 첫 사이클부터 활성화
            self.control_signals['PCEn'] = 1
            
            # 명령어 페치
            self.current_instruction = self.rom.read_word(self.pipeline_registers['PCOutData'])
            self.next_state = 'DECODE'
            
        elif self.control_state == 'DECODE':
            # 명령어 타입에 따른 다음 상태 결정
            if opcode == 0x33:  # R-type
                self.next_state = 'R_EXE'
            elif opcode == 0x23:  # S-type
                self.next_state = 'S_EXE'
            elif opcode == 0x03:  # L-type
                self.next_state = 'L_EXE'
            elif opcode == 0x13:  # I-type
                self.next_state = 'I_EXE'
            elif opcode == 0x63:  # B-type
                self.next_state = 'B_EXE'
            elif opcode == 0x37:  # LUI
                self.next_state = 'LU_EXE'
            elif opcode == 0x17:  # AUIPC
                self.next_state = 'AU_EXE'
            elif opcode == 0x6F:  # JAL
                self.next_state = 'J_EXE'
            elif opcode == 0x67:  # JALR
                self.next_state = 'JL_EXE'
            else:
                self.next_state = 'FETCH'
                
        elif self.control_state == 'R_EXE':
            self.aluControl = operator
            self.control_signals['regFileWe'] = 1
            self.next_state = 'FETCH'
            self._instruction_completed = True
            
        elif self.control_state == 'I_EXE':
            self.control_signals['regFileWe'] = 1
            self.control_signals['aluSrcMuxSel'] = 1
            if operator == 0xD:  # SRAI
                self.aluControl = operator
            else:
                self.aluControl = operator & 0x7
            self.next_state = 'FETCH'
            self._instruction_completed = True
            
        elif self.control_state == 'B_EXE':
            self.control_signals['branch'] = 1
            self.aluControl = operator
            self.next_state = 'FETCH'
            self._instruction_completed = True
            
        elif self.control_state == 'LU_EXE':
            self.control_signals['regFileWe'] = 1
            self.control_signals['RFWDSrcMuxSel'] = 2
            self.next_state = 'FETCH'
            self._instruction_completed = True
            
        elif self.control_state == 'AU_EXE':
            self.control_signals['regFileWe'] = 1
            self.control_signals['RFWDSrcMuxSel'] = 3
            self.next_state = 'FETCH'
            self._instruction_completed = True
            
        elif self.control_state == 'J_EXE':
            self.control_signals['regFileWe'] = 1
            self.control_signals['RFWDSrcMuxSel'] = 4
            self.control_signals['jal'] = 1
            self.next_state = 'FETCH'
            self._instruction_completed = True
            
        elif self.control_state == 'JL_EXE':
            self.control_signals['regFileWe'] = 1
            self.control_signals['RFWDSrcMuxSel'] = 4
            self.control_signals['jal'] = 1
            self.control_signals['jalr'] = 1
            self.next_state = 'FETCH'
            self._instruction_completed = True
            
        elif self.control_state == 'S_EXE':
            self.control_signals['aluSrcMuxSel'] = 1
            self.next_state = 'S_MEM'
            
        elif self.control_state == 'S_MEM':
            self.control_signals['aluSrcMuxSel'] = 1
            self.control_signals['busWe'] = 1
            # Store 명령어에 따른 ramControl 설정
            if func3 == 0:  # sb
                self.ramControl = 1
            elif func3 == 1:  # sh
                self.ramControl = 2
            elif func3 == 2:  # sw
                self.ramControl = 0
            self.next_state = 'FETCH'
            self._instruction_completed = True
            
        elif self.control_state == 'L_EXE':
            self.control_signals['aluSrcMuxSel'] = 1
            self.control_signals['RFWDSrcMuxSel'] = 1
            self.next_state = 'L_MEM'
            
        elif self.control_state == 'L_MEM':
            self.control_signals['aluSrcMuxSel'] = 1
            self.control_signals['RFWDSrcMuxSel'] = 1
            # Load 명령어에 따른 ramControl 설정
            if func3 == 0:  # lb
                self.ramControl = 1
            elif func3 == 1:  # lh
                self.ramControl = 2
            elif func3 == 2:  # lw
                self.ramControl = 0
            elif func3 == 4:  # lbu
                self.ramControl = 5
            elif func3 == 5:  # lhu
                self.ramControl = 6
            self.next_state = 'L_WB'
            
        elif self.control_state == 'L_WB':
            self.control_signals['regFileWe'] = 1
            self.control_signals['aluSrcMuxSel'] = 1
            self.control_signals['RFWDSrcMuxSel'] = 1
            self.next_state = 'FETCH'
            self._instruction_completed = True
        
        # 상태 전환
        self.control_state = self.next_state
    
    def execute_datapath(self):
        """DataPath 실행 (하드웨어와 동일)"""
        opcode = self.current_instruction & 0x7F
        rs1 = (self.current_instruction >> 15) & 0x1F
        rs2 = (self.current_instruction >> 20) & 0x1F
        rd = (self.current_instruction >> 7) & 0x1F
        
        # Register File 읽기 (x0는 항상 0)
        RFData1 = 0 if rs1 == 0 else self.regfile[rs1]
        RFData2 = 0 if rs2 == 0 else self.regfile[rs2]
        
        # Immediate 확장
        immExt = self.extract_immediate(self.current_instruction)
        
        # 파이프라인 레지스터 업데이트 (Decode 단계)
        if self.control_state == 'DECODE':
            self.pipeline_registers['DecReg_RFData1'] = RFData1
            self.pipeline_registers['DecReg_RFData2'] = RFData2
            self.pipeline_registers['DecReg_immExt'] = immExt
        
        # ALU 소스 멀티플렉서
        if self.control_signals['aluSrcMuxSel']:
            aluSrcMuxOut = self.pipeline_registers['DecReg_immExt']
        else:
            aluSrcMuxOut = self.pipeline_registers['DecReg_RFData2']
        
        # ALU 실행
        aluResult = self.execute_alu(self.pipeline_registers['DecReg_RFData1'], 
                                   aluSrcMuxOut, self.aluControl)
        
        # PC 관련 계산
        PC_4_AdderResult = self.pipeline_registers['PCOutData'] + 4
        PC_Imm_AdderSrcMuxOut = (self.pipeline_registers['PCOutData'] 
                                if not self.control_signals['jalr'] 
                                else self.pipeline_registers['DecReg_RFData1'])
        PC_Imm_AdderResult = self.pipeline_registers['DecReg_immExt'] + PC_Imm_AdderSrcMuxOut
        
        # PC 소스 멀티플렉서
        PCSrcMuxSel = self.control_signals['jal'] or (aluResult and self.control_signals['branch'])
        PCSrcMuxOut = PC_Imm_AdderResult if PCSrcMuxSel else PC_4_AdderResult
        
        # 메모리 접근 (Memory 단계)
        if self.control_signals['busWe']:  # Store
            addr = self.pipeline_registers['ExeReg_aluResult']
            data = self.pipeline_registers['ExeReg_RFData2']
            self.pipeline_registers['MemAccReg_busAddr'] = addr
            self.pipeline_registers['MemAccReg_busWData'] = data
            
            if 0 <= addr < 1024:
                if self.ramControl == 0:  # sw
                    self.ram.write_word(addr, data)
                elif self.ramControl == 1:  # sb
                    self.ram.write_byte(addr, data)
                elif self.ramControl == 2:  # sh
                    self.ram.write_half(addr, data)
        else:  # Load
            addr = self.pipeline_registers['ExeReg_aluResult']
            self.pipeline_registers['MemAccReg_busAddr'] = addr
            
            if 0 <= addr < 1024:
                if self.ramControl == 0:  # lw
                    self.pipeline_registers['MemAccReg_busRData'] = self.ram.read_word(addr)
                elif self.ramControl == 1:  # lb
                    value = self.ram.read_byte(addr)
                    if value & 0x80:
                        value |= 0xFFFFFF00
                    self.pipeline_registers['MemAccReg_busRData'] = value
                elif self.ramControl == 2:  # lh
                    value = self.ram.read_half(addr)
                    if value & 0x8000:
                        value |= 0xFFFF0000
                    self.pipeline_registers['MemAccReg_busRData'] = value
                elif self.ramControl == 5:  # lbu
                    self.pipeline_registers['MemAccReg_busRData'] = self.ram.read_byte(addr)
                elif self.ramControl == 6:  # lhu
                    self.pipeline_registers['MemAccReg_busRData'] = self.ram.read_half(addr)
        
        # Register File Write Data 소스 멀티플렉서
        RFWDSrcMuxOut = 0
        if self.control_signals['RFWDSrcMuxSel'] == 0:
            RFWDSrcMuxOut = aluResult
        elif self.control_signals['RFWDSrcMuxSel'] == 1:
            RFWDSrcMuxOut = self.pipeline_registers['MemAccReg_busRData']
        elif self.control_signals['RFWDSrcMuxSel'] == 2:
            RFWDSrcMuxOut = self.pipeline_registers['DecReg_immExt']
        elif self.control_signals['RFWDSrcMuxSel'] == 3:
            RFWDSrcMuxOut = PC_Imm_AdderResult
        elif self.control_signals['RFWDSrcMuxSel'] == 4:
            RFWDSrcMuxOut = PC_4_AdderResult
        
        # Register File 쓰기 (Writeback 단계) - 즉시 실행
        if self.control_signals['regFileWe'] and rd != 0:
            self.regfile[rd] = RFWDSrcMuxOut
        
        # 파이프라인 레지스터 업데이트 (Execute 단계)
        if self.control_state in ['R_EXE', 'I_EXE', 'B_EXE', 'LU_EXE', 'AU_EXE', 'J_EXE', 'JL_EXE', 'S_EXE', 'L_EXE']:
            self.pipeline_registers['ExeReg_aluResult'] = aluResult
            self.pipeline_registers['ExeReg_RFData2'] = self.pipeline_registers['DecReg_RFData2']
            self.pipeline_registers['ExeReg_PCSrcMuxOut'] = PCSrcMuxOut
        
        # PC 업데이트 - 즉시 실행 (PCEn이 1일 때)
        if self.control_signals['PCEn']:
            self.pipeline_registers['PCOutData'] = PCSrcMuxOut
        
        # x0 레지스터는 항상 0
        self.regfile[0] = 0
    
    def extract_immediate(self, instruction):
        """Immediate 값 추출 (immExtend 모듈과 동일)"""
        opcode = instruction & 0x7F
        func3 = (instruction >> 12) & 0x7
        
        if opcode == 0x33:  # R-type
            return 0
        elif opcode == 0x03:  # L-type
            imm = ((instruction >> 20) & 0xFFF)
            if imm & 0x800:
                imm |= 0xFFFFF000
            return imm
        elif opcode == 0x23:  # S-type
            imm = ((instruction >> 25) & 0x7F) << 5 | ((instruction >> 7) & 0x1F)
            if imm & 0x800:
                imm |= 0xFFFFF000
            return imm
        elif opcode == 0x13:  # I-type
            if func3 in [1, 5]:  # SLLI, SRLI, SRAI
                return (instruction >> 20) & 0x1F
            elif func3 == 3:  # SLTIU
                return (instruction >> 20) & 0xFFF
            else:
                imm = ((instruction >> 20) & 0xFFF)
                if imm & 0x800:
                    imm |= 0xFFFFF000
                return imm
        elif opcode == 0x63:  # B-type
            imm_12 = (instruction >> 31) & 0x1
            imm_11 = (instruction >> 7) & 0x1
            imm_10_5 = (instruction >> 25) & 0x3F
            imm_4_1 = (instruction >> 8) & 0xF
            imm = (imm_12 << 12) | (imm_11 << 11) | (imm_10_5 << 5) | (imm_4_1 << 1)
            if imm & 0x1000:
                imm |= 0xFFFFE000
            return imm
        elif opcode in [0x37, 0x17]:  # LUI, AUIPC
            return (instruction >> 12) & 0xFFFFF
        elif opcode == 0x6F:  # JAL
            imm_20 = (instruction >> 31) & 0x1
            imm_19_12 = (instruction >> 12) & 0xFF
            imm_11 = (instruction >> 20) & 0x1
            imm_10_1 = (instruction >> 21) & 0x3FF
            imm = (imm_20 << 20) | (imm_19_12 << 12) | (imm_11 << 11) | (imm_10_1 << 1)
            if imm & 0x100000:
                imm |= 0xFFE00000
            return imm
        elif opcode == 0x67:  # JALR
            imm = ((instruction >> 20) & 0xFFF)
            if imm & 0x800:
                imm |= 0xFFFFF000
            return imm
        return 0
    
    def execute_alu(self, a, b, aluControl):
        """ALU 실행 (alu 모듈과 동일)"""
        # 32비트 부호 있는 정수로 처리
        a_signed = a if a < 0x80000000 else a - 0x100000000
        b_signed = b if b < 0x80000000 else b - 0x100000000
        
        if aluControl == 0:  # ADD
            result = (a + b) & 0xFFFFFFFF
        elif aluControl == 8:  # SUB
            result = (a - b) & 0xFFFFFFFF
        elif aluControl == 1:  # SLL
            result = (a << (b & 0x1F)) & 0xFFFFFFFF
        elif aluControl == 5:  # SRL
            result = (a >> (b & 0x1F)) & 0xFFFFFFFF
        elif aluControl == 13:  # SRA
            if a & 0x80000000:  # 음수인 경우
                result = ((a >> (b & 0x1F)) | (0xFFFFFFFF << (32 - (b & 0x1F)))) & 0xFFFFFFFF
            else:
                result = (a >> (b & 0x1F)) & 0xFFFFFFFF
        elif aluControl == 2:  # SLT
            result = 1 if a_signed < b_signed else 0
        elif aluControl == 3:  # SLTU
            result = 1 if a < b else 0
        elif aluControl == 4:  # XOR
            result = a ^ b
        elif aluControl == 6:  # OR
            result = a | b
        elif aluControl == 7:  # AND
            result = a & b
        elif aluControl == 0x10:  # BEQ
            result = 1 if a == b else 0
        elif aluControl == 0x11:  # BNE
            result = 1 if a != b else 0
        elif aluControl == 0x14:  # BLT
            result = 1 if a_signed < b_signed else 0
        elif aluControl == 0x15:  # BGE
            result = 1 if a_signed >= b_signed else 0
        elif aluControl == 0x16:  # BLTU
            result = 1 if a < b else 0
        elif aluControl == 0x17:  # BGEU
            result = 1 if a >= b else 0
        else:
            result = 0
            
        return result
      
    def update_displays(self):
        # 상단 정보 업데이트
        self.cycle_label.config(text=str(self.cycle_count))
        self.instruction_label.config(text=str(self.instruction_count))
        self.state_label.config(text=self.control_state)
        self.pc_label.config(text=f"0x{self.pipeline_registers['PCOutData']:08X}")
        
        # 파이프라인 레지스터 정보 업데이트
        self.pipeline_text.delete(1.0, tk.END)
        pipeline_info = f"PC: 0x{self.pipeline_registers['PCOutData']:08X} | "
        pipeline_info += f"RF1: 0x{self.pipeline_registers['DecReg_RFData1']:08X} | "
        pipeline_info += f"RF2: 0x{self.pipeline_registers['DecReg_RFData2']:08X} | "
        pipeline_info += f"IMM: 0x{self.pipeline_registers['DecReg_immExt']:08X} | "
        pipeline_info += f"ALU: 0x{self.pipeline_registers['ExeReg_aluResult']:08X} | "
        pipeline_info += f"PC_SRC: 0x{self.pipeline_registers['ExeReg_PCSrcMuxOut']:08X} | "
        pipeline_info += f"BUS_ADDR: 0x{self.pipeline_registers['MemAccReg_busAddr']:08X} | "
        pipeline_info += f"BUS_WDATA: 0x{self.pipeline_registers['MemAccReg_busWData']:08X} | "
        pipeline_info += f"BUS_RDATA: 0x{self.pipeline_registers['MemAccReg_busRData']:08X}\n\n"
        
        # 제어 신호 정보
        control_info = "제어신호: "
        control_info += f"PCEn={self.control_signals['PCEn']} "
        control_info += f"regFileWe={self.control_signals['regFileWe']} "
        control_info += f"aluSrcMuxSel={self.control_signals['aluSrcMuxSel']} "
        control_info += f"busWe={self.control_signals['busWe']} "
        control_info += f"RFWDSrcMuxSel={self.control_signals['RFWDSrcMuxSel']} "
        control_info += f"branch={self.control_signals['branch']} "
        control_info += f"jal={self.control_signals['jal']} "
        control_info += f"jalr={self.control_signals['jalr']} "
        control_info += f"aluControl=0x{self.aluControl:02X} "
        control_info += f"ramControl={self.ramControl}\n\n"
        
        # 현재 명령어 정보
        instruction_info = f"현재명령어: 0x{self.current_instruction:08X} "
        if self.current_instruction != 0:
            opcode = self.current_instruction & 0x7F
            rs1 = (self.current_instruction >> 15) & 0x1F
            rs2 = (self.current_instruction >> 20) & 0x1F
            rd = (self.current_instruction >> 7) & 0x1F
            instruction_info += f"(opcode=0x{opcode:02X}, rs1=x{rs1}, rs2=x{rs2}, rd=x{rd})"
        
        self.pipeline_text.insert(tk.END, pipeline_info + control_info + instruction_info)
        
        # 레지스터 파일 업데이트
        self.reg_text.delete(1.0, tk.END)
        reg_names = ["zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2", "s0", "s1", 
                    "a0", "a1", "a2", "a3", "a4", "a5", "a6", "a7", "s2", "s3", "s4",
                    "s5", "s6", "s7", "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6"]
        
        for i in range(32):
            value = self.regfile[i]
            if i == 0:  # x0는 항상 0
                value = 0
            # 부호 있는 값 계산
            signed_value = value
            if value & 0x80000000:  # 음수인 경우
                signed_value = value - 0x100000000
            self.reg_text.insert(tk.END, f"x{i:2d}({reg_names[i]:4s}): 0x{value:08X} ({signed_value:10d})\n")
        
        # RAM 메모리 업데이트
        self.ram_text.delete(1.0, tk.END)
        for i in range(0, 1024, 4):  # 4바이트씩 표시 (256개 워드)
            word = self.ram.read_word(i)
            # 모든 주소의 값을 표시 (0이어도 표시)
            self.ram_text.insert(tk.END, f"0x{i:04X}: 0x{word:08X}\n")
        
        # ROM 메모리 업데이트
        self.rom_text.delete(1.0, tk.END)
        for i in range(0, 1024, 4):  # 4바이트씩 표시 (256개 워드)
            word = self.rom.read_word(i)
            if word != 0:  # 0이 아닌 값만 표시
                self.rom_text.insert(tk.END, f"0x{i:04X}: 0x{word:08X}\n")
    
    def start_monitoring(self):
        def monitor_loop():
            while True:
                if self.simulation_running:
                    self.step_execution()
                    
                    # 시뮬레이션이 정지되었는지 확인
                    if not self.simulation_running:
                        # GUI 업데이트를 메인 스레드에서 실행
                        self.root.after(0, lambda: self.status_label.config(text="시뮬레이션 완료"))
                        print("시뮬레이션 자동 종료됨")
                        break
                    
                    time.sleep(0.1)  # 100ms 딜레이
                time.sleep(0.01)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
    
    def save_state(self):
        """현재 상태를 히스토리에 저장"""
        # 깊은 복사로 현재 상태 저장
        regfile_copy = self.regfile.copy()
        ram_copy = Memory(1024)
        ram_copy.data = self.ram.data.copy()  # 바이트어레이 복사
        pc_copy = self.pipeline_registers['PCOutData'] # PC 복사
        cycle_copy = self.cycle_count # 사이클 카운터 복사
        
        self.history.append((regfile_copy, ram_copy, pc_copy, cycle_copy))
        
        # 히스토리 크기 제한
        if len(self.history) > self.max_history:
            self.history.pop(0)
    
    def undo_step(self):
        """이전 단계로 되돌리기"""
        if len(self.history) > 0:
            # 히스토리에서 이전 상태 복원
            prev_regfile, prev_ram, prev_pc, prev_cycle = self.history.pop()
            
            self.regfile = prev_regfile
            self.ram.data = prev_ram.data.copy()  # 바이트어레이 복사
            self.pipeline_registers['PCOutData'] = prev_pc # PC 복원
            self.cycle_count = prev_cycle # 사이클 카운터 복원
            
            # 디스플레이 업데이트
            self.update_displays()
            
            # 상태 메시지 업데이트
            rom_index = self.pipeline_registers['PCOutData'] // 4
            if rom_index < 256:  # ROM 크기: 1024바이트 = 256워드
                instruction = self.rom.read_word(self.pipeline_registers['PCOutData'])
                self.status_label.config(text=f"되돌림: PC: 0x{self.pipeline_registers['PCOutData']:04X} (다음 명령어: 0x{instruction:08X})")
            else:
                self.status_label.config(text=f"되돌림: PC: 0x{self.pipeline_registers['PCOutData']:04X} (ROM 범위 초과)")
            
            print(f"되돌리기 완료: PC 0x{self.pipeline_registers['PCOutData']:04X}")
        else:
            self.status_label.config(text="되돌릴 단계가 없습니다")
            print("되돌릴 단계가 없습니다")
    
    def start_logging(self):
        """로그 파일 시작"""
        try:
            self.log_file = open("python_simulation_log.txt", "w")
            self.log_file.write("cycle PC Instruction BusAddr BusWData BusRData BusWe\n")
            self.status_label.config(text="로그 기록 시작")
            print("로그 파일 시작: python_simulation_log.txt")
        except Exception as e:
            print(f"로그 파일 생성 오류: {e}")
    
    def stop_logging(self):
        """로그 파일 정지"""
        if self.log_file:
            self.log_file.close()
            self.log_file = None
            self.status_label.config(text="로그 기록 정지")
            print("로그 파일 정지")
    
    def write_log(self, cycle, pc, instruction, bus_addr, bus_wdata, bus_rdata, bus_we):
        """로그 파일에 한 줄 기록"""
        if self.log_file:
            self.log_file.write(f"{cycle} 0x{pc:08X} 0x{instruction:08X} 0x{bus_addr:08X} 0x{bus_wdata:08X} 0x{bus_rdata:08X} {bus_we}\n")
            self.log_file.flush()  # 즉시 파일에 쓰기
    
    def read_vivado_log(self):
        """Vivado 테스트벤치 로그 파일 읽기"""
        try:
            with open("simulation_log.txt", "r") as f:
                lines = f.readlines()
                
            # 헤더 건너뛰기
            if lines and "cycle" in lines[0]:
                lines = lines[1:]
            
            # 로그 분석
            vivado_data = []
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 7:
                    cycle = int(parts[0])
                    pc = int(parts[1], 16)
                    instruction = int(parts[2], 16)
                    bus_addr = int(parts[3], 16)
                    bus_wdata = int(parts[4], 16)
                    bus_rdata = int(parts[5], 16)
                    bus_we = int(parts[6])
                    
                    vivado_data.append({
                        'cycle': cycle,
                        'pc': pc,
                        'instruction': instruction,
                        'bus_addr': bus_addr,
                        'bus_wdata': bus_wdata,
                        'bus_rdata': bus_rdata,
                        'bus_we': bus_we
                    })
            
            # 결과 표시
            self.show_vivado_log(vivado_data)
            
        except FileNotFoundError:
            self.status_label.config(text="Vivado 로그 파일을 찾을 수 없습니다")
            print("simulation_log.txt 파일이 없습니다")
        except Exception as e:
            self.status_label.config(text=f"로그 읽기 오류: {str(e)}")
            print(f"로그 읽기 오류: {e}")
    
    def show_vivado_log(self, vivado_data):
        """Vivado 로그 데이터를 새 창에 표시"""
        # 새 창 생성
        log_window = tk.Toplevel(self.root)
        log_window.title("Vivado 테스트벤치 로그")
        log_window.geometry("800x600")
        
        # 텍스트 위젯
        text_widget = tk.Text(log_window, font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(log_window, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 헤더
        text_widget.insert(tk.END, "Vivado 테스트벤치 로그 분석\n")
        text_widget.insert(tk.END, "=" * 80 + "\n")
        text_widget.insert(tk.END, f"총 {len(vivado_data)}개 사이클\n\n")
        
        # 데이터 표시
        for i, data in enumerate(vivado_data[:50]):  # 처음 50개만 표시
            text_widget.insert(tk.END, f"사이클 {data['cycle']:3d}: ")
            text_widget.insert(tk.END, f"PC=0x{data['pc']:08X} ")
            text_widget.insert(tk.END, f"Inst=0x{data['instruction']:08X} ")
            text_widget.insert(tk.END, f"Addr=0x{data['bus_addr']:08X} ")
            text_widget.insert(tk.END, f"WData=0x{data['bus_wdata']:08X} ")
            text_widget.insert(tk.END, f"RData=0x{data['bus_rdata']:08X} ")
            text_widget.insert(tk.END, f"We={data['bus_we']}\n")
        
        if len(vivado_data) > 50:
            text_widget.insert(tk.END, f"\n... (총 {len(vivado_data)}개 중 50개만 표시)\n")
        
        text_widget.config(state=tk.DISABLED)  # 읽기 전용

if __name__ == "__main__":
    root = tk.Tk()
    app = RISCVMemoryMonitor(root)
    root.mainloop()
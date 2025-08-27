# APB (Advanced Peripheral Bus) 마스터/슬레이브 설계 리뷰

## 목차
1. [APB 프로토콜 개요](#apb-프로토콜-개요)
2. [APB 마스터 설계](#apb-마스터-설계)
3. [APB 슬레이브 설계](#apb-슬레이브-설계)
4. [주소 디코딩 및 멀티플렉싱](#주소-디코딩-및-멀티플렉싱)
5. [시뮬레이션 및 테스트](#시뮬레이션-및-테스트)
6. [학습 포인트](#학습-포인트)

---

## APB 프로토콜 개요

### APB의 특징
- **단순한 버스 프로토콜**: 복잡한 타이밍 제어 불필요
- **단일 클럭 전송**: 모든 전송이 PCLK에 동기화
- **비파이프라인**: 단순한 요청-응답 구조
- **저전력**: 필요할 때만 활성화

### APB 전송 시퀀스
1. **IDLE**: 대기 상태
2. **SETUP**: 주소와 제어 신호 설정 (PSEL=1, PENABLE=0)
3. **ACCESS**: 데이터 전송 (PSEL=1, PENABLE=1)
4. **IDLE**: 전송 완료 후 대기

---

## APB 마스터 설계

### 모듈 구조
```systemverilog
module APB_Master (
    // 글로벌 신호
    input logic PCLK, PRESET,
    
    // APB 인터페이스 신호
    output logic [31:0] PADDR, PWDATA,
    output logic PWRITE, PENABLE,
    output logic [3:0] PSELx,
    input logic [31:0] PRDATAx,
    input logic PREADYx,
    
    // 내부 인터페이스
    input logic transfer, write,
    input logic [31:0] addr, wdata,
    output logic ready,
    output logic [31:0] rdata
);
```

### 상태 머신
```systemverilog
typedef enum {
    IDLE,    // 대기 상태
    SETUP,   // 설정 단계
    ACCESS   // 접근 단계
} apb_state_e;
```

### 핵심 기능
1. **주소 디코딩**: 내부 주소를 APB 주소로 변환
2. **상태 제어**: APB 프로토콜에 따른 상태 전환
3. **데이터 멀티플렉싱**: 여러 슬레이브의 응답 처리

---

## APB 슬레이브 설계

### 기본 슬레이브 구조
```systemverilog
module APB_SLAVE (
    // 글로벌 신호
    input logic PCLK, PRESET,
    
    // APB 인터페이스
    input logic [31:0] PADDR, PWDATA,
    input logic PWRITE, PENABLE, PSEL,
    output logic [31:0] PRDATA,
    output logic PREADY
);
```

### RAM 슬레이브 구현
```systemverilog
module APB_RAM_SLAVE (
    // APB 인터페이스
    input logic PCLK, PRESET,
    input logic [31:0] PADDR, PWDATA,
    input logic PWRITE, PENABLE, PSEL,
    output logic [31:0] PRDATA,
    output logic PREADY
);
    
    // 주소 오프셋 처리
    assign ram_addr = PADDR - 32'h1000_0000;
    
    // RAM 인스턴스
    RAM u_ram(
        .clk(PCLK),
        .we(PSEL && PENABLE && PWRITE),
        .addr(ram_addr),
        .wData(PWDATA),
        .rData(PRDATA)
    );
```

### 핵심 개념
1. **주소 오프셋**: APB 주소에서 슬레이브별 베이스 주소 제거
2. **PREADY 신호**: 전송 완료를 마스터에게 알림
3. **PSEL 처리**: 슬레이브 선택 및 활성화

---

## 주소 디코딩 및 멀티플렉싱

### APB 디코더
```systemverilog
module APB_Decoder (
    input logic [31:0] sel,
    output logic [3:0] y,
    output logic [1:0] mux_sel
);
    always_comb begin
        casex (sel)
            32'h1000_0xxx: y = 4'b0001;  // RAM
            32'h1000_1xxx: y = 4'b0010;  // GPO
            32'h1000_2xxx: y = 4'b0100;  // GPI
            32'h1000_3xxx: y = 4'b1000;  // GPIO
        endcase
    end
endmodule
```

### APB 멀티플렉서
```systemverilog
module APB_Mux (
    input logic [1:0] sel,
    input logic [31:0] rdata0, rdata1, rdata2, rdata3,
    input logic ready0, ready1, ready2, ready3,
    output logic [31:0] rdata,
    output logic ready
);
    always_comb begin
        case (sel)
            2'd0: rdata = rdata0;  // RAM
            2'd1: rdata = rdata1;  // GPO
            2'd2: rdata = rdata2;  // GPI
            2'd3: rdata = rdata3;  // GPIO
        endcase
    end
endmodule
```

### 주소 매핑
| 슬레이브 | 주소 범위 | PSEL | 용도 |
|----------|-----------|------|------|
| RAM | 32'h1000_0xxx | PSEL0 | 메모리 |
| GPO | 32'h1000_1xxx | PSEL1 | 출력 포트 |
| GPI | 32'h1000_2xxx | PSEL2 | 입력 포트 |
| GPIO | 32'h1000_3xxx | PSEL3 | 입출력 포트 |

---

## 시뮬레이션 및 테스트

### 테스트벤치 구조
```systemverilog
module Tb_Sim();
    // 글로벌 신호
    logic PCLK, PRESET;
    
    // APB 인터페이스
    logic [31:0] PADDR, PWDATA;
    logic PWRITE, PENABLE;
    logic [3:0] PSELx;
    logic [31:0] PRDATAx;
    logic PREADYx;
    
    // 내부 인터페이스
    logic transfer, ready, write;
    logic [31:0] addr, wdata, rdata;
    
    // 모듈 인스턴스
    APB_Master uapb(.*);
    APB_SLAVE u_slave0(.*);  // RAM
    APB_SLAVE u_slave1(.*);  // GPO
    APB_SLAVE u_slave2(.*);  // GPI
    APB_SLAVE u_slave3(.*);  // GPIO
endmodule
```

### 테스트 시나리오
1. **쓰기 테스트**: RAM의 특정 주소에 데이터 쓰기
2. **읽기 테스트**: RAM의 특정 주소에서 데이터 읽기
3. **다중 슬레이브 테스트**: 여러 슬레이브에 순차 접근

---

## 학습 포인트

### 이해한 개념들
1. **APB 프로토콜**: 단순하고 효율적인 버스 프로토콜
2. **상태 머신**: IDLE → SETUP → ACCESS 순서의 중요성
3. **주소 디코딩**: 슬레이브 선택을 위한 주소 해석
4. **멀티플렉싱**: 여러 슬레이브의 응답 처리
5. **주소 오프셋**: 슬레이브별 로컬 주소 변환

### 핵심 설계 원칙
1. **모듈화**: 마스터와 슬레이브의 명확한 분리
2. **재사용성**: 범용적인 APB 슬레이브 인터페이스
3. **확장성**: 새로운 슬레이브 추가 용이
4. **표준 준수**: AMBA APB 프로토콜 규격 준수

### 기술적 세부사항
1. **동기 설계**: 모든 신호가 PCLK에 동기화
2. **리셋 처리**: PRESET 신호를 통한 초기화
3. **핸드셰이킹**: PREADY 신호를 통한 전송 완료 확인
4. **주소 정렬**: 워드 단위 주소 처리

---

## 추가 학습 방향
1. **AHB 프로토콜**: 고성능 버스 프로토콜 학습
2. **AXI 프로토콜**: 최신 고대역폭 버스 프로토콜
3. **버스 아비터**: 다중 마스터 환경에서의 버스 제어
4. **버스 브리지**: 서로 다른 버스 프로토콜 간 변환

---

## 데이터 정리 표 추천

### 1. APB 신호 정의표
| 신호명 | 방향 | 비트 | 설명 |
|--------|------|------|------|
| PCLK | input | 1 | APB 클럭 |
| PRESET | input | 1 | APB 리셋 (활성 HIGH) |
| PADDR | output | 32 | 주소 버스 |
| PWRITE | output | 1 | 쓰기/읽기 제어 (1=쓰기, 0=읽기) |
| PENABLE | output | 1 | 전송 활성화 신호 |
| PWDATA | output | 32 | 쓰기 데이터 |
| PSELx | output | 4 | 슬레이브 선택 신호 |
| PRDATAx | input | 32 | 읽기 데이터 |
| PREADYx | input | 4 | 전송 완료 신호 |

### 2. 상태 머신 전이표
| 현재 상태 | 조건 | 다음 상태 | 동작 |
|-----------|------|-----------|------|
| IDLE | transfer=1 | SETUP | 주소/데이터 설정 |
| SETUP | - | ACCESS | PSEL=1, PENABLE=0 |
| ACCESS | PREADY=1 | IDLE | 데이터 전송 완료 |

### 3. 주소 디코딩표
| 주소 범위 | PSEL | 슬레이브 | 내부 주소 변환 |
|-----------|------|----------|----------------|
| 32'h1000_0000~0FFF | PSEL0 | RAM | PADDR-32'h1000_0000 |
| 32'h1000_1000~1FFF | PSEL1 | GPO | PADDR-32'h1000_1000 |
| 32'h1000_2000~2FFF | PSEL2 | GPI | PADDR-32'h1000_2000 |
| 32'h1000_3000~3FFF | PSEL3 | GPIO | PADDR-32'h1000_3000 |

### 4. 타이밍 시퀀스표
| 클럭 | 상태 | PSEL | PENABLE | PADDR | PWDATA | 동작 |
|------|------|------|---------|-------|--------|------|
| T1 | IDLE | 0 | 0 | - | - | 대기 |
| T2 | SETUP | 1 | 0 | 설정 | 설정 | 주소 설정 |
| T3 | ACCESS | 1 | 1 | 유지 | 유지 | 데이터 전송 |
| T4 | IDLE | 0 | 0 | - | - | 완료 |

### 5. 테스트 케이스표
| 테스트 번호 | 동작 | 주소 | 데이터 | 예상 결과 |
|-------------|------|------|--------|-----------|
| TC001 | 쓰기 | 32'h1000_0000 | 32'd10 | RAM[0]=10 |
| TC002 | 읽기 | 32'h1000_0000 | - | rdata=10 |
| TC003 | 쓰기 | 32'h1000_0004 | 32'd20 | RAM[1]=20 |
| TC004 | 읽기 | 32'h1000_0004 | - | rdata=20 |

---


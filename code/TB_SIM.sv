`timescale 1ns / 1ps

module testbench_with_monitor();
    logic clk;
    logic reset;
    
    // MCU 인스턴스
    MCU u_mcu (
        .clk(clk),
        .reset(reset)
    );
    
    // 클럭 생성
    initial begin
        clk = 0;
        forever #5 clk = ~clk;
    end
    
    // 테스트 시나리오
    initial begin
        // 리셋
        reset = 1;
        #20;
        reset = 0;
        
        // 시뮬레이션 실행
        #1000;
        
        $finish;
    end
    
    // 실시간 모니터링
    always @(posedge clk) begin
        $display("=== clock cycle %0d ===", $time/10);
        $display("PC: 0x%08X", u_mcu.instrMemAddr);
        $display("Instruction: 0x%08X", u_mcu.instrCode);
        $display("Bus Address: 0x%08X", u_mcu.busAddr);
        $display("Bus Write Data: 0x%08X", u_mcu.busWData);
        $display("Bus Read Data: 0x%08X", u_mcu.busRData);
        $display("Bus Write Enable: %b", u_mcu.busWe);
        $display("---");
    end
    
    // 파일 출력을 통한 GUI 연동
    integer file_handle;
    initial begin
        file_handle = $fopen("simulation_log.txt", "w");
    end
    
    always @(posedge clk) begin
        $fdisplay(file_handle, "%0d 0x%08X 0x%08X 0x%08X 0x%08X 0x%08X %b", 
                 $time/10, u_mcu.instrMemAddr, u_mcu.instrCode, 
                 u_mcu.busAddr, u_mcu.busWData, u_mcu.busRData, u_mcu.busWe);
    end
    
    initial begin
        #10000;
        $fclose(file_handle);
    end
endmodule
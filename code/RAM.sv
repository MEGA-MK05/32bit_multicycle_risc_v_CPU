`timescale 1ns / 1ps

module RAM (
    input  logic        clk,
    input  logic        we,
    input  logic [31:0] addr,
    input  logic [31:0] wData,
    output logic [31:0] rData
);
    logic [31:0] mem[0:2**8-1]; // 0x00 ~ 0x0f => 0x10 * 4 => 0x40

    always_ff @( posedge clk ) begin
        if (we) mem[addr[31:2]] <= wData;
    end

    assign rData = mem[addr[31:2]];
endmodule





module RAMController (
    input  logic        clk,
    input  logic        we,
    input  logic [31:0] addr,
    input  logic [31:0] wData,
    output logic [31:0] rData,
    input  logic [2:0]  ramControl
);
    logic        ram_we;
    logic [31:0] ram_addr;
    logic [31:0] ram_wData;
    logic [31:0] ram_rData;
    logic [31:0] write_data;
    logic [31:0] read_data;

    RAM u_ram (
        .clk(clk),
        .we(ram_we),
        .addr(ram_addr),
        .wData(ram_wData),
        .rData(ram_rData)
    );

    // Write 데이터 처리
    always_comb begin
        case(ramControl)
            3'b001: begin // SB (Store Byte)
                case(addr[1:0])
                    2'b00: write_data = {ram_rData[31:8], wData[7:0]};
                    2'b01: write_data = {ram_rData[31:16], wData[7:0], ram_rData[7:0]};
                    2'b10: write_data = {ram_rData[31:24], wData[7:0], ram_rData[15:0]};
                    2'b11: write_data = {wData[7:0], ram_rData[23:0]};
                endcase
            end
            3'b010: begin // SH (Store Halfword)
                case(addr[1])
                    1'b0: write_data = {ram_rData[31:16], wData[15:0]};
                    1'b1: write_data = {wData[15:0], ram_rData[15:0]};
                endcase
            end
            default: write_data = wData; // SW (Store Word)
        endcase
    end

    // Read 데이터 처리
    always_comb begin
        case(ramControl)
            3'b001: begin // LB (Load Byte - signed)
                case(addr[1:0])
                    2'b00: read_data = {{24{ram_rData[7]}}, ram_rData[7:0]};
                    2'b01: read_data = {{24{ram_rData[15]}}, ram_rData[15:8]};
                    2'b10: read_data = {{24{ram_rData[23]}}, ram_rData[23:16]};
                    2'b11: read_data = {{24{ram_rData[31]}}, ram_rData[31:24]};
                endcase
            end
            3'b010: begin // LH (Load Halfword - signed)
                case(addr[1])
                    1'b0: read_data = {{16{ram_rData[15]}}, ram_rData[15:0]};
                    1'b1: read_data = {{16{ram_rData[31]}}, ram_rData[31:16]};
                endcase
            end
            3'b101: begin // LBU (Load Byte - unsigned)
                case(addr[1:0])
                    2'b00: read_data = {24'b0, ram_rData[7:0]};
                    2'b01: read_data = {24'b0, ram_rData[15:8]};
                    2'b10: read_data = {24'b0, ram_rData[23:16]};
                    2'b11: read_data = {24'b0, ram_rData[31:24]};
                endcase
            end
            3'b110: begin // LHU (Load Halfword - unsigned)
                case(addr[1])
                    1'b0: read_data = {16'b0, ram_rData[15:0]};
                    1'b1: read_data = {16'b0, ram_rData[31:16]};
                endcase
            end
            default: read_data = ram_rData; // LW (Load Word)
        endcase
    end

    // RAM 연결
    assign ram_we = we;
    assign ram_addr = addr;
    assign ram_wData = write_data;
    assign rData = read_data;

endmodule

module TOP_RAM (
    input  logic        clk,
    input  logic        we,
    input  logic [31:0] addr,
    input  logic [31:0] wData,
    output logic [31:0] rData,
    input  logic [2:0]  ramControl
);
    RAMController controller (
        .clk(clk),
        .we(we),
        .addr(addr),
        .wData(wData),
        .rData(rData),
        .ramControl(ramControl)
    );
endmodule


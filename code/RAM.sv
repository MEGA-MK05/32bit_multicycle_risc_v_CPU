`timescale 1ns / 1ps

// module RAM (
//     input  logic        clk,
//     input  logic        we,
//     input  logic [31:0] addr,
//     input  logic [31:0] wData,
//     output logic [31:0] rData
// );
//     logic [31:0] mem[0:2**4-1]; // 0x00 ~ 0x0f => 0x10 * 4 => 0x40

//     always_ff @( posedge clk ) begin
//         if (we) mem[addr[31:2]] <= wData;
//     end

//     assign rData = mem[addr[31:2]];
// endmodule


module RAM (
    input  logic        clk,
    input  logic        we,
    input  logic [31:0] addr,
    input  logic [31:0] wData,
    output logic [31:0] rData,
    input  logic [2:0]  ramControl
);
    logic [31:0] mem[0:2**8-1]; 

    always_ff @( posedge clk ) begin
        if (we) begin
            case(ramControl)
                3'b001: begin 
                    case(addr[1:0])
                        2'b00: mem[addr[31:2]][7:0] <= wData[7:0];
                        2'b01: mem[addr[31:2]][15:8] <= wData[7:0];
                        2'b10: mem[addr[31:2]][23:16] <= wData[7:0];
                        2'b11: mem[addr[31:2]][31:24] <= wData[7:0];
                    endcase
                end
                3'b010: begin 
                    case(addr[1])
                        1'b0: mem[addr[31:2]][15:0] <= wData[15:0];
                        1'b1: mem[addr[31:2]][31:16] <= wData[15:0];
                    endcase
                end
                default: mem[addr[31:2]] <= wData; 
            endcase
        end
    end
    
    always_comb begin
        case(ramControl)
            3'b001: begin 
                case(addr[1:0])
                    2'b00: rData = {{24{mem[addr[31:2]][7]}},mem[addr[31:2]][7:0]};
                    2'b01: rData = {{24{mem[addr[31:2]][15]}},mem[addr[31:2]][15:8]};
                    2'b10: rData = {{24{mem[addr[31:2]][23]}},mem[addr[31:2]][23:16]};
                    2'b11: rData = {{24{mem[addr[31:2]][31]}},mem[addr[31:2]][31:24]};
                endcase
            end
            3'b010: begin 
                case(addr[1])
                    1'b0: rData = {{16{mem[addr[31:2]][15]}},mem[addr[31:2]][15:0]};
                    1'b1: rData = {{16{mem[addr[31:2]][31]}},mem[addr[31:2]][31:16]};
                endcase
            end
            3'b101: begin //
                case(addr[1:0])
                    2'b00: rData = {24'b0,mem[addr[31:2]][7:0]};
                    2'b01: rData = {24'b0,mem[addr[31:2]][15:8]};
                    2'b10: rData = {24'b0,mem[addr[31:2]][23:16]};
                    2'b11: rData = {24'b0,mem[addr[31:2]][31:24]};
                endcase
            end
            3'b110: begin //
                case(addr[1])
                    1'b0: rData = {16'b0,mem[addr[31:2]][15:0]};
                    1'b1: rData = {16'b0,mem[addr[31:2]][31:16]};
                endcase
            end
            default: rData = mem[addr[31:2]]; 
        endcase
    end
endmodule


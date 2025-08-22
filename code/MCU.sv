`timescale 1ns / 1ps

module MCU (
    input logic clk,
    input logic reset,
    output logic busWe
);
    logic [31:0] instrCode;
    logic [31:0] instrMemAddr;
    logic        busWe;
    logic [31:0] busAddr;
    logic [31:0] busWData;
    logic [31:0] busRData;
    logic [2:0] ramControl;

    ROM U_ROM (
        .addr(instrMemAddr),
        .data(instrCode)
    );

    CPU_RV32I U_RV32I (.*);


    TOP_RAM U_topram (
        .clk  (clk),
        .we   (busWe),
        .addr (busAddr),
        .ramControl(ramControl),
        .wData(busWData),
        .rData(busRData)
    );
endmodule

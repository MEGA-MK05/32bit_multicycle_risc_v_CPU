```c
int main()
{
    int arData[6] = {5,4,3,2,1};
    
    int *pData = arData;
    int size = 5;
    
    for(int i = 0; i < size; i++) {
        for(int j = 0; j < size-i-1; j++) {
            if(pData[j] > pData[j+1]) {
                // swap 로직이 내부 처리리
                int temp = pData[j];
                pData[j] = pData[j+1];
                pData[j+1] = temp;
            }
        }
    }
    
    return 0;
}
```


이전에 c로 구성한 내 코드를 risc-v 구조에 맞는 asm 명령어로 바꿔주는  
"https://godbolt.org/" 사이트를 활용해서 asm 코드로 바꾸고  
"https://riscvasm.lucasteske.dev/#" 사이트를 활용해서 기계언어로 바꾸어   
rom에다가 저장해주었다.

하지만 이전 코드의 문제점은 아래에 해당하는 모든 코드에 명령어가 포함되지 않은 채로 asm 처리가 된것이다. 다음에 만들 코드는 버블 sorting을 활용하는 것이 아닌 아래 기술된 모든 명령어를 활용해서 만들 수 있는 다른 알고리즘을 만들 예정이다.



```asm
확인 해야 될 asm 명령어.


add
sub
sli
srl
sra
slt
sltu
xor
or
and


lb
lh
lw
lbu
lhu
addi
slti
sltiu
xori
ori
andi
slli
srli
srai



sb
sh
sw

beq
bne
blt
bge
bltu
bgeu

lui
auipc
jal
jalr
```


{R-type}

```c
int main() {
    int a = 10, b = 5, c = 0;
    unsigned int ua = 10, ub = 5;
    
    // R-type 산술/논리 연산 검증
    c = a + b;      // add
    c = a - b;      // sub
    c = a << 2;     // sll
    c = (unsigned int)a >> b;  // srl
    c = a >> 2;     // sra
    c = (a < b) ? 1 : 0;     // slt
    c = (ua < ub) ? 1 : 0;   // sltu
    c = a ^ b;      // xor
    c = a | b;      // or
    c = a & b;      // and
    
    return c;
}
```

```asm
		li 		sp, 0x40
main:
        addi    sp,sp,-48
        sw      ra,44(sp)
        sw      s0,40(sp)
        addi    s0,sp,48
        li      a5,10
        sw      a5,-20(s0)
        li      a5,5
        sw      a5,-24(s0)
        sw      zero,-28(s0)
        li      a5,10
        sw      a5,-32(s0)
        li      a5,5
        sw      a5,-36(s0)
        lw      a4,-20(s0)
        lw      a5,-24(s0)
        add     a5,a4,a5
        sw      a5,-28(s0)
        lw      a4,-20(s0)
        lw      a5,-24(s0)
        sub     a5,a4,a5
        sw      a5,-28(s0)
        lw      a5,-20(s0)
        slli    a5,a5,2
        sw      a5,-28(s0)
        lw      a4,-20(s0)
        lw      a5,-24(s0)
        srl     a5,a4,a5
        sw      a5,-28(s0)
        lw      a5,-20(s0)
        srai    a5,a5,2
        sw      a5,-28(s0)
        lw      a4,-20(s0)
        lw      a5,-24(s0)
        slt     a5,a4,a5
        andi    a5,a5,0xff
        sw      a5,-28(s0)
        lw      a4,-32(s0)
        lw      a5,-36(s0)
        sltu    a5,a4,a5
        andi    a5,a5,0xff
        sw      a5,-28(s0)
        lw      a4,-20(s0)
        lw      a5,-24(s0)
        xor     a5,a4,a5
        sw      a5,-28(s0)
        lw      a4,-20(s0)
        lw      a5,-24(s0)
        or      a5,a4,a5
        sw      a5,-28(s0)
        lw      a4,-20(s0)
        lw      a5,-24(s0)
        and     a5,a4,a5
        sw      a5,-28(s0)
        lw      a5,-28(s0)
        mv      a0,a5
        lw      ra,44(sp)
        lw      s0,40(sp)
        addi    sp,sp,48
        jr      ra
```


| 스택 주소 | 내용 | 설명 |
|-----------|------|------|
| 0x40 | [초기값] | 스택 시작 (sp 초기값) |
| 0x3C | ra (return address) | 44(sp) |
| 0x38 | s0 (frame pointer) | 40(sp) |
| 0x34 | [여유공간] | 36(sp) |
| 0x30 | a=10 | -20(s0) |
| 0x2C | b=5 | -24(s0) |
| 0x28 | c=0 (결과값) | -28(s0) |
| 0x24 | ua=10 | -32(s0) |
| 0x20 | ub=5 | -36(s0) |

| 연산 | 계산 | 결과 | 메모리 주소 |
|------|------|------|-------------|
| add | c = 10 + 5 | 15 | [0x28] = 15 |
| sub | c = 10 - 5 | 5 | [0x28] = 5 |
| sll | c = 10 << 2 | 40 | [0x28] = 40 |
| srl | c = 10 >> 5 | 0 | [0x28] = 0 |
| sra | c = 10 >> 2 | 2 | [0x28] = 2 |
| slt | c = (10 < 5) ? 1 : 0 | 0 | [0x28] = 0 |
| sltu | c = (10 < 5) ? 1 : 0 | 0 | [0x28] = 0 |
| xor | c = 10 ^ 5 | 15 | [0x28] = 15 |
| or | c = 10 \| 5 | 15 | [0x28] = 15 |
| and | c = 10 & 5 | 0 | [0x28] = 0 |

## **레지스터 파일 a5 (15번째) 값 변화:**

| 순서 | 명령어 | a5 값 | 설명 |
|------|--------|-------|------|
| 1 | `li a5,10` | 10 | 변수 a 초기화 |
| 2 | `li a5,5` | 5 | 변수 b 초기화 |
| 3 | `li a5,10` | 10 | 변수 ua 초기화 |
| 4 | `li a5,5` | 5 | 변수 ub 초기화 |
| 5 | `add a5,a4,a5` | 15 | add 연산 결과 (10+5) |
| 6 | `sub a5,a4,a5` | 5 | sub 연산 결과 (10-5) |
| 7 | `slli a5,a5,2` | 40 | sll 연산 결과 (10<<2) |
| 8 | `srl a5,a4,a5` | 0 | srl 연산 결과 (10>>5) |
| 9 | `srai a5,a5,2` | 2 | sra 연산 결과 (10>>2) |
| 10 | `slt a5,a4,a5` | 0 | slt 연산 결과 (10<5? 0) |
| 11 | `sltu a5,a4,a5` | 0 | sltu 연산 결과 (10<5? 0) |
| 12 | `xor a5,a4,a5` | 15 | xor 연산 결과 (10^5) |
| 13 | `or a5,a4,a5` | 15 | or 연산 결과 (10\|5) |
| 14 | `and a5,a4,a5` | 0 | and 연산 결과 (10&5) |
| 15 | `mv a0,a5` | 0 | 최종 결과를 a0로 복사 |

**최종 결과: a5 레지스터 = 0 (마지막 and 연산 결과)**

  



{I- type}
```c
int main() {
    int a = 10, c = 0;
    unsigned int ua = 10;
    
    // I-type Immediate 연산 검증
    c = a + 5;      // addi
    c = (a < 5) ? 1 : 0;     // slti
    c = (ua < 5) ? 1 : 0;    // sltiu
    c = a ^ 5;      // xori
    c = a | 5;      // ori
    c = a & 5;      // andi
    c = a << 5;     // slli
    c = (unsigned int)a >> 5;  // srli
    c = a >> 5;     // srai
    
    // I-type Load 명령어 검증
    char byte_val = (char)a;     // lb
    short half_val = (short)a;   // lh
    int word_val = a;            // lw
    unsigned char ubyte = (unsigned char)a;  // lbu
    unsigned short uhalf = (unsigned short)a; // lhu
    
    return c + byte_val + half_val + word_val + ubyte + uhalf;
}
```

```
		li		sp, 0x40
main:
        addi    sp,sp,-48
        sw      ra,44(sp)
        sw      s0,40(sp)
        addi    s0,sp,48
        li      a5,10
        sw      a5,-20(s0)
        sw      zero,-24(s0)
        li      a5,10
        sw      a5,-28(s0)
        lw      a5,-20(s0)
        addi    a5,a5,5
        sw      a5,-24(s0)
        lw      a5,-20(s0)
        slti    a5,a5,5
        andi    a5,a5,0xff
        sw      a5,-24(s0)
        lw      a5,-28(s0)
        sltiu   a5,a5,5
        andi    a5,a5,0xff
        sw      a5,-24(s0)
        lw      a5,-20(s0)
        xori    a5,a5,5
        sw      a5,-24(s0)
        lw      a5,-20(s0)
        ori     a5,a5,5
        sw      a5,-24(s0)
        lw      a5,-20(s0)
        andi    a5,a5,5
        sw      a5,-24(s0)
        lw      a5,-20(s0)
        slli    a5,a5,5
        sw      a5,-24(s0)
        lw      a5,-20(s0)
        srli    a5,a5,5
        sw      a5,-24(s0)
        lw      a5,-20(s0)
        srai    a5,a5,5
        sw      a5,-24(s0)
        lw      a5,-20(s0)
        sb      a5,-29(s0)
        lw      a5,-20(s0)
        sh      a5,-32(s0)
        lw      a5,-20(s0)
        sw      a5,-36(s0)
        lw      a5,-20(s0)
        sb      a5,-37(s0)
        lw      a5,-20(s0)
        sh      a5,-40(s0)
        lbu     a4,-29(s0)
        lw      a5,-24(s0)
        add     a4,a4,a5
        lh      a5,-32(s0)
        add     a4,a4,a5
        lw      a5,-36(s0)
        add     a4,a4,a5
        lbu     a5,-37(s0)
        add     a4,a4,a5
        lhu     a5,-40(s0)
        add     a5,a4,a5
        mv      a0,a5
        lw      ra,44(sp)
        lw      s0,40(sp)
        addi    sp,sp,48
        jr      ra
```

{S/B/J/LU/AU-type} 
```c
int test_function(int a, int b) {
    return a + b;  // jalr로 복귀
}

int main() {
    int a = 10, b = 5, c = 0;
    unsigned int ua = 10, ub = 5;
    
    // S-type Store 명령어 검증
    char byte_val = 0x12;
    short half_val = 0x1234;
    int word_val = 0x12345678;
    
    char* byte_ptr = &byte_val;
    short* half_ptr = &half_val;
    int* word_ptr = &word_val;
    
    *byte_ptr = 0xAA;    // sb
    *half_ptr = 0xBBBB;  // sh
    *word_ptr = 0xCCCCCCCC; // sw
    
    // B-type Branch 명령어 검증
    if (a == b) c = 1;   // beq
    if (a != b) c = 2;   // bne
    if (a < b) c = 3;    // blt
    if (a >= b) c = 4;   // bge
    if (ua < ub) c = 5;  // bltu
    if (ua >= ub) c = 6; // bgeu
    
    // LU-type Load Upper Immediate 검증
    int upper = 0x12345 << 12;  // lui
    
    // AU-type Add Upper Immediate PC 검증
    int pc_upper = 0x1000 + (0x12345 << 12); // auipc
    
    // J-type Jump 명령어 검증
    int result = test_function(a, b);  // jal, jalr
    
    return result + c + upper + pc_upper;
}
```





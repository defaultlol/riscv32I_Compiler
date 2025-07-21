# riscv32I_Compiler(Milestone 2)
#### Members:
- Abdul Raafi M. Bandrang
- Dennis Paulo S. Delgado

**Milestone 2 demo video**: [link](https://youtu.be/lBhajLnlru8)

**Milestone 2 demo site**: [link](https://riscv32icompiler-7zjnzcyvmxep4zimrtq9sn.streamlit.app/) (please run the application instead in case website is down)

### project updates
- implemented gui for memory and register
- implemented sequential run
- implemented step run

### TODO:
- implement pipelining
- add schemes to handle hazards
- implement complemete pipeline map
- extend covered instructions
- extend to other data type directives (byte and half)
- add ABI registers to the parser

### Steps to run locally
install dependencies
```pip install -r requirements.txt```

be sure to be in the working directory. 
run through streamlit cli (installed in the dependencies)
```streamlit run app.py```

#### Register and Memory GUI
Supports only I,B,R,S instructions for word as of the moment. Specifcally covers the following operations: ADD, SUB, LW, SW, ADDI, SLT, SLTI, SLL, SLLI, SRL, SRLI, AND, ANDI, OR, ORI, BEQ, BNE, BLT, BGE.

Also only supports .data, .text, .word, and .global for the directives as of the moment.


ASM code             |  oppcode
:-------------------------:|:-------------------------:
![](images/asmopp.png)  |  ![](images/oppcode.png)


#### Initial Execution Draft
Covers 4 specic error checks "Too many operands", "Not a recognized operator", "Register does not exists", and "Label does not exists". Also supports generic syntax and lexical errors with message "Incorrect Syntax" with column and line numbers.

ASM code             |  error check
:-------------------------:|:-------------------------:
![](images/errorasm.png)  |  ![](images/errorcheck.png)
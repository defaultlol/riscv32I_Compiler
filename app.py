import json
import streamlit as st
from code_editor import code_editor
from itables.sample_dfs import get_countries
from riscvparser import get_instruction_format
from exceptions import RiscSyntaxError

#Register initialization
if 'registers' not in st.session_state:
    st.session_state.registers = {f'x{i}': 0 for i in range(32)}

if 'memory' not in st.session_state:
    st.session_state.memory = {}

# code editor config variables
height = [19, 22]
theme = "default"
shortcuts = "vscode"
focus = False
wrap = True
editor_btns = [{
    "name": "Run",
    "feather": "Play",
    "primary": True,
    "hasText": True,
    "showWithIcon": True,
    "commands": ["submit"],
    "style": {"bottom": "0.44rem", "right": "0.4rem"}
}]
sample_python_code = '''.global main
.text
main:'''
# code editor
response_dict = code_editor(sample_python_code, height=height, theme=theme, shortcuts=shortcuts, focus=focus, buttons=editor_btns, options={"wrap": wrap, "showLineNumbers": True})
# show response dict
if len(response_dict['id']) != 0 and (response_dict['type'] == "selection" or response_dict['type'] == "submit"):
    # Capture the text part
    st.code('Assemble: assembling risc32i sample.')
    code_text = response_dict['text']
    try:
        df = get_instruction_format(code_text)
        st.code('Assemble: operation completed successfully.')
        st.dataframe(df, use_container_width=True)
        for _, row in df.iterrows():
            line = row.get("basic", "")
            st.write(f"Executing: {line}")
            parts = line.replace(",", "").split()
            instr = parts[0].upper()
            try:
                if instr == "ADDI":
                    rd, rs1, imm = parts[1], parts[2], int(parts[3])
                    st.session_state.registers[rd] = st.session_state.registers.get(rs1, 0) + imm

                elif instr == "ADD":
                    rd, rs1, rs2 = parts[1], parts[2], parts[3]
                    st.session_state.registers[rd] = (
                        st.session_state.registers.get(rs1, 0) + st.session_state.registers.get(rs2, 0)
                    )

                elif instr == "SUB":
                    rd, rs1, rs2 = parts[1], parts[2], parts[3]
                    st.session_state.registers[rd] = (
                        st.session_state.registers.get(rs1, 0) - st.session_state.registers.get(rs2, 0)
                    )

                elif instr == "AND":
                    rd, rs1, rs2 = parts[1], parts[2], parts[3]
                    st.session_state.registers[rd] = (
                        st.session_state.registers.get(rs1, 0) & st.session_state.registers.get(rs2, 0)
                    )

                elif instr == "ANDI":
                    rd, rs1, imm = parts[1], parts[2], int(parts[3])
                    st.session_state.registers[rd] = st.session_state.registers.get(rs1, 0) & imm

                elif instr == "OR":
                    rd, rs1, rs2 = parts[1], parts[2], parts[3]
                    st.session_state.registers[rd] = (
                        st.session_state.registers.get(rs1, 0) | st.session_state.registers.get(rs2, 0)
                    )

                elif instr == "ORI":
                    rd, rs1, imm = parts[1], parts[2], int(parts[3])
                    st.session_state.registers[rd] = st.session_state.registers.get(rs1, 0) | imm

                elif instr == "SLL":
                    rd, rs1, rs2 = parts[1], parts[2], parts[3]
                    shamt = st.session_state.registers.get(rs2, 0) & 0x1F
                    st.session_state.registers[rd] = st.session_state.registers.get(rs1, 0) << shamt

                elif instr == "SLLI":
                    rd, rs1, imm = parts[1], parts[2], int(parts[3]) & 0x1F
                    st.session_state.registers[rd] = st.session_state.registers.get(rs1, 0) << imm

                elif instr == "SLT":
                    rd, rs1, rs2 = parts[1], parts[2], parts[3]
                    st.session_state.registers[rd] = int(
                        st.session_state.registers.get(rs1, 0) < st.session_state.registers.get(rs2, 0)
                    )

                elif instr == "SLTI":
                    rd, rs1, imm = parts[1], parts[2], int(parts[3])
                    st.session_state.registers[rd] = int(
                        st.session_state.registers.get(rs1, 0) < imm
                    )

                elif instr == "LW":
                    rd, offset_reg = parts[1], parts[2]
                    offset, reg = offset_reg.replace(")", "").split("(")
                    addr = st.session_state.registers.get(reg, 0) + int(offset)
                    st.session_state.registers[rd] = st.session_state.memory.get(addr, 0)

                elif instr == "SW":
                    rs2, offset_reg = parts[1], parts[2]
                    offset, reg = offset_reg.replace(")", "").split("(")
                    addr = st.session_state.registers.get(reg, 0) + int(offset)
                    st.session_state.memory[addr] = st.session_state.registers.get(rs2, 0) # Execution for Operations 
            except Exception as e:
                st.code(f"Error: {e}")

        st.subheader("Register State")
        register_data = [
            {"Register": reg, "Value (Hex)": hex(val), "Value (Dec)": val}
            for reg, val in st.session_state.registers.items()
        ]
        st.dataframe(register_data, use_container_width=True)

        st.subheader("Memory State")
        mem_data = [
            {"Address (Hex)": hex(addr), "Value (Hex)": hex(val), "Value (Dec)": val}
            for addr, val in sorted(st.session_state.memory.items())
        ]
        st.dataframe(mem_data, use_container_width=True)

    except RiscSyntaxError as e:
        st.code(e)
        st.code('Assemble: operation completed with errors.')

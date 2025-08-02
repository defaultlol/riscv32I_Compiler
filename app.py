from email.mime import base
import json
import streamlit as st
from code_editor import code_editor
from itables.sample_dfs import get_countries
from riscvparser import get_instruction_format
from exceptions import RiscSyntaxError
import pandas as pd
import plotly.express as px
from bitarray import bitarray
from bitarray.util import ba2hex,ba2int
from oppinterpreter import get_init_memory,set_mem,get_step_run
Clock_Cycle = 1
def reload_register_table():
    st.session_state.registerdf = [
        {"Register": f'0x{reg}', "Value (Hex)": ba2hex(val), "Value (Dec)": ba2int(val)}
        for reg, val in st.session_state.registers.items()
    ]

# Register initialization
if 'registers' not in st.session_state:
    st.session_state.registers = {i: bitarray(2 ** 5) for i in range(32)}
if 'memory_idx' not in st.session_state:
    st.session_state.memory_idx = pd.DataFrame()
if 'memory' not in st.session_state:
    st.session_state.memory = get_init_memory()
if 'registerdf' not in st.session_state:
    reload_register_table()
if 'sec' not in st.session_state:
    st.session_state.sec = pd.DataFrame()
if 'current_addr' not in st.session_state:
    st.session_state.current_addr = None
if 'build_id' not in st.session_state:
    st.session_state.build_id = '0'
if 'cycle_counter' not in st.session_state:
    st.session_state.cycle_counter = 1
if 'pipeline_schedule' not in st.session_state:
    st.session_state.pipeline_schedule = []

# code editor config variables
height = [19, 22]
theme = "default"
shortcuts = "vscode"
focus = False
wrap = True
build_btns=[
    {
        "name": "Build",
        "feather": "Tool",
        "primary": True,
        "hasText": True,
        "showWithIcon": True,
        "commands": ["submit"],
        "style": {"bottom": ".44rem", "right": "0.4rem"},
    },
]
editor_btns = [
    {
        "name": "Build",
        "feather": "Tool",
        "primary": True,
        "hasText": True,
        "showWithIcon": True,
        "commands": ["submit"],
        "style": {"bottom": "4rem", "right": "0.4rem"},
    },
    {
        "name": "Run",
        "feather": "Play",
        "primary": True,
        "hasText": True,
        "showWithIcon": True,
        "commands": ["submit"],
        "style": {"bottom": "0.44rem", "right": "0.4rem"},
    },
    {
        "name": "Next",
        "feather": "SkipForward",
        "primary": True,
        "hasText": True,
        "showWithIcon": True,
        "commands": ["sumit"],
        "style": {"bottom": "2rem", "right": "0.4rem"},
    },
    

]
code_text = '''.global main
.text
main:'''
# code editor
response_dict = code_editor(code_text, height=height, theme=theme, shortcuts=shortcuts, focus=focus, buttons=build_btns, options={"wrap": wrap, "showLineNumbers": True})
# show response dict
def run_button():
    # print(code_text)
    st.session_state.registers = {i: bitarray(2 ** 5) for i in range(32)}
    st.session_state.memory =  get_init_memory()
    reload_register_table()
    st.session_state.sec = pd.DataFrame()
    st.session_state.current_addr = None
    st.session_state.cycle_counter = 1
    st.session_state.pipeline_schedule = []
    for _,row in st.session_state.memory_idx.iterrows():
        set_mem(st.session_state.memory,row['address'],row['hex'])
    df = st.session_state.instructions
    pc=df['address'].min()
    cycle_df=[]
    cycle_ins=[]
    while pc in df['address'].tolist():
        cycle_ins.append(pc)
        row=df.loc[df.address==pc].iloc[0]
        cycle_row=get_step_run(pc,row['instruction_format(Hex)'][2:],row['basic'],st.session_state.memory,st.session_state.registers)
        cycle_df.append(cycle_row)
        start_cycle = st.session_state.cycle_counter
        st.session_state.pipeline_schedule.append({
            "Instruction": row['basic'],
            "address": pc,
            "Stages": {
                "IF": start_cycle,
                "ID": start_cycle + 1,
                "EX": start_cycle + 2,
                "MEM": start_cycle + 3,
                "WB": start_cycle + 4
            }
        })
        st.session_state.cycle_counter +=1
        pc=cycle_row['PC']
        if pc not in df['address'].tolist():
            near_idx=df['address'].searchsorted(pc,'right')
            if near_idx<=df.index.max():
                pc=df.loc[near_idx,'address']
    st.session_state.sec =pd.DataFrame(cycle_df,index=cycle_ins)
    st.session_state.pipeline_regs = build_pipeline_register_table(list(st.session_state.sec.to_dict('index').values()))

    reload_register_table()

def step_button():
    # print(code_text)
    df = st.session_state.instructions
    pc=st.session_state.current_addr
    print(st.session_state.current_addr)
    cycle_df=st.session_state.sec
    if pc in df['address'].tolist():
        cycle_addr=pc
        row=df.loc[df.address==pc].iloc[0]
        cycle_row=get_step_run(pc,row['instruction_format(Hex)'][2:],row['basic'],st.session_state.memory,st.session_state.registers)
        pc=cycle_row['PC']
        if pc not in df['address'].tolist():
            near_idx=df['address'].searchsorted(pc,'right')
            if near_idx<=df.index.max():
                pc=df.loc[near_idx,'address']
        print(pc)
        st.session_state.current_addr=pc
        print(st.session_state.current_addr)
        cycle_row=pd.Series(cycle_row)
        cycle_row.rename(cycle_addr,inplace=True)
        st.session_state.sec =pd.concat([cycle_df,cycle_row.to_frame().T])
    reload_register_table()
def build_pipeline_table(sec_df):
    stages = ['IF', 'ID', 'EX', 'MEM', 'WB']
    table_rows = []

    for entry in st.session_state.pipeline_schedule:
        try:
            addr_int = int(entry["address"], 16) if isinstance(entry["address"], str) else entry["address"]
        except ValueError:
            addr_int = 0 
        instr_label = entry["Instruction"]
        stage_cycles = entry['Stages']
        row = {'Instruction': instr_label}
        for stage in stages:
            row[stage] = stage_cycles.get(stage, "-") 
        table_rows.append(row)

    return pd.DataFrame(table_rows)
def display_pipeline_register_table(register_data):
    import pandas as pd
    df = pd.DataFrame(register_data).transpose()
    df = df.fillna("")  
    st.subheader("Pipeline Registers Table")
    st.dataframe(df, use_container_width=True)
def build_pipeline_register_table(sequential_table):
    pipeline_registers = {
        "IF/ID.IR": {},
        "IF/ID.NPC": {},
        "PC": {},
        "ID/EX.A": {},
        "ID/EX.B": {},
        "ID/EX.IMM": {},
        "ID/EX.IR": {},
        "ID/EX.NPC": {},
        "EX/MEM.ALUOUTPUT": {},
        "EX/MEM.IR": {},
        "EX/MEM.B": {},
        "EX/MEM.COND": {},
        "MEM/WB.LMD": {},
        "MEM/WB.IR": {},
        "MEM/WB.ALUOUTPUT": {},
        "MEM[EX/MEM.ALUOutput]": {},
        "REGS[MEM/WB.IR[rd]]": {}
    }

    for i, instr in enumerate(sequential_table):
        base = i  # start cycle per instruction
        pipeline_registers["IF/ID.IR"][base + 0] = instr["IR"]
        pipeline_registers["IF/ID.NPC"][base + 0] = instr["NPC"]
        pipeline_registers["PC"][base + 0] = instr["PC"]

        pipeline_registers["ID/EX.IR"][base + 1] = instr["IR"]
        pipeline_registers["ID/EX.NPC"][base + 1] = instr["NPC"]
        pipeline_registers["ID/EX.A"][base + 1] = instr["A"]
        pipeline_registers["ID/EX.B"][base + 1] = instr["B"]
        pipeline_registers["ID/EX.IMM"][base + 1] = instr["Imm"]

        pipeline_registers["EX/MEM.IR"][base + 2] = instr["IR"]
        pipeline_registers["EX/MEM.ALUOUTPUT"][base + 2] = instr["ALU"]
        pipeline_registers["EX/MEM.B"][base + 2] = instr["B"]
        pipeline_registers["EX/MEM.COND"][base + 2] = instr["cond"]

        pipeline_registers["MEM/WB.IR"][base + 3] = instr["IR"]
        pipeline_registers["MEM/WB.LMD"][base + 3] = instr["LMD"]
        pipeline_registers["MEM[EX/MEM.ALUOutput]"][base + 3] = instr["ALU"]

        pipeline_registers["MEM/WB.IR"][base + 4] = instr["IR"]
        pipeline_registers["REGS[MEM/WB.IR[rd]]"][base + 4] = instr["Rn"]

    return pipeline_registers

print(response_dict)
if len(response_dict['id']) != 0 and (response_dict['type'] == "selection" or response_dict['type'] == "submit" ):
    if st.session_state.build_id!=response_dict['id']:
        st.session_state.build_id=response_dict['id']
        st.session_state.registers = {i: bitarray(2 ** 5) for i in range(32)}
        st.session_state.memory_idx = pd.DataFrame()
        st.session_state.memory = get_init_memory()
        reload_register_table()
        st.session_state.sec = pd.DataFrame()
        st.session_state.current_addr = None
        st.code('Assemble: assembling risc32i sample.')
        code_text = response_dict['text']
        try:
            df, mem_df = get_instruction_format(code_text)
            # df.to_csv('test.csv',index=False)
            st.session_state.current_addr=df['address'].min()
            st.session_state.instructions=df
            st.code('Assemble: operation completed successfully.')
            st.dataframe(df, use_container_width=True)
            

            st.dataframe(mem_df, use_container_width=True)
            st.session_state.memory_idx=mem_df
            for _,row in mem_df.iterrows():
                set_mem(st.session_state.memory,row['address'],row['hex'])
            
            st.session_state.code_built=True

        except RiscSyntaxError as e:
            st.code(e)
            st.code('Assemble: operation completed with errors.')
    st.subheader("Register State")
    st.dataframe(st.session_state.registerdf, use_container_width=True)

    st.subheader("Memory State")
    st.dataframe(st.session_state.memory_idx, use_container_width=True)
    st.dataframe(st.session_state.memory, use_container_width=True)
    st.subheader("Sequential Execution Cycle")
    st.dataframe(st.session_state.sec, use_container_width=True)
    if not st.session_state.sec.empty:
        st.subheader("Pipeline Map")
        pipeline_table = build_pipeline_table(st.session_state.sec)
        st.dataframe(pipeline_table, use_container_width=True)
        display_pipeline_register_table(st.session_state.pipeline_regs)
    col1, col2 = st.columns(2)
    with col1:
        st.button('Run', on_click=run_button)
    with col2:
        st.button('Step Run', on_click=step_button)

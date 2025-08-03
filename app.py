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
from opppipeline import get_init_memory_pipe,set_mem_pipe,get_cycle,set_pnt_registers,forward_data

st.set_page_config(layout="wide")

ireg_order = [
    "IF/ID.IR",
    "IF/ID.NPC",
    "PC",
    "ID/EX.A",
    "ID/EX.B",
    "ID/EX.IR",
    "ID/EX.Imm",
    "ID/EX.NPC",
    "EX/MEM.ALUoutput",
    "EX/MEM.B",
    "EX/MEM.IR",
    "EX/MEM.cond",
    "MEM/WB.ALUoutput",
    "MEM/WB.IR",
    "MEM/WB.LMD",
    "MEM[EX/MEM.ALUOutput]",
    "REGS[MEM/WB.IR[rd]]",
    "rd",
]
pipelinemap_reg=[
    'IF/ID.instruction',
    'IF/ID.address',
    'ID/EX.instruction',
    'ID/EX.address',
    'EX/MEM.instruction',
    'EX/MEM.address',
    'MEM/WB.instruction',
    'MEM/WB.address',
    'WB.instruction',
    'WB.address',
]
run_style_list=['Sequential','Pipeline']
data_hazard_list=['Forwarding']
control_hazard_list=['Predict-not-taken']


Clock_Cycle = 1
def reload_register_table():
    st.session_state.registerdf = [
        {"Register": f'0x{reg}', "Value (Hex)": ba2hex(val), "Value (Dec)": ba2int(val)}
        for reg, val in st.session_state.registers.items()
    ]
def reload_internal_registers():
    temp = {i:None for i in ireg_order}
    for i in pipelinemap_reg:
        temp[i]=None
    st.session_state.internal_reg=temp

def refresh_pipeline_table():
    pipeline_df=pd.DataFrame(st.session_state.pipeline_schedule)
    pipeline_df['cycle']=pipeline_df['cycle'].astype(int)
    pipeline_df.sort_values(['address','cycle'],inplace=True)
    pipeline_df['cycle_end']=pipeline_df['cycle']+1
    pipeline_df['delta'] = pipeline_df['cycle_end'] - pipeline_df['cycle']
    st.session_state.pipeline_table=pd.DataFrame(pipeline_df)
def refresh_cycle_table():
    temp_df=pd.DataFrame(st.session_state.register_cycles)
    temp_df['cycle']=temp_df['cycle'].astype(int)
    temp_df.drop(columns=['address','instruction']+pipelinemap_reg,inplace=True,errors='ignore')
    temp_df=temp_df.melt(id_vars=['cycle'],var_name='register')
    temp_df=temp_df.pivot_table(index=['register'],columns='cycle',values='value',aggfunc='first').reset_index()
    temp_df.index=temp_df.register.apply(lambda x:ireg_order.index(x))
    temp_df.sort_index(inplace=True)
    st.session_state.cycle_table=temp_df
# Register initialization
if 'registers' not in st.session_state:
    st.session_state.registers = {i: bitarray(2 ** 5) for i in range(32)}
if 'iset' not in st.session_state:
    st.session_state.iset = pd.DataFrame()
if 'memory_idx' not in st.session_state:
    st.session_state.memory_idx = pd.DataFrame()
if 'memory' not in st.session_state:
    st.session_state.memory = get_init_memory_pipe()
    
if 'registerdf' not in st.session_state:
    reload_register_table()
if 'sec' not in st.session_state:
    st.session_state.sec = pd.DataFrame()
if 'current_addr' not in st.session_state:
    st.session_state.current_addr = None
if 'build_id' not in st.session_state:
    st.session_state.build_id = '0'
if 'cycle_counter' not in st.session_state:
    st.session_state.cycle_counter = 0

if 'pipeline_schedule' not in st.session_state:
    st.session_state.pipeline_schedule = []
if 'register_cycles' not in st.session_state:
    st.session_state.register_cycles = []
if 'pipeline_table' not in st.session_state:
    st.session_state.pipeline_table = pd.DataFrame()
if 'cycle_table' not in st.session_state:
    st.session_state.cycle_table = pd.DataFrame()

if 'internal_reg' not in st.session_state:
    reload_internal_registers()

if 'branching' not in st.session_state:
    st.session_state.branching=0
if 'load_mem_stall' not in st.session_state:
    st.session_state.load_mem_stall=False
if 'last_schedule' not in st.session_state:
    st.session_state.last_schedule=[]

if 'complete_run' not in st.session_state:
    st.session_state.complete_run = False


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
with st.expander("Settings", expanded=True):
    col_d, col_e, col_f = st.columns([1,1,1])
    run_style = col_d.selectbox("Execution:", run_style_list, index=run_style_list.index("Sequential"))
    data_hazard_sol = col_e.selectbox("theme:", data_hazard_list)
    control_hazard_sol = col_f.selectbox("shortcuts:", control_hazard_list)
col1, col2 = st.columns(2)
with col1:
    st.subheader("Code Editor")
    response_dict = code_editor(code_text, height=height, theme=theme, shortcuts=shortcuts, focus=focus, buttons=build_btns, options={"wrap": wrap, "showLineNumbers": True})
    
# show response dict
def run_button_seq():
    # print(code_text)
    st.session_state.registers = {i: bitarray(2 ** 5) for i in range(32)}
    st.session_state.memory =  get_init_memory()
    reload_register_table()
    st.session_state.sec = pd.DataFrame()
    st.session_state.current_addr = None
    st.session_state.cycle_counter = 1
    st.session_state.pipeline_schedule = []
    for _,row in st.session_state.memory_idx.iterrows():
        set_mem_pipe(st.session_state.memory,row['address'],row['hex'])
    df = st.session_state.instructions
    pc=df['address'].min()
    st.session_state.register_cycles=[]
    st.session_state.pipeline_schedule=[]
    cycle_count=0
    while pc in df['address'].str.upper().tolist():
        row=df.loc[df.address.str.upper()==pc].iloc[0]
        pipeline_rows,cycle_rows=get_step_run(pc,row['instruction_format(Hex)'],row['basic'],st.session_state.memory,st.session_state.registers,cycle_count)
        st.session_state.register_cycles.extend(cycle_rows)
        st.session_state.pipeline_schedule.extend(pipeline_rows)
        cycle_count+=5
        pc=cycle_rows[-1]['PC']
        print(pc)

    st.session_state.cycle_counter +=cycle_count
    st.session_state.complete_run = True

    reload_register_table()
def run_button_pipe():
    # print(code_text)
    st.session_state.registers = {i: bitarray(2 ** 5) for i in range(32)}
    st.session_state.memory =  get_init_memory_pipe()
    reload_register_table()
    st.session_state.sec = pd.DataFrame()
    st.session_state.current_addr = None
    st.session_state.cycle_counter = 1
    st.session_state.pipeline_schedule = []
    for _,row in st.session_state.memory_idx.iterrows():
        set_mem(st.session_state.memory,row['address'],row['hex'])
    
    df = st.session_state.instructions
    for _,row in df.iterrows():
        set_mem(st.session_state.memory,row['address'],row['instruction_format(Hex)'])
    pc=df['address'].min().upper()
    st.session_state.register_cycles=[]
    st.session_state.pipeline_schedule=[]
    st.session_state.last_schedule=[]
    reload_internal_registers()
    cycle_count=0
    pipeline_rows=[]
    branching=None
    load_mem_stall=False
    while (pc in df['address'].str.upper().tolist()) or (len(pipeline_rows)>0):
        cycle_count+=1
        if pc in df['address'].str.upper().tolist():
            row=df.loc[df.address.str.upper()==pc].iloc[0]
            ins=row['basic']
        else:
            st.session_state.internal_reg['PC']=None
            pc=None
            ins=None
        pipeline_rows,cycle_row,branching=get_cycle(st.session_state.internal_reg,pc,ins,st.session_state.memory,st.session_state.registers,cycle_count,load_mem_stall)
        pc=cycle_row['PC']
        print(pc,cycle_count,load_mem_stall)
        if branching==2:
            # print('branching',cycle_row['MEM/WB.address'],cycle_row['MEM/WB.instruction'],'wb')
            # if cycle_row
            set_pnt_registers(cycle_row)
            # print('branching',cycle_row['MEM/WB.address'],cycle_row['MEM/WB.instruction'],'wb')
        load_mem_stall=forward_data(cycle_row,load_mem_stall)
        st.session_state.register_cycles.append(cycle_row)
        st.session_state.pipeline_schedule.extend(pipeline_rows)
        st.session_state.internal_reg=cycle_row
    st.session_state.cycle_counter=cycle_count
    st.session_state.complete_run = True
    reload_register_table()
def step_button_pipe():
    # print(code_text)
    df = st.session_state.instructions
    pc=st.session_state.current_addr
    print(st.session_state.current_addr)
    # cycle_df=st.session_state.sec
    if (pc in df['address'].str.upper().tolist()) or (len(st.session_state.last_schedule)>0):
        if pc in df['address'].str.upper().tolist():
            row=df.loc[df.address.str.upper()==pc].iloc[0]
            ins=row['basic']
        else:
            st.session_state.internal_reg['PC']=None
            pc=None
            ins=None
        pipeline_rows,cycle_row,branching=get_cycle(st.session_state.internal_reg,pc,ins,st.session_state.memory,st.session_state.registers,st.session_state.cycle_counter,st.session_state.load_mem_stall)
        st.session_state.current_addr=cycle_row['PC']
        print(pc,st.session_state.cycle_counter,st.session_state.load_mem_stall)
        if branching==2:
            set_pnt_registers(cycle_row)
        st.session_state.load_mem_stall=forward_data(cycle_row,st.session_state.load_mem_stall)
        st.session_state.register_cycles.append(cycle_row)
        st.session_state.pipeline_schedule.extend(pipeline_rows)
        st.session_state.last_schedule=pipeline_rows
        st.session_state.internal_reg=cycle_row
        st.session_state.cycle_counter+=1
    else:
        st.session_state.complete_run = True
    reload_register_table()
def step_button_seq():
    # print(code_text)
    df = st.session_state.instructions
    pc=st.session_state.current_addr
    print(st.session_state.current_addr)
    # cycle_df=st.session_state.sec
    if pc in df['address'].str.upper().tolist():
        # cycle_addr=pc
        row=df.loc[df.address.str.upper()==pc].iloc[0]
        pipeline_rows,cycle_rows=get_step_run(pc,row['instruction_format(Hex)'],row['basic'],st.session_state.memory,st.session_state.registers,st.session_state.cycle_counter)
        st.session_state.register_cycles.extend(cycle_rows)
        st.session_state.pipeline_schedule.extend(pipeline_rows)
        st.session_state.current_addr=cycle_rows[-1]['PC']
        st.session_state.cycle_counter+=5
    else:
        st.session_state.complete_run = True
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
    df.columns = [str(int(c) + 1) for c in df.columns] 
    df = df.fillna("")  
    st.subheader("Pipeline Registers Table")
    st.dataframe(df, use_container_width=True)

print(response_dict)
if len(response_dict['id']) != 0 and (response_dict['type'] == "selection" or response_dict['type'] == "submit" ):
    with col1:
        if st.session_state.build_id!=response_dict['id']:
            st.session_state.code_built=False
            print('new build',response_dict['id'])
            st.session_state.build_id=response_dict['id']
            st.session_state.registers = {i: bitarray(2 ** 5) for i in range(32)}
            st.session_state.memory_idx = pd.DataFrame()
            st.session_state.memory = get_init_memory_pipe()
            reload_register_table()
            reload_internal_registers()
            st.session_state.sec = pd.DataFrame()
            st.session_state.current_addr = None
            st.session_state.register_cycles=[]
            st.session_state.pipeline_schedule=[]
            st.session_state.last_schedule=[]
            
            st.session_state.cycle_counter=0
            st.code('Assemble: assembling risc32i sample.')
            code_text = response_dict['text']
            try:
                df, mem_df = get_instruction_format(code_text)
                # df.to_csv('test.csv',index=False)
                st.session_state.current_addr=df['address'].min()
                st.session_state.instructions=df
                st.code('Assemble: operation completed successfully.')
                # st.dataframe(df, use_container_width=True)
                

                # st.dataframe(mem_df, use_container_width=True)
                st.session_state.memory_idx=mem_df
                for _,row in mem_df.iterrows():
                    set_mem_pipe(st.session_state.memory,row['address'],row['hex'])
                for _,row in df.iterrows():
                    set_mem(st.session_state.memory,row['address'].upper(),row['instruction_format(Hex)'].upper())
                st.session_state.code_built=True
                st.session_state.complete_run=False
                

            except RiscSyntaxError as e:
                st.code(e)
                st.code('Assemble: operation completed with errors.')
            
        if st.session_state.code_built:
            st.dataframe(st.session_state.instructions, use_container_width=True)
            if not st.session_state.complete_run and run_style=='Sequential':
                subcol1, subcol2 = st.columns(2)
                with subcol1:
                    st.button('Run', on_click=run_button_seq)
                with subcol2:
                    st.button('Step Run', on_click=step_button_seq)
            if not st.session_state.complete_run and run_style=='Pipeline':
                subcol1, subcol2 = st.columns(2)
                with subcol1:
                    st.button('Run', on_click=run_button_pipe)
                with subcol2:
                    st.button('Step Run', on_click=step_button_pipe)
        
    with col2:
        st.subheader("Register State")
        st.dataframe(st.session_state.registerdf, use_container_width=True)
        st.subheader("Memory State")
        st.dataframe(st.session_state.memory_idx, use_container_width=True)
        st.dataframe(st.session_state.memory, use_container_width=True)
    if len(st.session_state.pipeline_schedule)>0:
        refresh_pipeline_table()
        st.subheader("Pipeline Map")
        # st.session_state.pipeline_table.to_csv('pipeline_test.csv')
        pipeline_df=st.session_state.pipeline_table
        fig = px.timeline(pipeline_df, x_start="cycle", x_end="cycle_end", y="instruction", color="stage")
        fig.update_yaxes(autorange="reversed")
        fig.layout.xaxis.type = 'linear'
        for i in range(len(fig.data)):
            fig.data[i].x = pipeline_df.loc[pipeline_df['stage']==fig.data[i]['legendgroup'],'delta'].tolist()
        # fig.show()
        event = st.plotly_chart(fig, use_container_width=True)

        # st.dataframe(st.session_state.pipeline_table, use_container_width=True)
        

    if len(st.session_state.register_cycles)>0:
        refresh_cycle_table()
        st.subheader("Internal Registers")
        st.dataframe(st.session_state.cycle_table, use_container_width=True)
    

    
    # if not st.session_state.sec.empty:
    #     st.subheader("Sequential Execution Cycle")
    #     st.dataframe(st.session_state.sec, use_container_width=True)
    #     st.subheader("Pipeline Map")
    #     pipeline_table = build_pipeline_table(st.session_state.sec)
    #     pipeline_table
    #     st.dataframe(pipeline_table, use_container_width=True)
    #     display_pipeline_register_table(st.session_state.pipeline_regs)

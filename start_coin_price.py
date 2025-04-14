from concurrent.futures import ThreadPoolExecutor
import subprocess

import yaml

with open('coinList.yaml', 'r') as file:
    data = yaml.safe_load(file)

# 参数列表，每个元素代表一组参数
OKX_coinList = data['okxCoinList']
BIN_coinList = data['BinCoinList']
Stock_List = data['StockList']
# 定义您的脚本路径
script_path = 'coinPrice_single.py'

# 定义一个函数，用于执行脚本
def execute_script(script_path,params,height):
    try:
        command = ["venv/Scripts/python", script_path, params, height]
        subprocess.run(command, check=True)
        print(f"执行成功: {' '.join(params)}")
    except Exception as e:
        print(f"执行失败: {' '.join(params)} - 错误信息: {e}")

# 使用ThreadPoolExecutor来并行执行
with ThreadPoolExecutor(max_workers=len(OKX_coinList+BIN_coinList+Stock_List)) as executor:
    # 并行执行所有的脚本实例
    h = len(OKX_coinList)+len(BIN_coinList)+len(Stock_List)+int((18*(len(OKX_coinList)+len(BIN_coinList)+len(Stock_List))))
    futures = [executor.submit(execute_script, script_path, params, str(h - (19 * i))) for i,params in enumerate(OKX_coinList+BIN_coinList+Stock_List)]

    # 等待所有任务完成
    for future in futures:
        try:
            future.result()
        except Exception as e:
            print(f"任务执行异常: {e}")

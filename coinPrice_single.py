import asyncio
import re
import sys

import requests
import websockets
import json
import threading
from tkinter import Tk, Label, StringVar
from queue import Queue  # 从 queue 模块导入 Queue 类
from datetime import datetime, time

async def websocket_event_loop_OKX(coin, update_gui_queue):
    try:
        async with websockets.connect("wss://wspri.coinall.ltd:8443/ws/v5/ipublic") as websocket:
            # 发送订阅消息
            message = '{"op":"subscribe","args":[{"channel":"tickers","instId":"' + coin + '"}]}'  # 以BTC为例
            await websocket.send(message)
            while True:
                # 接收消息
                response = await websocket.recv()
                res = json.loads(response)
                if 'data' in res:
                    last = float(res['data'][0]['last'])
                    open24h = float(res['data'][0]['open24h'])
                    # 将数据放入队列中，以便在GUI线程中处理
                    update_gui_queue.put((coin,last, (last - open24h) / open24h))
    except (websockets.exceptions.ConnectionClosedError,
            asyncio.TimeoutError,
            websockets.exceptions.InvalidStatusCode,
            asyncio.CancelledError,
            Exception) as e:
        print(f"OKX WebSocket connection error: {e}. Reconnecting...")
        await asyncio.sleep(5)  # 重新连接前等待一段时间
        await websocket_event_loop_OKX(coin, update_gui_queue)

async def websocket_event_loop_BIN(coin, update_gui_queue):
    try:
        uri = "wss://stream.yshyqxx.com/stream?streams={}usdt@ticker".format(str(coin).split('-')[0])
        async with websockets.connect(uri) as websocket:
            while True:
                # 接收消息
                message = await websocket.recv()
                res = json.loads(message)
                # 打印最新价格
                update_gui_queue.put((str(res['data']['s']).replace('USDT',''),float(res['data']['c']), float(res['data']['P']) / 100))
    except (websockets.exceptions.ConnectionClosedError,
            asyncio.TimeoutError,
            websockets.exceptions.InvalidStatusCode,
            asyncio.CancelledError,
            Exception) as e:
        print(f"BIN WebSocket connection error: {e}. Reconnecting...")
        await asyncio.sleep(5)  # 重新连接前等待一段时间
        await websocket_event_loop_BIN(coin, update_gui_queue)

async def stock_market(stock,update_gui_queue):
    try:
        # 请求URL
        url = f'http://20.push2his.eastmoney.com/api/qt/stock/kline/get?cb=jQuery35104018727892881515_1713852944394&secid={"1." + str(stock) if str(stock[0]) == "6" else "0." + str(stock)}&ut=fa5fd1943c7b386f172d6893dbfba10b&fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf52%2Cf53%2Cf54%2Cf55%2Cf56%2Cf57%2Cf58%2Cf59%2Cf60%2Cf61&klt=101&fqt=1&beg=0&end=20500101&smplmt=460&lmt=1000000&_=1713852944423'
        while True:
            # 发送GET请求
            while time(9, 15) <= datetime.now().time() <= time(15, 1):
                response = requests.get(url)
                # 检查请求是否成功
                if response.status_code == 200:
                    # 尝试匹配并提取JSON数据
                    jsonp_data = response.text
                    try:
                        # 使用正则表达式匹配并提取JSON部分
                        json_str = re.match(r'(.*)\((.*)\)(.*)', jsonp_data).group(2)
                        # 解析JSON数据
                        data = json.loads(json_str)
                        priceData = str(data['data']['klines'][-1]).split(',')
                        update_gui_queue.put((str(data['data']['name']),float(priceData[2]),float(priceData[-3]) / 100))
                    except Exception as e:
                        print("解析JSONP时出错: ", e)
                else:
                    print("请求失败，状态码: ", response.status_code)
            update_gui_queue.put(('未开盘', '/', '/'))
    except Exception as e:
        print(e)

# 更新GUI的函数
def update_gui(root, price_label, update_gui_queue):
    try:
        while True:
            # 从队列中获取数据更新
            coin, price, change = update_gui_queue.get()
            # 更新GUI部件
            if re.match(r'^[\u4e00-\u9fff]+$', coin):
                if coin == '未开盘':
                    root.withdraw()
                else:
                    root.deiconify()
                    root.after(1000, lambda: price_label.config(text=f"{coin}股票价格: {price:}  涨跌幅: {change:.2%}",font=("Helvetica", 12)))
            else:
                root.after(0, lambda: price_label.config(text=f"{str(coin).split('-')[0] + ('合约' if 'SWAP' in coin else '现货')}价格: {price:}   24H涨跌幅: {float(change):.2%}",font=("Helvetica", 12)))
    except Exception as E:
        print('update_gui函数出错：{}'.format(E))

# 创建Tkinter窗口
root = Tk()
root.title("Stock Ticker")

# 创建标签显示价格和变化
price_label = Label(root, text="Last Price: N/A")
price_label.pack()

# 创建一个队列用于在WebSocket线程和GUI线程之间传递数据
update_gui_queue = Queue()

# 开始WebSocket连接的线程
def start_websocket(coin):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        if 'BIN' in coin or 'USDT' in coin:
            threading.Thread(target=loop.run_until_complete, args=(websocket_event_loop_BIN(coin, update_gui_queue) if 'BIN' in coin else websocket_event_loop_OKX(coin, update_gui_queue),)).start()
        else:
            threading.Thread(target=loop.run_until_complete, args=(stock_market(coin, update_gui_queue),)).start()
    except Exception as E:
        print('start_websocket报错异常{}'.format(E))

# 开始更新GUI的线程
def start_gui_update_thread():
    try:
        threading.Thread(target=update_gui, args=(root, price_label, update_gui_queue)).start()
    except Exception as E:
        print('start_gui_update_thread报错异常{}'.format(E))

if __name__ == "__main__":
    # 启动WebSocket和GUI更新线程
    if len(sys.argv) > 1:
        start_websocket(sys.argv[1])
        start_gui_update_thread()
        root.overrideredirect(True)
        root.wm_attributes("-topmost", 1)
        # 设置窗口初始位置
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = screen_width - 330
        y = screen_height - (86 + int(sys.argv[2]))
        root.geometry(f"+{x}+{y}")
        # 运行Tkinter事件循环
        root.mainloop()

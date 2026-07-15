import flet as ft
import time, threading, websocket, json, ta, requests
import pandas as pd

# المتغيرات العامة
app_state = {
    "price": 0.0,
    "status": "WAITING...",
    "indicators": {"RSI": "WAIT", "EMA": "WAIT", "ADX": "WAIT"},
    "master_signal": "WAIT",
    "sl": 0.0,
    "tp": 0.0
}

SL_PERC, TP_PERC = 0.005, 0.01

def get_color(status):
    if status == "BUY": return ft.colors.GREEN_ACCENT
    if status == "SELL": return ft.colors.RED_ACCENT
    return ft.colors.YELLOW

def trading_engine(api_key, token, chat_id, timeframe):
    global app_state
    def on_message(ws, message):
        data = json.loads(message)
        if 'price' in data: app_state["price"] = float(data['price'])
    
    ws = websocket.WebSocketApp(f"wss://ws.twelvedata.com/v1/quotes/price?apikey={api_key}", on_message=on_message)
    threading.Thread(target=ws.run_forever, daemon=True).start()

    while True:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval={timeframe}&outputsize=100&apikey={api_key}"
            response = requests.get(url, timeout=10).json()
            if 'values' in response:
                df = pd.DataFrame(response['values']).iloc[::-1].reset_index(drop=True)
                df[['high', 'low', 'close']] = df[['high', 'low', 'close']].astype(float)
                
                rsi = ta.momentum.rsi(df['close'], window=14).iloc[-1]
                adx = ta.trend.adx(df['high'], df['low'], df['close'], window=14).iloc[-1]
                ema200 = ta.trend.ema_indicator(df['close'], window=200).iloc[-1]
                
                app_state["indicators"]["RSI"] = "BUY" if rsi < 35 else ("SELL" if rsi > 65 else "WAIT")
                app_state["indicators"]["EMA"] = "BUY" if app_state["price"] > ema200 else "SELL"
                app_state["indicators"]["ADX"] = "BUY" if adx > 25 else "WAIT"
                
                buys = list(app_state["indicators"].values()).count("BUY")
                sells = list(app_state["indicators"].values()).count("SELL")
                
                if buys > sells and buys >= 2:
                    app_state["master_signal"] = "BUY"
                    app_state["sl"] = round(app_state["price"] * (1 - SL_PERC), 2)
                    app_state["tp"] = round(app_state["price"] * (1 + TP_PERC), 2)
                elif sells > buys and sells >= 2:
                    app_state["master_signal"] = "SELL"
                    app_state["sl"] = round(app_state["price"] * (1 + SL_PERC), 2)
                    app_state["tp"] = round(app_state["price"] * (1 - TP_PERC), 2)
                else:
                    app_state["master_signal"] = "WAIT"
                    app_state["sl"] = 0.0
                    app_state["tp"] = 0.0
                app_state["status"] = "ACTIVE"
        except: app_state["status"] = "ERROR"
        time.sleep(30)

def main(page: ft.Page):
    page.title = "Mahmoud Quantum Terminal"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.colors.BLACK
    page.font_family = "monospace"

    # تصميم المربعات
    def create_tile(title, value, color=ft.colors.WHITE):
        return ft.Container(
            content=ft.Column([ft.Text(title, size=10, color=ft.colors.GREY), ft.Text(value, size=16, weight="bold", color=color)], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=100, height=80, bgcolor=ft.colors.with_opacity(0.1, ft.colors.WHITE),
            border=ft.border.all(1, ft.colors.GREEN), border_radius=10, padding=10
        )

    price_tile = create_tile("PRICE", "0.00", ft.colors.WHITE)
    signal_tile = create_tile("SIGNAL", "WAIT", ft.colors.YELLOW)
    sl_tile = create_tile("SL", "0.00", ft.colors.RED_ACCENT)
    tp_tile = create_tile("TP", "0.00", ft.colors.GREEN_ACCENT)

    def start_app(e):
        page.clean()
        page.add(
            ft.Text("MAHMOUD DASHBOARD", size=25, weight="bold", color=ft.colors.GREEN),
            ft.Row([price_tile, signal_tile], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([sl_tile, tp_tile], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider()
        )
        threading.Thread(target=trading_engine, args=(api_field.value, token_field.value, chat_field.value, tf_dropdown.value), daemon=True).start()
        threading.Thread(target=update_ui, args=(page,), daemon=True).start()

    def update_ui(page):
        while True:
            price_tile.content.controls[1].value = f"{app_state['price']:.2f}"
            signal_tile.content.controls[1].value = app_state["master_signal"]
            signal_tile.content.controls[1].color = get_color(app_state["master_signal"])
            sl_tile.content.controls[1].value = str(app_state['sl'])
            tp_tile.content.controls[1].value = str(app_state['tp'])
            page.update()
            time.sleep(1)

    api_field = ft.TextField(label="API Key", password=True)
    token_field = ft.TextField(label="Telegram Token", password=True)
    chat_field = ft.TextField(label="Chat ID")
    tf_dropdown = ft.Dropdown(label="Timeframe", options=[ft.dropdown.Option(i) for i in ["1min", "5min", "15min", "30min", "1h", "4h", "1day"]])

    page.add(ft.Container(content=ft.Text("MAHMOUD", size=50, weight="bold", color=ft.colors.GREEN), alignment=ft.alignment.center), 
             api_field, token_field, chat_field, tf_dropdown, ft.ElevatedButton("INITIATE", on_click=start_app))

ft.app(target=main)

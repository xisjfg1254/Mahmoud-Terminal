import flet as ft
import time, threading, websocket, json, requests
import pandas as pd
import pandas_ta as ta

# حالة التطبيق
app_state = {
    "price": 0.0,
    "status": "WAITING FOR START...",
    "indicators": {"RSI": "WAIT", "ADX": "WAIT", "EMA": "WAIT", "MACD": "WAIT", "BB": "WAIT"},
    "master_signal": "WAIT",
    "sl_hit": False,
    "tp_hit": False
}

def create_indicator_card(title, key):
    return ft.Container(
        content=ft.Column([
            ft.Text(title, size=10, color=ft.colors.GREY_400),
            ft.Text("WAIT", size=14, weight="bold", key=key)
        ], alignment=ft.MainAxisAlignment.CENTER),
        padding=10,
        bgcolor=ft.colors.BLUE_GREY_900,
        border_radius=10,
        width=70,
        height=60
    )

def trading_engine(api_key, token, chat_id, timeframe, sl_val, tp_val):
    global app_state
    
    def on_message(ws, message):
        data = json.loads(message)
        if 'price' in data:
            price = float(data['price'])
            app_state["price"] = price
            if sl_val and price <= sl_val: app_state["sl_hit"] = True
            if tp_val and price >= tp_val: app_state["tp_hit"] = True

    ws = websocket.WebSocketApp(f"wss://ws.twelvedata.com/v1/quotes/price?apikey={api_key}", on_message=on_message)
    threading.Thread(target=ws.run_forever, daemon=True).start()

    while True:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval={timeframe}&apikey={api_key}"
            response = requests.get(url, timeout=10).json()
            if 'values' in response:
                df = pd.DataFrame(response['values']).iloc[::-1].reset_index(drop=True)
                df[['high', 'low', 'close']] = df[['high', 'low', 'close']].astype(float)
                
                # حساب جميع المؤشرات
                rsi = df.ta.rsi(length=14).iloc[-1]
                adx = df.ta.adx(high=df['high'], low=df['low'], close=df['close'], length=14)['ADX_14'].iloc[-1]
                ema200 = df.ta.ema(close=df['close'], length=200).iloc[-1]
                macd = df.ta.macd(close=df['close'])
                bb = df.ta.bbands(close=df['close'], length=20)
                
                # تحديث الحالة
                app_state["indicators"]["RSI"] = "BUY" if rsi < 35 else ("SELL" if rsi > 65 else "WAIT")
                app_state["indicators"]["EMA"] = "BUY" if app_state["price"] > ema200 else "SELL"
                app_state["indicators"]["ADX"] = "BUY" if adx > 25 else "WAIT"
                app_state["indicators"]["MACD"] = "BUY" if macd['MACD_12_26_9'].iloc[-1] > macd['MACDs_12_26_9'].iloc[-1] else "SELL"
                app_state["indicators"]["BB"] = "BUY" if app_state["price"] < bb['BBL_20_2.0'].iloc[-1] else "SELL"
                
                # الإشارة
                buys = list(app_state["indicators"].values()).count("BUY")
                sells = list(app_state["indicators"].values()).count("SELL")
                app_state["master_signal"] = "BUY" if buys >= 3 else ("SELL" if sells >= 3 else "WAIT")
                app_state["status"] = "ANALYZING..."
        except:
            app_state["status"] = "API ERROR"
        time.sleep(30)

def main(page: ft.Page):
    page.title = "Mahmoud Quantum Terminal"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20

    api_field = ft.TextField(label="API Key", password=True)
    token_field = ft.TextField(label="Telegram Token", password=True)
    chat_field = ft.TextField(label="Chat ID")
    tf_dropdown = ft.Dropdown(label="Timeframe", options=[ft.dropdown.Option("1min"), ft.dropdown.Option("5min"), ft.dropdown.Option("15min"), ft.dropdown.Option("1h"), ft.dropdown.Option("4h")])
    sl_field = ft.TextField(label="SL Price", keyboard_type=ft.KeyboardType.NUMBER)
    tp_field = ft.TextField(label="TP Price", keyboard_type=ft.KeyboardType.NUMBER)
    
    price_text = ft.Text("0.00", size=40, weight="bold")
    status_text = ft.Text("STANDBY", size=18, color=ft.colors.YELLOW)
    
    # شبكة المؤشرات الكاملة
    cards = ft.Row([
        create_indicator_card("RSI", "RSI"), 
        create_indicator_card("EMA", "EMA"), 
        create_indicator_card("ADX", "ADX"),
        create_indicator_card("MACD", "MACD"),
        create_indicator_card("BB", "BB")
    ], alignment=ft.MainAxisAlignment.CENTER, wrap=True)

    def start_app(e):
        page.clean()
        page.add(ft.Text("QUANTUM TERMINAL", size=25, color=ft.colors.GREEN), price_text, status_text, ft.Divider(), cards)
        threading.Thread(target=trading_engine, args=(api_field.value, token_field.value, chat_field.value, tf_dropdown.value, float(sl_field.value or 0), float(tp_field.value or 0)), daemon=True).start()
        threading.Thread(target=update_loop, daemon=True).start()

    def update_loop():
        while True:
            price_text.value = f"{app_state['price']:,.2f}"
            status_text.value = f"SIGNAL: {app_state['master_signal']}"
            for c in cards.controls:
                key = c.content.controls[1].key
                c.content.controls[1].value = app_state["indicators"].get(key, "WAIT")
            page.update()
            time.sleep(1)

    page.add(ft.Text("LOGIN", size=20), api_field, token_field, chat_field, tf_dropdown, sl_field, tp_field, ft.ElevatedButton("INITIATE", on_click=start_app))

ft.app(target=main)

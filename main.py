import flet as ft
import time, threading, websocket, json, requests
import pandas as pd

# حالة التطبيق
app_state = {
    "price": 0.0,
    "status": "WAITING...",
    "indicators": {"RSI": "WAIT", "EMA": "WAIT", "MACD": "WAIT", "BB": "WAIT"},
    "master_signal": "WAIT"
}

# دالة الألوان والرموز (تم تحديثها لتناسب التحديث الجديد)
def get_style(status):
    if status == "BUY": return ft.Colors.GREEN_ACCENT, ft.Icons.CIRCLE
    if status == "SELL": return ft.Colors.RED_ACCENT, ft.Icons.CIRCLE
    return ft.Colors.YELLOW, ft.Icons.CIRCLE

# الحسابات اليدوية
def calculate_indicators(df):
    close = df['close']
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    ema = close.ewm(span=200, adjust=False).mean()
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    sma = close.rolling(20).mean()
    std = close.rolling(20).std()
    return rsi.iloc[-1], ema.iloc[-1], macd.iloc[-1], (sma + (std * 2)).iloc[-1], (sma - (std * 2)).iloc[-1]

def create_indicator_card(title, key):
    return ft.Container(
        content=ft.Column([
            ft.Text(title, size=10, color=ft.Colors.GREY_400),
            ft.Row([ft.Icon(ft.Icons.CIRCLE, size=12, color=ft.Colors.YELLOW, key=f"icon_{key}"), 
                    ft.Text("WAIT", size=14, weight="bold", key=key)], alignment=ft.MainAxisAlignment.CENTER)
        ], alignment=ft.MainAxisAlignment.CENTER),
        padding=10, bgcolor=ft.Colors.BLUE_GREY_900, border_radius=15, width=85, height=70
    )

def trading_engine(api_key, timeframe):
    global app_state
    def on_message(ws, message):
        data = json.loads(message)
        if 'price' in data: app_state["price"] = float(data['price'])

    ws = websocket.WebSocketApp(f"wss://ws.twelvedata.com/v1/quotes/price?apikey={api_key}", on_message=on_message)
    threading.Thread(target=ws.run_forever, daemon=True).start()

    while True:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval={timeframe}&apikey={api_key}"
            response = requests.get(url, timeout=10).json()
            if 'values' in response:
                df = pd.DataFrame(response['values']).iloc[::-1].reset_index(drop=True)
                df['close'] = df['close'].astype(float)
                rsi, ema, macd, upper, lower = calculate_indicators(df)
                
                app_state["indicators"]["RSI"] = "BUY" if rsi < 35 else ("SELL" if rsi > 65 else "WAIT")
                app_state["indicators"]["EMA"] = "BUY" if app_state["price"] > ema else "SELL"
                app_state["indicators"]["MACD"] = "BUY" if macd > 0 else "SELL"
                app_state["indicators"]["BB"] = "BUY" if app_state["price"] < lower else ("SELL" if app_state["price"] > upper else "WAIT")
                
                buys = list(app_state["indicators"].values()).count("BUY")
                sells = list(app_state["indicators"].values()).count("SELL")
                app_state["master_signal"] = "BUY" if buys >= 2 else ("SELL" if sells >= 2 else "WAIT")
        except: app_state["status"] = "ERROR"
        time.sleep(30)

def main(page: ft.Page):
    page.title = "Mahmoud Quantum Terminal"
    page.theme_mode = ft.ThemeMode.DARK
    
    api_field = ft.TextField(label="API Key", password=True)
    tf_dropdown = ft.Dropdown(label="Timeframe", options=[ft.dropdown.Option("1min"), ft.dropdown.Option("5min"), ft.dropdown.Option("1h")])
    
    cards = ft.Row([create_indicator_card("RSI", "RSI"), create_indicator_card("EMA", "EMA"), create_indicator_card("MACD", "MACD"), create_indicator_card("BB", "BB")], alignment=ft.MainAxisAlignment.CENTER)

    def start_app(e):
        page.clean()
        page.add(ft.Text("QUANTUM TERMINAL", size=25, color=ft.Colors.GREEN, weight="bold"), 
                 ft.Text("0.00", size=40, key="price_text"), cards)
        threading.Thread(target=trading_engine, args=(api_field.value, tf_dropdown.value), daemon=True).start()
        threading.Thread(target=update_ui, args=(page,), daemon=True).start()

    def update_ui(page):
        while True:
            # تحديث السعر
            price_txt = page.get_control("price_text")
            if price_txt: price_txt.value = f"{app_state['price']:,.2f}"
            
            for c in cards.controls:
                # الوصول للعناصر المحددة
                row_container = c.content.controls[1]
                icon = row_container.controls[0]
                text = row_container.controls[1]
                key = text.key
                
                val = app_state["indicators"].get(key, "WAIT")
                color, icon_type = get_style(val)
                icon.color = color
                text.value = val
                text.color = color
            page.update()
            time.sleep(1)

    page.add(ft.Text("LOGIN", size=20), api_field, tf_dropdown, ft.ElevatedButton("START", on_click=start_app))

ft.app(target=main)

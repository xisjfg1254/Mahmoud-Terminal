import flet as ft
import time, threading, websocket, json, ta, requests
import pandas as pd

# المتغيرات العامة للحالة
app_state = {
    "price": 0.0,
    "status": "WAITING FOR START...",
    "indicators": {"RSI": "WAIT", "ADX": "WAIT", "EMA": "WAIT", "MACD": "WAIT", "BB": "WAIT", "DIV": "WAIT"},
    "master_signal": "WAIT"
}

# دالة الألوان حسب حالة الهاكر
def get_color(status):
    if status == "BUY": return ft.colors.GREEN_ACCENT
    if status == "SELL": return ft.colors.RED_ACCENT
    return ft.colors.YELLOW

# منطق التداول (يعمل في الخلفية)
def trading_engine(api_key, token, chat_id, timeframe):
    global app_state
    
    # Websocket لجلب السعر اللحظي
    def on_message(ws, message):
        data = json.loads(message)
        if 'price' in data: app_state["price"] = float(data['price'])
    
    ws = websocket.WebSocketApp(f"wss://ws.twelvedata.com/v1/quotes/price?apikey={api_key}", on_message=on_message)
    threading.Thread(target=ws.run_forever, daemon=True).start()

    while True:
        try:
            # جلب البيانات
            url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval={timeframe}&outputsize=100&apikey={api_key}"
            response = requests.get(url, timeout=10).json()
            if 'values' in response:
                df = pd.DataFrame(response['values']).iloc[::-1].reset_index(drop=True)
                df[['high', 'low', 'close']] = df[['high', 'low', 'close']].astype(float)
                
                # حساب المؤشرات
                rsi = ta.momentum.rsi(df['close'], window=14).iloc[-1]
                adx = ta.trend.adx(df['high'], df['low'], df['close'], window=14).iloc[-1]
                ema200 = ta.trend.ema_indicator(df['close'], window=200).iloc[-1]
                macd = ta.trend.MACD(df['close'])
                bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
                
                # تحديث الحالة (منطق التصويت)
                app_state["indicators"]["RSI"] = "BUY" if rsi < 35 else ("SELL" if rsi > 65 else "WAIT")
                app_state["indicators"]["EMA"] = "BUY" if app_state["price"] > ema200 else "SELL"
                app_state["indicators"]["ADX"] = "BUY" if adx > 25 else "WAIT"
                
                # تحديد الإشارة العامة
                buys = list(app_state["indicators"].values()).count("BUY")
                sells = list(app_state["indicators"].values()).count("SELL")
                
                if buys > sells and buys >= 2: app_state["master_signal"] = "BUY"
                elif sells > buys and sells >= 2: app_state["master_signal"] = "SELL"
                else: app_state["master_signal"] = "WAIT"
                
                app_state["status"] = f"ANALYZING {timeframe}..."
            
        except Exception as e:
            app_state["status"] = "ERROR: CHECK API"
        time.sleep(30)

# واجهة المستخدم (الواجهة الرسومية)
def main(page: ft.Page):
    page.title = "Mahmoud Quantum Terminal"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.colors.BLACK
    page.font_family = "monospace"

    # المدخلات
    api_field = ft.TextField(label="API Key", password=True)
    token_field = ft.TextField(label="Telegram Token", password=True)
    chat_field = ft.TextField(label="Chat ID")
    tf_dropdown = ft.Dropdown(label="Timeframe", options=[
        ft.dropdown.Option("1min"), ft.dropdown.Option("5min"), ft.dropdown.Option("15min"),
        ft.dropdown.Option("30min"), ft.dropdown.Option("1h"), ft.dropdown.Option("4h"), ft.dropdown.Option("1day")
    ])

    # عناصر الداشبورد
    price_text = ft.Text("0.00", size=40, weight="bold", color=ft.colors.WHITE)
    status_text = ft.Text("SYSTEM READY", size=18, color=ft.colors.YELLOW)
    
    indicators_grid = ft.Row([
        ft.Container(content=ft.Column([ft.Text("RSI", size=10), ft.Text("WAIT", size=14, key="RSI")]), padding=10, border=ft.border.all(1, ft.colors.GREEN), border_radius=5),
        ft.Container(content=ft.Column([ft.Text("EMA", size=10), ft.Text("WAIT", size=14, key="EMA")]), padding=10, border=ft.border.all(1, ft.colors.GREEN), border_radius=5),
        ft.Container(content=ft.Column([ft.Text("ADX", size=10), ft.Text("WAIT", size=14, key="ADX")]), padding=10, border=ft.border.all(1, ft.colors.GREEN), border_radius=5)
    ], alignment=ft.MainAxisAlignment.CENTER)

    def start_app(e):
        page.clean()
        page.add(
            ft.Text("MAHMOUD QUANTUM TERMINAL", size=20, color=ft.colors.GREEN),
            price_text, status_text, ft.Divider(), indicators_grid
        )
        threading.Thread(target=trading_engine, args=(api_field.value, token_field.value, chat_field.value, tf_dropdown.value), daemon=True).start()
        threading.Thread(target=update_ui, args=(page,), daemon=True).start()

    def update_ui(page):
        while True:
            price_text.value = f"{app_state['price']:,.2f}"
            status_text.value = app_state["status"]
            status_text.color = get_color(app_state["master_signal"])
            # تحديث الكروت
            for c in indicators_grid.controls:
                key = c.content.controls[0].value
                val_text = c.content.controls[1]
                val_text.value = app_state["indicators"].get(key, "WAIT")
                val_text.color = get_color(val_text.value)
            page.update()
            time.sleep(1)

    page.add(ft.Text("MHMOUD LOGIN", size=30, color=ft.colors.GREEN), api_field, token_field, chat_field, tf_dropdown, ft.ElevatedButton("INITIATE", on_click=start_app))

ft.app(target=main)

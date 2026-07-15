import flet as ft
import time, threading, websocket, json, requests
import pandas as pd

# حالة التطبيق
app_state = {
    "price": 0.0,
    "status": "SCANNING...",
    "indicators": {
        "EMA200": {"val": 0.0, "status": "WAIT", "tp": "---", "sl": "---"},
        "ADX": {"val": 0.0, "status": "WAIT", "tp": "---", "sl": "---"},
        "RSI": {"val": 0.0, "status": "WAIT", "tp": "---", "sl": "---"},
        "MACD": {"val": 0.0, "status": "WAIT", "tp": "4038.0", "sl": "4030.1"},
        "EMA_F": {"val": 0.0, "status": "WAIT", "tp": "4030.1", "sl": "4036.4"},
        "BB": {"val": 0.0, "status": "WAIT", "tp": "---", "sl": "---"}
    }
}

def get_color(status):
    if "BUY" in status: return ft.Colors.GREEN_ACCENT
    if "SELL" in status or "BEARISH" in status: return ft.Colors.RED_ACCENT
    if "WAIT" in status or "WEAK" in status: return ft.Colors.YELLOW
    return ft.Colors.WHITE

def create_row(label, key):
    # هذا التصميم الذي سيظهر بشكل "ليست" أو Terminal
    return ft.Container(
        content=ft.Row([
            ft.Text(f"{label:<12}", size=13, weight="bold", font_family="Monospace"),
            ft.Text("---", size=13, font_family="Monospace", key=f"val_{key}"),
            ft.Text("[WAIT]", size=13, weight="bold", font_family="Monospace", color=ft.Colors.YELLOW, key=f"stat_{key}"),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=ft.padding.symmetric(vertical=5),
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.GREY_800))
    )

def main(page: ft.Page):
    page.title = "Quantum Terminal Pro"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 10

    # الواجهة (Layout)
    market_price = ft.Text("Market Price : 0.00", size=20, weight="bold", color=ft.Colors.WHITE)
    mode_text = ft.Text("MODE : PRO SCALPING (5min)", color=ft.Colors.GREEN_ACCENT, weight="bold")
    status_text = ft.Text("Status : SCANNING...", color=ft.Colors.YELLOW)

    rows_container = ft.Column(controls=[
        create_row("EMA200", "EMA200"),
        create_row("ADX", "ADX"),
        create_row("RSI", "RSI"),
        create_row("MACD", "MACD"),
        create_row("EMA_F", "EMA_F"),
        create_row("BB", "BB"),
    ])

    dashboard = ft.Container(
        content=ft.Column([
            mode_text,
            ft.Divider(),
            market_price,
            ft.Divider(),
            rows_container,
            ft.Divider(),
            status_text
        ]),
        border=ft.border.all(1, ft.Colors.GREY_700),
        border_radius=10,
        padding=15
    )

    page.add(dashboard)

    # وظيفة التحديث (Simulation) - يمكنك ربطها بـ trading_engine لاحقاً
    def update_loop():
        while True:
            # تحديث السعر
            market_price.value = f"Market Price : {app_state['price']:.2f}"
            
            # تحديث المؤشرات
            for key in app_state["indicators"]:
                val_text = page.get_control(f"val_{key}")
                stat_text = page.get_control(f"stat_{key}")
                if val_text and stat_text:
                    val_text.value = f"{app_state['indicators'][key]['val']:.2f}"
                    stat_text.value = f"[{app_state['indicators'][key]['status']}]"
                    stat_text.color = get_color(app_state['indicators'][key]['status'])
            
            page.update()
            time.sleep(1)

    threading.Thread(target=update_loop, daemon=True).start()

ft.app(target=main)

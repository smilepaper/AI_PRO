import tkinter as tk
import websocket
import json
import threading
import time
import winsound


class OSOverlay:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)   # 無邊框
        self.root.attributes("-topmost", True)  # 永遠置頂
        self.root.attributes("-alpha", 0.9)
        self.root.configure(bg="#1a1a2e")

        self.state = "badge"  # 'badge', 'menu', 'pomodoro'
        self.pomodoro_time = 25 * 60
        self.timer_running = False
        self.last_gesture_time = 0
        self.tracking_active = True
        self.ws_connected = False

        # 螢幕定位 (右上角)
        screen_w = self.root.winfo_screenwidth()
        self.pos_x = screen_w - 310
        self.pos_y = 20

        self.build_ui()
        self.show_badge()

        # 啟動 WebSocket 客戶端
        threading.Thread(target=self.ws_thread, daemon=True).start()

        self.update_clock()
        self.root.mainloop()

    def build_ui(self):
        # ─── 狀態列 (永遠可見) ───
        self.frame_badge = tk.Frame(self.root, bg="#1a1a2e")
        self.lbl_status_icon = tk.Label(
            self.frame_badge, text="●", fg="#00ff88",
            bg="#1a1a2e", font=("Segoe UI", 16)
        )
        self.lbl_status_icon.pack(side="left", padx=(10, 4))
        self.lbl_status_text = tk.Label(
            self.frame_badge, text="Tracking ON", fg="#00ff88",
            bg="#1a1a2e", font=("Segoe UI", 12, "bold")
        )
        self.lbl_status_text.pack(side="left", padx=(0, 6))
        self.lbl_ws = tk.Label(
            self.frame_badge, text="⚡ 未連線", fg="#555555",
            bg="#1a1a2e", font=("Segoe UI", 9)
        )
        self.lbl_ws.pack(side="right", padx=(0, 10))

        # ─── 功能選單 ───
        self.frame_menu = tk.Frame(self.root, bg="#1a1a2e")
        tk.Frame(self.frame_menu, bg="#00ffcc", height=2).pack(fill="x", padx=10, pady=(6, 10))
        tk.Label(
            self.frame_menu, text="🔮 AI 懸浮功能欄",
            fg="#00ffcc", bg="#1a1a2e", font=("Segoe UI", 15, "bold")
        ).pack(pady=(0, 10))

        items_frame = tk.Frame(self.frame_menu, bg="#1a1a2e")
        items_frame.pack(fill="x", padx=10)
        tk.Label(
            items_frame, text="🍅  [Timeout]  啟動番茄鐘",
            fg="#ffffff", bg="#2a2a3e", font=("Segoe UI", 11),
            padx=14, pady=7, anchor="w"
        ).pack(fill="x", pady=3)
        tk.Label(
            items_frame, text="👎  [Dislike]   關閉選單",
            fg="#999999", bg="#1a1a2e", font=("Segoe UI", 10),
            padx=14, pady=4, anchor="w"
        ).pack(fill="x", pady=2)

        # ─── 番茄鐘 ───
        self.frame_pomodoro = tk.Frame(self.root, bg="#1a1a2e")
        tk.Frame(self.frame_pomodoro, bg="#ff3366", height=2).pack(fill="x", padx=10, pady=(6, 6))
        tk.Label(
            self.frame_pomodoro, text="🍅 專注番茄鐘",
            fg="#ff3366", bg="#1a1a2e", font=("Segoe UI", 14, "bold")
        ).pack(pady=(0, 2))
        self.lbl_time = tk.Label(
            self.frame_pomodoro, text="25:00",
            fg="#ffffff", bg="#1a1a2e", font=("Consolas", 38, "bold")
        )
        self.lbl_time.pack(pady=4)
        self.lbl_timer_status = tk.Label(
            self.frame_pomodoro, text="⏸ 已暫停",
            fg="#aaaaaa", bg="#1a1a2e", font=("Segoe UI", 10)
        )
        self.lbl_timer_status.pack()
        tk.Label(
            self.frame_pomodoro,
            text="[Timeout] 暫停/繼續   [Mute] 重設   [Dislike] 縮小",
            fg="#555555", bg="#1a1a2e", font=("Segoe UI", 8)
        ).pack(pady=(6, 2))

    # ── 視窗狀態切換 ──────────────────────────────────────

    def show_badge(self):
        """最小化模式：只顯示 Tracking ON/OFF 小狀態列"""
        self.state = "badge"
        self.frame_menu.pack_forget()
        self.frame_pomodoro.pack_forget()
        self.frame_badge.pack(fill="x")
        self.root.geometry(f"250x38+{self.pos_x + 50}+{self.pos_y}")
        self.root.deiconify()
        self.root.lift()

    def show_menu(self):
        """展開功能選單"""
        self.state = "menu"
        self.frame_pomodoro.pack_forget()
        self.frame_badge.pack_forget()
        self.frame_badge.pack(fill="x")
        self.frame_menu.pack(fill="both", expand=True)
        self.root.geometry(f"280x210+{self.pos_x}+{self.pos_y}")
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        print("[UI] 功能選單已展開")

    def show_pomodoro(self):
        """展開番茄鐘"""
        self.state = "pomodoro"
        self.frame_menu.pack_forget()
        self.frame_badge.pack_forget()
        self.frame_badge.pack(fill="x")
        self.frame_pomodoro.pack(fill="both", expand=True)
        self.root.geometry(f"280x250+{self.pos_x}+{self.pos_y}")
        self.root.deiconify()
        self.root.lift()
        print("[UI] 番茄鐘已展開")

    # ── Tracking 狀態顯示 ────────────────────────────────

    def update_tracking_display(self, is_active):
        self.tracking_active = is_active
        if is_active:
            self.lbl_status_icon.config(fg="#00ff88")
            self.lbl_status_text.config(text="Tracking ON", fg="#00ff88")
        else:
            self.lbl_status_icon.config(fg="#ff4444")
            self.lbl_status_text.config(text="Tracking OFF", fg="#ff4444")

    def update_ws_indicator(self, connected):
        self.ws_connected = connected
        if connected:
            self.lbl_ws.config(text="⚡ 已連線", fg="#00ffcc")
        else:
            self.lbl_ws.config(text="⚡ 未連線", fg="#ff4444")

    # ── 番茄鐘計時 ───────────────────────────────────────

    def update_clock(self):
        if self.timer_running and self.pomodoro_time > 0:
            self.pomodoro_time -= 1
            self.lbl_timer_status.config(text="▶ 專注中...", fg="#00ff88")
            if self.pomodoro_time <= 0:
                self.timer_running = False
                self.pomodoro_time = 0
                self.lbl_time.config(text="00:00", fg="#ff0000")
                self.lbl_timer_status.config(text="🔔 時間到！", fg="#ff3366")
                self.show_pomodoro()  # 時間到自動彈出提醒
                winsound.Beep(1000, 300)
                winsound.Beep(1200, 500)

        if self.pomodoro_time > 0:
            mins = self.pomodoro_time // 60
            secs = self.pomodoro_time % 60
            self.lbl_time.config(text=f"{mins:02d}:{secs:02d}")

        if not self.timer_running and self.pomodoro_time > 0 and self.pomodoro_time < 25 * 60:
            self.lbl_timer_status.config(text="⏸ 已暫停", fg="#ffaa00")

        self.root.after(1000, self.update_clock)

    # ── WebSocket 客戶端 ─────────────────────────────────

    def ws_thread(self):
        def on_message(ws, message):
            try:
                data = json.loads(message)
                gesture = data.get("gesture", "").lower()
                tracking = data.get("tracking", True)

                # 即時更新 Tracking 狀態顯示 (不受冷卻限制)
                self.root.after(0, lambda t=tracking: self.update_tracking_display(t))

                now = time.time()
                # 手勢冷卻時間，避免連續觸發
                if now - self.last_gesture_time < 1.2:
                    return

                if gesture == "ok":
                    if self.state == "badge":
                        self.root.after(0, self.show_menu)
                        self.last_gesture_time = now
                        print(f"[手勢] OK → 開啟選單")

                elif gesture == "dislike":
                    if self.state != "badge":
                        self.root.after(0, self.show_badge)
                        self.last_gesture_time = now
                        print(f"[手勢] Dislike → 收起至狀態列")

                elif gesture == "timeout":
                    if self.state == "menu":
                        self.timer_running = True
                        self.root.after(0, self.show_pomodoro)
                    else:
                        self.timer_running = not self.timer_running
                        if self.timer_running and self.state == "badge":
                            self.root.after(0, self.show_pomodoro)
                    self.last_gesture_time = now
                    print(f"[手勢] Timeout → 計時器: {'運行中' if self.timer_running else '已暫停'}")

                elif gesture == "mute":
                    if self.state == "pomodoro":
                        self.timer_running = False
                        self.pomodoro_time = 25 * 60
                        self.root.after(0, lambda: self.lbl_time.config(text="25:00", fg="#ffffff"))
                        self.root.after(0, lambda: self.lbl_timer_status.config(text="⏸ 已重設", fg="#aaaaaa"))
                        self.last_gesture_time = now
                        print(f"[手勢] Mute → 番茄鐘已重設")

            except Exception as e:
                print(f"[錯誤] 處理訊息時出錯: {e}")

        def on_open(ws):
            self.root.after(0, lambda: self.update_ws_indicator(True))
            print("[WS] ✅ 已成功連線至 app_ws.py")

        def on_close(ws, close_status_code, close_msg):
            self.root.after(0, lambda: self.update_ws_indicator(False))
            print(f"[WS] ❌ 連線已斷開 (code={close_status_code})")

        def on_error(ws, error):
            print(f"[WS] ⚠️ 錯誤: {error}")

        while True:
            try:
                ws = websocket.WebSocketApp(
                    "ws://localhost:8765",
                    on_message=on_message,
                    on_open=on_open,
                    on_close=on_close,
                    on_error=on_error
                )
                ws.run_forever()
            except Exception as e:
                print(f"[WS] 重新連線中... ({e})")
            time.sleep(2)


if __name__ == "__main__":
    print("=" * 50)
    print("  AI 全域懸浮選單 & 番茄鐘")
    print("  等待 WebSocket 連線 (ws://localhost:8765)...")
    print("  請確認 app_ws.py 已在另一個終端機執行")
    print("=" * 50)
    OSOverlay()

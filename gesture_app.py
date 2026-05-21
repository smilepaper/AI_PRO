"""
AI 手勢控制系統 (整合版 v6)
============================
單一檔案，一行指令啟動：python gesture_app.py

手勢對照表：
  移動游標    → two_up
  左鍵點擊    → peace (V字，座標鎖定)
  右鍵點擊    → fist (握拳，座標鎖定)
  雙擊        → little_finger (小指)
  滾動頁面    → rock (手上下移動控制滾動方向與速度)
  Esc 鍵     → hand_heart2
  開啟追蹤    → holy
  關閉追蹤    → xsign
  播放/暫停   → timeout (媒體鍵)
  切換靜音    → mute (系統靜音 ON/OFF)
  音量增加    → like (👍)
  音量降低    → dislike (👎)
  螢幕截圖    → take_picture (附閃光特效)
  開啟選單    → thumb_index
  關閉選單    → ok
"""

import cv2
import tkinter as tk
import threading
import time
import winsound
import pyautogui
from ultralytics import YOLO


# ══════════════════════════════════════════════════════════
#  共享狀態
# ══════════════════════════════════════════════════════════

class GestureState:
    def __init__(self):
        self.gesture = "None"
        self.x = 0.5
        self.y = 0.5
        self.tracking_active = True
        self.running = True
        self.screenshot_flash = False   # 攝影機執行緒設 True → UI 執行緒播放閃光
        self.tracking_start_flash = False
        self.tracking_stop_flash = False


# 只有移動手勢才更新游標座標
MOVE_GESTURES = {"two_up"}


# ══════════════════════════════════════════════════════════
#  攝影機 + YOLO + 滑鼠/鍵盤控制 (背景執行緒)
# ══════════════════════════════════════════════════════════

def camera_loop(state: GestureState):
    pyautogui.FAILSAFE = False
    screen_w, screen_h = pyautogui.size()

    model = YOLO("YOLOv10n_gestures.pt")
    cap = cv2.VideoCapture(0)
    print("[Camera] 攝影機已開啟  |  在 OpenCV 視窗按 'q' 退出")

    smoothed_x = 0.5
    smoothed_y = 0.5

    # 冷卻計時器
    last_lclick_time = 0
    last_rclick_time = 0
    last_dblclick_time = 0
    last_holy_time = 0
    last_xsign_time = 0
    last_timeout_time = 0
    last_mute_time = 0
    last_volup_time = 0
    last_voldn_time = 0
    last_screenshot_time = 0
    last_esc_time = 0
    last_scroll_time = 0

    current_held_gesture = "None"
    gesture_hold_start = 0

    while state.running and cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        results = model(frame, conf=0.5, verbose=False)

        state.gesture = "None"
        coords_text = "No Hand Detected"

        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                class_id = int(box.cls[0])
                gesture_name = model.names[class_id]
                confidence = float(box.conf[0])

                cv2.putText(frame, f"{gesture_name} {confidence:.2f}",
                            (x1, y1 - 35), cv2.FONT_HERSHEY_SIMPLEX, 1,
                            (0, 255, 0), 2)

                coords_text = f"X1={x1} Y1={y1} | X2={x2} Y2={y2}"

                # ── 計算原始座標 (所有手勢都算，供滾動等功能使用) ──
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0
                margin_x = w * 0.25
                margin_y = h * 0.25
                raw_x = max(0.0, min(1.0, (cx - margin_x) / (w - 2 * margin_x)))
                raw_y = max(0.0, min(1.0, (cy - margin_y) / (h - 2 * margin_y)))

                now = time.time()

                # ── 手勢確認機制 (Dwell Time) ──
                if gesture_name != current_held_gesture:
                    current_held_gesture = gesture_name
                    gesture_hold_start = now
                
                hold_duration = now - gesture_hold_start
                
                # 進度條與過濾
                if gesture_name not in MOVE_GESTURES:
                    req_time = 0.25 if gesture_name in {"rock", "like", "dislike"} else 0.45
                    progress = min(1.0, hold_duration / req_time)
                    bar_w = max(50, int((x2 - x1) * 0.8))
                    bar_x = x1 + int((x2 - x1) * 0.1)
                    # 畫背景與進度
                    cv2.rectangle(frame, (bar_x, y1 - 25), (bar_x + bar_w, y1 - 18), (50, 50, 50), -1)
                    cv2.rectangle(frame, (bar_x, y1 - 25), (bar_x + int(bar_w * progress), y1 - 18), (0, 255, 0), -1)
                    
                    if hold_duration < req_time:
                        continue  # 還沒達到確認時間，跳過觸發邏輯

                state.gesture = gesture_name  # 確認後才給 UI 用

                # ── 只在移動手勢時更新平滑座標 ──
                if gesture_name in MOVE_GESTURES:
                    smoothing = 0.55
                    smoothed_x += smoothing * (raw_x - smoothed_x)
                    smoothed_y += smoothing * (raw_y - smoothed_y)
                    state.x = smoothed_x
                    state.y = smoothed_y

                # ══ 追蹤開關 ══
                if gesture_name == "holy" and (now - last_holy_time > 1.5):
                    if not state.tracking_active:
                        state.tracking_active = True
                        state.tracking_start_flash = True
                        print("[Holy] Tracking → ON")
                    last_holy_time = now

                elif gesture_name == "xsign" and (now - last_xsign_time > 1.5):
                    if state.tracking_active:
                        state.tracking_active = False
                        state.tracking_stop_flash = True
                        print("[XSign] Tracking → OFF")
                    last_xsign_time = now

                # ══ 媒體 & 音量 ══
                elif gesture_name == "timeout" and (now - last_timeout_time > 1.5):
                    pyautogui.press("playpause", _pause=False)
                    last_timeout_time = now
                    print("[Timeout] 播放/暫停")

                elif gesture_name == "mute" and (now - last_mute_time > 1.5):
                    pyautogui.press("volumemute", _pause=False)
                    last_mute_time = now
                    print("[Mute] 切換靜音")

                elif gesture_name == "like" and (now - last_volup_time > 0.4):
                    pyautogui.press("volumeup", _pause=False)
                    last_volup_time = now

                elif gesture_name == "dislike" and (now - last_voldn_time > 0.4):
                    pyautogui.press("volumedown", _pause=False)
                    last_voldn_time = now

                # ══ 截圖 (附閃光特效) ══
                elif gesture_name == "take_picture" and (now - last_screenshot_time > 2.0):
                    pyautogui.hotkey("win", "printscreen", _pause=False)
                    state.screenshot_flash = True
                    last_screenshot_time = now
                    print("[Screenshot] 已截圖")

                # ══ Esc 鍵 ══
                elif gesture_name == "hand_heart2" and (now - last_esc_time > 1.5):
                    pyautogui.press("escape", _pause=False)
                    last_esc_time = now
                    print("[Hand Heart] Esc")

                # ══ 滾動模式 ══
                elif gesture_name == "rock" and (now - last_scroll_time > 0.05):
                    # 手在畫面上半部 → 頁面往上滾，下半部 → 往下滾
                    # 離中心越遠滾越快 (raw_y=0.5 為中心不滾動)
                    diff = 0.5 - raw_y
                    if abs(diff) > 0.05:
                        scroll_amount = diff * 300
                        pyautogui.scroll(int(scroll_amount), _pause=False)
                    last_scroll_time = now

                # ══ 滑鼠控制 (追蹤啟用時) ══
                if state.tracking_active:
                    sx = int(state.x * screen_w)
                    sy = int(state.y * screen_h)

                    # 移動
                    if gesture_name in MOVE_GESTURES:
                        pyautogui.moveTo(sx, sy, _pause=False)

                    # 左鍵 (V字)
                    elif gesture_name == "peace" and now - last_lclick_time > 0.8:
                        pyautogui.click(x=sx, y=sy, button="left", _pause=False)
                        last_lclick_time = now

                    # 右鍵 (握拳)
                    elif gesture_name == "fist" and now - last_rclick_time > 1.2:
                        pyautogui.click(x=sx, y=sy, button="right", _pause=False)
                        last_rclick_time = now

                    # 雙擊 (小指)
                    elif gesture_name == "little_finger" and now - last_dblclick_time > 1.0:
                        pyautogui.doubleClick(x=sx, y=sy, _pause=False)
                        last_dblclick_time = now

        # ── 感測區框線 ──
        mx = int(w * 0.25)
        my = int(h * 0.25)
        cv2.rectangle(frame, (mx, my), (w - mx, h - my), (255, 0, 255), 2)

        # ── HUD ──
        overlay_img = frame.copy()
        cv2.rectangle(overlay_img, (10, 10), (400, 70), (0, 0, 0), -1)
        cv2.addWeighted(overlay_img, 0.6, frame, 0.4, 0, frame)

        tag = "ON" if state.tracking_active else "OFF"
        clr = (0, 255, 0) if state.tracking_active else (0, 0, 255)
        cv2.putText(frame, f"Tracking: {tag}", (20, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, clr, 2, cv2.LINE_AA)
        cv2.putText(frame, coords_text, (20, 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (66, 252, 241), 1, cv2.LINE_AA)

        cv2.imshow("AI Gesture Control", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    state.running = False
    print("[Camera] 攝影機已關閉")


# ══════════════════════════════════════════════════════════
#  Tkinter 全域懸浮 UI (主執行緒)
# ══════════════════════════════════════════════════════════

class OSOverlay:
    def __init__(self, shared: GestureState):
        self.shared = shared

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.92)
        self.root.configure(bg="#1a1a2e")

        self.ui_state = "badge"
        self.last_gesture_time = 0

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()
        self.pos_x = self.screen_w - 370
        self.pos_y = 20

        self._build_ui()
        self.show_badge()
        self._poll_gestures()

        # 啟動時顯示歡迎特效
        self.root.after(500, lambda: self._flash_color("#00ffcc", "🔮 手勢控制系統已啟動 🔮"))

        self.root.mainloop()

    def _build_ui(self):
        # ─ 狀態列 ─
        self.frame_badge = tk.Frame(self.root, bg="#1a1a2e")
        self.lbl_icon = tk.Label(
            self.frame_badge, text="●", fg="#00ff88",
            bg="#1a1a2e", font=("Segoe UI", 16))
        self.lbl_icon.pack(side="left", padx=(10, 4))
        self.lbl_status = tk.Label(
            self.frame_badge, text="Tracking ON", fg="#00ff88",
            bg="#1a1a2e", font=("Segoe UI", 12, "bold"))
        self.lbl_status.pack(side="left", padx=(0, 10))

        # ─ 手勢快捷選單 ─
        self.frame_menu = tk.Frame(self.root, bg="#1a1a2e")
        tk.Frame(self.frame_menu, bg="#00ffcc", height=2).pack(
            fill="x", padx=10, pady=(6, 8))
        tk.Label(self.frame_menu, text="🔮 手勢快捷指南",
                 fg="#00ffcc", bg="#1a1a2e",
                 font=("Segoe UI", 14, "bold")).pack(pady=(0, 6))

        items = tk.Frame(self.frame_menu, bg="#1a1a2e")
        items.pack(fill="x", padx=10)

        hints = [
            ("🖱️", "Two Up → 移動游標", "#ffffff", "#2a2a3e"),
            ("🖱️", "Peace → 左鍵    Fist → 右鍵", "#ffffff", "#2a2a3e"),
            ("🖱️", "Little Finger → 雙擊", "#ffffff", "#2a2a3e"),
            ("📜", "Rock → 滾動頁面 (上下移動手)", "#ffffff", "#2a2a3e"),
            ("⎋", "Hand Heart → Esc 鍵", "#ffffff", "#2a2a3e"),
            ("✋", "Holy → 開追蹤    XSign → 關追蹤", "#ffffff", "#2a2a3e"),
            ("⏯️", "Timeout → 播放/暫停", "#ffffff", "#2a2a3e"),
            ("🔊", "Like → 音量+    Dislike → 音量-", "#ffffff", "#2a2a3e"),
            ("🔇", "Mute → 切換靜音", "#ffffff", "#2a2a3e"),
            ("📸", "Take Picture → 截圖", "#ffffff", "#2a2a3e"),
            ("👌", "OK → 關閉此選單", "#888888", "#1a1a2e"),
        ]
        for emoji, text, fg, bg in hints:
            row = tk.Frame(items, bg=bg)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=emoji, fg=fg, bg=bg,
                     font=("Segoe UI", 10), width=3).pack(side="left", padx=(6, 0))
            tk.Label(row, text=text, fg=fg, bg=bg,
                     font=("Segoe UI", 10), anchor="w",
                     padx=6, pady=3).pack(side="left", fill="x", expand=True)

    def show_badge(self):
        self.ui_state = "badge"
        self.frame_menu.pack_forget()
        self.frame_badge.pack(fill="x")
        self.root.geometry(f"250x38+{self.pos_x + 110}+{self.pos_y}")
        self.root.deiconify()
        self.root.lift()

    def show_menu(self):
        self.ui_state = "menu"
        self.frame_badge.pack_forget()
        self.frame_badge.pack(fill="x")
        self.frame_menu.pack(fill="both", expand=True)
        self.root.geometry(f"360x430+{self.pos_x}+{self.pos_y}")
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    # ── 截圖閃光特效 ──────────────────────────────────

    def _flash_screen(self):
        """全螢幕白色閃光 (無快門音效)"""
        flash = tk.Toplevel(self.root)
        flash.overrideredirect(True)
        flash.attributes("-topmost", True)
        flash.attributes("-alpha", 0.75)
        flash.configure(bg="#ffffff")
        flash.geometry(f"{self.screen_w}x{self.screen_h}+0+0")

        # 閃光漸退動畫
        def fade():
            alpha = flash.attributes("-alpha")
            if alpha > 0.05:
                flash.attributes("-alpha", alpha - 0.15)
                flash.after(30, fade)
            else:
                flash.destroy()

        flash.after(80, fade)

    def _flash_color(self, color, text):
        """全螢幕顏色閃光特效 + 中央科幻提示 (漸退)"""
        # 1. 建立全螢幕閃光
        flash = tk.Toplevel(self.root)
        flash.overrideredirect(True)
        flash.attributes("-topmost", True)
        flash.attributes("-alpha", 0.25)
        flash.configure(bg=color)
        flash.geometry(f"{self.screen_w}x{self.screen_h}+0+0")
        
        # 2. 建立中央提示窗
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.attributes("-alpha", 0.95)
        toast.configure(bg="#0f0f1e", highlightbackground=color, highlightcolor=color, highlightthickness=3)
        
        tw, th = 400, 80
        cx = (self.screen_w - tw) // 2
        cy = (self.screen_h - th) // 2
        toast.geometry(f"{tw}x{th}+{cx}+{cy}")
        
        lbl = tk.Label(
            toast, text=text, fg=color, bg="#0f0f1e",
            font=("Microsoft JhengHei", 18, "bold")
        )
        lbl.pack(expand=True, fill="both")

        # 漸退動畫
        def fade():
            a_flash = flash.attributes("-alpha")
            a_toast = toast.attributes("-alpha")
            
            if a_flash > 0.0:
                flash.attributes("-alpha", max(0.0, a_flash - 0.08))
            else:
                flash.withdraw()
                
            if a_toast > 0.05:
                toast.attributes("-alpha", max(0.0, a_toast - 0.08))
                toast.after(25, fade)
            else:
                flash.destroy()
                toast.destroy()

        toast.after(400, fade)  # 0.4 秒後開始漸退

    # ── 手勢輪詢 ────────────────────────────────────

    def _poll_gestures(self):
        if not self.shared.running:
            self.root.quit()
            return

        # 截圖閃光
        if self.shared.screenshot_flash:
            self.shared.screenshot_flash = False
            self._flash_screen()

        # 開始/結束追蹤特效
        if self.shared.tracking_start_flash:
            self.shared.tracking_start_flash = False
            self._flash_color("#00ff88", "🔮 系統追蹤已啟動 🔮")

        if self.shared.tracking_stop_flash:
            self.shared.tracking_stop_flash = False
            self._flash_color("#ff4444", "🛑 系統追蹤已關閉 🛑")

        if self.shared.tracking_active:
            self.lbl_icon.config(fg="#00ff88")
            self.lbl_status.config(text="Tracking ON", fg="#00ff88")
        else:
            self.lbl_icon.config(fg="#ff4444")
            self.lbl_status.config(text="Tracking OFF", fg="#ff4444")

        gesture = self.shared.gesture.lower()
        now = time.time()

        if now - self.last_gesture_time > 1.2:
            if gesture == "thumb_index" and self.ui_state == "badge":
                self.show_menu()
                self.last_gesture_time = now
            elif gesture == "ok" and self.ui_state == "menu":
                self.show_badge()
                self.last_gesture_time = now

        self.root.after(33, self._poll_gestures)


# ══════════════════════════════════════════════════════════
#  啟動
# ══════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 52)
    print("  AI 手勢控制系統 (v6)")
    print("  在 OpenCV 視窗按 'q' 退出")
    print("=" * 52)
    print()
    print("  🖱️ 滑鼠")
    print("     移動游標  → Two Up")
    print("     左鍵      → Peace (V字)")
    print("     右鍵      → Fist (握拳)")
    print("     雙擊      → Little Finger (小指)")
    print("     滾動頁面  → Rock 🤘 (手上下移動控制速度)")
    print()
    print("  🔀 系統")
    print("     Esc 鍵    → Hand Heart ❤️")
    print("     開啟追蹤  → Holy")
    print("     關閉追蹤  → XSign")
    print("     截圖      → Take Picture 📸 (附閃光特效)")
    print()
    print("  🎬 媒體")
    print("     播放/暫停 → Timeout")
    print("     切換靜音  → Mute")
    print("     音量 +    → Like 👍")
    print("     音量 -    → Dislike 👎")
    print()
    print("  📋 選單")
    print("     開啟      → Thumb Index")
    print("     關閉      → OK")
    print("=" * 52)

    state = GestureState()

    cam = threading.Thread(target=camera_loop, args=(state,), daemon=True)
    cam.start()

    OSOverlay(state)

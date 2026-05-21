import cv2
import asyncio
import websockets
import json
import threading
import time
import pyautogui
from ultralytics import YOLO

# 設定 PyAutoGUI
pyautogui.FAILSAFE = False # 關閉預設的四角防呆，我們自己實作安全機制
screen_w, screen_h = pyautogui.size()

# Initialize model
model = YOLO('YOLOv10n_gestures.pt') 

# Global variables to store gesture state and coordinates
latest_gesture = "None"
latest_x = 0.5
latest_y = 0.5
smoothed_x = 0.5
smoothed_y = 0.5

# OS-Level Control Variables
os_tracking_active = True
last_click_time = 0
last_rclick_time = 0
last_mute_time = 0

async def gesture_server(websocket):
    print("Webpage connected successfully.")
    while True:
        if latest_gesture != "None":
            # Send data continuously for smooth tracking
            message = json.dumps({
                "gesture": latest_gesture,
                "x": latest_x,
                "y": latest_y,
                "tracking": os_tracking_active
            })
            await websocket.send(message)
        
        # Approximately 30 updates per second to match webcam framerate
        await asyncio.sleep(0.03)

async def start_server_async():
    # Modern approach to start the websockets server
    async with websockets.serve(gesture_server, "localhost", 8765):
        print("WebSocket server started on ws://localhost:8765")
        await asyncio.Future()

def start_ws_server():
    # Use asyncio.run to properly handle the event loop in a new thread
    asyncio.run(start_server_async())

# Start WebSocket in a background thread so it does not block OpenCV
ws_thread = threading.Thread(target=start_ws_server, daemon=True)
ws_thread.start()

cap = cv2.VideoCapture(0)
print("Camera opened. Press 'q' to quit.")

while cap.isOpened():
    success, frame = cap.read()
    if not success: 
        break
    
    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape

    # 2. 將畫面丟給 YOLO 模型進行預測
    # conf=0.5 代表信心度要大於 50% 才算數
    results = model(frame, conf=0.5, verbose=False)
    
    latest_gesture = "None"
    coords_text = "Coords: No Hand Detected"
    
    # 3. 解析 YOLO 的預測結果
    for result in results:
        boxes = result.boxes # 取得所有偵測到的方框
        for box in boxes:
            # 畫上方框
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # 取得手勢名稱與信心度
            class_id = int(box.cls[0])
            latest_gesture = model.names[class_id] # 例如 "like", "ok", "peace"
            confidence = float(box.conf[0])
            
            # 把手勢文字寫在畫面上
            cv2.putText(frame, f"{latest_gesture} {confidence:.2f}", 
                        (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # 更新座標文字
            coords_text = f"Coords: X1={x1}, Y1={y1} | X2={x2}, Y2={y2}"
            
            # Calculate the center of the bounding box
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            
            # 1. 邊緣映射 (Margin Mapping) - 判定框再縮小，只需在中間小區域移動即可
            margin_x = w * 0.25
            margin_y = h * 0.25
            raw_x = (cx - margin_x) / (w - 2 * margin_x)
            raw_y = (cy - margin_y) / (h - 2 * margin_y)
            raw_x = max(0.0, min(1.0, raw_x))
            raw_y = max(0.0, min(1.0, raw_y))
            
            # 2. 絲滑濾波 (Exponential Moving Average)
            smoothing = 0.55
            smoothed_x += smoothing * (raw_x - smoothed_x)
            smoothed_y += smoothing * (raw_y - smoothed_y)
            
            latest_x = smoothed_x
            latest_y = smoothed_y

            # 3. OS-Level 全域滑鼠控制
            now_time = time.time()
            if latest_gesture == 'mute' and (now_time - last_mute_time > 1.5):
                os_tracking_active = not os_tracking_active
                last_mute_time = now_time
                print("OS Tracking Toggled:", os_tracking_active)

            if os_tracking_active:
                target_sx = int(latest_x * screen_w)
                target_sy = int(latest_y * screen_h)
                
                # 移動滑鼠 (手掌、V字、小指)
                if latest_gesture in ['palm', 'open_palm', 'peace', 'little_finger']:
                    # 使用 tweening 可以讓軌跡更平滑，但我們已經有 EMA 了，所以直接丟 moveTo
                    pyautogui.moveTo(target_sx, target_sy, _pause=False)
                
                # 左鍵點擊 (握拳)
                elif latest_gesture == 'fist':
                    if now_time - last_click_time > 0.8:
                        pyautogui.click(x=target_sx, y=target_sy, button='left', _pause=False)
                        last_click_time = now_time
                
                # 右鍵點擊 (暫停手勢)
                elif latest_gesture == 'stop':
                    if now_time - last_rclick_time > 1.2:
                        pyautogui.click(x=target_sx, y=target_sy, button='right', _pause=False)
                        last_rclick_time = now_time

    # 繪製有效感測區域提示框 (使用者只需在框內移動即可涵蓋全螢幕)
    margin_x_int = int(w * 0.25)
    margin_y_int = int(h * 0.25)
    cv2.rectangle(frame, (margin_x_int, margin_y_int), (w - margin_x_int, h - margin_y_int), (255, 0, 255), 2)

    # 4. 在視窗左上角繪製固定座標 HUD 區域 (半透明黑色背景)
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (380, 70), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    
    tracking_status = "ON (OS Mouse)" if os_tracking_active else "OFF (Muted)"
    color_status = (0, 255, 0) if os_tracking_active else (0, 0, 255)
    cv2.putText(frame, f"Tracking: {tracking_status}", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color_status, 2, cv2.LINE_AA)
    cv2.putText(frame, coords_text, (20, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (66, 252, 241), 1, cv2.LINE_AA)

    cv2.imshow('HaGRID YOLOv10 Gesture', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): 
        break

cap.release()
cv2.destroyAllWindows()
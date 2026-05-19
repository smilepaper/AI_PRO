import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision
import asyncio
import websockets
import json
import threading
from ultralytics import YOLO

# 1. 載入你從 HaGRID 下載的模型檔案
model = YOLO('YOLOv10n_gestures.pt') 

latest_gesture = "None"
def gesture_result_callback(result, output_image, timestamp_ms):
    global latest_gesture
    if result.gestures:
        # 取得第一隻手的最佳預測手勢
        latest_gesture = result.gestures[0][0].category_name
    else:
        latest_gesture = "None"

# --- 2. WebSocket Server Logic ---
async def gesture_server(websocket):
    print("Webpage connected successfully.")
    last_sent = ""
    while True:
        # If a valid gesture is detected and it is different from the last sent gesture
        if latest_gesture != "None" and latest_gesture != last_sent:
            message = json.dumps({"gesture": latest_gesture})
            await websocket.send(message)
            last_sent = latest_gesture
        
        # Pause slightly to prevent high CPU usage
        await asyncio.sleep(0.05)

async def start_server_async():
    # Modern approach to start the websockets server
    async with websockets.serve(gesture_server, "localhost", 8765):
        print("WebSocket server started on ws://localhost:8765")
        # Run forever
        await asyncio.Future()

def start_ws_server():
    # Use asyncio.run to properly handle the event loop in a new thread
    asyncio.run(start_server_async())

# Start WebSocket in a background thread so it does not block OpenCV
ws_thread = threading.Thread(target=start_ws_server, daemon=True)
ws_thread.start()

cap = cv2.VideoCapture(0)
timestamp = 0

print('📷 開啟鏡頭... (按 q 離開)')
while cap.isOpened():
    success, frame = cap.read()
    if not success: break
    
    frame = cv2.flip(frame, 1)

    # 2. 將畫面丟給 YOLO 模型進行預測
    # conf=0.5 代表信心度要大於 50% 才算數
    results = model(frame, conf=0.5, verbose=False)
    
    latest_gesture = "None"
    
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

    cv2.imshow('HaGRID YOLOv10 Gesture', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
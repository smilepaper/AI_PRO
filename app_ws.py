import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision
import asyncio
import websockets
import json
import threading

# --- 1. 全域變數：儲存最新手勢 ---
latest_gesture = "None"

def gesture_result_callback(result, output_image, timestamp_ms):
    global latest_gesture
    if result.gestures:
        # 取得第一隻手的最佳預測手勢
        latest_gesture = result.gestures[0][0].category_name
    else:
        latest_gesture = "None"

# --- 2. WebSocket 伺服器邏輯 ---
async def gesture_server(websocket):
    print("網頁已成功連線！")
    last_sent = ""
    while True:
        # 如果偵測到有效手勢，且跟前一次傳送的不同，就傳給網頁
        if latest_gesture != "None" and latest_gesture != last_sent:
            message = json.dumps({"gesture": latest_gesture})
            await websocket.send(message)
            last_sent = latest_gesture
        
        await asyncio.sleep(0.05) # 稍微暫停，避免吃光 CPU 資源

def start_ws_server():
    # 建立一個獨立的事件迴圈給 WebSocket 使用
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    start_server = websockets.serve(gesture_server, "localhost", 8765)
    print("WebSocket 伺服器啟動於 ws://localhost:8765")
    loop.run_until_complete(start_server)
    loop.run_forever()

# 使用多執行緒在背景啟動 WebSocket，才不會卡住 OpenCV 的鏡頭畫面
ws_thread = threading.Thread(target=start_ws_server, daemon=True)
ws_thread.start()

# --- 3. 原本的 MediaPipe 與 OpenCV 邏輯 ---
options = vision.GestureRecognizerOptions(
    base_options=mp.tasks.BaseOptions(model_asset_path='gesture_recognizer.task'),
    running_mode=vision.RunningMode.LIVE_STREAM,
    result_callback=gesture_result_callback
)

recognizer = vision.GestureRecognizer.create_from_options(options)
cap = cv2.VideoCapture(0)
timestamp = 0

print('📷 開啟鏡頭... (按 q 離開)')

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
    timestamp += 1
    recognizer.recognize_async(mp_image, timestamp)

    # 顯示目前手勢在畫面上，方便除錯
    cv2.putText(frame, f"Gesture: {latest_gesture}", (50, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)

    cv2.imshow('Gesture Recognizer Server', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

recognizer.close()
cap.release()
cv2.destroyAllWindows()
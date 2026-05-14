import cv2
import mediapipe as mp
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- 影像組 (Vision Team): 初始化與 Webcam 設定 ---
model_path = 'hand_landmarker.task' # Ensure this file is in your folder

BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# Create options for LIVE_STREAM mode
options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_path),
    running_mode=VisionRunningMode.LIVE_STREAM,
    num_hands=2,
    result_callback=lambda result, output_image, timestamp_ms: process_result(result)
)

# Global variable to store coordinates (for Logic Team)
latest_result = None

# 定義手部 21 個節點的連線規則
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),         # 大拇指 (Thumb)
    (0, 5), (5, 6), (6, 7), (7, 8),         # 食指 (Index)
    (5, 9), (9, 10), (10, 11), (11, 12),    # 中指 (Middle)
    (9, 13), (13, 14), (14, 15), (15, 16),  # 無名指 (Ring)
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20) # 小拇指與手掌邊緣
]

def draw_skeleton_opencv(image, vector_data):
    # 取得影像的實際寬高 (因為 vector_data 裡面的 x, y 是 0.0 ~ 1.0 的比例)
    h, w, _ = image.shape
    
    # 1. 畫出骨架連線 (Line)
    for connection in HAND_CONNECTIONS:
        pt1_idx, pt2_idx = connection
        
        # 將 0.0~1.0 的比例轉換為實際的像素座標
        x1, y1 = int(vector_data[pt1_idx]["x"] * w), int(vector_data[pt1_idx]["y"] * h)
        x2, y2 = int(vector_data[pt2_idx]["x"] * w), int(vector_data[pt2_idx]["y"] * h)
        
        # 畫線 (圖片, 起點, 終點, 顏色 BGR, 粗細)
        cv2.line(image, (x1, y1), (x2, y2), (255, 255, 0), 2) # 青色線條
        
    # 2. 畫出關節點 (Circle)
    for idx, point in vector_data.items():
        cx, cy = int(point["x"] * w), int(point["y"] * h)
        # 畫圓 (圖片, 中心點, 半徑, 顏色 BGR, 填滿)
        cv2.circle(image, (cx, cy), 5, (0, 0, 255), cv2.FILLED) # 紅色關節點

# --- Data Export Function for Logic Team ---
def extract_vector_data(hand_landmarks):
    # Create a dictionary to store the 21 landmarks
    hand_vector_dict = {}
    
    # Loop through all 21 points
    for index, landmark in enumerate(hand_landmarks):
        # Extract x, y, z and store them with their index ID (0-20)
        hand_vector_dict[index] = {
            "x": landmark.x,
            "y": landmark.y,
            "z": landmark.z
        }
        
    return hand_vector_dict

def process_result(result):
    global latest_result
    latest_result = result

# Initialize camera
cap = cv2.VideoCapture(0)
detector = HandLandmarker.create_from_options(options)
timestamp = 0

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    # Convert BGR to RGB for MediaPipe
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
    
    # Send frame for detection
    timestamp += 1
    detector.detect_async(mp_image, timestamp)

    # Gesture Recognition ---
    if latest_result and latest_result.hand_landmarks:
        for landmarks in latest_result.hand_landmarks:
            # 1. Vision Team: Export data to a clean dictionary
            vector_data = extract_vector_data(landmarks)
            draw_skeleton_opencv(frame, vector_data)
            
            # 2. Logic Team: Now they can easily use the dictionary
            tip_y = vector_data[8]["y"]
            pip_y = vector_data[6]["y"]
            
            if tip_y < pip_y:
                cv2.putText(frame, "INDEX UP", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                cv2.putText(frame, "INDEX DOWN", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow('Hand Tracking (Tasks API)', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

detector.close()
cap.release()
cv2.destroyAllWindows()
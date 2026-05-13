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

    # --- 邏輯組 (Logic Team): 判斷手勢 ---
    if latest_result and latest_result.hand_landmarks:
        for landmarks in latest_result.hand_landmarks:
            # Task API output is a list of normalized landmarks
            # Landmark 8 is Index Finger Tip, 6 is Index Finger Pip
            index_tip = landmarks[8]
            index_pip = landmarks[6]

            if index_tip.y < index_pip.y:
                cv2.putText(frame, "INDEX UP", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                # Integration Team can put pyautogui logic here
            else:
                cv2.putText(frame, "INDEX DOWN", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow('Hand Tracking (Tasks API)', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

detector.close()
cap.release()
cv2.destroyAllWindows()
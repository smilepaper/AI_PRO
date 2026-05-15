import cv2
import mediapipe as mp
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

model_path = 'hand_landmarker.task'

BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_path),
    running_mode=VisionRunningMode.LIVE_STREAM,
    num_hands=2,
    result_callback=lambda result, output_image, timestamp_ms: process_result(result)
)

latest_result = None

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)
]

def draw_skeleton_opencv(image, vector_data):
    h, w, _ = image.shape
    
    for connection in HAND_CONNECTIONS:
        pt1_idx, pt2_idx = connection
        
        x1, y1 = int(vector_data[pt1_idx]["x"] * w), int(vector_data[pt1_idx]["y"] * h)
        x2, y2 = int(vector_data[pt2_idx]["x"] * w), int(vector_data[pt2_idx]["y"] * h)
        
        cv2.line(image, (x1, y1), (x2, y2), (255, 255, 0), 2)
        
    for idx, point in vector_data.items():
        cx, cy = int(point["x"] * w), int(point["y"] * h)
        cv2.circle(image, (cx, cy), 5, (0, 0, 255), cv2.FILLED)

def extract_vector_data(hand_landmarks):
    hand_vector_dict = {}
    
    for index, landmark in enumerate(hand_landmarks):
        hand_vector_dict[index] = {
            "x": landmark.x,
            "y": landmark.y,
            "z": landmark.z
        }
        
    return hand_vector_dict

def process_result(result):
    global latest_result
    latest_result = result

cap = cv2.VideoCapture(0)
detector = HandLandmarker.create_from_options(options)
timestamp = 0

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
    
    timestamp += 1
    detector.detect_async(mp_image, timestamp)

    if latest_result and latest_result.hand_landmarks:
        for landmarks in latest_result.hand_landmarks:
            vector_data = extract_vector_data(landmarks)
            draw_skeleton_opencv(frame, vector_data)
            
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
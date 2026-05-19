import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision

# Model path for the gesture recognizer task asset
model_path = 'gesture_recognizer.task'

BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = vision.GestureRecognizer
GestureRecognizerOptions = vision.GestureRecognizerOptions
VisionRunningMode = vision.RunningMode


def gesture_result_callback(result, output_image, timestamp_ms):
    if not result.gestures:
        return

    # Print the first recognized gesture and its score
    first_gesture = result.gestures[0]
    gesture_name = first_gesture.category_name if first_gesture.category_name else 'Unknown'
    score = first_gesture.score if first_gesture.score is not None else 0.0
    print(f'Gesture: {gesture_name}  Score: {score:.2f}')


options = GestureRecognizerOptions(
    base_options=BaseOptions(model_asset_path=model_path),
    running_mode=VisionRunningMode.LIVE_STREAM,
    result_callback=gesture_result_callback
)

recognizer = GestureRecognizer.create_from_options(options)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise RuntimeError('Cannot open camera')

print('Press q to quit')

timestamp = 0

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
    timestamp += 1
    recognizer.recognize_async(mp_image, timestamp)

    cv2.imshow('Gesture Recognizer', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

recognizer.close()
cap.release()
cv2.destroyAllWindows()

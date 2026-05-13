import cv2

print("準備開啟鏡頭...")
# 如果你的筆電有內建鏡頭又有外接鏡頭，可以把 0 改成 1 試試看
cap = cv2.VideoCapture(0) 

if not cap.isOpened():
    print("❌ 錯誤：無法開啟鏡頭。請確認：")
    print("1. 鏡頭是否有接好？")
    print("2. 是否有其他程式（如 Zoom, Line, OBS）正在佔用鏡頭？")
    print("3. Windows 隱私權設定是否允許 Python 使用相機？")
else:
    print("✅ 鏡頭連線成功！嘗試讀取畫面...")
    while True:
        success, img = cap.read()
        if not success:
            print("❌ 錯誤：鏡頭連線了，但讀取不到畫面！")
            break
            
        cv2.imshow("Pure Webcam Test", img)
        
        # 按 'q' 關閉
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
print("程式結束。")
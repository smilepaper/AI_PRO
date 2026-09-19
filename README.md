AI 手勢控制系統 (AI Gesture Control)
===================================

簡介
-----
這是一個以 YOLO 手勢辨識驅動的桌面手勢控制系統，使用攝影機偵測手勢並對系統產生滑鼠、鍵盤與多媒體控制操作。主要程式為 [gesture_app.py](gesture_app.py)，可直接以一行指令啟動。

主要功能
-----
- 移動游標、左鍵/右鍵/雙擊
- 捲動頁面（根據手在視訊影像中的上下位置）
- 截圖（附螢幕閃光特效）
- 播放/暫停、靜音、音量調整
- 開啟/關閉追蹤（顯示 UI 提示）
- 快捷說明選單（Tkinter 懸浮視窗）

手勢對照（預設）
-----
- 移動游標: `two_up`
- 左鍵點擊: `peace` (V 字，座標鎖定)
- 右鍵點擊: `fist` (握拳，座標鎖定)
- 雙擊: `little_finger`
- 滾動頁面: `rock`（手上下移動控制方向與速度）
- Esc 鍵: `hand_heart2`
- 開啟追蹤: `holy`
- 關閉追蹤: `xsign`
- 播放/暫停: `timeout`
- 切換靜音: `mute`
- 音量增加: `like`
- 音量降低: `dislike`
- 螢幕截圖: `take_picture`
- 開啟選單: `thumb_index`
- 關閉選單: `ok`

快速開始
-----
1. 建議建立並啟用 Python 虛擬環境：

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
```

2. 安裝必要套件：

```powershell
pip install ultralytics opencv-python pyautogui pillow
```

3. 將模型檔 `YOLOv10n_gestures.pt` 放在專案根目錄（已包含於此專案）。

4. 執行程式：

```powershell
python gesture_app.py
```

使用說明
-----
- 執行後會彈出 OpenCV 視窗（即攝影機輸出）與右上角懸浮說明面板。
- 在 OpenCV 視窗按 `q` 可關閉攝影機並結束程式。
- UI 面板會在偵測到 `thumb_index` 時展開選單，`ok` 可關閉選單。

設定與調整
-----
- 若偵測不穩定，可調整 `gesture_app.py` 中 YOLO 推論的 `conf`（信心值）或 Dwell Time（停留確認秒數）。
- 若滑鼠移動過快或過慢，可在程式中修改平滑係數 `smoothing` 或將螢幕映射區域調整為不同 margin。

相依/相容性
-----
- 測試平台：Windows（使用 `pyautogui` 控制系統輸入）
- 需安裝相容的 Python 3.8+ 環境


聯絡
-----
如需更多功能或翻譯/文件修改，請在專案中開 issue 或直接聯絡作者。

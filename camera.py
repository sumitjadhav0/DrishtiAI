"""camera.py - Live video capture (OpenCV)"""
import cv2
import time
import queue


# ---------- Function 1: Camera open karun return karto ----------
def open_camera(index=None, width=640, height=480):
    import os
    import config
    index = config.CAMERA_SOURCE if index is None else index
    if isinstance(index, int):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW) if os.name == 'nt' else cv2.VideoCapture(index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    else:                                   # URL / RTSP (glasses, phone camera)
        cap = cv2.VideoCapture(index)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # junya frames jama hou det nahi
    if not cap.isOpened():
        raise RuntimeError("Camera open zala nahi!")
    return cap


# ---------- Function 2: Pratek 10ms la frame ghevun Queue madhe takto ----------
def capture_frames(cap, frame_queue, stop_event, interval=0.01, on_frame=None):
    """interval = 0.01 sec = 10 ms.
    Queue chi size lahan theva (2). Queue full asel tar junа frame kadhun navin takto,
    mhanje model la nehmi LATEST frame milto (lag hot nahi)."""
    while not stop_event.is_set():
        ok, frame = cap.read()
        if ok:
            if on_frame:
                on_frame(frame)                # video display: pratek frame (camera fps)
            if frame_queue.full():
                try:
                    frame_queue.get_nowait()   # junа frame phekun dya
                except queue.Empty:
                    pass
            frame_queue.put((time.time(), frame))  # (time, frame)
        time.sleep(interval)
    cap.release()

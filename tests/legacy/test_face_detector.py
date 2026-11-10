#!/usr/bin/env python3
##
## EPITECH PROJECT, 2026
## MAGIC MIROR
## File description:
## test face_detector
##

import cv2
import time
import sys
sys.path.append("vision")
from camera import Camera
from face_detector import FaceDetector

def test_face_detector_draw():
    cam = Camera()
    detector = FaceDetector()
    face_detected = False
    faces = []
    last_update = 0
    while True:
        frame = cam.get_frame()
        if frame is not None:
            current_time = time.time()
            
            if current_time - last_update >= 0.3:
                face_detected = detector.detect_face(frame)
                if face_detected:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    faces = detector.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
                last_update = current_time
            
            if face_detected:
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                text = "Face detected"
            else:
                text = "No face"
            cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
            cv2.imshow('Face Detection', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            print("Error of capture")
            break
    cv2.destroyAllWindows()
    cam.cap.release()

if __name__ == "__main__":
    test_face_detector_draw()

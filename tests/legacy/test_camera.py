#!/usr/bin/env python3
##
## EPITECH PROJECT, 2026
## MAGIC MIROR
## File description:
## test camera
##

import cv2
import sys
sys.path.append("vision")
from camera import Camera

def test_camera():
    cam = Camera()
    while True:
        frame = cam.get_frame()
        if frame is not None:
            cv2.imshow('MAGIC MIROR', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            print("Error: No frame")
            break
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_camera()

#!/usr/bin/env python3
# coding=utf-8
import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
from task4_object_detection.srv import YOLOLastFrame, YOLOLastFrameResponse
from task4_object_detection.msg import YOLODetection
import numpy as np
from yolov4 import Detector
import random


class YOLOService:
    def __init__(self):
        self.detector = Detector(gpu_id=0, config_path='/opt/darknet/cfg/yolov4.cfg',
                                 weights_path='/opt/darknet/yolov4.weights',
                                 lib_darknet_path='/opt/darknet/libdarknet.so',
                                 meta_path='/ros_ws/src/task4_object_detection/cfg/coco.data')

        self.bridge = CvBridge()
        self.cam_subs = rospy.Subscriber("/usb_cam/image_raw", Image, self.img_callback)

        self.pub = rospy.Publisher("/test_image", Image, queue_size=1)
        self.cv_image = None

        rospy.init_node('yolo_ros')
        s = rospy.Service('get_detections', YOLOLastFrame, self.yolo_service)
        rospy.spin()

    def img_callback(self, msg):
        # TODO: Keep only one every 10 frames
        self.cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='rgb8')

    def yolo_service(self, request):
        res = YOLOLastFrameResponse()
        if self.cv_image is not None:
            img_arr = cv2.resize(self.cv_image, (self.detector.network_width(), self.detector.network_height()))
            detections = self.detector.perform_detect(image_path_or_buf=img_arr, show_image=True)

            for detection in detections:
                box = detection.left_x, detection.top_y, detection.width, detection.height
                print(f'{detection.class_name.ljust(10)} | {detection.class_confidence * 100:.1f} % | {box}')
                d = YOLODetection(detection.class_name, detection.class_confidence, detection.left_x, detection.top_y,
                                  detection.width, detection.height)
                
                res.detections.append(d)
            else:
                # TODO report error
                rospy.logwarn("No Images recieved!")
                pass
        return res

if __name__ == '__main__':
    yolo_ros = YOLOService()
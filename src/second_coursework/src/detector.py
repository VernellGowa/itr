#!/usr/bin/env python

from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np
from yolov4 import Detector
import rospy
import rospkg
import os

class DetectorSingleton:
    _instance = None
    def __new__(cls):
        if cls._instance is None:

            rospack = rospkg.RosPack()
            try:
                package_path = rospack.get_path('second_coursework')
            except rospkg.ResourceNotFound:
                rospy.logerr("Could not find package 'second_coursework'")
                return None
            
            meta_path = os.path.join(package_path, 'cfg', 'coco.data')
            cls._instance = super(DetectorSingleton, cls).__new__(cls)
            cls._instance.detector = Detector(gpu_id=0, config_path='/opt/darknet/cfg/yolov4.cfg',
                                 weights_path='/opt/darknet/yolov4.weights',
                                 lib_darknet_path='/opt/darknet/libdarknet.so',
                                 meta_path=meta_path)
            cls._instance.bridge = CvBridge()
            cls._instance.cv_image = None
            rospy.Subscriber("/usb_cam/image_raw", Image, cls._instance.img_callback) 
        return cls._instance
    
    def img_callback(self, msg):
        self.cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='rgb8')

    def get_detections(self):
        if self.cv_image is not None:
            img_arr = cv2.resize(self.cv_image, (self.detector.network_width(), self.detector.network_height()))
            return self.detector.perform_detect(image_path_or_buf=img_arr, show_image=True)
        else:
            rospy.logwarn("No Images recieved!")
        return []

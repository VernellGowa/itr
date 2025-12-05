#!/usr/bin/env python

import rospy
import smach
from smach import StateMachine, Concurrence
import smach_ros
from smach_ros import SimpleActionState
import random
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from actionlib_msgs.msg import GoalStatus
from geometry_msgs.msg import Twist
import actionlib
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool
from std_srvs.srv import Empty, EmptyResponse

from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
from itr.srv import YOLOLastFrame, YOLOLastFrameResponse
from itr.msg import YOLODetection
import numpy as np
from yolov4 import Detector

def nav_to_room_cb(userdata, goal):
    target = MoveBaseGoal()
    target.target_pose.header.frame_id = "map"
    target.target_pose.header.stamp = rospy.Time.now()
    target.target_pose.pose.position.x = userdata.goal_coords_in[0]
    target.target_pose.pose.position.y = userdata.goal_coords_in[1]
    target.target_pose.pose.orientation.w = 1.0
    return target

class YOLODetectionState(smach.State):
    target_objects = {
        "book": (2,3),
        "phone": (10,9),
        "bottle": (1,9),
        "apple": None
    }

    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(YOLODetectionState, cls).__new__(cls)
        return cls.instance
    
    def __init__(self):
        smach.State.__init__(self, 
                            outcomes=['succeeded', 'aborted'],
                            input_keys=['object_detected_in'],
                            output_keys=['goal_coords_out', 'object_detected_out'] )
        
        self.detector = Detector(gpu_id=0, config_path='/opt/darknet/cfg/yolov4.cfg',
                                 weights_path='/opt/darknet/yolov4.weights',
                                 lib_darknet_path='/opt/darknet/libdarknet.so',
                                 meta_path='/home/k24052303/ros_ws/src/itr/cfg/coco.data')

        self.bridge = CvBridge()
        self.cam_subs = rospy.Subscriber("/usb_cam/image_raw", Image, self.img_callback)

        self.cv_image = None
        self.rate = rospy.Rate(10)

    def img_callback(self, msg):
        self.cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='rgb8')

    def execute(self, userdata):
        while not rospy.is_shutdown():
            if self.cv_image is not None:
                img_arr = cv2.resize(self.cv_image, (self.detector.network_width(), self.detector.network_height()))
                detections = self.detector.perform_detect(image_path_or_buf=img_arr, show_image=True)

                for detection in detections:
                    if detection.class_name in self.target_objects and detection.class_name != userdata.object_detected_in:
                        print(f"DETECTED {detection.class_name}")
                        if detection.class_name == 'apple':
                            return 'aborted'
                        else:
                            userdata.object_detected_out = detection.class_name
                            userdata.goal_coords_out = self.target_objects[detection.class_name]
                            return 'succeeded'
            else:
                rospy.logwarn("No Images recieved!")
                pass
                
            self.rate.sleep()
        return 'succeeded'  

def charger_goal_cb(userdata, goal):
    target = MoveBaseGoal()
    target.target_pose.header.frame_id = "map"
    target.target_pose.header.stamp = rospy.Time.now()
    target.target_pose.pose.position.x = goal.x
    target.target_pose.pose.position.y = goal.y
    target.target_pose.pose.orientation.w = 1.0
    return target      
    
def child_term_cb(outcome_map): 
    if outcome_map.get('DETECT_OBJECTS') == 'succeeded':
        return True
    if outcome_map.get('DETECT_OBJECTS') == 'aborted':
        return True
        
    if outcome_map.get('NAVIGATE_TO_ROOM') == 'completed':
        return True
    if outcome_map.get('NAVIGATE_TO_ROOM') in ['aborted', 'preempted']:
        return 'failed'
    return False

def main():
    rospy.init_node('yolo_node')
    mb_client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
    mb_client.wait_for_server()

    sm = StateMachine(outcomes=['finished'])
    sm.userdata.sm_object_detected = '' 
    sm.userdata.sm_goal_coords = []

    with sm:

        cc = Concurrence(outcomes = ['new_goal', 'completed', 'aborted', 'failed'],
                        default_outcome = 'completed',
                        input_keys=['goal_coords_in', 'object_detected_in'], 
                        output_keys=['goal_coords_out', 'object_detected_out'], 
                        child_termination_cb=child_term_cb,
                        outcome_map={
                            'new_goal': {'DETECT_OBJECTS': 'succeeded'},
                            'aborted': {'DETECT_OBJECTS': 'aborted'},
                            'completed': {'NAVIGATE_TO_ROOM': 'succeeded'},
                            'failed': {'NAVIGATE_TO_ROOM': 'aborted'},
                        })
            
        with cc:
            Concurrence.add('DETECT_OBJECTS', YOLODetectionState(),
                            remapping={'goal_coords_out': 'goal_coords_out', 'object_detected_out': 'object_detected_out',
                             'object_detected_in': 'object_detected_in'})
            Concurrence.add('NAVIGATE_TO_ROOM', 
                SimpleActionState('move_base', MoveBaseAction, goal_cb=nav_to_room_cb, input_keys=['goal_coords_in']),
                    remapping={'goal_coords_in': 'goal_coords_in'})

        StateMachine.add('DETECT_OBJECTS', YOLODetectionState(),
            transitions={'succeeded': 'PARALLEL_MOVE', 'aborted': 'finished', },
            remapping={'goal_coords_out':'sm_goal_coords', 'object_detected_out': 'sm_object_detected',
            'object_detected_in': 'sm_object_detected'}) 
    
        StateMachine.add('PARALLEL_MOVE', cc,
            transitions={'completed': 'DETECT_OBJECTS', 'new_goal': 'PARALLEL_MOVE', 'aborted': 'finished', 'failed': 'finished'},
            remapping={'goal_coords_in':'sm_goal_coords', 'goal_coords_out':'sm_goal_coords', 
            'object_detected_out': 'sm_object_detected', 'object_detected_in': 'sm_object_detected'})

    outcome = sm.execute()

if __name__ == '__main__':
    main()
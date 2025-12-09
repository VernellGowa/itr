#!/usr/bin/env python
from std_msgs.msg import Bool
import rospy
import smach
from smach import StateMachine, Concurrence
import smach_ros
from smach_ros import SimpleActionState
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from actionlib_msgs.msg import GoalStatus
import actionlib
from detector import DetectorSingleton

from second_coursework.srv import FindObject, FindObjectResponse, FindObjectRequest
from second_coursework.msg import FindObjectAction, FindObjectFeedback

ROOMS = {
    'A': (4,8),
    'B': (8,8),
    'C': (2,2),
    'D': (2,8),
    'E': (4,2),
    'F': (8,2),
}

class FindObjectState(smach.State):
    food_items = ['pizza', 'sandwich', 'banana', 'broccol']
    
    def __init__(self, find_object_serv):
        smach.State.__init__(self, 
                            outcomes=['found', 'not_found'],
                            output_keys=['found', 'room_no'] )
        
        self.detector = DetectorSingleton()
        self.rate = rospy.Rate(10)
        self.server = find_object_serv
        
    def execute(self, userdata):
        timeout_duration = rospy.Duration(5.0)
        start_time = rospy.Time.now()

        while (rospy.Time.now() - start_time) < timeout_duration and not rospy.is_shutdown():
            if self.server.is_preempt_requested():
                self.server.set_preempted()
                return 'preempted'
            
            detections = self.detector.get_detections()
            if detections:
                for detection in detections:
                    if detection.class_name == userdata.object_name:
                        userdata.has_found = True

                        return 'found'

            self.rate.sleep()
        userdata.room_no = (userdata.room_no+1) % 6

        return 'not_found'        


class ReportState(smach.State):
    def __init__(self):
        smach.State.__init__(self, 
                            outcomes=['finished',], )
        
    def execute(self, userdata):
        txt = f"Found the object, {userdata.object_name} in room {chr(65+userdata.room_no)}"

        return 'finished' 

class FindObjectActionServer():
    def __init__(self):
        self.find_object_serv = actionlib.SimpleActionServer('find_object_action', FindObjectAction,
            execute_cb=self.find_object_execute_cb, auto_start=False)

        self.mb_client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        self.mb_client.wait_for_server()

        self.find_object_serv.start()

    def nav_to_room_cb(self, userdata, goal):
        target = MoveBaseGoal()
        coords = ROOMS[chr(65+userdata.room_no)] if not userdata.has_found else ROOMS['E']
        target.target_pose.header.frame_id = "map"
        target.target_pose.header.stamp = rospy.Time.now()
        target.target_pose.pose.position.x = coords[0]
        target.target_pose.pose.position.y = coords[1]
        target.target_pose.pose.orientation.w = 1.0
        return target
    
    def nav_result_cb(self, userdata, status, result):
        if status == GoalStatus.SUCCEEDED:
            if userdata.has_found:
                return 'found'
            else:
                return 'succeeded'
        
        return 'aborted'

    def find_object_execute_cb(self, goal):
        sm = StateMachine(outcomes=['finished'])
        sm.userdata.room_no = 0
        sm.userdata.has_found = False
        sm.userdata.object_name = goal.name

        with sm:
            StateMachine.add('NAVIGATE_TO_ROOM', 
                SimpleActionState('move_base', MoveBaseAction, goal_cb=self.nav_to_room_cb, result_cb=self.nav_result_cb),
                transitions={'succeeded': 'find_object', 'aborted':'failed', 'found':'report'},
                remapping={'room_no': 'room_no', 'has_found': 'has_found'})
        
            StateMachine.add('find_object', FindObjectState(self.find_object_serv),
                transitions={'found': 'NAVIGATE_TO_ROOM', 'not_found': 'NAVIGATE_TO_ROOM', 'preempted': 'finished'},
                remapping={'object_name': 'object_name', 'room_no':'room_no', 'has_found': 'has_found'}) 
            
            StateMachine.add('report', ReportState(),
                transitions={'finished': 'finished',},
                remapping={'room_no': 'room_no', 'object_name': 'object_name'}) 
        
        outcome = sm.execute()
    
        if outcome == 'preempted':
            self.find_object_serv.set_preempted()
        elif outcome == 'succeeded':
            self.find_object_serv.set_succeeded()
        else:
            self.find_object_serv.set_aborted()

if __name__ == '__main__':
    rospy.init_node('find_object_node')
    server = FindObjectActionServer()
    rospy.spin()
    




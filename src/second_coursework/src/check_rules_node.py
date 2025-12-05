#!/usr/bin/env python

import rospy
import smach
from smach import StateMachine, Concurrence
from smach_ros import SimpleActionState
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
import actionlib
from second_coursework.msg import CheckRulesAction, CheckRulesFeedback
from detector import DetectorSingleton

ROOMS = {
    'kitchen': (4,8),
    'bedroom': (8,8)
}

class CheckRuleState(smach.State):
    food_items = ['pizza', 'sandwich', 'banana', 'broccol']
    
    def __init__(self, check_rules_serv):
        smach.State.__init__(self, 
                            outcomes=['finished', 'preempted'],
                             output_keys=['room_out'] )
        
        self.detector = DetectorSingleton()
        self.rate = rospy.Rate(10)
        self.server = check_rules_serv

    def execute(self, userdata):
        if self.preempt_requested():
            self.service_preempt()
            return 'preempted'

        feedback = CheckRulesFeedback()
        timeout_duration = rospy.Duration(5.0)
    
        start_time = rospy.Time.now()
        userdata.room_out = 'kitchen' if userdata.room == 'bedroom' else 'bedroom'

        while (rospy.Time.now() - start_time) < timeout_duration and not rospy.is_shutdown():
            if self.server.is_preempt_requested():
                self.server.set_preempted()
                return 'preempted'
            
            detections = self.detector.get_detections()
            for detection in detections:
                if userdata.room == 'kitchen':
                    if detection.class_name == 'human':
                        # self.rule_pub.publish(1)
                        feedback.broken_rule = 1
                        self.server.publish_feedback(feedback)

                elif userdata.room == 'bedroom':
                    if detection.class_name in self.food_items:
                        # self.rule_pub.publish(2)
                        feedback.broken_rule = 2
                        self.server.publish_feedback(feedback)
            self.rate.sleep()

        return 'finished'

class CheckRulesActionServer():
    def __init__(self):
        self.check_rules_serv = actionlib.SimpleActionServer('check_rules', CheckRulesAction,
         execute_cb=self.check_rules_execute_cb, auto_start=False)

        self.mb_client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        self.mb_client.wait_for_server()

        self.check_rules_serv.start()

    def nav_to_room_cb(self, userdata, goal):
        target = MoveBaseGoal()
        coords = ROOMS[userdata.room]
        target.target_pose.header.frame_id = "map"
        target.target_pose.header.stamp = rospy.Time.now()
        target.target_pose.pose.position.x = coords[0]
        target.target_pose.pose.position.y = coords[1]
        target.target_pose.pose.orientation.w = 1.0
        return target

    def check_rules_execute_cb(self, goal):
        sm = StateMachine(outcomes=['finished'])
        sm.userdata.room = 'kitchen'

        with sm:
            StateMachine.add('NAVIGATE_TO_ROOM', 
                SimpleActionState('move_base', MoveBaseAction, goal_cb=self.nav_to_room_cb),
                transitions={'succeeded': 'CHECK_RULES', 'aborted':'failed', 'preempted':'failed'},
                remapping={'room': 'room'})
        
            StateMachine.add('CHECK_RULES', CheckRuleState(self.check_rules_serv),
                transitions={'finished': 'NAVIGATE_TO_ROOM', 'preempted': 'preempted'},
                remapping={'room':'room', 'room_out':'room'}) 
            
        outcome = sm.execute()
    
        if outcome == 'preempted':
            self.check_rules_serv.set_preempted()
        elif outcome == 'succeeded':
            self.check_rules_serv.set_succeeded()
        else:
            self.check_rules_serv.set_aborted()

if __name__ == '__main__':
    rospy.init_node('check_rules_node')
    server = CheckRulesActionServer()
    rospy.spin()
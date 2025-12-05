#!/usr/bin/env python

import rospy
import smach
from smach import StateMachine, Concurrence
from smach_ros import SimpleActionState
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
import actionlib
from second_coursework.srv import FindObject, FindObjectResponse
from second_coursework.msg import FindObjectAction, FindObjectGoal
from second_coursework.msg import CheckRulesAction, CheckRulesGoal

class WaitState(smach.State):
    def __init__(self):
        smach.State.__init__(self, 
                            outcomes=['finished', 'preempted'],)
        
    def execute(self, userdata):
        for _ in range(100): 
            if rospy.is_shutdown(): return 'preempted'
            rospy.sleep(0.1)
        return 'finished'
    
class WorkerState(smach.State):
    def __init__(self):
        smach.State.__init__(self, 
                             outcomes=['preempted', ],)
        self.check_rules_client = actionlib.SimpleActionClient('/check_rules', CheckRulesAction)
        self.find_object_client = actionlib.SimpleActionClient('/find_object_action', FindObjectAction)
        
        self.check_rules_client.wait_for_server()
        self.find_object_client.wait_for_server()

        self.is_searching_for_object = False 
        self.trigger_find_object = False
        self.object_name = ""

        self.service = rospy.Service('/find_object', FindObject, self.handle_find_object_request)

    def execute(self, userdata):
        self.start_check_rules()
        rate = rospy.Rate(10)
        
        while not rospy.is_shutdown():
            if self.trigger_find_object:
                self.check_rules_client.cancel_all_goals()

                goal = FindObjectGoal()
                goal.name = self.object_name 
                self.find_object_client.send_goal(goal)
                self.find_object_client.wait_for_result()
                
                self.trigger_find_object = False
                self.start_check_rules()

            rate.sleep()
            
        return 'preempted'
    def start_check_rules(self):
        goal = CheckRulesGoal()
        self.check_rules_client.send_goal(goal)

    def handle_find_object_request(self, req):
        if self.trigger_find_object:
            rospy.logwarn("Already searching for an object.")
            return False 
        
        self.object_name = req.object_name
        self.trigger_find_object = True

        return True 

def main():
    rospy.init_node('cw2_node')
    mb_client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
    mb_client.wait_for_server()

    sm = StateMachine(outcomes=['finished', 'failed'])
    with sm:
    
        StateMachine.add('WAIT', WaitState(),
            transitions={'finished': 'WORKER', 'preempted': 'failed'},) 
        StateMachine.add('WORKER', WorkerState(),
            transitions={'preempted': 'failed'},) 
    outcome = sm.execute()

if __name__ == '__main__':
    main()
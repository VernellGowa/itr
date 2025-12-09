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


battery = 100
vel = None


def low_battery(req):
    global battery
    battery = 10
    return EmptyResponse()

def low_battery_server():
    s = rospy.Service('low_battery', Empty, low_battery)

def charger_goal_cb(userdata, goal):
    target = MoveBaseGoal()
    target.target_pose.header.frame_id = "map"
    target.target_pose.header.stamp = rospy.Time.now()
    target.target_pose.pose.position.x = 11.0
    target.target_pose.pose.position.y = 2.0
    target.target_pose.pose.orientation.w = 1.0
    return target

class CleanState(smach.State):
    def __init__(self):
        smach.State.__init__(self, 
                             outcomes=['succeeded'], )
        self.dirt_pub = rospy.Publisher('/dirt_detected', Bool, queue_size=10)
        
    def execute(self, userdata):
        rate = rospy.Rate(2) 
        command = Twist()
        command.angular.z = 5

        for _ in range(20):
            vel.publish(command)
            rate.sleep()
        self.dirt_pub.publish(False)

        return 'succeeded'
    
class TurnState(smach.State):
    def __init__(self):
        smach.State.__init__(self, 
                             outcomes=['clear',], )
    #     self.trigger = False
        
    # def avoid_obstacles(self, data: LaserScan):
    #     closest_object = min(data.ranges)
    #     self.trigger = closest_object < 0.5

    def execute(self, userdata):
        # sub = rospy.Subscriber('/base_scan/pose', LaserScan, self.avoid_obstacles)
        # while not rospy.is_shutdown():
        #     if self.preempt_requested():
        #         self.service_preempt()
        #         return 'clear'
            
        # if self.trigger:
        rate = rospy.Rate(10) 
        command = Twist()
        command.angular.z = 1

        for _ in range(5):
            vel.publish(command)
            rate.sleep()        

            # return 'blocked'
        return 'clear'

class MonitorObstaclesState(smach.State):
    def __init__(self):
        smach.State.__init__(self, 
                             outcomes=['clear', 'blocked'], )
        self.trigger = False
        
    def avoid_obstacles(self, data: LaserScan):
        closest_object = min(data.ranges)
        self.trigger = closest_object < 0.5

    def execute(self, userdata):
        sub = rospy.Subscriber('/base_scan', LaserScan, self.avoid_obstacles)
        while not rospy.is_shutdown():
            if self.preempt_requested():
                self.service_preempt()
                return 'clear'
            
            if self.trigger:
                return 'blocked'
            
        return 'clear'

class DetectDirtState(smach.State):
    def __init__(self):
        smach.State.__init__(self, 
                             outcomes=['detected_dirt', 'not_detected_dirt'],)
        self.trigger = False
        
    def detect_dirt(self, data: Bool):
        self.trigger = data.data     
        
    def execute(self, userdata):
        self.trigger = False
        sub = rospy.Subscriber('/dirt_detected', Bool, self.detect_dirt)
        while not rospy.is_shutdown():
            if self.preempt_requested():
                self.service_preempt()
                return 'not_detected_dirt'
            if self.trigger:
                
                return 'detected_dirt'
            
        return 'not_detected_dirt'

class MonitorBatteryState(smach.State):
    def __init__(self):
        smach.State.__init__(self, 
                             outcomes=['high', 'low'],)
        
    def execute(self, userdata):
        global battery
        if battery < 20:
            return 'low'
        else:
            return 'high'

class ChargeState(smach.State):
    def __init__(self):
        smach.State.__init__(self, 
                             outcomes=['high'],)
        
    def execute(self, userdata):
        global battery
        print("CHARGINGGG")
        while battery < 100:
            battery += 1
            rospy.sleep(0.25)

        return 'high'
    
class RandomMoveState(smach.State):
    def __init__(self):
        smach.State.__init__(self, 
                             outcomes=['preempted', 'low', 'aborted'],)
        
    def execute(self, userdata):
        rate = rospy.Rate(10) 
        global battery

        while not rospy.is_shutdown():
            if self.preempt_requested():
                self.service_preempt()
                return 'preempted'

            command = Twist()
            command.linear.x = 0.5
            command.angular.z = random.uniform(-1, 1)
            vel.publish(command)

            if battery < 20:
                return 'low'
            
            rate.sleep()
        return 'aborted'
        
def child_term_cb(outcome_map): 
    if outcome_map.get('DETECT_DIRT') == 'detected_dirt':
        return True
    if outcome_map['MONITOR_OBSTACLES'] == 'blocked':
        return True
    if outcome_map['RANDOM_MOVE'] == 'low':
        return True

    return False

def main():
    rospy.init_node('vacuum_behaviour')
    low_battery_server()
    mb_client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
    mb_client.wait_for_server()

    global vel
    vel = rospy.Publisher('/cmd_vel', Twist, queue_size=10)

    sm = StateMachine(outcomes=['finished'])

    with sm:
        cc = Concurrence(outcomes = ['preempted', 'low', 'obstructed', 'found_dirt'],
                        default_outcome = 'preempted',
                        child_termination_cb=child_term_cb,
                        outcome_map={
                            'found_dirt': {'DETECT_DIRT': 'detected_dirt'},
                            'obstructed': {'MONITOR_OBSTACLES': 'blocked'},
                            'low': {'RANDOM_MOVE': 'low'}
                        })
        
        with cc:
            Concurrence.add('DETECT_DIRT', DetectDirtState())
            Concurrence.add('RANDOM_MOVE', RandomMoveState())
            Concurrence.add('MONITOR_OBSTACLES', MonitorObstaclesState())

        StateMachine.add('PARALLEL_MOVE', cc,
            transitions={'preempted': 'MONITOR_CHARGING', 'found_dirt': 'CLEAN', 'obstructed': 'TURN', 'low': 'NAVIGATE_TO_CHARGER'})
        
        StateMachine.add('MONITOR_CHARGING', MonitorBatteryState(),
            transitions={'high': 'PARALLEL_MOVE', 'low': 'NAVIGATE_TO_CHARGER'})
        
        StateMachine.add('NAVIGATE_TO_CHARGER', 
            SimpleActionState('move_base', MoveBaseAction, goal_cb=charger_goal_cb),
            transitions={'succeeded': 'CHARGE', 'aborted':'PARALLEL_MOVE', 'preempted':'PARALLEL_MOVE'})
        
        StateMachine.add('CHARGE', ChargeState(),
            transitions={'high': 'PARALLEL_MOVE',}) 
        
        StateMachine.add('TURN', TurnState(),
            transitions={'clear': 'PARALLEL_MOVE'}) 

        StateMachine.add('CLEAN', CleanState(),
            transitions={'succeeded': 'PARALLEL_MOVE'}) 
   
    outcome = sm.execute()

if __name__ == '__main__':
    main()
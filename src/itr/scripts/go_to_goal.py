#!/usr/bin/env python3
import math
import rospy 
import actionlib
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal 
from actionlib_msgs.msg import GoalStatus

rospy.init_node('go_to_point')

move_base_client = actionlib.SimpleActionClient( 'move_base', MoveBaseAction)
move_base_client.wait_for_server()

goal = MoveBaseGoal()

goal.target_pose.header.stamp = rospy.get_rostime()
goal.target_pose.header.frame_id = 'map'

goal.target_pose.pose.position.x = 1.95
goal.target_pose.pose.position.y = 8.66
goal.target_pose.pose.position.z = 0

goal.target_pose.pose.orientation.x = 0
goal.target_pose.pose.orientation.y = 0
goal.target_pose.pose.orientation.z = math.sin(-math.pi/4)
goal.target_pose.pose.orientation.w = math.cos(-math.pi/4)

print("about to start")

move_base_client.send_goal(goal)
move_base_client.wait_for_result()

status = move_base_client.get_state()

if status == GoalStatus.SUCCEEDED:
    print("yay")
else:
    print("noo")

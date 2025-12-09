#!/usr/bin/env python3

import rospy
import math
import angles
from geometry_msgs.msg import Twist
import actionlib
from geometry_msgs.msg import Point


from task2_actions_services.msg import LookAtAction
from task2_actions_services.msg import LookAtGoal

from task2_actions_services.msg import GoToLocationAction
from task2_actions_services.msg import GoToLocationGoal

def delivery():
    def act(room, look_at_goal):
        go_to_goal = GoToLocationGoal(room)

        # GO TO LOCATION ACTION
        go_to_client.send_goal(go_to_goal)
        no_timeout = go_to_client.wait_for_result(rospy.Duration(80.0))

        if not no_timeout:
            rospy.loginfo("Go to clinet Action did not finish before the timeout.")
            go_to_client.cancel_goal()
            return

        go_to_result = go_to_client.get_result()

        if go_to_result:
            rospy.loginfo(f"Action finished! Reached successfully!")
        else:
            rospy.loginfo(f"Action finished! Failed to reach successfully!")

        # LOOK AT ACTION

        look_at_client.send_goal(look_at_goal)
        no_timeout = look_at_client.wait_for_result(rospy.Duration(30.0))

        if not no_timeout:
            rospy.loginfo("Action did not finish before the timeout.")
            look_at_client.cancel_goal()

        look_at_result = look_at_client.get_result()

        if look_at_result:
            rospy.loginfo(f"Action finished! Oriented successfully!")
        else:
            rospy.loginfo(f"Action finished! Failed to orient successfully!")

    rospy.init_node('delivery')

    go_to_client = actionlib.SimpleActionClient('go_to', GoToLocationAction)
    look_at_client = actionlib.SimpleActionClient('look_at', LookAtAction)

    go_to_client.wait_for_server()
    look_at_client.wait_for_server()

    # go_to_goal = GoToLocationGoal("living_room")
    # go_to_goal2 = GoToLocationGoal("kitchen")

    look_at_goal = LookAtGoal()
    look_at_goal.location.x = 1
    look_at_goal.location.y = 1
    look_at_goal.location.z = 0

    act("living_room", look_at_goal)
    act("kitchen", look_at_goal)



if __name__ == '__main__':
    try:
        delivery()
    except rospy.ROSInterruptException:
        pass
#!/usr/bin/env python3

import rospy
import math
import angles
import actionlib
from random import random
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from actionlib_msgs.msg import GoalStatus
from tf.transformations import quaternion_from_euler, euler_from_quaternion
import tf

from itr.msg import LookAtAction
from itr.msg import LookAtGoal
from itr.msg import LookAtResult
from itr.msg import LookAtFeedback

from itr.msg import GoToLocationAction
from itr.msg import GoToLocationGoal
from itr.msg import GoToLocationResult
from itr.msg import GoToLocationFeedback

from itr.srv import GetCoordinates

class CleanerActionServer():


    def __init__(self):
        self.tf_listener = tf.TransformListener()

        self.go_to_location_serv = actionlib.SimpleActionServer('go_to', GoToLocationAction,
         execute_cb=self.go_to_location_execute_cb, auto_start=False)
        
        self.mb_client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        self.mb_client.wait_for_server()

        self.look_at_serv.start()
        self.go_to_location_serv.start()

    def get_robot_pose(self):
        # try:
            return self.tf_listener.lookupTransform('/map', '/base_link', rospy.Time(0))
        # except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
        #     return None, None


    def go_to_location_execute_cb(self, goal):
        rospy.wait_for_service('get_coordinates')
        location_result = GoToLocationResult()

        try:
            get_coordinates = rospy.ServiceProxy('get_coordinates', GetCoordinates)
            self.goal_coords = get_coordinates(goal.name).coords

            mb_goal = MoveBaseGoal()
            mb_goal.target_pose.header.frame_id = "map"
            mb_goal.target_pose.header.stamp = rospy.Time.now()

            mb_goal.target_pose.pose.position.x = uniform(-5, 5)
            mb_goal.target_pose.pose.position.y = uniform(-5, 5)
            mb_goal.target_pose.pose.orientation.w = 1

            self.mb_client.send_goal(mb_goal, feedback_cb=self.location_feedback_callback)
            self.mb_client.wait_for_result()

            status = self.mb_client.get_state()

            if status == GoalStatus.SUCCEEDED:
                location_result.result = True 
                self.go_to_location_serv.set_succeeded(location_result)
            else:
                self.go_to_location_serv.set_aborted()
                return False

        except rospy.ServiceException as e:
            print("Service call failed: %s"%e)

    def location_feedback_callback(self, feedback):
        location_feedback = GoToLocationFeedback()

        current_x = feedback.base_position.pose.position.x
        current_y = feedback.base_position.pose.position.y

        diff = (self.goal_coords.x - current_x, self.goal_coords.y - current_y)

        location_feedback.distance = math.hypot(*diff)

        self.go_to_location_serv.publish_feedback(location_feedback)


if __name__ == '__main__':
    rospy.init_node('delivery_actions')
    server = CleanerActionServer()
    rospy.spin()
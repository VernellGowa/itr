#!/usr/bin/env python3

import rospy
import math
import angles
import actionlib
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

class DeliveryActionServer():


    def __init__(self):
        self.tf_listener = tf.TransformListener()

        self.look_at_serv = actionlib.SimpleActionServer('look_at', LookAtAction,
         execute_cb=self.look_at_execute_cb, auto_start=False)

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

    def look_at_execute_cb(self, goal):
        look_at_result = LookAtResult()
        self.person_location = goal.location
        print("about to start", goal.location)
        try:
            pos, qt = self.get_robot_pose()

            diff = (self.person_location.x - pos[0], self.person_location.y- pos[1])
            goal_orientation = math.atan2(diff[1], diff[0])

            q_orientation = quaternion_from_euler(0, 0, goal_orientation)
            
            mb_goal = MoveBaseGoal()
            mb_goal.target_pose.header.frame_id = "map"
            mb_goal.target_pose.header.stamp = rospy.Time.now()

            mb_goal.target_pose.pose.position.x = pos[0]
            mb_goal.target_pose.pose.position.y = pos[1]

            mb_goal.target_pose.pose.orientation.x = 0
            mb_goal.target_pose.pose.orientation.y = 0
            mb_goal.target_pose.pose.orientation.z = q_orientation[2]
            mb_goal.target_pose.pose.orientation.w = q_orientation[3]

            self.mb_client.send_goal(mb_goal, feedback_cb=self.look_at_feedback_callback)
            self.mb_client.wait_for_result()

            status = self.mb_client.get_state()

            if status == GoalStatus.SUCCEEDED:
                look_at_result.result = True 
                self.look_at_serv.set_succeeded(look_at_result)
            else:
                self.look_at_serv.set_aborted()
                return False

        except rospy.ServiceException as e:
            print("Service call failed: %s"%e)

    def go_to_location_execute_cb(self, goal):
        rospy.wait_for_service('get_coordinates')
        location_result = GoToLocationResult()

        try:
            get_coordinates = rospy.ServiceProxy('get_coordinates', GetCoordinates)
            self.goal_coords = get_coordinates(goal.name).coords

            mb_goal = MoveBaseGoal()
            mb_goal.target_pose.header.frame_id = "map"
            mb_goal.target_pose.header.stamp = rospy.Time.now()

            mb_goal.target_pose.pose.position.x = self.goal_coords.x
            mb_goal.target_pose.pose.position.y = self.goal_coords.y
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

    def look_at_feedback_callback(self, feedback):
        look_at_feedback = LookAtFeedback()

        current_x = feedback.base_position.pose.position.x
        current_y = feedback.base_position.pose.position.y

        diff = (self.person_location.x - current_x, self.person_location.y - current_y)

        orientation_quat = feedback.base_position.pose.orientation
        quaternion = [0, 0, orientation_quat.z, orientation_quat.w]

        _, _, angle = euler_from_quaternion(quaternion)
        goal_orientation = math.atan2(diff[1], diff[0])

        look_at_feedback.offset = angles.shortest_angular_distance(angle, goal_orientation)
        self.look_at_serv.publish_feedback(look_at_feedback)

if __name__ == '__main__':
    rospy.init_node('delivery_actions')
    server = DeliveryActionServer()
    rospy.spin()

# source devel/setup.bash
# roslaunch itr delivery.launch
# rosrun itr delivery.py
# roslaunch rosplan_stage_demo empty_stage_single_robot.launch
# rosrun rviz rviz rospack -d `rospack find rosplan_stage_demo`/config/rosplan_stage_demo.rviz

    # def go_to_location_execute_cb(self, goal):
    #     rospy.wait_for_service('get_coordinates')
    #     location_result = GoToLocationResult()
    #     look_at_result = LookAtResult()

    #     try:
    #         get_coordinates = rospy.ServiceProxy('get_coordinates', GetCoordinates)
    #         self.goal_coords = get_coordinates(goal.name)

    #         diff = (self.person_location[0] - self.goal_coords.x, self.person_location[1]- self.goal_coords.y)
    #         goal_orientation = math.atan2(diff[1], diff[0])

    #         q_orientation = quaternion_from_euler(0, 0, goal_orientation)
            
    #         mb_client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
    #         mb_client.wait_for_server()

    #         goal = MoveBaseGoal()
    #         goal.target_pose.header.frame_id = "map"
    #         goal.target_pose.header.stamp = rospy.Time.now()

    #         goal.target_pose.pose.position.x = self.goal_coords.x
    #         goal.target_pose.pose.position.y = self.goal_coords.y
    #         goal.target_pose.pose.position.z = 0.0

    #         goal.target_pose.pose.orientation.x = 0
    #         goal.target_pose.pose.orientation.y = 0
    #         goal.target_pose.pose.orientation.z = q_orientation[2]
    #         goal.target_pose.pose.orientation.w = q_orientation[3]

    #         mb_client.send_goal(goal, feedback_cb=self.feedback_callback)
    #         mb_client.wait_for_result()


    #         status = mb_client.get_state()

    #         if status == GoalStatus.SUCCEEDED:
    #             location_result.success = True 
    #             self.go_to_location_serv.set_succeeded(location_result)
    #         else:
    #             self.go_to_location_serv.set_aborted()
    #             return False

    #     except rospy.ServiceException as e:
    #         print("Service call failed: %s"%e)

    # def look_at_execute_cb(self, goal):
    #     command = Twist()
    #     diff = (self.person_location[0] - self.goal_coords.x, self.person_location[1]- self.goal_coords.y)
    #     goal_orientation = math.atan2(diff[1], diff[0])
    #     arrived = False
    #     look_at_feedback = LookAtFeedback()

    #     while not arrived:

    #         angle_diff = angles.shortest_angular_distance(goal.theta, goal_orientation)

    #         if angle_diff < -0.01: 
    #             command.angular.z = -1
    #         elif angle_diff > 0.01:
    #             command.angular.z = 1
    #         else:
    #             arrived = True

    #         look_at_feedback.offset = angle_diff
    #         self.look_at_serv.publish_feedback(look_at_feedback)
            
            
    #         # vel.publish(command)
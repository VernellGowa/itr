#!/usr/bin/env python3

import rospy
import math
import angles
from turtlesim.msg import Pose
from geometry_msgs.msg import Twist
import actionlib
from itr.msg import LookAtAction
from itr.msg import LookAtGoal
from itr.msg import LookAtResult
from itr.msg import LookAtFeedback

from itr.msg import GoToLocationAction
from itr.msg import GoToLocationGoal
from itr.msg import GoToLocationResult
from itr.msg import GoToLocationFeedback

rospy.init_node('goto_node')
vel = rospy.Publisher('/turtle1/cmd_vel', Twist, queue_size=5000)

class DeliveryActionServer():

    def __init__(self):
        self.look_at_serv = actionlib.SimpleActionServer('delivery', LookAtAction,
         execute_cb=self.look_at_execute_cb)

        self.go_to_location_serv = actionlib.SimpleActionServer('delivery', LookAtAction,
         execute_cb=self.go_to_location_execute_cb)

        self.look_at_serv.start()
        self.go_to_location_serv.start()
        self.arrived_orientation = False

    def look_at_execute_cb(self, goal):
        self.goal_orientation = goal

        while self.arrived_orientation:
            rospy.Subscriber('/turtle1/pose', Pose, self.look_at)
        command = Twist()
        diff = (x - current.x, y- current.y)
        goal_orientation = math.atan2(diff[1], diff[0])

        angle_diff = angles.shortest_angular_distance(current.theta, goal_orientation)

    def look_at(self, current: Pose):

        if current.theta > self.goal_orientation + 0.01:
            command.angular.z = -1
        elif current.theta < self.goal_orientation - 0.01:
            command.angular.z = 1
        else:
            command.angular.z = -current.theta
            self.arrived_orientation = True
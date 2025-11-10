#!/usr/bin/env python3

import rospy
import math
import angles
from turtlesim.msg import Pose
from geometry_msgs.msg import Twist


START = (2, 2)
LENGTH = 10
rospy.init_node('goto_node')
vel = rospy.Publisher('/turtle1/cmd_vel', Twist, queue_size=5000)
# command = Twist()

def closed(current: Pose, x, y):
    arrived = False
    command = Twist()
    diff = (x - current.x, y- current.y)
    goal_orientation = math.atan2(diff[1], diff[0])

    angle_diff = angles.shortest_angular_distance(current.theta, goal_orientation)

    if angle_diff < -0.087: 
        
        command.angular.z = -1
    elif angle_diff > 0.087:
        command.angular.z = 1
    elif math.hypot(*diff) > 0.2:
        command.linear.x = 1
    
    if math.hypot(*diff) < 0.2:
        if current.theta > 0.01:
            command.angular.z = -1
        elif current.theta < -0.01:
            command.angular.z = 1
        else:
            command.angular.z = -current.theta
            arrived = True

    vel.publish(command)
    return arrived

def open():
    rate = rospy.Rate(LENGTH//2) 

    # def pause():
    #     command = Twist()
    #     vel.publish(command)
    #     for i in range(5): rate.sleep()     

    # def rotate():
    #     command = Twist()
    #     command.angular.z = math.pi / (4)
    #     for i in range(LENGTH):
    #         vel.publish(command)
    #         rate.sleep()

    def act(linear=0, angular=0, loops=5):
        command = Twist()
        command.linear.x = linear
        command.angular.z = angular

        for i in range(loops):
            vel.publish(command)
            rate.sleep()

    def move_corner(distance):
        act()                                   # Pause
        act(linear=1, loops=distance)           # Move Forward
        act()                                   # Pause
        act(angular=math.pi/4, loops=LENGTH)    # Rotate

    while not rospy.is_shutdown():
        move_corner(LENGTH*4)
        move_corner(LENGTH*2)


def receive_position(current: Pose):
    arrived = closed(current, START[0], START[1])

    if arrived:
        open()

rospy.Subscriber('/turtle1/pose', Pose, receive_position)
rospy.spin()
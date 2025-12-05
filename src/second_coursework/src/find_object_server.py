#!/usr/bin/env python3

import rospy
from second_coursework.srv import FindObject, FindObjectResponse, FindObjectRequest
from std_msgs.msg import Bool

location_map = { "kitchen": [10, 8.0, 0.0], "living_room": [2.0, 3.0, 0] }

def find_object(req: FindObjectRequest):
    response = FindObjectResponse()
    response.request_accepted = False

    try:
        msg = rospy.wait_for_message('/searching', Bool, timeout=5.0)
        response.request_accepted = msg.data

    except rospy.ROSException:
        rospy.logwarn("Timeout: No message received on /searching")

    return response

def find_object_server():
    rospy.init_node('find_object_server')
    s = rospy.Service('find_object', FindObject, find_object)
    rospy.spin()

if __name__ == "__main__":
    find_object_server()



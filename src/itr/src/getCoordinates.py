#!/usr/bin/env python3

import rospy
from itr.srv import GetCoordinates, GetCoordinatesResponse, GetCoordinatesRequest
from geometry_msgs.msg import Point

location_map = { "kitchen": [10, 8.0, 0.0], "living_room": [2.0, 3.0, 0] }

def get_coordinates(req: GetCoordinatesRequest):
    if req.name in location_map:
        room = location_map[req.name]
        p = Point(x=room[0], y=room[1], z=room[2])
        return GetCoordinatesResponse(p)
    
    return GetCoordinatesResponse(Point(x=0, y=0, z=0))

def get_coordinates_server():
    rospy.init_node('get_coordinates_server')
    s = rospy.Service('get_coordinates', GetCoordinates, get_coordinates)
    rospy.spin()

if __name__ == "__main__":
    get_coordinates_server()

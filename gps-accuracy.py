import argparse
import gpxpy
import gpxpy.gpx
from pyproj import Proj
import numpy as np
from pandas import DataFrame
from scipy import spatial
import itertools
import math

# assume England - change this if you live elsewhere
UTM_ZONE = '30U'
myProj = Proj("+proj=utm +zone="+UTM_ZONE+", +north, +ellps=WGS84 +datum=WGS84 +units=m +no_defs")

def get_args():
    parser = argparse.ArgumentParser(description='Measure GPS accuracy by comparing recorded track points with a planned route.', prog='gps-accuracy')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
    parser.add_argument('route', help='filename of route (GPX track format)')
    parser.add_argument('track', help='filename of track (GPX track format)')
    args = parser.parse_args()
    return args

def gpx_to_utm(filename):   # return arrays, X and Y, which are UTM coordinates of points in the GPX
    # convert points to XY in Universal Transverse Mercator (UTM) - assume England
    coords = []
    prev = 0
    t = gpxpy.parse(open(filename))
    for track in t.tracks:
        for segment in track.segments:
            for point in segment.points:
                if point != prev:  # prevent identical successive coordinates
                    coords.append(myProj(point.longitude, point.latitude))
                prev = point
    return coords

def utm_to_gpx(p):
    lon, lat = myProj(p[0], p[1], inverse=True)
    return lat, lon

def distance(a, b):
    # euclidian distance between two points a and b, which are (x, y) tuples
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

def distance_sqr(a, b):
    # squared euclidian distance between two points a and b, which are (x, y) tuples
    return (a[0]-b[0])**2 + (a[1]-b[1])**2

def calculate_error(asqr, bsqr, csqr):
    if csqr == 0:
        return asqr
    else:
        return math.sqrt(asqr - (((csqr+asqr-bsqr)**2)/(4 * csqr)))

def intersection(t, r1, r2):
    # Calculate the gradient and intercept of the route vector.
    try:     # there's a risk of divide by zero errors
        r_grad = (r1[1] - r2[1]) / (r1[0] - r2[0])
        r_intercept = r1[1] - r_grad * r1[0]
        # gradient of the perpendicular error bar is -1/m
        e_grad = -1.0 / r_grad
        e_intercept = t[1] - e_grad * t[0]
        # solve the two equations of form y = mx + c to find the intersection point
        multiplier = - r_grad / e_grad
        y = (r_intercept + multiplier * e_intercept) / (multiplier + 1)
        x = (y - r_intercept) / r_grad
    except ZeroDivisionError:
        # R1 and R2 must be either due N-S or due E-W
        if r1[0] == r2[0]:
            # due N-S. Intersection point is X from R1 & R2, Y from T
            x = r1[0]
            y = t[1]
        elif r1[1] == r2[1]:
            # due E-W. Intersection is X from T and Y from R1 & R2
            x = t[0]
            y = r1[1]

    return is_on_line((x, y), r1, r2), x, y, distance((x, y), t)

def is_on_line(crosspt, r1, r2):
    # In fact it only checks if crosspt is in the bounding box defined by R1 and R2
    # but since we know this is a solution of the two linear equations, if it's in
    # the box, it's also on the line.
    flag = False
    if crosspt[0] > min(r1[0], r2[0]) and crosspt[0] < max(r1[0], r2[0]):
        if crosspt[1] > min(r1[1], r2[1]) and crosspt[1] < max(r1[1], r2[1]):
            flag = True
    return flag

# For debug / test purposes, create a GPX file that visualises the track and errors
class VisGpx:

    def __init__(self):
        self.gpx = gpxpy.gpx.GPX()
        self.gpx_track = gpxpy.gpx.GPXTrack()
        self.gpx.tracks.append(self.gpx_track)
        self.gpx_segment = gpxpy.gpx.GPXTrackSegment()
        self.gpx_track.segments.append(self.gpx_segment)
        

    def append(self, t, e_point):
        # Add three points to the track: T, the calculated error, and T again.
        e_point_lat, e_point_lon = utm_to_gpx(e_point)
        t_lat, t_lon = utm_to_gpx(t)
        self.gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(t_lat, t_lon))
        self.gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(e_point_lat, e_point_lon))
        self.gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(t_lat, t_lon))

     
    def finish(self):
        open("__VisGPX.gpx", "w+").write(self.gpx.to_xml())


## MAIN ##
vis = VisGpx()
#args = get_args()
#print(args)
#print(args.verbose)
#print(args.route)
#print(args.track)

# load each GPX file as a series of track points with location as lat, lon
# track = gpx_to_utm(args.track)
# route = gpx_to_utm(args.route)
track = gpx_to_utm("track.gpx")
route = gpx_to_utm("route.gpx")

print("track:", len(track), "x", len(track[0]), "track[0]:", track[0])
print("route:", len(route), "x", len(route[0]), "route[0]:", route[0])

# Our task is to find the nearest adjacent pair of points in the route for each point in the track
# so set up a KD tree of route points
tree = spatial.cKDTree(route)
distances, indexes = tree.query(track)

# For each track point, we now know the index of the nearest route point, and its distance.
# As described in the README file, we'll call this distance 'a'
for (t, a, i) in zip(track, distances, indexes):
    nearest = route[i]

    # Three cases:
    # 1. Closest distance from track point T to route is directly to point 'nearest'
    # 2. Closest distance from track point T to route is on the line joining 'nearest' with its predecessor.
    # 3. Closest distance from track point T to route is on the line joining 'nearest, with its succcessor.

    # We can distinguish by expressing each line R1-R2 as an equation in the form 
    # y = mx + c, then another line through T, perpendicular to R1-R2, and solving
    # to find the point of intersection.

    # Set up for case 1.
    shortest_d = distance(t, nearest)
    closest_x = nearest[0]
    closest_y = nearest[1]

    # Check for case 2.
    if i > 0:
        valid, x, y, d = intersection(t, nearest, route[i-1])
        if valid and d < shortest_d:
            closest_x = x
            closest_y = y

    # Check for case 3.
    if i < len(route)-1:
        valid, x, y, d = intersection(t, nearest, route[i+1])
        if valid and d < shortest_d:
            closest_x = x
            closest_y = y

    e = shortest_d
    vis.append(t, (closest_x, closest_y))
    
vis.finish()


#    d_predecessor = 
#    print("track point:", p)
#    print("index:", i)
#    print("distance:", d)
#    print("route:", route[i])
    
# GPXPY = gpxpy.parse(open(INFILE))


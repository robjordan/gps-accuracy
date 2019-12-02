import argparse
import gpxpy
from pyproj import Proj
import numpy as np
from pandas import DataFrame
from scipy import spatial
import itertools
import math

# assume England - change this if you live elsewhere
UTM_ZONE = '30U'

def get_args():
    parser = argparse.ArgumentParser(description='Measure GPS accuracy by comparing recorded track points with a planned route.', prog='gps-accuracy')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
    parser.add_argument('route', help='filename of route (GPX track format)')
    parser.add_argument('track', help='filename of track (GPX track format)')
    args = parser.parse_args()
    return args

def gpx_to_utm(filename):   # return arrays, X and Y, which are UTM coordinates of points in the GPX
    # convert points to XY in Universal Transverse Mercator (UTM) - assume England
    myProj = Proj("+proj=utm +zone="+UTM_ZONE+", +north, +ellps=WGS84 +datum=WGS84 +units=m +no_defs")
    coords = []
    t = gpxpy.parse(open(filename))
    for track in t.tracks:
        for segment in track.segments:
            for point in segment.points:
                coords.append(myProj(point.longitude, point.latitude))
    return coords

def distance(a, b):
    # euclidian distance between two points a and b, which are (x, y) tuples
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

def distance_sqr(a, b):
    # squared euclidian distance between two points a and b, which are (x, y) tuples
    return (a[0]-b[0])**2 + (a[1]-b[1])**2

def calculate_error(asqr, bsqr, csqr):
    return math.sqrt(asqr - (((csqr+asqr-bsqr)**2)/(4 * csqr)))

## MAIN ##
args = get_args()
print(args)
print(args.verbose)
print(args.route)
print(args.track)

# load each GPX file as a series of track points with location as lat, lon
track = gpx_to_utm(args.track)
route = gpx_to_utm(args.route)

print("track:", len(track), "x", len(track[0]), "track[0]:", track[0])
print("route:", len(route), "x", len(route[0]), "route[0]:", route[0])

# Our task is to find the nearest adjacent pair of points in the route for each point in the track
# so set up a KD tree of route points
tree = spatial.cKDTree(route)
distances, indexes = tree.query(track)

# For each track point, we now know the index of the nearest route point, and its distance.
# As described in the README file, we'll call this distance 'a'
for (p, a, i) in zip(track, distances, indexes):
    nearest = route[i]
    # We'll need the squared distance for our error calculation
    a_squared = a**2

    # Which route point is closer to p (the track point), the predecessor or the successor?
    # As described in the README, we'll call this distance 'b' and calculate b**2
    if i == 0:                      # first route point
        second_nearest = route[i+1]
        b_squared = distance_sqr(p, route[i+1])
    elif i == len(route):           # last route point
        second_nearest = route[i-1]
        b_squared = distance_sqr(p, route[i-1])
    else:                           # the general case: mid route point
        dsqr_prev = distance_sqr(p, route[i-1])
        dsqr_next = distance_sqr(p, route[i+1])
        if dsqr_prev < dsqr_next:
            second_nearest = route[i-1]
            b_squared = dsqr_prev
        else:
            second_nearest = route[i+1]
            b_squared = dsqr_next

    
    # to solve the triangles we also need to know the squared distance between the adjacent route points, i.e. 'c'
    c_squared = distance_sqr(nearest, second_nearest)

    # Now we have all the terms needed to calculate the error 'e', using a**2, b**2 and c**2
    e = calculate_error(a_squared, b_squared, c_squared)

    print("a: {}, b: {}, c: {}, e: {}".format(math.sqrt(a_squared), math.sqrt(b_squared), math.sqrt(c_squared), e))

        


#    d_predecessor = 
#    print("track point:", p)
#    print("index:", i)
#    print("distance:", d)
#    print("route:", route[i])
    
# GPXPY = gpxpy.parse(open(INFILE))


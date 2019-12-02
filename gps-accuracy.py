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
    t = gpxpy.parse(open(filename))
    for track in t.tracks:
        for segment in track.segments:
            for point in segment.points:
                coords.append(myProj(point.longitude, point.latitude))
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

# For debug / test purposes, create a GPX file that visualises the track and errors
class VisGpx:

    def __init__(self):
        self.gpx = gpxpy.gpx.GPX()
        self.gpx_track = gpxpy.gpx.GPXTrack()
        self.gpx.tracks.append(self.gpx_track)
        self.gpx_segment = gpxpy.gpx.GPXTrackSegment()
        self.gpx_track.segments.append(self.gpx_segment)
        

    def append(self, t, nearest, second_nearest, a_squared, b_squared, c_squared, e):
        # Add three points to the track: T, the calculated error, and T again.
        # Calculate the gradient and intercept of the route vector.
        try:     # there's a risk of divide by zero errors - just pass if they occur
            r_grad = (nearest[1] - second_nearest[1]) / (nearest[0] - second_nearest[0])
            r_intercept = nearest[1] - r_grad * nearest[0]
            # gradient of the error bar is -1/m
            e_grad = -1.0 / r_grad
            e_intercept = t[1] - e_grad * t[0]
            # solve the two equations of form y = mx + c to find the intersection point
            multiplier = - r_grad / e_grad
            y_solution = (r_intercept + multiplier * e_intercept) / (multiplier + 1)
            x_solution = (y_solution - r_intercept) / r_grad
            e_endpoint = (x_solution, y_solution)
            e_endpoint_lat, e_endpoint_lon = utm_to_gpx(e_endpoint)
            t_lat, t_lon = utm_to_gpx(t)
            self.gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(t_lat, t_lon))
            self.gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(e_endpoint_lat, e_endpoint_lon))
            self.gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(t_lat, t_lon))
            try:
                assert e == distance(t, e), "Distance mismatch"
            except:
                print("t: {}, nearest: {}, 2nd: {}, e_endpoint: {}, e: {}, distance: {}".format(t, nearest, second_nearest, e_endpoint, e, distance(t, e_endpoint)))
        except:
            print ("divide by zero")
     
    def finish(self):
        open("__VisGPX.gpx", "w+").write(self.gpx.to_xml())


## MAIN ##
vis = VisGpx()
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
    elif i == len(route)-1:           # last route point
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

    # DEBUG Make a GPX file to visualise the error
    vis.append(p, nearest, second_nearest, a_squared, b_squared, c_squared, e)
        
vis.finish()


#    d_predecessor = 
#    print("track point:", p)
#    print("index:", i)
#    print("distance:", d)
#    print("route:", route[i])
    
# GPXPY = gpxpy.parse(open(INFILE))


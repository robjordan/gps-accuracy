import argparse
import gpxpy
import gpxpy.gpx
from pyproj import Proj
import numpy as np
from scipy.spatial import cKDTree
import itertools
import math
import statistics as st
from datetime import datetime, timezone, MINYEAR

# assume England - change this if you live elsewhere
UTMZ = '30U'
myProj = Proj("+proj=utm +zone="+UTMZ+", +north, +ellps=WGS84 +datum=WGS84 +units=m +no_defs")


def get_args():
    parser = argparse.ArgumentParser(
        description='Measure GPS accuracy by comparing recorded track points with a planned route.',
        prog='gps-accuracy')
    parser.add_argument(
        '-d', 
        '--debug', 
        action='store_true', 
        help='generate debug output, including a GPX file visualising tracking errors')
    parser.add_argument('route', help='filename of route (GPX track format)')
    parser.add_argument('track', help='filename of track (GPX track format)')
    args = parser.parse_args()
    return args


def gpx_to_utm(filename, prefix=None):
    """Return arrays X and Y, which are UTM coordinates of points in the GPX"""
    # convert points to XY in Universal Transverse Mercator - assume England
    coords = []
    prev = None
    distance = 0
    end_time = None
    start_time = None
    intervals = []

    if prefix is not None:
        print("{}.filename\t{}".format(prefix, filename))
    t = gpxpy.parse(open(filename))

    for track in t.tracks:
        for segment in track.segments:
            for point in segment.points:
                if point != prev:  # prevent identical successive coordinates
                    coords.append(myProj(point.longitude, point.latitude))
                    if prev is not None and prefix is not None:
                        intervals.append(point.time - prev.time)
                prev = point

        distance = distance + track.length_2d()
        track_start, end_time = track.get_time_bounds()
        if not start_time:
            start_time = track_start

    if prefix is not None:
        print("{}.num_points\t{}".format(prefix, len(coords)))
        print("{0}.distance\t{1: .0f}".format(prefix, distance))
        print("{}.start\t{}".format(prefix, start_time))
        print("{}.end\t{}".format(prefix, end_time))
        print("{}.intervals.mean\t{}".format(
            prefix,
            np.mean(intervals)))
        print("{}.intervals.max\t{}".format(
            prefix, np.max(intervals)))
    return coords


def print_error_stats(errors):
    """Print a variety of stats characterising the track errors."""
    print("errors.mean\t{0: .2f}".format(np.mean(errors)))
    print("errors.median\t{0: .2f}".format(np.median(errors)))
    print("errors.95th_percentile\t{0: .2f}".format(
        np.percentile(errors, 95)))


def utm_to_gpx(p):
    """Convert a single UTM cooordinate, passed as tuple, to lat, lon"""
    lon, lat = myProj(p[0], p[1], inverse=True)
    return lat, lon


def distance(a, b):
    """Calculate euclidian distance between 2 points which are (x, y) tuples"""
    return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)


def intersection(t, r1, r2):
    """Given two route points, r1, r2, find the perpendicular intersection from track point t"""
    # Calculate the gradient and intercept of the route vector.
    try:     # there's a risk of divide by zero errors
        r_grad = (r1[1] - r2[1]) / (r1[0] - r2[0])
        r_intercept = r1[1] - r_grad * r1[0]
        # gradient of the perpendicular error bar is -1/m
        e_grad = -1.0 / r_grad
        e_intercept = t[1] - e_grad * t[0]
        # solve the two equations of form y = mx + c to find the
        # intersection
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
    # In fact it only checks if crosspt is in the bounding box defined
    # by R1 and R2 but since we know this is a solution of the two
    # linear equations, if it's in the box, it's also on the line.
    flag = False
    if crosspt[0] > min(r1[0], r2[0]) and crosspt[0] < max(r1[0], r2[0]):
        if crosspt[1] > min(r1[1], r2[1]) and crosspt[1] < max(r1[1], r2[1]):
            flag = True
    dbg_print("cross: {}, r1: {}, r2: {}, valid: {}".format(crosspt, r1, r2, flag))
    return flag


def dbg_print(*prargs):
    if args.debug:
        print(prargs)


# For debug / test purposes, create a GPX file that visualises the
# track and the error bar for each track point
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
        self.gpx_segment.points.append(
            gpxpy.gpx.GPXTrackPoint(t_lat, t_lon))
        self.gpx_segment.points.append(
            gpxpy.gpx.GPXTrackPoint(e_point_lat, e_point_lon))
        self.gpx_segment.points.append(
            gpxpy.gpx.GPXTrackPoint(t_lat, t_lon))

    def finish(self):
        open("__VisGPX.gpx", "w+").write(self.gpx.to_xml())


# MAIN #
vis = VisGpx()
args = get_args()
dbg_print(args)
dbg_print(args.debug)
dbg_print(args.route)
dbg_print(args.track)

# load each GPX file as a series of track points with location as lat, lon
track = gpx_to_utm(args.track, "track")
route = gpx_to_utm(args.route)
errors = []

dbg_print("track:", len(track), "x", len(track[0]), "track[0]:", track[0])
dbg_print("route:", len(route), "x", len(route[0]), "route[0]:", route[0])

# Our task is to find the nearest adjacent pair of points in the route
# for each point in the track, so set up a KD tree of route points and
# query the nearest neighbour or each point in the current track
distances, indexes = cKDTree(route).query(track)

# For each track point, we now know the index of the nearest route
# point, and its distance, d.
for (t, d, i) in zip(track, distances, indexes):
    nearest = route[i]

    # Two cases:
    # 1. Closest distance from track point T to route is directly to
    #    point 'nearest'
    # 2. Closest distance from track point T to route is to a point on a
    #    line between successive nearby route points. It's indeterminate
    #    now many route points to check, but in practice we seem to
    #    correctly find the shortest distance by considering (i-2, i-1),
    #    (i-1, i), (i, i+1), (i+1, i+2)

    # Set up for case 1.
    dbg_print("Considering t={}, {}".format(t, utm_to_gpx(t)))
    dbg_print(
        "Nearest point i={}, {}, {}".format(i, route[i], utm_to_gpx(route[i])))
    shortest_d = d
    closest_x = nearest[0]
    closest_y = nearest[1]
    dbg_print(
        "Route point i={}, location={}, d={}".format(i, nearest, shortest_d))

    # Check for case 2. We can find the potential closest point by
    # expressing each line R1-R2 as an equation in the form y = mx + c,
    # then describing another line through T, perpendicular to R1-R2
    # (which will have gradient -1/m), and solving the two equations to
    # find the point of intersection.
    for r1 in range(max(0, i-2), min(i+2, len(route)-1)):
        valid, x, y, d = intersection(t, route[r1], route[r1+1])
        dbg_print(
            "Route segment r1={}, r2={},  intersect={}, d={}, valid={}".format(
                r1, r1+1, (x, y), d, valid))
        if valid and d < shortest_d:
            dbg_print("new closest")
            closest_x = x
            closest_y = y
            shortest_d = d

    errors.append(shortest_d)
    if args.debug:
        vis.append(t, (closest_x, closest_y))

if args.debug:
    vis.finish()

# Print a summary of the results of our analysis
print_error_stats(errors)

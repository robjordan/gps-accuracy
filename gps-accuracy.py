import argparse
import gpxpy
from pyproj import Proj
import numpy as np
from pandas import DataFrame
from scipy import spatial
import itertools

def get_args():
    parser = argparse.ArgumentParser(description='Measure GPS accuracy by comparing recorded track points with a planned route.', prog='gps-accuracy')
    parser.add_argument('-v', '--verbose', action='store_true', help='verbose output')
    parser.add_argument('route', help='filename of route (GPX track format)')
    parser.add_argument('track', help='filename of track (GPX track format)')
    args = parser.parse_args()
    return args

def gpx_to_utm(filename):   # return arrays, X and Y, which are UTM coordinates of points in the GPX
    # convert points to XY in Universal Transverse Mercator (UTM) - assume England
    myProj = Proj("+proj=utm +zone=30U, +north, +ellps=WGS84 +datum=WGS84 +units=m +no_defs")
    coords = []
    t = gpxpy.parse(open(filename))
    for track in t.tracks:
        for segment in track.segments:
            for point in segment.points:
                coords.append(myProj(point.longitude, point.latitude))
    return coords



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

# our task is to find the nearest adjacent pair of points in the route for each point in the track
# so set up a KD tree of route points
tree = spatial.cKDTree(route)
distances, indexes = tree.query(track)
for (p, d, i) in zip(track, distances, indexes):
    print("track point:", p)
    print("index:", i)
    print("distance:", d)
    print("route:", route[i])
    
# GPXPY = gpxpy.parse(open(INFILE))


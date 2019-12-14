# gps-accuracy
The purpose of this script is to quantify the accuracy of a GPS device by
comparing the location of track points against points in the planned route.

Usage:
```
gps-accuracy [-h] [-d] route track

positional arguments:
  route        filename of route (GPX track format)
  track        filename of track (GPX track format)

optional arguments:
  -h, --help   show this help message and exit
  -d, --debug  generate debug output, including a GPX file visualising
               tracking errors
```
The output reports on the mean, median and 95% percentile distance from each GPX
track point to the nearest point along the planned route. It also reports on the
start and finish time of the track, the number of trackpoints and the mean/max
interval between successive track points. 

It is assumed that the trackpoints in the `route` file are closely-spaced, such
that the intended route can be considered to follow a straight line between
successive route points. We also make an assumption that - since the distances
between points in the route and track are very small - the curvature of the
earth can be ignored. The first step is therefore to convert the lat/long
coordinates the route and track to XY coordinates (units are metres).

The core of the algorithm is to find the nearest point on the planned route to each track point. There are two main scenarios:


The GPS error for each point is calculated as follows.

![Error calculation](https://github.com/robjordan/gps-accuracy/raw/master/error-case-1.svg)

The intended route is represented as a straight line between successive route
points *R1* and *R2*. The GPS records a track point *T*. The error that we want
to calculate is *e*, the perpendicular distance from *T* to the straight line
joining *R1* and *R2*. To find *e*, we need to solve, by Pythagoras, the two
right-angle triangles, one formed by *R1*, *T* and *e*, and the the other formed
by *R2*, *T* and *e*. Because the coordinates of points *R1*, *R2* and *T* are
known, we can also calculate the distances between the points: *a*, *b* and *c*.
The unknowns are *e*, and *m*, which is the distance from *R1* to the point
where line *e* intersects *R1*-*R2*.

By Pythagoras, the equations of the two triangles are:

![Triangle one](https://github.com/robjordan/gps-accuracy/raw/master/CodeCogsEqn(1).gif)

![Triangle two](https://github.com/robjordan/gps-accuracy/raw/master/CodeCogsEqn(2).gif)

By substituting the value of *e<sup>2</sup2>* from the first equation into the second, we can derive an expression for the first unknown, *m*, and thus also *m<sup>2</sup>*:

![Derivation of m](https://github.com/robjordan/gps-accuracy/raw/master/CodeCogsEqn(3).gif)

Finally, by substiting *m<sup>2</sup>* back into the first equation, we derive a formula to calculate *e* using only the known lengths, *a*, *b*, and *c*:

![Derivation of e](https://github.com/robjordan/gps-accuracy/raw/master/CodeCogsEqn(4).gif)
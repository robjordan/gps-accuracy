# gps-accuracy
The purpose of this script is to quantify the accuracy of a GPS device by comparing the location of track points against points in the planned route.

Usage:
`gps-accuracy [-h] [-v] route track`

Where `route` and `track` are gpx track files.

It is assumed that the trackpoints in the `route` file are closely-spaced, such that the intended route can be considered to follow a straight line between successive route points. We also make an assumption that - since the distances between points in the route and track are very small - the curvature of the earth can be ignored. The first step is therefore to convert the lat/long coordinates the route and track to XY coordinates (units are metres).

The GPS error for each point is calculated as follows.

![Error calculation](https://github.com/robjordan/gps-accuracy/raw/master/trigonometry.png)

The intended route is represented as a straight line between successive route points *R1* and *R2*. The GPS records a track point *T*. The error that we want to calculate is *e*, the perpendicular distance from *T* to the straight line joining *R1* and *R2*. To find *e*, we need to solve, by Pythagoras, the two right-angle triangles, one formed by *R1*, *T* and *e*, and the the other formed by *R2*, *T* and *e*. Because the coordinates of points *R1*, *R2* and *T* are known, we can also calculate the distances between the points: *a*, *b* and *c*. The unknowns are *e*, and *m*, which is the distance from *R1* to the point where line *e* intersects *R1*-*R2*.

By Pythagoras, the equations of the two triangles are:

![Triangle one](https://github.com/robjordan/gps-accuracy/raw/master/CodeCogsEqn(1).gif)

![Triangle two](https://github.com/robjordan/gps-accuracy/raw/master/CodeCogsEqn(2).gif)

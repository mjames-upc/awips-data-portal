import sys, cStringIO, os, os.path, datetime
import random
import string
import cherrypy
from ufpy.dataaccess import DataAccessLayer
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy
#import cartopy.crs as ccrs
#import cartopy.io.img_tiles as cimgt
from mpl_toolkits.basemap import Basemap, cm
# requires netcdf4-python (netcdf4-python.googlecode.com)
#from netCDF4 import Dataset as NetCDFFile
import numpy as np
from numpy import linspace
from numpy import meshgrid
import matplotlib.pyplot as plt

DataAccessLayer.changeEDEXHost("edex.unidata.ucar.edu")
gridTimeIndex = -1

# EDEX Data Access Framework
request = DataAccessLayer.newDataRequest()
request.setDatatype("maps")
request.setParameters("cwa","wfo")
request.addIdentifier("locationField","wfo")
request.addIdentifier("geomField","the_geom")
request.addIdentifier("table","mapdata.cwa")
request.setLocationNames("BOU")
response = DataAccessLayer.getGeometryData(request, None)

# Now set area
request = DataAccessLayer.newDataRequest()
request.setEnvelope(response[0].getGeometry())

# Now query grid
request.setDatatype("grid")
request.setLocationNames("HRRR")
request.setParameters("T")
request.setLevels("500MB")
t = DataAccessLayer.getAvailableTimes(request)
print t
exit()
response = DataAccessLayer.getGridData(request, [t[gridTimeIndex]])
data = response[0]

fig = plt.figure(figsize=(8,8))
ax = fig.add_axes([0.1,0.1,0.8,0.8])

lons,lats = data.getLatLonCoords()


lat_min = min(lats[-1])
lat_max = max(lats[0])
lon_min = min(lons[0])
lon_max = max(lons[-1])
# map = Basemap(projection='tmerc',
#               lat_0=0, lon_0=3,
#               llcrnrlat=lat_min,
#               urcrnrlat=lat_max,
#               llcrnrlon=lon_min,
#               urcrnrlon=lon_max)
map = Basemap(
    projection = 'merc',
    llcrnrlat=lat_min, urcrnrlat=lat_max,
    llcrnrlon=lon_min, urcrnrlon=lon_max,
    rsphere=6371200., resolution='l', area_thresh=10000
)
map.drawcoastlines()
map.drawstates()
map.drawcountries()
x = linspace(0, map.urcrnrx, data.getRawData().shape[0])
y = linspace(0, map.urcrnry, data.getRawData().shape[1])

xx, yy = meshgrid(y,x)

#lons2, lats2 = meshgrid(lons, lats)

# compute native map projection coordinates of lat/lon grid.
#lons2, lats2 = map(lons2*180./np.pi, lats2*180./np.pi)

#clevs = [-12,-11,-10,-9,-8,-7,-6,-5,-4,-3,-2,-1,0]
#cs = map.contourf(xx, yy, data.getRawData())

#cs = map.pcolormesh(lons, lats, data.getRawData(), shading='flat', latlon=True)

lat_min = lats.min()
lat_max = lats.max()
lon_min = lons.min()
lon_max = lons.max()

width = lats.shape[1]
height = lats.shape[0]
lllon, lllat, urlon, urlat = -144.99499512, -59.95500183, -65.03500366, 60.00500107
lllon, lllat, urlon, urlat = lon_min, lat_min, lon_max, lat_max
dlon = (urlon-lllon) / width
dLat = (urlat-lllat) / height
baseArray = np.fromfunction(lambda y,x: (1000.0 / (width + height)) * (y+x), (height, width), dtype = float)
lons2 = np.arange(lllon, urlon, dlon)
lats2 = np.arange(lllat, urlat, dLat)
lons2, lats2 = np.meshgrid(lons2, lats2)

fig = plt.figure()
plt.title("The Plot")
m = Basemap(projection='cyl',
          resolution = 'c',
          llcrnrlon = lllon, llcrnrlat = lllat,
          urcrnrlon =urlon, urcrnrlat = urlat
)
m.drawcoastlines()
m.drawstates()
m.drawcountries()
m.pcolormesh(lons2, lats2, baseArray, shading='flat', latlon=True)


varString =  "len(response) = %s<br>" % ( len(response) )
varString +=  "x.shape (" + ','.join([str(x) for x in x.shape]) + ")<br>"
varString +=  "y.shape (" + ','.join([str(x) for x in y.shape]) + ")<br>"
varString +=  "xx.shape (" + ','.join([str(x) for x in xx.shape]) + ")<br>"
varString +=  "yy.shape (" + ','.join([str(x) for x in yy.shape]) + ")<br>"
varString +=  "lats.shape (" + ','.join([str(x) for x in lats.shape]) + ")<br>"
varString +=  "lons.shape (" + ','.join([str(x) for x in lons.shape]) + ")<br>"
varString +=  "data.getRawData().shape (" + ','.join([str(x) for x in data.getRawData().shape]) + ")<br>"
varString +=  "baseArray.shape (" + ','.join([str(x) for x in baseArray.shape]) + ")<br>"


print "x"
print x
print "y"
print y.shape
print y
print "xx"
print xx.shape
print xx
print "yy"
print yy.shape
print yy
print "lats2"
print lats2.shape
print lats2
print "lons2"
print lons2.shape
print lons2
print "baseArray"
print baseArray.shape
print baseArray
print "lats"
print lats.shape
print lats
print "lons"
print lons.shape
print lons
print "data.getRawData().shape"
print data.getRawData().shape
print data.getRawData()
#
#
# # add colorbar.
# cbar = map.colorbar(cs,location='bottom',pad="5%")
# cbar.set_label(data.getUnit())
# plt.title(data.getParameter())
# plt.show()


# lons2 = [-97.9547, -97.9747, -97.4256]
# lats2 = [35.5322, 35.864, 35.4111]
# data2 = [2,2,2]
#
# xs, ys = np.meshgrid(lons, lats)
# #dataMesh = np.empty_like(xs)
#
#
# #print dataMesh
# print "xs.shape"
# print xs.shape
# print xs
# print "ys.shape"
# print ys.shape
# print ys
# #print "dataMesh.shape"
# #print dataMesh.shape
#
# print "lats.shape"
# print lats.shape
# print lats
# print "lons.shape"
# print lons.shape
# print lons
# print "data.getRawData().shape"
# print data.getRawData().shape
# print data.getRawData()

##
## If we want to show all cycles/fcst hours
##

# gridTableString=''
# for eachI in t:
#     forecastTimes = DataAccessLayer.getAvailableTimes(request,False)
#
#     cycleTime = eachI.getRefTime().getTime()/1000.0
#     showString = str(datetime.datetime.fromtimestamp(cycleTime).strftime('%Y-%m-%d %H%M')+" UTC")
#     linkString = str(datetime.datetime.fromtimestamp(cycleTime).strftime('%Y%m%d%H%M'))
#
#     gridTableString += "<tr><td><a href='grid?name="+ name +"'>" + showString + "</a>"
#     for eachJ in forecastTimes:
#         if str(eachI.getRefTime()) == str(eachJ.getRefTime()):
#             gridTableString += "<br>" + str(eachJ.getValidPeriod()) + ", "
# gridTableString += "</td></tr>"




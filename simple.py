##
## Flask hello world
##

#from flask import Flask
#app = Flask(__name__)
#@app.route("/")
#def hello():
#    return "Hello World!"
#
#if __name__ == "__main__":
#    app.run(debug=True)

##
## cherrypy
##
import os, os.path, datetime
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
import numpy as np
import matplotlib.pyplot as plt


DataAccessLayer.changeEDEXHost("edex.unidata.ucar.edu")


# First we will request the BOU CWA from the maps database.
# We will use this to create the envelope for our grid request.
# this is to reduce bandwidth while testing
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
request.setEnvelope(response[0].getGeometry().buffer(2))

# Now query grid
request.setDatatype("grid")
request.setLocationNames("NAM-12km")
request.setParameters("T")
request.setLevels("850MB")
t = DataAccessLayer.getAvailableTimes(request)
response = DataAccessLayer.getGridData(request, [t[-1]])
data = response[0]
print data
# create figure and axes instances
fig = plt.figure(figsize=(8,8))
ax = fig.add_axes([0.1,0.1,0.8,0.8])

lons,lats = data.getLatLonCoords()

lat_min = min(lats[-1])
lat_max = max(lats[0])
lon_min = min(lons[0])
lon_max = max(lons[-1])

wave = 0.75*(np.sin(2.*lats)**8*np.cos(4.*lons))
mean = 0.5*np.cos(2.*lats)*((np.sin(2.*lats))**2 + 2.)

lat_min = min(lats[-1])
print lat_min
lat_max = max(lats[0])
print lat_max
lon_min = min(lons[0])
print lon_min
lon_max = max(lons[-1])
print lon_max

print lons
print lats
print data.getRawData()

# lons2 = [-97.9547, -97.9747, -97.4256]
# lats2 = [35.5322, 35.864, 35.4111]
# data2 = [2,2,2]

xs, ys = np.meshgrid(lons, lats)
dataMesh = np.empty_like(xs)

print xs
print ys
print dataMesh


print "wave.shape"
print wave.shape
print "mean.shape"
print mean.shape

print "xs.shape"
print xs.shape
print "ys.shape"
print ys.shape
print "dataMesh.shape"
print dataMesh.shape

print "lats.shape"
print lats.shape
print "lons.shape"
print lons.shape
print "data.getRawData().shape"
print data.getRawData().shape

print "data.getRawData().shape[0]"
print data.getRawData().shape[0]
print "data.getRawData().shape[1]"
print data.getRawData().shape[1]
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




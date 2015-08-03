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




class EdexInventory(object):


    @cherrypy.expose
    def index(self):
        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")
        available_grids = DataAccessLayer.getAvailableLocationNames(request)
        gridTableString=''
        for grid in available_grids:
            gridTableString += "<tr><td><a href='grid?name="+ grid +"'>" + grid + "</a></td></tr>"

        return """<html><head><link href="/static/css/style.css" rel="stylesheet"></head>
    <body>
    <table width="" border="1">
    """ + gridTableString + """
    </table>
    </body>
    </html>"""

    @cherrypy.expose
    def grid(self, name=""):
        # First we will request the BOU CWA from the maps database.
        # We will use this to create the envelope for our grid request.
        # this is to reduce bandwidth while testing




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
        request.setEnvelope(response[0].getGeometry().buffer(3))

        # Now query grid
        request.setDatatype("grid")
        request.setLocationNames(name)
        request.setParameters("RH")
        request.setLevels("850MB")
        t = DataAccessLayer.getAvailableTimes(request)

        response = DataAccessLayer.getGridData(request, [t[-1]])
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
        x = linspace(0, map.urcrnrx, data.getRawData().shape[1])
        y = linspace(0, map.urcrnry, data.getRawData().shape[0])

        yy, xx = meshgrid(x, y)


        wave = 0.75*(np.sin(2.*lats)**8*np.cos(4.*lons))
        mean = 0.5*np.cos(2.*lats)*((np.sin(2.*lats))**2 + 2.)
        #varString = "wave.shape: "  + str(wave.shape)

        # compute native map projection coordinates of lat/lon grid.
        #lons2, lats2 = map(lons2*180./np.pi, lats2*180./np.pi)

        #clevs = [260,270,280,290,300,310,320,330]
        cs = map.contourf(xx, yy, data.getRawData())


        varString =  "wave.shape (" + ','.join([str(x) for x in wave.shape]) + ")<br>"
        varString +=  "mean.shape (" + ','.join([str(x) for x in mean.shape]) + ")<br>"
        varString +=  "lats.shape (" + ','.join([str(x) for x in lats.shape]) + ")<br>"
        varString +=  "lons.shape (" + ','.join([str(x) for x in lons.shape]) + ")<br>"
        varString +=  "data.getRawData().shape (" + ','.join([str(x) for x in data.getRawData().shape]) + ")<br>"


        #
        #
        # # add colorbar.
        cbar = map.colorbar(cs,location='bottom',pad="5%")
        cbar.set_label(data.getUnit())
        plt.title(data.getParameter())
        #plt.show()
        # save or show
        #plt.show()
        format = "png"
        sio = cStringIO.StringIO()
        plt.savefig(sio, format=format)
        print "Content-Type: image/%s\n" % format
        sys.stdout.write(sio.getvalue())

        ##
        ## If we want to show all cycles/fcst hours
        ##

        gridTableString=''

        cycleTime = t[-1].getRefTime().getTime()/1000.0
        fsctTime = t[-1].getValidPeriod()
        showString = str(datetime.datetime.fromtimestamp(cycleTime).strftime('%Y-%m-%d %H%M')+" UTC")
        linkString = str(datetime.datetime.fromtimestamp(cycleTime).strftime('%Y%m%d%H%M'))

        for each in t:
            #print each.getRefTime(),each.getValidPeriod()

            gridTableString += "<pre>%s</pre>" % (each.getValidPeriod() ,)


        plt.title('contour lines over filled continent background')
        return """<html><head><link href="/static/css/style.css" rel="stylesheet"></head>
    <body>
    <h1>""" + name + """ forecast cycles avialable</h1>
    <table width="" border="1">
    <img src="data:image/png;base64,%s"/><br>
    %s<br>%s<br>
    </table>
    </body>
    </html>""" % (sio.getvalue().encode("base64").strip(), gridTableString, varString)

    @cherrypy.expose
    def image(self, name=""):
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
        request.setEnvelope(response[0].getGeometry().buffer(3))
        # Now query grid
        request.setDatatype("grid")
        request.setLocationNames(name)
        request.setLevels("850MB")
        varString = ''
        request.setParameters("RH")
        t = DataAccessLayer.getAvailableTimes(request)
        response = DataAccessLayer.getGridData(request, [t[0]])
        data = response[0]
        lons,lats = data.getLatLonCoords()

        fig = plt.figure(figsize=(8,8))
        ax = fig.add_axes([0.1,0.1,0.8,0.8])

        # DAF DONE

        # MODIFY PRECIP MAP
        # perspective of satellite looking down at 50N, 100W.
        # use low resolution coastlines.
        #map = Basemap(projection='ortho',lat_0=45,lon_0=-100,resolution='l')

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

        xx, yy = meshgrid(y, x)


        wave = 0.75*(np.sin(2.*lats)**8*np.cos(4.*lons))
        mean = 0.5*np.cos(2.*lats)*((np.sin(2.*lats))**2 + 2.)
        #varString = "wave.shape: "  + str(wave.shape)

        # compute native map projection coordinates of lat/lon grid.
        #lons2, lats2 = map(lons2*180./np.pi, lats2*180./np.pi)

        #clevs = [260,270,280,290,300,310,320,330]
        cs = map.contourf(xx, yy, data.getRawData())


        varString +=  "wave.shape (" + ','.join([str(x) for x in wave.shape]) + ")<br>"
        varString +=  "mean.shape (" + ','.join([str(x) for x in mean.shape]) + ")<br>"
        varString +=  "lats.shape (" + ','.join([str(x) for x in lats.shape]) + ")<br>"
        varString +=  "lons.shape (" + ','.join([str(x) for x in lons.shape]) + ")<br>"
        varString +=  "data.getRawData().shape (" + ','.join([str(x) for x in data.getRawData().shape]) + ")<br>"
        varString +=  "data.getRawData() => " + ','.join(str(item) for innerlist in data.getRawData() for item in innerlist)


        #x, y = m(lons*180./np.pi, lats*180./np.pi)

        #cs = m.contour(lons, lats, wave+mean)
        #cs = m.contour(x,y,wave+mean,15,linewidths=1.5)
        # add colorbar.
        cbar = map.colorbar(cs,location='bottom',pad="5%")
        cbar.set_label(data.getUnit())
        plt.title(data.getParameter())
        #plt.show()
        # save or show
        #plt.show()
        format = "png"
        sio = cStringIO.StringIO()
        plt.savefig(sio, format=format)
        print "Content-Type: image/%s\n" % format
        sys.stdout.write(sio.getvalue())
        plt.title('contour lines over filled continent background')
        return """<html><head><link href="/static/css/style.css" rel="stylesheet"></head>
    <body>
    <h1>""" + name + """ forecast cycles avialable</h1>
    <table width="" border="1">
    <img src="data:image/png;base64,%s"/><br>
    %s<br>
    </table>
    </body>
    </html>""" % (sio.getvalue().encode("base64").strip(), varString)

    @cherrypy.expose
    def display(self):
        return cherrypy.session['mystring']

if __name__ == '__main__':
    conf = {
         '/': {
             'tools.sessions.on': True,
             'tools.staticdir.root': os.path.abspath(os.getcwd())
         },
         '/static': {
             'tools.staticdir.on': True,
             'tools.staticdir.dir': './public'
         }
    }
    DataAccessLayer.changeEDEXHost("edex.unidata.ucar.edu")
    cherrypy.quickstart(EdexInventory(), '/', conf)

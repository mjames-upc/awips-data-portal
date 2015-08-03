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
import numpy as np
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
        request.setLocationNames(name)
        request.setParameters("T")
        request.setLevels("850MB")
        t = DataAccessLayer.getAvailableTimes(request)
        response = DataAccessLayer.getGridData(request, [t[-1]])
        data = response[0]

        # create figure and axes instances
        #fig = plt.figure(figsize=(8,8))
        #ax = fig.add_axes([0.1,0.1,0.8,0.8])
        # create polar stereographic Basemap instance.
        #m = Basemap(projection='merc',llcrnrlat=-80,urcrnrlat=80,\
        #    llcrnrlon=-180,urcrnrlon=180,lat_ts=20,resolution='c')
        # draw coastlines, state and country boundaries, edge of map.
        #m.drawcoastlines()
        #m.drawstates()
        #m.drawcountries()
        # draw parallels.
        #parallels = np.arange(0.,90,10.)
        #m.drawparallels(parallels,labels=[1,0,0,0],fontsize=10)
        # draw meridians
        #meridians = np.arange(180.,360.,10.)
        #m.drawmeridians(meridians,labels=[0,0,0,1],fontsize=10)

        fig = plt.figure(figsize=(8,8))
        ax = fig.add_axes([0.1,0.1,0.8,0.8])

        lons,lats = data.getLatLonCoords()

        lat_min = min(lats[-1])
        lat_max = max(lats[0])
        lon_min = min(lons[0])
        lon_max = max(lons[-1])

        m = Basemap(
            projection = 'merc',
            llcrnrlat=lat_min, urcrnrlat=lat_max,
            llcrnrlon=lon_min, urcrnrlon=lon_max,
            rsphere=6371200., resolution='l', area_thresh=10000
        )

        m.drawcoastlines()
        m.drawstates()
        m.drawcountries()

        clevs = [260,270,280,290,300,310,320,330]
        cs = m.contourf(lons, lats, data.getRawData(),clevs )
        # add colorbar.
        cbar = m.colorbar(cs,location='bottom',pad="5%")
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
        return """<html><head><link href="/static/css/style.css" rel="stylesheet"></head>
    <body>
    <h1>""" + name + """ forecast cycles avialable</h1>
    <table width="" border="1">
    Units are in """ + data.getUnit() + """ for """ + data.getParameter() + """<br>
    Data array is """ + str(data.getRawData().shape) +"""<br>
    <img src="data:image/png;base64,%s"/>
    </table>
    </body>
    </html>""" % sio.getvalue().encode("base64").strip()


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

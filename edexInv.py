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
import matplotlib.tri as mtri
import matplotlib.pyplot as plt
from matplotlib.transforms import offset_copy
#import cartopy.crs as ccrs
#import cartopy.io.img_tiles as cimgt
from mpl_toolkits.basemap import Basemap, cm
# requires netcdf4-python (netcdf4-python.googlecode.com)
#from netCDF4 import Dataset as NetCDFFile
import numpy as np
from numpy import linspace, transpose
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


        gridTimeIndex = -1

        # EDEX Data Access Framework
        request = DataAccessLayer.newDataRequest()
        request.setDatatype("maps")
        request.setParameters("state")
        request.addIdentifier("locationField","name")
        request.addIdentifier("geomField","the_geom")
        request.addIdentifier("table","mapdata.states")
        request.setLocationNames("Colorado")
        response = DataAccessLayer.getGeometryData(request, None)
        # Now set area
        request = DataAccessLayer.newDataRequest()
        #request.setEnvelope(response[0].getGeometry().buffer(2))
        # Now query grid
        request.setDatatype("grid")

        # grid select
        available_grids = DataAccessLayer.getAvailableLocationNames(request)
        gridSelect = '<select id="gridSelect" name="gridSelect">'
        for grid in available_grids:
            gridSelect +=  '<option value="%s">%s</option>' % (grid, grid)
        gridSelect += '</select>'

        request.setLocationNames(name)
        request.setParameters("RH")
        request.setLevels("500MB")
        t = DataAccessLayer.getAvailableTimes(request)
        response = DataAccessLayer.getGridData(request, [t[gridTimeIndex]])
        data = response[0]
        lons,lats = data.getLatLonCoords()
        # DAF END

        fig = plt.figure(figsize=(8,8))
        ax = fig.add_axes([0.1,0.1,0.8,0.8])
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

        #map = Basemap(
        #    projection = 'merc',
        #    llcrnrlat=lat_min, urcrnrlat=lat_max,
        #    llcrnrlon=lon_min, urcrnrlon=lon_max,
        #    rsphere=6371200., resolution='l', area_thresh=10000
        #)
	map = Basemap(projection='cyl',
          resolution = 'c',
          llcrnrlon = lons.min(), llcrnrlat = lats.min(),
          urcrnrlon =lons.max(), urcrnrlat = lats.max()
	)
        map.drawcoastlines()
        map.drawstates()
        map.drawcountries()
        x = linspace(0, map.urcrnrx, data.getRawData().shape[1])
        y = linspace(0, map.urcrnry, data.getRawData().shape[0])
        xx, yy = meshgrid(x, y)
        #cs = map.pcolormesh(xx, yy, data.getRawData())

        #map = Basemap(projection='npstere',boundinglat=40,lon_0=-100,resolution='l')

        #cs = map.pcolormesh(lons,lats, data.getRawData(), shading='flat', latlon=True, vmin=0, vmax=100)
       
	ngrid = len(x)
        rlons = np.repeat(np.linspace(np.min(lons), np.max(lons), ngrid),
                  ngrid).reshape(ngrid, ngrid)
        rlats = np.repeat(np.linspace(np.min(lats), np.max(lats), ngrid),
                  ngrid).reshape(ngrid, ngrid).T
        tli = mtri.LinearTriInterpolator(mtri.Triangulation(lons.flatten(), lats.flatten()),
		data.getRawData().flatten())
        rdata = tli(rlons, rlats)
        cs = map.pcolormesh(rlons, rlats, rdata, latlon=True, vmin=0, vmax=100)
        clevs = [0,10,20,30,40,50,60,70,80,90,100]
        #cs = map.contourf(rlons,rlats, rdata,clevs)


        # yy,xx = meshgrid(x,y)
        # #yy2,xx2 = meshgrid(y,x)
        # #xx,yy = map(*np.meshgrid(lons,lats))
        # # compute native map projection coordinates of lat/lon grid.
        # #lons2, lats2 = map(lons2*180./np.pi, lats2*180./np.pi)
        # clevs = [0,10,20,30,40,50,60,70,80,90,100]
        #
        # tmpRaw = transpose(data.getRawData())
        #
        # cs = map.contourf(lons,lats, data.getRawData(),clevs)

        #cs = map.contourf(xx2,yy2, tmpRaw,clevs)


        varString =  "len(response) = %s<br>" % ( len(response) )
        varString +=  "x.shape (" + ','.join([str(x) for x in x.shape]) + ")<br>"
        varString +=  "y.shape (" + ','.join([str(x) for x in y.shape]) + ")<br>"
        varString +=  "xx.shape (" + ','.join([str(x) for x in xx.shape]) + ")<br>"
        varString +=  "yy.shape (" + ','.join([str(x) for x in yy.shape]) + ")<br>"
        #varString +=  "xx2.shape (" + ','.join([str(x) for x in xx2.shape]) + ")<br>"
        #varString +=  "yy2.shape (" + ','.join([str(x) for x in yy2.shape]) + ")<br>"
        varString +=  "lats.shape (" + ','.join([str(x) for x in lats.shape]) + ")<br>"
        varString +=  "lons.shape (" + ','.join([str(x) for x in lons.shape]) + ")<br>"
        varString +=  "data.getRawData().shape (" + ','.join([str(x) for x in data.getRawData().shape]) + ")<br>"
        #varString +=  "tmpRaw.shape (" + ','.join([str(x) for x in tmpRaw.shape]) + ")<br>"

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


        #cycleTime = t[-1].getRefTime().getTime()/1000.0
        #fsctTime = t[-1].getValidPeriod()
        #showString = str(datetime.datetime.fromtimestamp(cycleTime).strftime('%Y-%m-%d %H%M')+" UTC")
        #linkString = str(datetime.datetime.fromtimestamp(cycleTime).strftime('%Y%m%d%H%M'))

        #for each in t:
        #print each.getRefTime(),each.getValidPeriod()
        gridSelect += "<pre>%s,%s</pre>" % (t[gridTimeIndex].getRefTime(),t[gridTimeIndex].getValidPeriod())


        plt.title('contour lines over filled continent background')
        return """<html><head><link href="/static/css/style.css" rel="stylesheet"></head>
    <script type="text/javascript" src="https://code.jquery.com/jquery-1.11.3.min.js"></script>
    <script type="text/javascript">
    $(document).ready(function(){
        $('#gridSelect').val('""" + name + """');
        $("#gridSelect").change(function () {
            console.log("going to /grid?name=" + $(this).val());
           location.href = "/grid?name=" + $(this).val();
        })
    });
    </script>
    <body>
    <h1>""" + name + """ forecast cycles avialable</h1>
    <table width="" border="1">
    %s<br>
    <img style="border: 2px solid black;" src="data:image/png;base64,%s"/><br>
    %s<br>
    </table>
    </body>
    </html>""" % ( gridSelect, sio.getvalue().encode("base64").strip(), varString )

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
    def static(self):
        fig = plt.figure(figsize=(8,8))
        ax = fig.add_axes([0.1,0.1,0.8,0.8])
        lats = np.array([
            [ 41.30340576,  41.33528519,  41.36596298,  41.39544296,  41.42372513,   41.45080566,  41.47668457,  41.50136566,  41.52484131,  41.54711914],
            [ 41.56819153,  41.58806229,  41.60673141,  40.9545784,   40.98640823,   41.01704025,  41.04647827,  41.07471466,  41.10175323,  41.12759399],
            [ 41.15223694,  41.17567825,  41.19792175,  41.21896362,  41.23880768,   41.25744629,  40.60508347,  40.63686371,  40.66744995,  40.69684219],
            [ 40.72503662,  40.75203323,  40.77783585,  40.80244064,  40.82584381,   40.84805298,  40.86906433,  40.88887405,  40.90748978,  40.25493622],
            [ 40.28666687,  40.31720352,  40.34654999,  40.37469864,  40.4016571,   40.42741776,  40.45198059,  40.47535324,  40.49752426,  40.5185051 ],
            [ 40.5382843,   40.55686951,  39.90415192,  39.93583298,  39.96632004,   39.99561691,  40.0237236,   40.05063629,  40.07635498,  40.10087967],
            [ 40.12421417,  40.14635468,  40.16729736,  40.18704605,  40.20560074,   39.552742,  39.58436966,  39.61481094,  39.64405823,  39.67211914],
            [ 39.69898605,  39.72466278,  39.74915314,  39.77244568,  39.79454803,   39.81546021,  39.83517456,  39.85369873,  39.20072556,  39.2322998 ],
            [ 39.26268768,  39.29188919,  39.31990051,  39.34672546,  39.37236023,   39.39680481,  39.42006302,  39.44212723,  39.46300125,  39.4826889 ],
            [ 39.50118256,  38.8481102,   38.87963104,  38.90996933,  38.93911743,   38.96708298,  38.99386215,  39.01945496,  39.04385757,  39.06707382],
            [ 39.0891037,   39.10994339,  39.12959671,  39.14805984,  38.49491501,   38.52638245,  38.55666733,  38.58576584,  38.61368179,  38.64041519],
            [ 38.66596222,  38.69032669,  38.71350098,  38.73549271,  38.75629807,   38.77591324,  38.79434586,  38.14115524,  38.17256546,  38.20279694],
            [ 38.23184586,  38.25971222,  38.28639603,  38.31190109,  38.33621979,   38.35935593,  38.38130951,  38.40207672,  38.42165756,  38.44005585]])
        lons = np.array([
            [-107.59836578, -107.13432312, -106.66999817, -106.20539093, -105.74052429, -105.27540588, -104.81004333, -104.3444519, -103.87863922, -103.41261292],
            [-102.94638824, -102.47998047, -102.01338959, -107.55528259, -107.09280396, -106.63005066, -106.16702271, -105.70373535, -105.24019623, -104.77642059],
            [-104.31240845, -103.84818268, -103.38375092, -102.91912079, -102.45429993, -101.98930359, -107.51248932, -107.05157471, -106.59037781, -106.12892151],
            [-105.66719818, -105.20523071, -104.74302673, -104.28059387, -103.81793976, -103.35508728, -102.89203644, -102.42880249, -101.96539307, -107.46998596],
            [-107.01062012, -106.55097961, -106.09107208, -105.63090515, -105.17050171, -104.70985413, -104.24898529, -103.78790283, -103.32661438, -102.86513519],
            [-102.4034729, -101.94163513, -107.42776489, -106.96994019, -106.51184082, -106.05348206, -105.59486389, -105.13600159, -104.6769104, -104.21759796],
            [-103.75806427, -103.29833984, -102.83841705, -102.37831879, -101.91804504, -107.38583374, -106.92954254, -106.47296906, -106.0161438, -105.55905914],
            [-105.10173798, -104.64418793, -104.18641663, -103.7284317, -103.27025604, -102.81188202, -102.35333252, -101.89461517, -107.34418488, -106.8894043 ],
            [-106.43435669, -105.97905731, -105.52349854, -105.06770325, -104.61168671, -104.15544891, -103.6989975, -103.24235535, -102.78552246, -102.3285141 ],
            [-101.87134552, -107.30281067, -106.84954071, -106.39600372, -105.94221497, -105.48817444, -105.03390503, -104.57939911, -104.12468719, -103.66976166],
            [-103.21464539, -102.75934601, -102.30387115, -101.84822845, -107.26171875, -106.80994415, -106.35791016, -105.90562439, -105.45308685, -105.00032043],
            [-104.54733276, -104.09413147, -103.64072418, -103.18712616, -102.7333374, -102.2793808, -101.82526398, -107.22089386, -106.77061462, -106.32006836],
            [-105.86927032, -105.41823578, -104.96696472, -104.51548004, -104.06378174, -103.61187744, -103.15978241, -102.7075119, -102.25506592, -101.80245209]])
        data = np.array([
            [ 90.,  96.,  96.,  97.,  98.,  82.,  85.,  92.,  88.,  79.],
            [ 73.,  67.,  68.,  91.,  93.,  89.,  90.,  95.,  92.,  76.],
            [ 80.,  80.,  79.,  78.,  70.,  73.,  91.,  96.,  91.,  90.],
            [ 85.,  88.,  69.,  70.,  79.,  88.,  80.,  75.,  65.,  86.],
            [ 94.,  86.,  81.,  75.,  77.,  65.,  72.,  91.,  95.,  83.],
            [ 81.,  90.,  93.,  93.,  83.,  81.,  78.,  72.,  68.,  79.],
            [ 95.,  89.,  89.,  77.,  83.,  95.,  81.,  81.,  79.,  72.],
            [ 70.,  73.,  82.,  86.,  88.,  89.,  75.,  95.,  84.,  85.],
            [ 73.,  71.,  65.,  65.,  68.,  75.,  77.,  86.,  86.,  74.],
            [ 95.,  85.,  79.,  58.,  42.,  40.,  52.,  63.,  63.,  75.],
            [ 88.,  77.,  77.,  81.,  79.,  61.,  28.,  29.,  41.,  54.],
            [ 71.,  79.,  90.,  86.,  74.,  87.,  90.,  65.,  55.,  30.],
            [ 42.,  55.,  72.,  83.,  84.,  80.,  93.,  81.,  86.,  92.]])
        lllon, lllat, urlon, urlat = lons.min(), lats.min(), lons.max(), lats.max()
        fig = plt.figure()
        m = Basemap(projection='cyl',
                  resolution = 'c',
                  llcrnrlon = lllon, llcrnrlat = lllat,
                  urcrnrlon =urlon, urcrnrlat = urlat)
        m.drawcoastlines()
        m.drawstates()
        m.drawcountries()
        #cs = m.pcolormesh( lons, lats, data, shading='flat', latlon=True, vmin=0, vmax=100)
	ngrid = 50
	rlons = np.repeat(np.linspace(np.min(lons), np.max(lons), ngrid),
                  ngrid).reshape(ngrid, ngrid)
	rlats = np.repeat(np.linspace(np.min(lats), np.max(lats), ngrid),
                  ngrid).reshape(ngrid, ngrid).T
	tli = mtri.LinearTriInterpolator(mtri.Triangulation(lons.flatten(), lats.flatten()),
                                 data.flatten())
	rdata = tli(rlons, rlats)
	cs = m.pcolormesh(rlons, rlats, rdata, latlon=True, vmin=0, vmax=100)
        #plt.draw()
        for i in range(len(lats)):
                    for j in range(len(lats[i])):
                        x,y = m(lons[i][j], lats[i][j])
                        m.plot(x, y, 'bo', markersize=3, label=i)
        format = "png"
        sio = cStringIO.StringIO()
        plt.savefig(sio, format=format)
        print "Content-Type: image/%s\n" % format
        sys.stdout.write(sio.getvalue())
        plt.title('contour lines over filled continent background')
        return """<html><head><link href="/static/css/style.css" rel="stylesheet"></head>
    <body>
    <table width="" border="1">
    <img src="data:image/png;base64,%s"/><br>
    </table>
    </body>
    </html>""" % (sio.getvalue().encode("base64").strip())


    @cherrypy.expose
    def nc(self, name=""):
        # examples of filled contour plots on map projections.
        # read in data on lat/lon grid.
        hgt = np.loadtxt('500hgtdata.gz')
        lons = np.loadtxt('500hgtlons.gz')
        lats = np.loadtxt('500hgtlats.gz')
        lons, lats = np.meshgrid(lons, lats)

        # create new figure
        fig = plt.figure()
        ax = fig.add_axes([0.1,0.1,0.8,0.8])
        # setup of orthographic basemap
        #m = Basemap(resolution='c',projection='ortho',\
        #            lat_0=45.,lon_0=-120.)
        m = Basemap(llcrnrlon=-145.5,llcrnrlat=1.,urcrnrlon=-2.566,urcrnrlat=46.352,\
            rsphere=(6378137.00,6356752.3142),\
            resolution='l',area_thresh=1000.,projection='lcc',\
            lat_1=50.,lon_0=-107.,ax=ax)
        # make a filled contour plot.
        x, y = m(lons, lats)
        CS1 = m.contour(x,y,hgt,15,linewidths=0.5,colors='k')
        CS2 = m.contourf(x,y,hgt,CS1.levels,cmap=plt.cm.jet,extend='both')
        m.colorbar(CS2) # draw colorbar
        # draw coastlines and political boundaries.
        m.drawcoastlines()
        m.fillcontinents()
        m.drawmapboundary()
        # draw parallels and meridians.
        parallels = np.arange(-80.,90,20.)
        m.drawparallels(parallels)
        meridians = np.arange(-360.,360.,20.)
        m.drawmeridians(meridians)

        varString = ''
        varString +=  "lats.shape (" + ','.join([str(x) for x in lats.shape]) + ")<br>"
        varString +=  "lons.shape (" + ','.join([str(x) for x in lons.shape]) + ")<br>"
        varString +=  "hgt => " + ','.join(str(item) for innerlist in hgt for item in innerlist) + ")<br>"

        plt.title('Orthographic Filled Contour Demo')
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
    %s</table>
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

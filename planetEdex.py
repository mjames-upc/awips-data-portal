import sys, os, cStringIO
import json
import datetime
import cherrypy
from awips.dataaccess import DataAccessLayer
import matplotlib.tri as mtri
#import matplotlib.pyplot as plt
#import matplotlib
#import cartopy.crs as ccrs
import numpy as np
import re
from parms import parm_dict, level_dict, grid_dictionary, navigation, nws_subcenters, wmo_centers, ncep_subcenters
import binascii, struct
from jinja2 import Environment, FileSystemLoader


class Edex:
    @cherrypy.expose
    def index(self):
        tmpl = env.get_template('index.html')
        return tmpl.render(salutation='Hello', target='World')



    def hash(s):
        return binascii.b2a_base64(struct.pack('i', hash(s)))



    @cherrypy.expose
    def json(self, name="", parm="", level="",time=""):

        # Need point query results for time-series
        # Cross-sections
        # Time-height
        # Var vs. Height

        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")

        if name != "": request.setLocationNames(name)
        if parm != "": request.setParameters(parm)
        if level != "": request.setLevels(level)

        cycles = DataAccessLayer.getAvailableTimes(request, True)
        t = DataAccessLayer.getAvailableTimes(request)

        fcstRun = []
        fcstRun.append(t[0])
        response = DataAccessLayer.getGridData(request, fcstRun)
        grid = response[0]
        data = grid.getRawData()
        lons, lats = grid.getLatLonCoords()

        columns = (
            'dtype', 'id', 'crs', 'dx', 'dy', 'firstgridpointcorner', 'the_geom',
            'la1', 'lo1', 'name', 'nx', 'ny', 'spacingunit', 'latin1', 'latin2', 'lov',
            'majoraxis', 'minoraxis', 'la2', 'latin', 'lo2', 'lad'
        )

        return json.dumps(data, indent=2)

        #coverage = ''
        #results = []
        #for row in cur.fetchall():
        #    results.append(dict(zip(columns, row)))
        #coverage += json.dumps(results, indent=2)






    @cherrypy.expose
    def radar(self, id="klch", product="32"):
        from cartopy.feature import ShapelyFeature,NaturalEarthFeature
        from awips import ThriftClient, RadarCommon
        from dynamicserialize.dstypes.com.raytheon.uf.common.time import TimeRange
        from dynamicserialize.dstypes.com.raytheon.uf.common.dataplugin.radar.request import GetRadarDataRecordRequest
        from datetime import datetime
        import matplotlib.pyplot as plt
        from datetime import timedelta
        from numpy import ma
        from metpy.plots import ctables
        import cartopy.crs as ccrs
        from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER

        request = DataAccessLayer.newDataRequest()
        request.setDatatype('radar')
        # locations
        availableSites = DataAccessLayer.getAvailableLocationNames(request)
        availableSites.sort()
        request.setLocationNames(id)
        # products
        availableProds = DataAccessLayer.getAvailableParameters(request)
        availableProds.sort()
        request.setParameters(str(product))

        availableLevels = DataAccessLayer.getAvailableLevels(request)
        availableLevels.sort()
        request.setLevels(availableLevels[0])

        times = DataAccessLayer.getAvailableTimes(request)

        print(str(len(times)) + " scans available")
        print(str(times[0].getRefTime()) + " to " + str(times[-1].getRefTime()))

        response = DataAccessLayer.getGridData(request, [times[-1]])
        grid = response[0]
        data = ma.masked_invalid(grid.getRawData())
        lons, lats = grid.getLatLonCoords()

        def make_map(bbox, projection=ccrs.PlateCarree()):
            fig, ax = plt.subplots(figsize=(7, 7),
                    subplot_kw=dict(projection=projection))
            ax.set_extent(bbox)
            ax.coastlines(resolution='50m')
            gl = ax.gridlines(draw_labels=True)
            gl.xlabels_top = gl.ylabels_right = False
            gl.xformatter = LONGITUDE_FORMATTER
            gl.yformatter = LATITUDE_FORMATTER
            gl.xlabel_style = {'size': 6}
            gl.ylabel_style = {'size': 6}
            return fig, ax

        nexrad = {
            "N0Q": {
                'id': 94,
                'unit': 'dBZ',
                'name': '0.5 deg Base Reflectivity',
                'ctable': ['NWSStormClearReflectivity', -20., 0.5],
                'scale': [-32.0, 94.5],
                'res': 1000.,
                'elev': '0.5'},
            "DHR": {
                'id': 32,
                'unit': 'dBZ',
                'name': '0.5 deg Digital Hybrid Reflectivity',
                'ctable': ['NWSStormClearReflectivity', -20., 0.5],
                'scale': [-32.0, 94.5],
                'res': 1000.,
                'elev': '0.5'},
            "N0U": {
                'id': 99,
                'unit': 'kts',
                'name': '0.5 deg Base Velocity',
                'ctable': ['NWS8bitVel', -100., 1.],
                'scale': [-100, 100],
                'res': 250.,
                'elev': '0.5'},
            "EET": {
                'id': 135,
                'unit': 'kft',
                'name': 'Enhanced Echo Tops',
                'ctable': ['NWSEnhancedEchoTops', 2, 1],
                'scale': [0, 255],
                'res': 1000.,
                'elev': '0.0'}
        }
        nexrad_info = [kv for kv in nexrad.items() if kv[1]['id'] == int(product)][0]
        code = nexrad_info[0]
        bbox = [lons.min(), lons.max(), lats.min(), lats.max()]
        print(nexrad_info)
        print(code)

        data = ma.masked_invalid(data)

        ctable = nexrad[code]['ctable'][0]
        beg = nexrad[code]['ctable'][1]
        inc = nexrad[code]['ctable'][2]
        norm, cmap = ctables.registry.get_with_steps(ctable, beg, inc)

        fig, ax = make_map(bbox=bbox)
        cs = ax.pcolormesh(lons, lats, data, norm=norm, cmap=cmap, vmin=nexrad[code]['scale'][0],
                           vmax=nexrad[code]['scale'][1])
        cbar = fig.colorbar(cs, extend='both', shrink=0.85, orientation='horizontal')
        cbar.set_label(str(id).upper() + " " \
                       + str(grid.getLevel()) + " " \
                       + str(grid.getParameter()) \
                       + " (" + str(grid.getUnit()) + ") " \
                       + "valid " + str(grid.getDataTime().getRefTime()))
        political_boundaries = NaturalEarthFeature(category='cultural',
                                       name='admin_0_boundary_lines_land',
                                       scale='50m', facecolor='none')
        states = NaturalEarthFeature(category='cultural',
                                       name='admin_1_states_provinces_lines',
                                       scale='50m', facecolor='none')
        ax.add_feature(political_boundaries, linestyle='-',edgecolor='black')
        ax.add_feature(states, linestyle='-',edgecolor='black')
        plt.tight_layout()

        # Write image
        fformat = "png"
        sio = cStringIO.StringIO()
        plt.savefig(sio, format=fformat)
        print("Content-Type: image/%s\n" % fformat)
        sys.stdout.write(sio.getvalue())
        cartopyImage = '<img style="border: 0;" src="data:image/png;base64,'+sio.getvalue().encode("base64").strip()+'"/>'

        # Build Dropdowns
        prodString = '<table class="ui single line table"><thead><tr><th>Product</th><th>Description</th><th>Unit</th><th>DAF</th></tr></thead>'
        siteSelect = '<select class="ui select dropdown" id="site-select">'
        for radarsite in availableSites:
            siteSelect += '<option value="%s">%s</option>' % (radarsite, radarsite.upper())
        siteSelect += '</select>'
        prodMenu = ''
        prodSelect = '<select class="ui select dropdown" id="prod-select">'
        for prod in availableProds:
            if RepresentsInt(prod):
                idhash = hash(id + prod)
                prodSelect += '<option value="%s">%s</option>' % (prod, prod)
                prodActiveClass = ''
                if prod == product:
                    prodActiveClass = 'active'

                prodMenu += '<a class="item %s" href="/radar?id=%s&parm=%s"><div class="small ui blue label">%s</div></a>' % (prodActiveClass, id, prod,prod)
                prodString += '<tr><td><a href="/radar?id='+id+'&product='+ prod +'"><b>' + prod + '</b></a></td>' \
                    '<td><div class="small ui label"></div></td>' \
                    '<td><div class="small ui label"></div></td>' \
                    '<td><a class="showcode circular ui icon basic button" name="'+str(idhash)+'" ' \
                                'href="/json_radar?id=' + id + '&product=' + prod + '">' \
                                 '<i class="code icon small"></i></a></td></tr>'

                prodString += '''<tr id="''' + str(idhash) + '''" class="transition hidden"><td colspan=5><div class="ui instructive bottom attached segment">
    <pre><code class="code xml">request = DataAccessLayer.newDataRequest()
    request.setDatatype("radar")
    request.setLocationNames("''' + id + '''")
    request.setParameters("''' + prod + '''")</code></pre>
    </div></td></tr>'''

        prodSelect += '</select>'
        prodString += '</table>'

        # Last Scan
        dateString = str(times[-1])[0:19]
        hourdiff = datetime.utcnow() - datetime.strptime(dateString, '%Y-%m-%d %H:%M:%S')
        hours = hourdiff.seconds / 3600
        days = hourdiff.days
        minute = str((hourdiff.seconds - (3600 * hours)) / 60)
        hourdiff = ''
        if hours > 0:
            hourdiff += str(hours) + "hr "
        hourdiff += str(minute) + "m ago"
        if days > 1:
            hourdiff = str(days) + " days ago"

        renderHtml =  """
                <div class="ui grid three column row">
                    <div class="left floated column"><h1>"""+ id.upper() + """</h1></div>
                 </div>
                <p><b>Last volume scan:</b> """+ dateString + """ (""" + hourdiff + """)</p>
                <div class="ui divider"></div>
                <div class="ui two column stackable grid container">
                    <div class="column align right">"""+ siteSelect +"""</div>
                    <div class="column align right">"""+ prodSelect +"""</div>
                </div>

                <div class="ui segment">
                    <div id="cartopy">""" + cartopyImage + """</div>
                </div>
                <div class="ui divider"></div>
                <h2 class="first">"""+id.upper()+""" Radar Products</h2>
                <div>"""+ prodString +"""</div>"""

        sideContent = ""
        stringReturn = createpage(id,str(product),'',str(times[-1]),renderHtml,sideContent,prodMenu)
        return stringReturn




    @cherrypy.expose
    def grid(self, name="RAP13", parm="", level=""):

        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")

        # Grid Names
        available_grids = DataAccessLayer.getAvailableLocationNames(request)
        available_grids.sort()

	if name == "": name=available_grids[-1]
        request.setLocationNames(name)

        # Grid Parameters
        availableParms = DataAccessLayer.getAvailableParameters(request)
        availableParms.sort()

	if len(availableParms) == 0:
	    stringReturn = createpage(name,"","","",server+": no grid records found for "+name,"","")
            return stringReturn	
	
        if parm == "": parm = availableParms[-1]
        request.setParameters(str(parm))

        # Grid Levels
        availableLevels = DataAccessLayer.getAvailableLevels(request)
        availableLevels.sort()
        if level == "": level = availableLevels[-1]
        request.setLevels(str(level))

        # Build Dropdowns
        parmString = '<table class="ui single line table"><thead><tr><th>Parameter</th><th>Description</th><th>Unit</th><th>DAF</th></tr></thead>'
        lvlString = ''
        gridSelect = '<select class="ui select dropdown" id="grid-select">'
        for grid in available_grids:
            grid = grid.decode('utf-8')
            if not pattern.match(grid): gridSelect += '<option value="'+grid+'">'+grid+'</option>'
        gridSelect += '</select>'
        parmMenu = ''
        parmSelect = '<select class="ui select dropdown" id="parm-select">'
        for gridparm in availableParms:
            gridparm = gridparm.decode('utf-8')
            parmDescription = ''
            parmUnit = ''
            for item in parm_dict:
                idhash = hash(name + gridparm)
                replaced = re.sub('[0-9]{1,2}hr$', '', gridparm)
                if item == replaced:
                    parmDescription = parm_dict[item][0]
                    parmUnit = parm_dict[item][1]
            parmSelect += '<option value="%s">%s - %s</option>' % (gridparm, gridparm, parmDescription)
            parmActiveClass = ''
            if gridparm == parm:
                parmActiveClass = 'active'

            if parmDescription != "":
                parmMenu += '<a class="item %s" href="/grid?name=%s&parm=%s"><div class="small ui blue label">%s</div> %s</a>' % (parmActiveClass, name, gridparm,gridparm, parmDescription)
            parmString += '<tr><td><a href="/grid?name='+name+'&parm='+ gridparm +'"><b>' + gridparm + '</b></a></td>' \
                '<td>' + parmDescription + '</td>' \
                '<td><div class="small ui label">' + parmUnit + '</div></td>' \
                '<td><a class="showcode circular ui icon basic button" name="'+str(idhash)+'" ' \
                            'href="/json?name=' + name + '&parm=' + gridparm + '">' \
                             '<i class="code icon small"></i></a></td></tr>'

            parmString += '''<tr id="''' + str(idhash) + '''" class="transition hidden"><td colspan=5><div class="ui instructive bottom attached segment">
<pre><code class="code xml">request = DataAccessLayer.newDataRequest()
request.setDatatype("grid")
request.setLocationNames("''' + name + '''")
request.setParameters("''' + gridparm + '''")
levels = DataAccessLayer.getAvailableLevels(request)
request.setLevels(levels[0])</code></pre>
</div></td></tr>'''

        parmSelect += '</select>'
        parmString += '</table>'

        parmDescription = ''
        parmUnit = ''
        for item in parm_dict:
            replaced = re.sub('[0-9]{1,2}hr$', '', parm.decode('utf-8'))
            if item == replaced:
                parmDescription = parm_dict[item][0]
                parmUnit = parm_dict[item][1]

        levelSelect = '<select class="ui select dropdown" id="level-select">'
        for llevel in availableLevels:
            levelSelect += '<option value="%s">%s</option>' % (llevel, llevel)
        levelSelect += '</select>'

        # Forecast Cycles
        cycles = DataAccessLayer.getAvailableTimes(request, True)
        times = DataAccessLayer.getAvailableTimes(request)
        latest_run = DataAccessLayer.getForecastRun(cycles[-1], times)

        # Last Run
        dateString = str(latest_run[0:1][0])[0:19]
        hourdiff = datetime.datetime.utcnow() - datetime.datetime.strptime(dateString, '%Y-%m-%d %H:%M:%S')
        hours = hourdiff.seconds / 3600  # integer
        days = hourdiff.days
        minute = str((hourdiff.seconds - (3600 * hours)) / 60)
        hourdiff = ''
        if hours > 0:
            hourdiff += str(hours) + "hr "
        hourdiff += str(minute) + "m ago"
        if days > 1:
            hourdiff = str(days) + " days ago"

        # Grid Info
        for gname, info in grid_dictionary.iteritems():
            if gname == name:
                centerid = info[0]
                subcenterid = info[1]
                gridid = info[2]
                #gridname = info[3]
                centername = wmo_centers[centerid]
                gridnav = navigation[gridid]
                grid_size = gridnav[1] + "x" + gridnav[2]
                grid_res = gridnav[3] +" " + gridnav[5]

        renderHtml =  """                <script type="text/javascript">
                    var createGeoJSON = function(){
                        getGeoJSON('/api?name="""+ name + """&parm="""+parm+"""&level="""+str(level)+"""',function(response) {
                            var json = response.json;
                            var container = document.getElementById('dsmap');
                            var maps = mapConfig(colormaps, container);
                            maps.jsonMap.drawImage(json, response.json.metadata);
                        });
                        getGeoJSONBounds('/polygon?name="""+ name + """',function(response) {
                            var coveragePolygon = response.json;
                            var container = document.getElementById('datamap');
                            var polygon =  [geoJsonPolygonFeature(coveragePolygon)] ;
                            var jsonMap = dataMap.map({
                                el: container,
                                scrollWheelZoom: false,
                                center: {lat: 40, lng: -105}
                            }).init().drawPolygon(polygon).zoomToBounds(polygon);
                        });
                    }
                </script>

                <div class="ui grid three column row">
                    <div class="left floated column"><h1>"""+ name + """</h1></div>
                    <div class="right floated column">"""+ gridSelect +"""</div>
                 </div>
                <p>""" + centername[1] + """ &nbsp;<a class="ui tiny label" href="#">""" + centername[0] + """</a></p>
                <p><b>Last run:</b> """+ dateString + """ (""" + hourdiff + """)</p>
                <div class="ui divider"></div>
                <div class="ui two column stackable grid container">
                    <div class="column align right">"""+ levelSelect +"""</div>
                    <div class="column align right">"""+ parmSelect +"""</div>
                </div>
                <div class="ui segment" id="dsmap"></div>
                <h2 class="first">"""+name+""" Grid Parameters</h2>
                <div>"""+ parmString +"""</div>"""

        sideContent = """
                <div class="ui raised segment">
                    <a class="ui right ribbon label">Projection</a>
                    <div class="ui middle aligned divided list">
                        <p>""" + gridnav[0] + """</p>
                        <div class="item"><b>Grid size</b>
                            <div class="right floated content">""" + grid_size + """</div>
                        </div>
                        <div class="item"><b>Resolution</b>
                            <div class="right floated content">""" + grid_res + """</div>
                        </div>
                        <div class="item"><b>Center ID</b>
                            <div class="right floated content">""" + centerid + """</div>
                        </div>
                        <div class="item"><b>Subcenter ID</b>
                            <div class="right floated content">""" + subcenterid + """</div>
                        </div>
                        <div class="item"><b>Grid Number</b>
                            <div class="right floated content">""" + gridid + """</div>
                        </div>
                    </div>
                </div>
		<div class="ui segment" id="datamap"></div>
            """

        stringReturn = createpage(name,parm,str(level),str(latest_run[0]),renderHtml,sideContent, parmMenu)
        return stringReturn


    @cherrypy.expose
    def remapped(self, name="", parm="", level=""):
        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")
        request.setLocationNames(name)
        request.setParameters(parm)
        availableLevels = DataAccessLayer.getAvailableLevels(request)
        availableLevels.sort()
        level = str(level)
        if level == "": level = availableLevels[-1]
        request.setLevels(level)
        cycles = DataAccessLayer.getAvailableTimes(request, True)
        times = DataAccessLayer.getAvailableTimes(request)
        fcstRun = DataAccessLayer.getForecastRun(cycles[-1], times)
        response = DataAccessLayer.getGridData(request, [fcstRun[-1]])
        data = response[0].getRawData()
        lons, lats = response[0].getLatLonCoords()
        ngrid = data.shape[1]
        rlons = np.repeat(np.linspace(np.min(lons), np.max(lons), ngrid),
                      ngrid).reshape(ngrid, ngrid)
        rlats = np.repeat(np.linspace(np.min(lats), np.max(lats), ngrid),
                      ngrid).reshape(ngrid, ngrid).T
        tli = mtri.LinearTriInterpolator(mtri.Triangulation(lons.flatten(),
                       lats.flatten()), data.flatten())
        rdata = tli(rlons, rlats)
        jslat = rlats[0].tolist()
        jslon = rlons[:,0].tolist()
        jsdict = {
            "lats"    : jslat[::-1],
            "lons"    : jslon,
            "values"  : rdata.transpose().tolist()[::-1],
            "metadata": {
                "datetime": "1484956800000",
                "unit": "K",
                "projection": "remapped",
                "coverage": {
                    "latmax": rlats[0].max(),
                    "lonmin": rlons[:,0].min(),
                    "lonmax": rlons[:,0].max(),
                    "latmin": rlats[0].min()
                }
            }
        }
        return json.dumps(jsdict)




    @cherrypy.expose
    def api(self, name="", parm="", level=""):
        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")
        request.setLocationNames(name)
        request.setParameters(parm)
        availableLevels = DataAccessLayer.getAvailableLevels(request)
        availableLevels.sort()
        level = str(level)
        if level == "": level = availableLevels[-1]
        request.setLevels(level)

        cycles = DataAccessLayer.getAvailableTimes(request, True)
        times = DataAccessLayer.getAvailableTimes(request)
        fcstRun = DataAccessLayer.getForecastRun(cycles[-1], times)
        response = DataAccessLayer.getGridData(request, [fcstRun[-1]])

        data = response[0].getRawData()
        lon, lat = response[0].getLatLonCoords()
        datadict = {
            "lats"    : lat.transpose().tolist()[::-1],
            "lons"    : lon.transpose().tolist()[::-1],
            "values"  : data.transpose().tolist()[::-1],
            "metadata": {
                "datetime": "1484956800000",
                "unit": "K",
                "projection": "native",
                "coverage": {
                    "latmax": str(lat.max()),
                    "lonmin": str(lon.min()),
                    "lonmax": str(lon.max()),
                    "latmin": str(lat.min())
                }
            }
        }
        return json.dumps(datadict)








    @cherrypy.expose
    def coverage(self, name="RAP13"):
        import psycopg2
        conn = None
        coverage = ''
        try:
            conn = psycopg2.connect("dbname = 'metadata' user = 'awips' host = 'localhost' password='awips'")
            cur = conn.cursor()
            cur.execute("select * from gridcoverage where id = "
                        "(select distinct location_id from grid_info where datasetid = '" + name + "');")
            columns = ( 'dtype', 'id', 'crs', 'dx', 'dy', 'firstgridpointcorner', 'the_geom',
                'la1', 'lo1', 'name', 'nx', 'ny', 'spacingunit', 'latin1', 'latin2', 'lov',
                'majoraxis', 'minoraxis', 'la2', 'latin', 'lo2', 'lad')
            results = []
            for row in cur.fetchall():
                results.append(dict(zip(columns, row)))
            coverage = json.dumps(results, indent=2)
        except psycopg2.DatabaseError as ex:
            print('Unable to connect the database: ' + str(ex))
        return coverage








    @cherrypy.expose
    def polygon(self, name="RAP13"):
        import psycopg2
        conn = None
        polygon = ''
        try:
            conn = psycopg2.connect("dbname = 'metadata' user = 'awips' host = 'localhost' password='awips'")
            cur = conn.cursor()
            cur.execute("SELECT ST_AsGeoJSON(the_geom)::text from gridcoverage where id = "
                        "(select distinct location_id from grid_info where datasetid = '" + name + "');")
            recs = cur.fetchall()
            return recs[0]
        except psycopg2.DatabaseError as ex:
            print('Unable to connect the database: ' + str(ex))


    @cherrypy.expose
    def image(self, name="RAP13", parm="T", level="0.0SFC"):
        import cartopy.crs as ccrs
        import matplotlib.pyplot as plt
        from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
        import numpy as np
        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")
        request.setLocationNames(name)
        request.setParameters(parm)
        request.setLevels(str(level))
        cycles = DataAccessLayer.getAvailableTimes(request, True)
        times = DataAccessLayer.getAvailableTimes(request)
        fcstRun = DataAccessLayer.getForecastRun(cycles[-1], times)
        response = DataAccessLayer.getGridData(request, [fcstRun[-1]])
        grid = response[0]
        data = grid.getRawData()
        lons, lats = grid.getLatLonCoords()
        bbox = [lons.min(), lons.max(), lats.min(), lats.max()]

        def make_map(bbox, projection=ccrs.PlateCarree()):
            fig, ax = plt.subplots(subplot_kw=dict(projection=projection))
            fig.tight_layout()
            ax.set_extent(bbox)
            ax.coastlines(resolution='50m')
            gl = ax.gridlines(draw_labels=True)
            gl.xlabels_top = gl.ylabels_right = False
            #gl.xformatter = LONGITUDE_FORMATTER
            #gl.yformatter = LATITUDE_FORMATTER
            return fig, ax

        fig, ax = make_map(bbox=bbox)
        cs = ax.pcolormesh(lons, lats, data, cmap=plt.get_cmap('rainbow'))
        cbar = fig.colorbar(cs, extend='both', shrink=0.5, orientation='horizontal')
        cbar.set_label(str(grid.getLocationName()) +" " \
                + str(grid.getLevel()) + " " \
                + str(grid.getParameter()) + " " \
                + "(" + str(grid.getUnit()) + ") " \
                + " valid " + str(grid.getDataTime().getRefTime()) )

        # Write image
        format = "png"
        sio = cStringIO.StringIO()
        plt.savefig(sio, format=format)
        print("Content-Type: image/%s\n" % format)
        sys.stdout.write(sio.getvalue())
        #cartopyImage = '<img style="border: 0;" src="data:image/png;base64,'+sio.getvalue().encode("base64").strip()+'"/>'
        #cartopyImage = '<img style="border: 0;" src="data:image/png;base64,'+sio.getvalue().encode("base64").strip()+'"/>'
        #self.set_header('Content-Type', 'image/png')
        #self.write(figdata.getvalue())
        #return sio
        return sio.getvalue()







    @cherrypy.expose
    def geojson(self, name="RAP13", parm="T", level="0.0SFC"):
        import cartopy.crs as ccrs
        import matplotlib.pyplot as plt
        from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
        import numpy as np

        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")
        request.setLocationNames(name)
        request.setParameters(parm)
        request.setLevels(str(level))

        cycles = DataAccessLayer.getAvailableTimes(request, True)
        times = DataAccessLayer.getAvailableTimes(request)
        fcstRun = DataAccessLayer.getForecastRun(cycles[-1], times)
        response = DataAccessLayer.getGridData(request, [fcstRun[-1]])
        grid = response[0]
        data = grid.getRawData()
        lons, lats = grid.getLatLonCoords()
        bbox = [lons.min(), lons.max(), lats.min(), lats.max()]

        def make_map(bbox, projection=ccrs.PlateCarree()):
            fig, ax = plt.subplots(subplot_kw=dict(projection=projection))
            fig.tight_layout()
            ax.set_extent(bbox)
            ax.coastlines(resolution='50m')
            gl = ax.gridlines(draw_labels=True)
            gl.xlabels_top = gl.ylabels_right = False
            #gl.xformatter = LONGITUDE_FORMATTER
            #gl.yformatter = LATITUDE_FORMATTER
            return fig, ax

        fig, ax = make_map(bbox=bbox)
        cs = ax.pcolormesh(lons, lats, data, cmap=plt.get_cmap('rainbow'))
        cbar = fig.colorbar(cs, extend='both', shrink=0.5, orientation='horizontal')
        cbar.set_label(str(grid.getLocationName()) +" " \
                + str(grid.getLevel()) + " " \
                + str(grid.getParameter()) + " " \
                + "(" + str(grid.getUnit()) + ") " \
                + " valid " + str(grid.getDataTime().getRefTime()) )

        # Write image
        format = "png"
        sio = cStringIO.StringIO()
        plt.savefig(sio, format=format)
        print("Content-Type: image/%s\n" % format)
        sys.stdout.write(sio.getvalue())
        cartopyImage = '<img style="border: 0;" src="data:image/png;base64,'+sio.getvalue().encode("base64").strip()+'"/>'

        renderHtml =  """
                <script type="text/javascript">
                    var createGeoJSON = function(){

                        getGeoJSON('/api?name="""+name+"""&parm=T&level=0.0SFC',function(response) {
                            var json = response.json;
                            var container = document.getElementById('dsmap');
                            var maps = mapConfig(colormaps, container);
                            maps.jsonMap.drawImage(json, response.json.metadata);
                        })

                        getGeoJSONBounds('/polygon?name="""+name+"""',function(response) {
                            var coveragePolygon = response.json;
                            var container = document.getElementById('datamap');
                            var polygon =  [geoJsonPolygonFeature(coveragePolygon)] ;
                            var jsonMap = dataMap.map({
                                el: container,
                                scrollWheelZoom: false,
                                center: {lat: 40, lng: -105}
                            }).init().drawPolygon(polygon).zoomToBounds(polygon);
                        });

                        // Remapped (static example)
                        var json = response_json;
                        json.values = json.values.map(function(d, i) {
                            return d.map(function(b) {
                                if (b === -999) {return null;}
                                return b
                            });
                        });
                        json.uniqueValues = unique(json.values).sort();
                        var container = document.getElementById('remapped');
                        var maps = mapConfig(colormaps, container);
                        maps.jsonMap.drawImage(json, response_json.metadata);
                    }
                </script>
                <h1>Building a GeoJSON API with python-awips and CherryPy</h1>

<p>Using a DataAccessLayer <a target='_blank' href='http://python-awips.readthedocs.io/en/latest/api/IDataRequest.html'>newDataRequest()</a> to request a grid feild ("""+name+""" surface temperature) we can interpolate to a regularly-spaced coordinate grid using Matplotlib, returned as a JSON object.</p>

<pre class='small'><code>   from awips.dataaccess import DataAccessLayer
   import json

   class Edex:

       @cherrypy.expose
       def api(self, name=""""+name+"""", parm="T", level="0.0SFC"):
           request = DataAccessLayer.newDataRequest()
           request.setDatatype("grid")
           request.setLocationNames(name)
           request.setParameters(parm)
           request.setLevels(str(level))
           cycles = DataAccessLayer.getAvailableTimes(request, True)
           times = DataAccessLayer.getAvailableTimes(request)
           fcstRun = DataAccessLayer.getForecastRun(cycles[-1], times)
           response = DataAccessLayer.getGridData(request, [fcstRun[-1]])
           data = response[0].getRawData()
           lon, lat = response[0].getLatLonCoords()
           datadict = {
               "lats"    : lat.transpose().tolist()[::-1],
               "lons"    : lon.transpose().tolist()[::-1],
               "values"  : data.transpose().tolist()[::-1],
               "metadata": {
                   "datetime": "1484956800000",
                   "unit": "K",
                   "coverage": {
                       "latmax": str(lat.max()),
                       "lonmin": str(lon.min()),
                       "lonmax": str(lon.max()),
                       "latmin": str(lat.min())
                   }
               }
           }
           return json.dumps(datadict)


       if __name__ == '__main__':
           DataAccessLayer.changeEDEXHost(server)
           from cherrypy.process.plugins import Daemonizer
           d = Daemonizer(cherrypy.engine)
           d.subscribe()
           cherrypy.quickstart(Edex(), '/', config=server_config)</code></pre>



	<!--
        <div class="ui segment">
            <h2>Render Native (Irregular) Grid w Leaflet</h2>
            <div id="dsmap"></div>

            <p><a href='/api?name="""+name+"""&parm="""+parm+"""&level=0.0SFC'>/api?name="""+name+"""&parm="""+parm+"""&level=0.0SFC</a></p>

        </div>


        <div class="ui segment">
            <h2>Render Remapped Grid w Leaflet</h2>
            <div id="remapped"></div>

            <p><a href='/remapped?name="""+name+"""&parm="""+parm+"""&level=0.0SFC'>/remapped?name="""+name+"""&parm="""+parm+"""&level=0.0SFC</a></p>

        </div>
	-->
        <div class="ui segment">
            <h2>Render w Cartopy and Matplotlib</h2>
            <div id="cartopy">""" + cartopyImage + """</div>

            <pre><code>
    import cartopy.crs as ccrs
    import matplotlib.pyplot as plt
    from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
    import numpy as np

    DataAccessLayer.changeEDEXHost("edex-cloud.unidata.ucar.edu")
    request = DataAccessLayer.newDataRequest()
    request.setDatatype("grid")
    request.setLocationNames("RAP13")
    request.setParameters("T")
    request.setLevels("0.0SFC")

    cycles = DataAccessLayer.getAvailableTimes(request, True)
    times = DataAccessLayer.getAvailableTimes(request)
    fcstRun = DataAccessLayer.getForecastRun(cycles[-1], times)
    response = DataAccessLayer.getGridData(request, [fcstRun[-1]])
    grid = response[0]
    data = grid.getRawData()
    lons, lats = grid.getLatLonCoords()
    bbox = [lons.min(), lons.max(), lats.min(), lats.max()]

    def make_map(bbox, projection=ccrs.PlateCarree()):
        fig, ax = plt.subplots(subplot_kw=dict(projection=projection))
        fig.tight_layout()
        ax.set_extent(bbox)
        ax.coastlines(resolution='50m')
        gl = ax.gridlines(draw_labels=True)
        gl.xlabels_top = gl.ylabels_right = False
        gl.xformatter = LONGITUDE_FORMATTER
        gl.yformatter = LATITUDE_FORMATTER
        return fig, ax

    fig, ax = make_map(bbox=bbox)
    cs = ax.pcolormesh(lons, lats, data, cmap=plt.get_cmap('rainbow'))
    cbar = fig.colorbar(cs, extend='both', shrink=0.5, orientation='horizontal')
    cbar.set_label(str(grid.getLocationName()) +" " \\
        + str(grid.getLevel()) + " " \\
        + str(grid.getParameter()) + " " \\
        + "(" + str(grid.getUnit()) + ") " \\
        + " valid " + str(grid.getDataTime().getRefTime()) )
    plt.show()
    </code></pre>
        </div>




     <h2>Leaflet Bounding Box Overlay</h2>
        <div class="ui segment">
                <h3>1) Using Psycopg2 and json.dumps</h3>

                <pre class='small'><code>    conn = None
        try:
            conn = psycopg2.connect("dbname = 'metadata' user = 'awips' host = 'localhost' password='awips'")
            cur = conn.cursor()
            cur.execute("select * from gridcoverage where id = "
                        "(select distinct location_id from grid_info where datasetid = '"""+name+"""');")
            columns = ('dtype', 'id', 'crs', 'dx', 'dy', 'firstgridpointcorner', 'the_geom',
                'la1', 'lo1', 'name', 'nx', 'ny', 'spacingunit', 'latin1', 'latin2', 'lov',
                'majoraxis', 'minoraxis', 'la2', 'latin', 'lo2', 'lad')
            results = []
            for row in cur.fetchall():
                results.append(dict(zip(columns, row)))
            coverage = json.dumps(results, indent=2)</code></pre>

            Result:

            <pre class='small'><code>    [
      {
        "dtype": "LambertConformalGridCoverage",
        "la1": 16.281,
        "la2": 25.0,
        "spacingunit": "km",
        "minoraxis": 25.0,
        "id": 94,
        "nx": 151,
        "ny": 113,
        "lo1": -126.138,
        "lov": 6378160.0,
        "latin": null,
        "lad": null,
        "dx": 40.63525,
        "dy": 40.63525,
        "name": "236",
        "latin2": -95.0,
        "lo2": null,
        "firstgridpointcorner": "LowerLeft",
        "majoraxis": 6356775.0
        "the_geom": "010300000001000000050000006B1552B2CA915FC089E7C36C19103040C3F91A0F673D51C04A01767C91253140211C8D4436954CC085312DFAFCD64B406656249C828561C0E7A795565D2C4B406B1552B2CA915FC089E7C36C19103040", "latin1": null, "crs": "PROJCS[\"Lambert Conformal (SP: 25.0/25.0, Origin: -95.0)\", \n GEOGCS[\"WGS84(DD)\", \n DATUM[\"WGS84\", \n SPHEROID[\"WGS84\", 6378137.0, 298.257223563]], \n PRIMEM[\"Greenwich\", 0.0], \n UNIT[\"degree\", 0.017453292519943295], \n AXIS[\"Geodetic longitude\", EAST], \n AXIS[\"Geodetic latitude\", NORTH]], \n PROJECTION[\"Lambert_Conformal_Conic_1SP\"], \n PARAMETER[\"semi_major\", 6378160.0], \n PARAMETER[\"semi_minor\", 6356775.0], \n PARAMETER[\"central_meridian\", -95.0], \n PARAMETER[\"latitude_of_origin\", 25.0], \n PARAMETER[\"scale_factor\", 1.0], \n PARAMETER[\"false_easting\", 0.0], \n PARAMETER[\"false_northing\", 0.0], \n UNIT[\"m\", 1.0], \n AXIS[\"Easting\", EAST], \n AXIS[\"Northing\", NORTH]]"
      }
   ]
            </code></pre>
        </div>
        <div class="ui segment">
                <h3>2) Simple bounds using <b>ST_AsGeoJSON</b></h3>

                <pre class='small'><code>    SELECT ST_AsGeoJSON(the_geom) from gridcoverage
    where id = (select distinct location_id
                from grid_info
                where datasetid = '"""+name+"""');</code></pre>

                Result:

                <pre class='small'><code>    {
        "type":"Polygon",
        "coordinates":[[
            [-126.277996616516,16.0628879526408],
            [-68.9594152224955,17.1467511928652],
            [-57.1657186211598,55.6795952530547],
            [-140.172193594906,54.3465984564535],
            [-126.277996616516,16.0628879526408]
        ]]
    }</code></pre>
        </div>

                <div id="datamap"></div>"""

        stringReturn = createpage(name,parm,str(level),'',renderHtml,'','')
        return stringReturn

    # PARM PAGE

    @cherrypy.expose
    def parm(self, parm="", level=""):
        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")
        availableParms = DataAccessLayer.getAvailableParameters(request)
        availableParms.sort()
        request.setParameters(parm)
        parmText = ''
        parmDesc = ''
        parmUnit = ''

        gridString = ''
        for item in parm_dict:
            replaced = re.sub('[0-9]{1,2}hr$', '', parm)
            if item == replaced:
                parmText = parm_dict[item][0]
                parmUnit = parm_dict[item][1]

        #parameter_content = 'var parameter_content = ['
        #previous = ''
        #for gridparm in availableParms:
        #    for item in parm_dict:
        #        replaced = re.sub('[0-9]{1,2}hr', '', gridparm)
        #        if item == replaced and replaced <> previous:
        #            previous = replaced
        #            parmDesc = parm_dict[item][0]
        #            parameter_content += "{ name: '" + replaced + "', title: '" + replaced + " - " + parmDesc + "'},"
        #parameter_content += '];'


        # Grid names
        available_grids = DataAccessLayer.getAvailableLocationNames(request)
        available_grids.sort()
        parmSearch = """"""
        gridLabels = ''
        count=0
        for grid in available_grids:
            lcount = 0
            count += 1
            if not pattern.match(grid) or 1 == 1:
                gridString += '<a class="parm table" name="'+grid+'"><div class="ui horizontal divider"></div></a><div class="parm table"><h2><a href="/grid?name='+grid+'">'+grid+'</a></h2>'\
                        '<table class="ui single line table"><thead>' \
                        '<tr><th>Parameter</th><th>Description</th><th>Unit</th><th>Level</th><th>DAF</th></tr>' \
                        '</thead>'
                request.setLocationNames(grid)
                availableLevels = DataAccessLayer.getAvailableLevels(request)
                availableLevels.sort()
                for llevel in availableLevels:
                    lcount += 1
                    for litem in level_dict:
                        lreplaced = re.sub('^[0-9|\.|\_]+', '', str(llevel))
                        if str(litem) == lreplaced:
                            levelDesc = level_dict[litem][0]
                    idhash = hash(grid+parm+str(llevel))
                    gridString += '<tr><td><a href="/grid?name=' + grid + '&parm=' + parm + '">' + parm + '</a></td>' \
                            '<td>'+ parmText +'</td>' \
                            '<td>'+ parmUnit +'</td>' \
                            '<td><div class="small ui label" data-tooltip="' + levelDesc + '">' + str(llevel) +'</div></td>' \
                            '<td><a class="showcode circular ui icon basic button" name="'+str(idhash)+'" ' \
                            'href="/json?name=' + grid + '&parm=' + parm + '&level=' + str(llevel) + '">' \
                             '<i class="code icon small"></i></a></td></tr>'
                    gridString += '''<tr id="'''+str(idhash)+'''" class="transition hidden"><td colspan=5><div class="ui instructive bottom attached segment"><pre><code id="code'''+str(idhash)+'''" class="code xml">request = DataAccessLayer.newDataRequest()
request.setDatatype("grid")
request.setLocationNames("'''+grid+'''")
request.setParameters("'''+parm+'''")
request.setLevels("'''+str(llevel)+'''")
</code></pre></div></td></tr>'''

                gridString += '</table></div>'

            levelCount = str(lcount) + ' level'
            if lcount > 1: levelCount += 's'

            gridLabels += '<a href="#'+grid+'" class="small ui label" data-tooltip="' + levelCount + '">' + grid +'</a>'

        # Build dropdowns
        # lvlString = ''
        # renderHtml = '<div class=""><select class="ui select dropdown" id="grid-select">'
        # for grid in available_grids:
        #     if not pattern.match(grid): renderHtml += '<option value="%s">%s</option>' % (grid, grid)
        # renderHtml += '</select></div>'
        #
        # renderHtml += '<div class=""><select class="ui select dropdown" id="level-select">'
        # for llevel in availableLevels:
        #     renderHtml += '<option value="%s">%s</option>' % (llevel, llevel)
        # renderHtml += '</select></div>'
        #
        # # Forecast Cycles
        # cycles = DataAccessLayer.getAvailableTimes(request, True)
        # t = DataAccessLayer.getAvailableTimes(request)
        # fcstRun = []
        # for time in t:
        #     if str(time)[:19] == str(cycles[-1]):
        #         fcstRun.append(time)
        #
        # renderHtml += '<div class="ui one column grid"><div class="ten wide column"><div><select class="ui select dropdown" id="cycle-select">'
        # for time in fcstRun:
        #     renderHtml += '<option value="%s">%s</option>' % (time, time)
        # renderHtml += '</select></div><br><Br>'
        suf = 's'
        if count == 1:
             suf = ''
        renderHtml = parmSearch + '<h1 class="ui dividing header">' + parm + ' - ' + parmText + ' (' + parmUnit + ')</h1>' \
                     + str(count) + ' record' +suf+ ' ' + gridLabels + '<p>' + gridString + '</p></div></div>'

        sideContent = ''
        parmlist = ''
        stringReturn = createpage('',parm,str(level),"",renderHtml,sideContent, parmlist)
        return stringReturn





def parameterDictionary(availableParms):
    javascriptString = 'var parameter_content = ['
    previous = ''
    for gridparm in availableParms:
        for item in parm_dict:
            replaced = re.sub('[0-9]{1,2}hr', '', gridparm)
            if item == replaced and replaced != previous:
                previous = replaced
                parmDescription = parm_dict[item][0]
                javascriptString += "{ name: '"+replaced+"', title: '"+replaced+" - "+parmDescription+"'},"
    javascriptString += '];'
    return javascriptString

def createpage(name, parmname, level, time, mainContent, sideContent, parmlist):
    tmpl = env.get_template('page.html')
    return tmpl.render(name=name,
                       parmname=parmname,
                       level=level,
                       time=time,
                       mainContent=mainContent,
                       sideContent=sideContent,
                       parmlist=parmlist
                       )


# http://stackoverflow.com/a/1267145/5191979
def RepresentsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


if __name__ == '__main__':
    server="edex-cloud.unidata.ucar.edu"
    env = Environment(loader=FileSystemLoader('templates'))
    # regex exclude list
    pattern = re.compile("^((ECMF|UKMET|QPE|MPE|FFG|GribModel|HFR|RFCqpf|EPAC40))")
    DataAccessLayer.changeEDEXHost("edex-cloud.unidata.ucar.edu")
    #DataAccessLayer.changeEDEXHost("edextest.unidata.ucar.edu")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    server_config ={
        'global': {
            'server.socket_host': '0.0.0.0',
            'server.socket_port': 8080
        },
        '/css': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(current_dir, 'css')
        },
        '/js': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': os.path.join(current_dir, 'js')
        },
         '/images': {
             'tools.staticdir.on': True,
             'tools.staticdir.dir': os.path.join(current_dir, 'images')
         },
         '/components': {
             'tools.staticdir.on': True,
             'tools.staticdir.dir': os.path.join(current_dir, 'components')
         }
    }
    # run as daemon
    #from cherrypy.process.plugins import Daemonizer
    #d = Daemonizer(cherrypy.engine)
    #d.subscribe()
    cherrypy.quickstart(Edex(), '/', config=server_config)

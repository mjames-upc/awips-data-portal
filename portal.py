import sys, os, cStringIO
import json
import datetime
import psycopg2
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
    def radar(self, id="kdox", product="32"):
        from cartopy.feature import ShapelyFeature,NaturalEarthFeature
        from awips import ThriftClient, RadarCommon
        from dynamicserialize.dstypes.com.raytheon.uf.common.time import TimeRange
        from dynamicserialize.dstypes.com.raytheon.uf.common.dataplugin.radar.request import GetRadarDataRecordRequest
        from datetime import datetime
        import matplotlib.pyplot as plt
	plt.switch_backend('agg')
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
        prodString = '<table class="ui single line table"><thead><tr><th>Product</th><th>Description</th><th>Unit</th><th>API</th></tr></thead>'
        siteSelect = '<select class="ui select dropdown" id="site-select">'
        for radarsite in availableSites:
            siteSelect += '<option value="%s">%s</option>' % (radarsite, radarsite.upper())
        siteSelect += '</select>'
        prodMenu = ''
        prodSelect = '<select class="ui select dropdown" id="prod-select">'
        for prod in availableProds:
            if RepresentsInt(prod):
                nexrad_info = [kv for kv in nexrad.items() if kv[1]['id'] == prod][0]
                code = nexrad_info[0]
                idhash = hash(id + prod)
                prodSelect += '<option value="%s">%s</option>' % (prod, prod)
                prodActiveClass = ''
                if prod == product:
                    prodActiveClass = 'active'

                prodMenu += '<a class="item %s" href="/radar?id=%s&parm=%s"><div class="small ui blue label">%s</div></a>' % (prodActiveClass, id, prod,prod)
                prodString += '<tr><td><a href="/radar?id='+id+'&product='+ prod +'"><b>' + prod + '</b></a></td>' \
                    '<td>'+nexrad[code]['name']+'</td>' \
                    '<td><div class="small ui label">'+nexrad[code]['unit']+'</div></td>' \
                    '<td><a class="showcode circular ui icon basic button" name="'+str(idhash)+'" ' \
                                'href="/json_radar?id=' + id + '&product=' + prod + '">' \
                                 '<i class="code icon small"></i></a></td></tr>'

                prodString += """<tr id=""" + str(idhash) + """ class="transition hidden"><td colspan=5><div class="ui instructive bottom attached segment">
    <pre class="code xml">request = DataAccessLayer.newDataRequest()
request.setDatatype("radar")
request.setLocationNames(\"""" + id + """\")
request.setParameters(\"""" + prod + """\")</pre>
    </div></td></tr>"""

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
    def inventory(self, server="edex-cloud.unidata.ucar.edu"):

        from datetime import datetime, timedelta

        edex_server = [
            'edextest.unidata.ucar.edu',
            'js-156-89.jetstream-cloud.org',
            'js-157-49.jetstream-cloud.org'
            ]
        edex_desc = [
            'onsite backup',
            'edex-cloud',
            'edex-cloud2'
        ]

        serverSelect = '<div class="ui raised segments sticky fixed">'

        for addr, desc in zip(edex_server, edex_desc):
            try:
                DataAccessLayer.changeEDEXHost(addr)
                dataTypes = DataAccessLayer.getSupportedDatatypes()
                status='<i class="checkmark green icon"></i>'
            except:
                status='<i class="remove red circle icon"></i>'

            serverSelect += """
                <div class="ui segment">
                    <a href="/inventory?server="""+addr+"""">
                        <h4 class="ui header">"""+desc+""" """ + status + """</h4>
                        """+addr+"""
                    </a>
                </div>"""

        serverSelect += '</div>'

        DataAccessLayer.changeEDEXHost(server)
        productList = """<h1 class='ui dividing header'>"""+server+"""</h1><div class="ui divided list">"""

        gridnames=["NCWF","HRRR","GFS","NAM12","CMC","MRMS_0500","MRMS_1000"]

        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")

        try:
            available_grids = DataAccessLayer.getAvailableLocationNames(request)
            available_grids.sort()
        except:
            content = "<div class='ui negative message'><p class='ui error red'>Could not connect to "+server+"</p></div>"
            stringReturn = createpage(id,'','','',content,serverSelect,'')
            return stringReturn

        if not available_grids:
            available_grids = gridnames

        productList += """<table class="ui single line table">

                <tr>
                    <td colspan=3>
                        <h2 class="ui header">
                          <img src="/images/grid.png" class="ui circular image">
                          Gridded Data
                        </h2>
                    </td>
                </tr>
                """
        for grid in available_grids:
            if not pattern.match(grid):
                request.setLocationNames(grid)
                cycles = DataAccessLayer.getAvailableTimes(request, True)
                times = DataAccessLayer.getAvailableTimes(request)
                if not cycles:
                    productList += product_status('red', str(grid), 'None')
                else:
                    utc_now  = datetime.utcnow()
                    utc_prod = datetime.utcfromtimestamp(int(cycles[-1].getRefTime().getTime()/1000))
                    utc_str = str(utc_prod)

                    ddiff = utc_now-utc_prod
                    hours = ddiff.seconds / 3600
                    days = ddiff.days
                    minute = str((ddiff.seconds - (3600 * hours)) / 60)
                    hrdiff = ''
                    if hours > 0:
                        hrdiff += str(hours) + " hr"
                    hrdiff += str(minute) + " min ago"
                    if days > 1:
                        hrdiff = str(days) + " days ago"
                    color="green"
                    if hours > 10 or days > 1:
                        color="orange"
                    productList += product_status(color, str(grid), str(hrdiff), utc_str)



        # NEXRAD

        productList += """
                <tr>
                    <td colspan=3>
                        <h2 class="ui header">
                          <img src="/images/radar.png" class="ui circular image">
                          Radar Products
                        </h2>
                    </td>
                </tr>"""

        request = DataAccessLayer.newDataRequest()
        request.setDatatype("radar")
        site="kftg"
        request.setLocationNames(site)

        wsrProducts = DataAccessLayer.getAvailableParameters(request)
        wsrProducts.sort()

        request.setParameters('94')

        datatimes = DataAccessLayer.getAvailableTimes(request)

        if not datatimes:
            productList += product_status('red', str(site).upper(), 'None')
        else:
            dateString = str(datatimes[-1])
            utc_str = str(datetime.utcfromtimestamp(int(datatimes[-1].getRefTime().getTime()/1000)))
            ddiff = datetime.utcnow() - datetime.strptime(dateString, '%Y-%m-%d %H:%M:%S')
            hours = ddiff.seconds / 3600
            days = ddiff.days
            minute = str((ddiff.seconds - (3600 * hours)) / 60)
            hrdiff = ''
            if hours > 0:
                hrdiff += str(hours) + "hr "
            hrdiff += str(minute) + "m ago"
            if days > 1:
                hrdiff = str(days) + " days ago"
            color='green'
            if hours > 1:
                color='orange'
            product_string = str(site).upper() + product_count_label(len(wsrProducts))
            productList += product_status(color, product_string, str(hrdiff), utc_str)

        sect = "NEXRCOMP"
        request = DataAccessLayer.newDataRequest()
        request.setDatatype("satellite")
        request.setLocationNames(sect)
        nexrcompProducts = DataAccessLayer.getAvailableParameters(request)
        nexrcompProducts.sort()
        if not nexrcompProducts:
            productList += product_status('red', sect, 'None') + '</div></div></div>'
        else:
            request.setParameters(nexrcompProducts[0])
            utc = datetime.utcnow()
            times = DataAccessLayer.getAvailableTimes(request)

            utc_str = str(datetime.utcfromtimestamp(int(times[-1].getRefTime().getTime()/1000)))


            hourdiff = utc - datetime.strptime(str(times[-1]),'%Y-%m-%d %H:%M:%S')
            hours,days = hourdiff.seconds/3600,hourdiff.days
            minute = str((hourdiff.seconds - (3600 * hours)) / 60)
            offsetStr = ''
            if hours > 0:
                offsetStr += str(hours) + "hr "
            offsetStr += str(minute) + "min ago"
            if days > 1:
                offsetStr = str(days) + " days ago"
            color="green"
            if hours > 1:
                color="orange"

            product_string = sect + product_count_label(len(nexrcompProducts))

            productList += product_status(color, product_string, offsetStr, utc_str)



        # Satellite

        productList += """
                <tr>
                    <td colspan=3>
                        <h2 class="ui header">
                          <img src="/images/satellite.png" class="ui circular image">
                          Satellite Imagery
                        </h2>
                    </td>
                </tr>"""

        request = DataAccessLayer.newDataRequest()
        request.setDatatype("satellite")

        availableSectors = DataAccessLayer.getAvailableLocationNames(request)
        availableSectors.sort()
        availableSectors.remove('NEXRCOMP')

        for sect in availableSectors:
            request = DataAccessLayer.newDataRequest()
            request.setDatatype("satellite")
            request.setLocationNames(sect)
            availableProducts = DataAccessLayer.getAvailableParameters(request)
            availableProducts.sort()
            if not availableProducts:
                productList += product_status('red', sect, 'None')
            else:
                request.setParameters(availableProducts[0])
                utc = datetime.utcnow()
                times = DataAccessLayer.getAvailableTimes(request)
                utc_str = str(datetime.utcfromtimestamp(int(times[-1].getRefTime().getTime()/1000)))
                try:
                    hourdiff = utc - datetime.strptime(str(times[-1]),'%Y-%m-%d %H:%M:%S')
                except:
                    hourdiff = utc - datetime.strptime(str(times[-1]),'%Y-%m-%d %H:%M:%S.%f')
                hours,days = hourdiff.seconds/3600,hourdiff.days
                minute = str((hourdiff.seconds - (3600 * hours)) / 60)
                offsetStr = ''
                if hours > 0:
                    offsetStr += str(hours) + "hr "
                offsetStr += str(minute) + "min ago"
                if days > 1:
                    offsetStr = str(days) + " days ago"
                color="green"
                if hours > 4:
                    color="orange"

                product_string = sect + product_count_label(len(availableProducts))
                productList += product_status(color, product_string, offsetStr, utc_str)

        # GEOMETRIES

        ## Warnings

        product="Warnings"

        import numpy as np
        import cartopy.crs as ccrs
        from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
        from dynamicserialize.dstypes.com.raytheon.uf.common.time import TimeRange

        productList += """
                <tr>
                    <td colspan=3>
                        <h2 class="ui header">
                          <img src="/images/warning.png" class="ui circular image">
                          Geometries
                        </h2>
                    </td>
                </tr>"""

        request = DataAccessLayer.newDataRequest()
        request.setDatatype("warning")
        request.setParameters('act','countyheader', 'endtime','etn','floodbegin',
                              'floodcrest', 'floodend','floodrecordstatus',
                              'floodseverity', 'id', 'immediatecause', 'inserttime',
                              'issuetime', 'loc', 'locationid', 'motdir', 'motspd',
                              'overviewtext', 'phen', 'phensig', 'pil', 'productclass',
                              'purgetime', 'rawmessage', 'seg', 'segtext', 'sig',
                              'starttime', 'ugczones', 'vtecstr', 'wmoid', 'xxxid')

        beginRange = datetime.utcnow() - timedelta(hours=3)
        endRange = datetime.utcnow()
        timerange = TimeRange(beginRange, endRange)

        response = DataAccessLayer.getGeometryData(request, timerange)

        geometries=np.array([])
        for ob in response:
            geometries = np.append(geometries,ob.getGeometry())
            siteid = str(ob.getLocationName())
            period = ob.getDataTime().getValidPeriod()
            reftime = ob.getDataTime().getRefTime()

        if not response:
            productList += product_status('red', product, 'None')
        else:
            utc = datetime.utcnow()
            utc_str = datetime.strptime(str(reftime),'%Y-%m-%d %H:%M:%S.%f')
            try:
                hourdiff = utc - datetime.strptime(str(reftime),'%Y-%m-%d %H:%M:%S')
            except:
                hourdiff = utc - datetime.strptime(str(reftime),'%Y-%m-%d %H:%M:%S.%f')
            hours,days = hourdiff.seconds/3600,hourdiff.days
            minute = str((hourdiff.seconds - (3600 * hours)) / 60)
            offsetStr = ''
            if hours > 0:
                offsetStr += str(hours) + "hr "
            offsetStr += str(minute) + "min ago"
            if days > 1:
                offsetStr = str(days) + " days ago"
            color="green"
            if hours > 1:
                color="orange"

            product_string = product + " <div class='ui label mini'>" + str(len(response)) + " products (last 3 hr)</div>"
            productList += product_status(color, product_string, offsetStr, utc_str)









        productList += """</table></div>"""

        renderHtml = "<title>AWIPS Data Portal - Inventory</title>" + productList

        stringReturn = createpage(id,'','','',renderHtml,serverSelect,'')
        return stringReturn


    @cherrypy.expose
    def grid(self, name="", parm="", level="", title="Gridded Data"):

        from datetime import datetime
        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")

        # Grid Names
        available_grids = DataAccessLayer.getAvailableLocationNames(request)
        available_grids.sort()

        if name == "":
            DataAccessLayer.changeEDEXHost(server)
            productList = """<div class="ui divided list">"""

            gridnames=["NCWF","HRRR","GFS","NAM12","CMC","MRMS_0500","MRMS_1000"]

            request = DataAccessLayer.newDataRequest()
            request.setDatatype("grid")

            try:
                available_grids = DataAccessLayer.getAvailableLocationNames(request)
                available_grids.sort()
            except:
                content = "<div class='ui negative message'><p class='ui error red'>Could not connect to "+server+"</p></div>"
                stringReturn = createpage(id,'','','',content,serverSelect,'')
                return stringReturn

            if not available_grids:
                available_grids = gridnames

            mapJs = """<script type="text/javascript">
                        var createGeoJSON = function(){
                            getGeoJSONBounds('/polygons',function(response) {
                                var coveragePolygon = response.json;
                                var container = document.getElementById('datamap');
                                var jsonMap = dataMap.map({
                                    el: container,
                                    scrollWheelZoom: false,
                                    center: {lat: 40, lng: -105}
                                }).init();
                                for (var i = 0; i < coveragePolygon.length; i++) {
                                    var poly = JSON.parse(coveragePolygon[i]["st_asgeojson"]);
				    console.log(poly)
				    var polygon = [geoJsonPolygonFeature(poly)];
                                    jsonMap.drawPolygon(polygon);
				}
                            });
                    }
                </script>"""
            renderMap = """<div class="ui segment" id="datamap"></div>"""
            productList += """
                <h2 class="ui header">
                  <img src="/images/grid.png" class="ui circular image">
                  Gridded Data
                </h2>
                <div class="ui cards">
                    """
            for grid in available_grids:
                if not pattern.match(grid):
                    request.setLocationNames(grid)
                    cycles = DataAccessLayer.getAvailableTimes(request, True)
                    times = DataAccessLayer.getAvailableTimes(request)
                    if not cycles:
                        productList += ''
                    else:
                        utc_now  = datetime.utcnow()
                        utc_prod = datetime.utcfromtimestamp(int(cycles[-1].getRefTime().getTime()/1000))
                        utc_str = str(utc_prod)

                        ddiff = utc_now-utc_prod
                        hours = ddiff.seconds / 3600
                        days = ddiff.days
                        minute = str((ddiff.seconds - (3600 * hours)) / 60)
                        hrdiff = ''
                        if hours > 0:
                            hrdiff += str(hours) + " hr"
                        hrdiff += str(minute) + " min ago"
                        if days > 1:
                            hrdiff = str(days) + " days ago"
                        color="green"
                        if not days > 1:
                            productList += product_card('grid', str(grid), str(hrdiff), utc_str)


            productList += """</table></div>"""

            renderHtml = "<title>AWIPS Data Portal - "+ title +"</title>" + mapJs + renderMap + productList

            stringReturn = createpage(id,'','','',renderHtml,'','')
            return stringReturn








        import cartopy.crs as ccrs
        import matplotlib.pyplot as plt
        from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
        import numpy as np
	plt.switch_backend('agg')

        request.setLocationNames(name)

        # Grid Parameters
        availableParms = DataAccessLayer.getAvailableParameters(request)
        availableParms.sort()

        if len(availableParms) == 0:
            stringReturn = createpage(name,"","","",server+": no grid records found for "+name,"","")
            return stringReturn	
	
        if parm == "":
            request.setParameters(str(availableParms[0]))
        else:
            request.setParameters(str(parm))

        # Grid Levels
        availableLevels = DataAccessLayer.getAvailableLevels(request)
        availableLevels.sort()
        if level == "":
            request.setLevels(str(availableLevels[0]))
        else:
            request.setLevels(str(level))

        # Build Dropdowns

        parmBlock = ''
        parmTableHeader = """
            <table class="ui selectable single line table">
                <thead>
                    <tr>
                        <th>Grid Parameter</th>
                        <th>Description</th>
                        <th>Unit</th>
                        <th>API</th>
                    </tr>
                </thead>"""
        parmTable = parmTableHeader

        lvlString = ''

        gridSelect = """
            <div class="ui fluid search selection dropdown grid">
                <input type="hidden" id="grid-select" name="grid">
                <i class="dropdown icon"></i>
                <div class="default text">Select Grid</div>
                <div class="menu">"""

        for grid in available_grids:
            grid = grid.decode('utf-8')
            if not pattern.match(grid): gridSelect += '<div class="item" data-value="'+grid+'">'+grid+'</div>'

        gridSelect += """</div></div>"""

        parmMenu = ''
        parmSelect = """
                    <div class="ui fluid search selection dropdown parm">
                        <input type="hidden" id="parm-select" name="grid">
                        <i class="dropdown icon"></i>
                        <div class="default text">Parameter</div>
                        <div class="menu">"""

        for gridparm in availableParms:
            gridparm = gridparm.decode('utf-8')
            parmDescription = ''
            parmUnit = ''
            for item in parm_dict:
                idhash = hash(name + gridparm)
                replaced = re.sub('[0-9]{1,2}hr$', '', gridparm)
                if item == replaced:
                    parmDescription = parm_dict[item][0]
                    if len(parm_dict[item]) > 1:
                        parmUnit = parm_dict[item][1]
            parmSelect += '<div class="item" data-value="'+gridparm+'">'+gridparm+' - '+parmDescription+'</div>'
            parmActiveClass = ''
            if gridparm == parm:
                parmActiveClass = 'active'

            if parmDescription != "":
                parmMenu += '<a class="item %s" href="/grid?name=%s&parm=%s"><div class="small ui blue label">%s</div> %s</a>' % (parmActiveClass, name, gridparm,gridparm, parmDescription)



            if str(gridparm) == str(parm):

                parmBlock = '<tr><td><a href="/grid?name='+name+'&parm='+ gridparm +'"><b>' + gridparm + '</b></a></td>' \
                        '<td>' + parmDescription + '</td>' \
                        '<td><div class="small ui label">' + parmUnit + '</div></td>' \
                        '<td><a class="showcode circular ui icon basic button" name="'+str(idhash)+'" ' \
                                    'href="/json?name=' + name + '&parm=' + gridparm + '">' \
                                     '<i class="code icon small"></i></a></td></tr>'

                parmBlock = parmTableHeader + parmBlock + """
                        <tr id=""" + str(idhash) + """ class="transition">
                            <td colspan=5>
                                <div class="ui instructive bottom attached segment">
<pre class="code xml">request = DataAccessLayer.newDataRequest()
request.setDatatype("grid")
request.setLocationNames(\"""" + name + """\")
request.setParameters(\"""" + gridparm + """\")
levels = DataAccessLayer.getAvailableLevels(request)
request.setLevels(levels[0])</pre>
                                </div>
                            </td>
                        </tr>
                    </table>"""

            else:
                parmTable += '<tr><td><a href="/grid?name='+name+'&parm='+ gridparm +'"><b>' + gridparm + '</b></a></td>' \
                                '<td>' + parmDescription + '</td>' \
                                '<td><div class="small ui label">' + parmUnit + '</div></td>' \
                                '<td><a class="showcode circular ui icon basic button" name="'+str(idhash)+'" ' \
                                            'href="/json?name=' + name + '&parm=' + gridparm + '">' \
                                             '<i class="code icon small"></i></a></td></tr>'
                parmTable += """<tr id=""" + str(idhash) + """ class="transition hidden"><td colspan=5><div class="ui instructive bottom attached segment">
<pre class="code xml">request = DataAccessLayer.newDataRequest()
request.setDatatype("grid")
request.setLocationNames(\"""" + name + """\")
request.setParameters(\"""" + gridparm + """\")
levels = DataAccessLayer.getAvailableLevels(request)
request.setLevels(levels[0])</pre>
</div></td></tr>"""

        parmSelect += """</div></div>"""
        parmTable += '</table>'

        parmDescription = ''
        parmUnit = ''
        for item in parm_dict:
            replaced = re.sub('[0-9]{1,2}hr$', '', parm.decode('utf-8'))
            if item == replaced:
                parmDescription = parm_dict[item][0]
                parmUnit = parm_dict[item][1]

        levelSelect = """
                    <div class="ui fluid search selection dropdown level">
                        <input type="hidden" id="level-select" name="grid">
                        <i class="dropdown icon"></i>
                        <div class="default text">Level</div>
                        <div class="menu">"""

        for llevel in availableLevels:
            levelSelect += '<div class="item" data-value="'+str(llevel)+'">'+str(llevel)+'</div>'
        levelSelect += '</div></div>'

        if not parm: parmSelect = ''
        if not level: levelSelect = ''


        # Forecast Cycles
        cycles = DataAccessLayer.getAvailableTimes(request, True)
        times = DataAccessLayer.getAvailableTimes(request)
        latest_run = DataAccessLayer.getForecastRun(cycles[-1], times)

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

        if cycles:
            response = DataAccessLayer.getGridData(request, [latest_run[0]])
            grid = response[0]
            data = grid.getRawData()
            lons, lats = grid.getLatLonCoords()
            bbox = [lons.min(), lons.max(), lats.min(), lats.max()]

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



        # Last Run
        dateString = str(latest_run[0:1][0])[0:19]
        hourdiff = datetime.utcnow() - datetime.strptime(dateString, '%Y-%m-%d %H:%M:%S')
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
                grid_size = gridnav[1] + " x " + gridnav[2]
                grid_res = gridnav[3] +" " + gridnav[5]

        renderMap = ''
        mapJs = ''
        if parm:
            mapJs = """
                                getGeoJSONBounds('/polygon?name="""+ name + """',function(response) {
                                    var coveragePolygon = response.json;
                                    var container = document.getElementById('datamap');
                                    var polygon =  [geoJsonPolygonFeature(coveragePolygon)] ;
				    console.log(coveragePolygon);
			            console.log(polygon);
                                    var jsonMap = dataMap.map({
                                        el: container,
                                        scrollWheelZoom: false,
                                        center: {lat: 40, lng: -105}
                                    }).init().drawPolygon(polygon).zoomToBounds(polygon);
                                });"""
            renderMap = """
                        <div>
                            <div class="ui top attached tabular menu">
                              <a class="item active" data-tab="leaflet">Leaflet</a>
                              <a class="item" data-tab="cartopy">Cartopy</a>
                            </div>
                            <div class="ui bottom attached active tab segment" data-tab="leaflet">
                                <div class="ui segment" id="dsmap"></div>
                            </div>
                            <div class="ui bottom attached tab segment" data-tab="cartopy">
                                <div class="ui segment" id="pymap">"""+ cartopyImage +"""</div>
                            </div>
                        </div>"""

        renderHtml =  """<title>AWIPS Data Portal - """+ name +""" """+parm+""" Gridded Data</title>
                <script type="text/javascript">
                        var createGeoJSON = function(){
                        """ + mapJs + """
                    }
                </script>

                <div class="ui grid three column row">
                    <div class="left floated column"><h1>"""+ name + """</h1></div>
                 </div>
                <p>""" + centername[1] + """ &nbsp;<a class="ui tiny label" href="#">""" + centername[0] + """</a></p>

                """+ parmBlock + renderMap + parmTable


        sideContent = """

                <div class="ui raised segment small">
                    <a class="ui top right attached label">Grid Info</a>

                    """+ gridSelect + parmSelect + levelSelect +"""

                    <div class="ui middle aligned list">
                    <div class="item"><b>Last Run</b>
                        <div class="right floated content">"""+ dateString +"""</div>
                    </div>
                    </div>

                    <h5 class="ui horizontal header divider">
                      <i class="world icon"></i>Projection
                    </h5>

                    <div class="ui middle aligned divided list">
                        <p>""" + gridnav[0] + """</p>
                        <div class="item"><b>Source</b>
                            <div class="right floated content"><a href="#">""" + centername[0] + """</a></div>
                        </div>
                        <div class="item"><b>Center ID</b>
                            <div class="right floated content">""" + centerid + """</div>
                        </div>
                        <div class="item"><b>Subcenter</b>
                            <div class="right floated content">""" + subcenterid + """</div>
                        </div>
                        <div class="item"><b>Grid Number</b>
                            <div class="right floated content">""" + gridid + """</div>
                        </div>
                        <div class="item"><b>Resolution</b>
                            <div class="right floated content">""" + grid_res + """</div>
                        </div>
                        <div class="item"><b>Size</b>
                            <div class="right floated content">""" + grid_size + """</div>
                        </div>
                    </div>
                </div>
		<div class="ui segment" id="datamap"></div>
            """

        stringReturn = createpage(name,parm,str(level),str(latest_run[0]),renderHtml,sideContent, parmMenu)
        return stringReturn



    ##
    ## DERIVED PARAMETERS ALL GRIDS
    ##

    @cherrypy.expose
    def derived(self, title="Derived Parameters"):
        from datetime import datetime
        import numpy as np
        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")
        availableParms = DataAccessLayer.getAvailableParameters(request)
        availableParms.sort()
        parmTable = """
            <table class="ui selectable single line table">
                <thead>
                    <tr>
                        <th>Grid Parameter</th>
                        <th>Description</th>
                        <th>Unit</th>
                    </tr>
                </thead>"""
        for gridparm in availableParms:
            gridparm = gridparm.decode('utf-8')
            parmDescription = ''
            parmUnit = ''
            for item in parm_dict:
                idhash = hash(gridparm)
                replaced = re.sub('[0-9]{1,2}hr$', '', gridparm)
                if item == replaced:
                    parmDescription = parm_dict[item][0]
                    if len(parm_dict[item]) > 1:
                        parmUnit = parm_dict[item][1]
            if parmDescription == "":
                parmTable += """
                        <tr>
                            <td>
                                <b>""" + gridparm + """</b>
                            </td>
                            <td>""" + parmDescription + """</td>
                            <td><div class="small ui label">""" + parmUnit + """</div></td>
                        </tr>"""
        parmTable += "</table>"
        renderHtml =  """
                <title>AWIPS Data Portal - """+ title + """</title>
                <h1>"""+ title + """</h1>"""+ parmTable
        stringReturn = createpage('','','','',renderHtml,'','')
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
        if level == "": level = availableLevels[0]
        request.setLevels(level)
        cycles = DataAccessLayer.getAvailableTimes(request, True)
        times = DataAccessLayer.getAvailableTimes(request)
        fcstRun = DataAccessLayer.getForecastRun(cycles[-1], times)
        response = DataAccessLayer.getGridData(request, [fcstRun[0]])
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

        if level == "":
            availableLevels = DataAccessLayer.getAvailableLevels(request)
            availableLevels.sort()
            level = availableLevels[0]
            level = str(level)
            request.setLevels(level)

        cycles = DataAccessLayer.getAvailableTimes(request, True)
        times = DataAccessLayer.getAvailableTimes(request)
        fcstRun = DataAccessLayer.getForecastRun(cycles[-1], times)
        response = DataAccessLayer.getGridData(request, [fcstRun[0]])

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
    def polygons(self):
        import psycopg2
        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")
        available_grids = DataAccessLayer.getAvailableLocationNames(request)
        if not available_grids:
            available_grids = ["NCWF","HRRR","GFS","NAM12","CMC","MRMS_0500","MRMS_1000"]
        my_query = query_db("SELECT ST_AsGeoJSON(the_geom)::text from gridcoverage where id in "
                        "(select distinct location_id from grid_info where datasetid in ('NCWF','HRRR','NAM12','MRMS_1000'));")
	json_output = json.dumps(my_query)
        dataset = list(json_output)
        return dataset

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
        response = DataAccessLayer.getGridData(request, [fcstRun[0]])
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
    def geojson(self, name="RAP13", parm="T", level="0.0SFC", server="edex-cloud.unidata.ucar.edu"):
        import cartopy.crs as ccrs
        import matplotlib.pyplot as plt
        from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
        import numpy as np

        plt.switch_backend('agg')

        DataAccessLayer.changeEDEXHost(server)
        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")
        request.setLocationNames(name)
        request.setParameters(parm)
        request.setLevels(str(level))

        cycles = DataAccessLayer.getAvailableTimes(request, True)
        times = DataAccessLayer.getAvailableTimes(request)

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

        if cycles:
            fcstRun = DataAccessLayer.getForecastRun(cycles[-1], times)
            response = DataAccessLayer.getGridData(request, [fcstRun[0]])
            grid = response[0]
            data = grid.getRawData()
            lons, lats = grid.getLatLonCoords()
            bbox = [lons.min(), lons.max(), lats.min(), lats.max()]

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
               response = DataAccessLayer.getGridData(request, [fcstRun[0]])
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
        response = DataAccessLayer.getGridData(request, [fcstRun[0]])
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
    def parm(self, parm="", level="", title="Parameters"):
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
                        '<tr><th>Parameter</th><th>Description</th><th>Unit</th><th>Level</th><th>API</th></tr>' \
                        '</thead>'
                request.setLocationNames(grid)
                availableLevels = DataAccessLayer.getAvailableLevels(request)
                availableLevels.sort()
                for llevel in availableLevels:
                    lcount += 1
                    for litem in level_dict:
                        lreplaced = re.sub('^[0-9|\.|\_]+', '', str(llevel))
                        levelDesc = ''
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
                    gridString += """<tr id=""""+str(idhash)+"""" class="transition hidden"><td colspan=5><div class="ui instructive bottom attached segment"><pre><code id="code"""+str(idhash)+"""" class="code xml">request = DataAccessLayer.newDataRequest()
request.setDatatype("grid")
request.setLocationNames(""""+grid+"""")
request.setParameters(""""+parm+"""")
request.setLevels(""""+str(llevel)+"""")
</code></pre></div></td></tr>"""

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
    # See templates/page.html
    tmpl = env.get_template('page.html')
    return tmpl.render(name=name,
                       parmname=parmname,
                       level=level,
                       time=time,
                       mainContent=mainContent,
                       sideContent=sideContent,
                       parmlist=parmlist
                       )


def product_status(color='black', product='', time='', utc=''):
    icon=''
    if color in ('red','orange'):
        icon=" <i class='attention icon'></i>"
    return """
          <tr><td>
            <div class="item">
              <div class="content">
                """+ product + """
              </div>
            </div>
          </td>
          <td>
             <span style="color:"""+color+""";">"""+ time + icon +"""</span>
          </td>
          <td>
             <div class="small">""" + str(utc) + """</div>
          </td></tr>
            """

def product_card(type='grid', product='', time='', utc=''):
    #icon='<img class="right floated mini ui circular image" src="/images/'+type+'.png">'
    icon=''

    for gname, info in grid_dictionary.iteritems():
        print gname, info
        if gname == product:
            centerid = info[0]
            subcenterid = info[1]
            gridid = info[2]
            centername = wmo_centers[centerid]
            gridnav = navigation[gridid]
            print gridnav
            grid_size = gridnav[1] + "x" + gridnav[2]
            grid_res = gridnav[3] +" " + gridnav[5]


    product = '<a href="/'+type+'?name='+product+'">'+product+'</a>'

    return """
          <div class="card">
              <div class="content">
                """+ icon +"""
                <div class="header">
                  """+ product +"""
                </div>
                <div class="meta">
                  """ + str(utc) + """
                </div>
                <div class="description">

                            <p class="mini">""" + gridnav[0] + """</p>
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
           </div>
          """


def product_count_label(count=0):
    if count > 1:
        return " <div class='ui label mini'>" + str(count) + " products</div>"
    else:
        return " <div class='ui label mini'>" + str(count) + " product</div>"


def db():
    return psycopg2.connect("dbname = 'metadata' user = 'awips' host = 'localhost' password='awips'")

def query_db(query, args=(), one=False):
    cur = db().cursor()
    cur.execute(query, args)
    r = [dict((cur.description[i][0], value) \
               for i, value in enumerate(row)) for row in cur.fetchall()]
    cur.connection.close()
    return (r[0] if r else None) if one else r





# http://stackoverflow.com/a/1267145/5191979
def RepresentsInt(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


if __name__ == '__main__':

    server="edex-cloud.unidata.ucar.edu"
    #server="149.165.157.49"

    env = Environment(loader=FileSystemLoader('templates'))

    # exclude list
    pattern = re.compile("^((ECMF|UKMET|MPE|FFG|GribModel|HFR|EPAC40))")

    DataAccessLayer.changeEDEXHost(server)

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

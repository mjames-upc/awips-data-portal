import sys, os, cStringIO
import psycopg2
import json
import geojson
import datetime
import cherrypy
from awips.dataaccess import DataAccessLayer
import matplotlib.tri as mtri
import matplotlib.pyplot as plt
import matplotlib
import cartopy.crs as ccrs
import numpy as np
import re
from parms import parm_dict, level_dict, grid_dictionary, navigation, nws_subcenters, wmo_centers, ncep_subcenters
import binascii, struct

class Edex:


    def hash(s):
        return binascii.b2a_base64(struct.pack('i', hash(s)))

    @cherrypy.expose
    def json(self, name="", parm="", level="",time=""):

        #
        # Need point query results for time-series
        # Cross-sections
        # Time-height
        # Var vs. Height
        #

        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")
        if name != "": request.setLocationNames(name)
        if parm != "": request.setParameters(parm)
        if level != "": request.setLevels(level)
        cycles = DataAccessLayer.getAvailableTimes(request, True)
        t = DataAccessLayer.getAvailableTimes(request)
        fcstRun = []
        #for time in t:
        #    if str(time)[:19] == str(cycles[-1]):
        #        fcstRun.append(time)
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
    def index(self):

        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")
        # Grid names
        available_grids = DataAccessLayer.getAvailableLocationNames(request)
        available_grids.sort()
        # Grid parameters
        availableParms = DataAccessLayer.getAvailableParameters(request)
        availableParms.sort()

        # Build dropdowns
        lvlString = ''
        gridSelect = """
        <h1>AWIPS Forecast & Analysis Grids</h1>
        <div class="ui search">
          <div class="ui icon input">
            <input class="prompt" type="text" placeholder="Search parameters...">
            <i class="search icon"></i>
          </div>
          <div class="results"></div>
        </div>
        """
        gridCards = '<div class="ui link cards">'
        gridMenu = ''
        for grid in available_grids:

            for gname, info in grid_dictionary.iteritems():
                if gname == grid:
                    centerid = info[0]
                    subcenterid = info[1]
                    gridid = info[2]
                    centername = wmo_centers[centerid]
                    gridnav = navigation[gridid]
                    # '216': ['grid over Alaska (polar stereographic)', '139', '107', '45.0', '45.0', 'km'],
                    grid_size = gridnav[1] + "x" + gridnav[2]
                    grid_res = str(round(float(gridnav[3]),2)) + " " + gridnav[5]

            if not pattern.match(grid):
                gridMenu += """<a class="item" href="/grid?name="""+ grid +"""">"""+ grid +"""</a>"""
                gridCards += """<div class="card">
                                    <div class="image"></div>
                                    <div class="content">
                                        <div class="header"><a href="/grid?name="""+ grid +"""">"""+ grid +"""</a></div>
                                        <div class="meta">""" + gridnav[0] + """</div>
                                        <div class="description">""" + centername[1] + """ (""" + centername[0] + """)</div>
                                    </div>
                                    <div class="extra content">
                                      <span class="right floated">""" + grid_size + """</span>
                                      <span>
                                        """ + grid_res + """ resolution
                                      </span>
                                    </div>
                                </div>


                                """





        parameter_content = 'var parameter_content = ['
        previous = ''
        for gridparm in availableParms:
            for item in parm_dict:
                replaced = re.sub('[0-9]{1,2}hr', '', gridparm)
                if item == replaced and replaced <> previous:
                    previous = replaced
                    parmDescription = parm_dict[item][0]
                    parameter_content += "{ name: '"+replaced+"', title: '"+replaced+" - "+parmDescription+"'},"
        gridCards += '</div>'
        parameter_content += '];'
        renderHtml = gridSelect + gridCards
        sideContent = ''

        stringReturn = createpage("", "", "", "",renderHtml,sideContent,parameter_content,gridMenu)
        return stringReturn


    @cherrypy.expose
    def grid(self, name="RAP40", parm="", level=""):
        conn = None
        coverage = ''

        try:
            conn = psycopg2.connect("dbname = 'metadata' user = 'awips' host = 'localhost' password='awips'")
            cur = conn.cursor()
            cur.execute("select * from gridcoverage where id = "
                        "(select distinct location_id from grid_info where datasetid = '" + name + "');")
            columns = (
                'dtype', 'id', 'crs', 'dx', 'dy', 'firstgridpointcorner', 'the_geom',
                'la1', 'lo1', 'name', 'nx', 'ny', 'spacingunit', 'latin1', 'latin2', 'lov',
                'majoraxis', 'minoraxis', 'la2', 'latin', 'lo2', 'lad'
            )
            results = []
            for row in cur.fetchall():
                results.append(dict(zip(columns, row)))
            coverage += json.dumps(results, indent=2)
            # coverage = ''
            # for res in results:
            #    coverage =+ res
        except psycopg2.DatabaseError, ex:
            print 'I am unable to connect the database: ' + str(ex)
            #sys.exit(1)



        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")
        # Grid names
        available_grids = DataAccessLayer.getAvailableLocationNames(request)
        available_grids.sort()
        request.setLocationNames(name)
        # Grid parameters
        availableParms = DataAccessLayer.getAvailableParameters(request)
        availableParms.sort()
        if parm == "": parm = availableParms[-1]
        request.setParameters(parm)
        # Grid levels
        availableLevels = DataAccessLayer.getAvailableLevels(request)
        availableLevels.sort()

        if level == "": level = availableLevels[-1]
        request.setLevels(level)

        # Build dropdowns

        parmString = '<table class="ui single line table"><thead><tr><th>Parameter</th><th>Description</th><th>Unit</th><th>DAF</th></tr></thead>'
        lvlString = ''
        #gridSelect = '<div class=""><select class="ui select dropdown" id="gridSelect">'
        #for grid in available_grids:
        #    if not pattern.match(grid): gridSelect += '<option value="%s">%s</option>' % (grid, grid)
        #gridSelect += '</select></div>'
        parmMenu = ''
        parmSelect = '<div class=""><select class="ui select dropdown" id="parmSelect">'
        for gridparm in availableParms:
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

        parmSelect += '</select></div>'

        parmString += '</table>'

        parmDescription = ''
        parmUnit = ''
        for item in parm_dict:
            replaced = re.sub('[0-9]{1,2}hr$', '', parm)
            if item == replaced:
                parmDescription = parm_dict[item][0]
                parmUnit = parm_dict[item][1]

        levelSelect = '<div class=""><select class="ui select dropdown" id="levelSelect">'
        for llevel in availableLevels:
            levelSelect += '<option value="%s">%s</option>' % (llevel, llevel)
        levelSelect += '</select></div>'

        # Forecast Cycles
        cycles = DataAccessLayer.getAvailableTimes(request, True)
        times = DataAccessLayer.getAvailableTimes(request)
        latest_run = DataAccessLayer.getForecastCycle(cycles[-1], times)

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

        # CREATE IMAGE
        import scipy.ndimage
        gridImage = ''
        showImg = True


        #import folium
        #map = folium.Map(location=[35, -100],
        #                     tiles='Mapbox Bright', zoom_start=2)
        # folium.GeoJson(open('antarctic_ice_edge.json'),
        #                name='geojson'
        #                ).add_to(map)
        #
        # folium.TopoJson(open('antarctic_ice_shelf_topo.json'),
        #                 'objects.antarctic_ice_shelf',
        #                 name='topojson',
        #                 ).add_to(map)
        #folium.LayerControl().add_to(map)
        #map.save('map.html')
        #import codecs
        #f = codecs.open("map.html", 'r')
        #mapImage = f.read()
        from math import isinf

        if showImg:
            if len(latest_run) != 0:
            # Request, receive, and interpolate grid
                response = DataAccessLayer.getGridData(request, latest_run[0:1])
                grid = response[0]
                data = grid.getRawData()
                lons, lats = grid.getLatLonCoords()
                if data.shape[1] > 500:
                    factor = 151. / data.shape[1]
                    data = scipy.ndimage.zoom(data, factor, order=0)
                    lons = scipy.ndimage.zoom(lons, factor, order=0)
                    lats = scipy.ndimage.zoom(lats, factor, order=0)
                ngrid = data.shape[1]
                gridSize = str(data.shape[0]) + "x" + str(data.shape[1])
                gridUnit = str(grid.getUnit())

            # Turn off mpl interpolation (takes too long with high res grids)
            if name != "":
                rlons = np.repeat(np.linspace(np.min(lons), np.max(lons), ngrid),
                              ngrid).reshape(ngrid, ngrid)
                rlats = np.repeat(np.linspace(np.min(lats), np.max(lats), ngrid),
                              ngrid).reshape(ngrid, ngrid).T
                tli = mtri.LinearTriInterpolator(mtri.Triangulation(lons.flatten(),
                                                   lats.flatten()), data.flatten())
                rdata = tli(rlons, rlats)
                # Create Map
                cmap = plt.get_cmap('rainbow')
                matplotlib.rcParams.update({'font.size': 8})
                plt.figure(figsize=(6, 4), dpi=100)
                ax = plt.axes(projection=ccrs.PlateCarree())
                #maxValue = rdata.min()
                maxValue = rdata.max()
                #if rdata.min() > 9999:
                #    maxValue = 100
                minValue = rdata.min()

                cs = plt.contourf(rlons, rlats, rdata, 60, cmap=cmap,
                              transform=ccrs.PlateCarree(),
                              vmin=minValue, vmax=maxValue)
                ax.gridlines()
                ax.coastlines()
                ax.set_aspect('auto', adjustable=None)
                cbar = plt.colorbar(orientation='horizontal')
                cbar.set_label(name +" "+ grid.getLevel() + " " + parmDescription + " "  + grid.getParameter() + " " \
                        "(" + grid.getUnit() + ") " + " valid " + str(grid.getDataTime().getRefTime()) )
                # Write image to stream
                format = "png"
                sio = cStringIO.StringIO()
                plt.savefig(sio, format=format,bbox_inches='tight')
                print "Content-Type: image/%s\n" % format
                sys.stdout.write(sio.getvalue())
                gridImage = '<img style="border: 0;" src="data:image/png;base64,'+sio.getvalue().encode("base64").strip()+'"/>'

        if not showImg:
            gridSize = ''
            gridUnit = ''

        renderDetails = ''

        # 'GFS': ['7', '0', '193'],
        for gname, info in grid_dictionary.iteritems():
            if gname == name:
                centerid = info[0]
                subcenterid = info[1]
                gridid = info[2]
                centername = wmo_centers[centerid]
                gridnav = navigation[gridid]
                # '216': ['grid over Alaska (polar stereographic)', '139', '107', '45.0', '45.0', 'km'],
                grid_size = gridnav[1] + "x" + gridnav[2]
                grid_res = gridnav[3] +" " + gridnav[5]

        renderHtml =  """
                <h1>"""+ name + """</h1>
                <p>""" + centername[1] + """ &nbsp;<a class="ui mini label" href="#">""" + centername[0] + """</a></p>


                <p><b>Last run:</b> """+ dateString + """ (""" + hourdiff + """)</p>

                <div class="ui divider"></div>

                <div class="ui two column grid">
                    <div class="eight wide column align right">
                        """+ levelSelect +"""
                    </div>
                    <div class="eight wide column align right">
                        """+ parmSelect +"""
                    </div>
                </div>

                <div class="sixteen wide column middle aligned">
                    """ + gridImage + """
                </div>

                <!--<div><h3>Grid Projection</h3><pre class="small">coverage = """+coverage +"""</pre></div>-->
                <h3 class="first">"""+name+""" Grid Parameters</h3>
                <div>"""+ parmString +"""</div>"""



        sideContent = """
                <div class="ui raised segment">

                    <a class="ui right ribbon label">Projection</a>
                    <div class="ui middle aligned divided list">
                        <p>""" + gridnav[0] + """</p>
                        <div class="item"><b>Grid size</b><div class="right floated content">""" + grid_size + """</div></div>
                        <div class="item"><b>Resolution</b><div class="right floated content">""" + grid_res + """</div></div>
                        <div class="item"><b>Center ID</b><div class="right floated content">""" + centerid + """</div></div>
                        <div class="item"><b>Subcenter ID</b><div class="right floated content">""" + subcenterid + """</div></div>
                        <div class="item"><b>Grid Number</b>
                            <div class="right floated content">
                                <div class="ui" data-tooltip='"""+coverage+"""' data-position="top right" data-title='"""+name+"""'>
                                """ + gridid + """
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            """

        parameter_content = 'var parameter_content = [];'
        stringReturn = createpage(name,parm,str(level),str(latest_run[0]),renderHtml,sideContent,parameter_content, parmMenu)
        return stringReturn

    @cherrypy.expose
    def parm(self, name="", parm="", level=""):
        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")
        availableParms = DataAccessLayer.getAvailableParameters(request)
        availableParms.sort()
        request.setParameters(parm)
        parmDescription = ''
        parmUnit = ''
        for item in parm_dict:
            replaced = re.sub('[0-9]{1,2}hr$', '', parm)
            if item == replaced:
                parmDescription = parm
                parmDescription = parm_dict[item][0]
                parmUnit = parm_dict[item][1]

        # Grid names
        available_grids = DataAccessLayer.getAvailableLocationNames(request)
        available_grids.sort()
        parmSearch = """
                <h1>AWIPS Forecast & Analysis Grids</h1>
                <div class="ui search">
                  <div class="ui icon input">
                    <input class="prompt" type="text" placeholder="Search parameters...">
                    <i class="search icon"></i>
                  </div>
                  <div class="results"></div>
                </div>
                """
        gridString = ''
        for grid in available_grids:
            if not pattern.match(grid):
                gridString += '<h3><a href="/grid?name='+grid+'">'+grid+'</a></h3>'\
                        '<table class="ui single line table"><thead>' \
                        '<tr><th>Parameter</th><th>Description</th><th>Unit</th><th>Level</th><th>DAF</th></tr>' \
                        '</thead>'
                request.setLocationNames(grid)
                availableLevels = DataAccessLayer.getAvailableLevels(request)
                availableLevels.sort()
                for llevel in availableLevels:
                    for litem in level_dict:
                        lreplaced = re.sub('^[0-9|\.|\_]+', '', str(llevel))
                        if str(litem) == lreplaced:
                            levelDesc = level_dict[litem][0]
                    idhash = hash(grid+parm+str(llevel))
                    gridString += '<tr><td><a href="/grid?name=' + grid + '&parm=' + parm + '">' + parm + '</a></td>' \
                            '<td> ' + parmDescription + '</td>' \
                            '<td>'+ parmUnit +'</td>' \
                            '<td><div class="small ui label" data-tooltip="' + levelDesc + '">' + str(llevel) +'</div></td>' \
                            '<td><a class="showcode circular ui icon basic button" name="'+str(idhash)+'" ' \
                            'href="/json?name=' + grid + '&parm=' + parm + '&level=' + str(llevel) + '">' \
                             '<i class="code icon small"></i></a></td></tr>'


                    gridString += '''<tr id="'''+str(idhash)+'''" class="transition hidden"><td colspan=5><div class="ui instructive bottom attached segment"><pre><code class="code xml">request = DataAccessLayer.newDataRequest()
request.setDatatype("grid")
request.setLocationNames("'''+grid+'''")
request.setParameters("'''+parm+'''")
request.setLevels("'''+str(llevel)+'''")
</code></pre></div></td></tr>'''

                gridString += '</table>'

        # Build dropdowns
        # lvlString = ''
        # renderHtml = '<div class=""><select class="ui select dropdown" id="gridSelect">'
        # for grid in available_grids:
        #     if not pattern.match(grid): renderHtml += '<option value="%s">%s</option>' % (grid, grid)
        # renderHtml += '</select></div>'
        #
        # renderHtml += '<div class=""><select class="ui select dropdown" id="levelSelect">'
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
        # renderHtml += '<div class="ui one column grid"><div class="ten wide column"><div><select class="ui select dropdown" id="cycleSelect">'
        # for time in fcstRun:
        #     renderHtml += '<option value="%s">%s</option>' % (time, time)
        # renderHtml += '</select></div><br><Br>'


        parameter_content = 'var parameter_content = ['
        previous = ''
        for gridparm in availableParms:
            for item in parm_dict:
                replaced = re.sub('[0-9]{1,2}hr', '', gridparm)
                if item == replaced and replaced <> previous:
                    previous = replaced
                    parmDescription = parm_dict[item][0]
                    parameter_content += "{ name: '" + replaced + "', title: '" + replaced + " - " + parmDescription + "'},"
        parameter_content += '];'

        renderHtml = parmSearch + '<h1 class="ui dividing header">' + parm + ' - ' + parmDescription + ' (' + parmUnit + ')</h1>' \
                     + '<p>' + gridString + '</p></div></div>'

        sideContent = ''
        parmlist = ''
        stringReturn = createpage(name,parm,str(level),"",renderHtml,sideContent,parameter_content, parmlist)
        return stringReturn


def createpage(name, parm, level, time, mainContent, sideContent, parameter_content, parmlist):



    return """
        <html>
            <head>
                <script type="text/javascript" src="/js/jquery-1.11.3.min.js"></script>
                <link rel="stylesheet" type="text/css" href="/css/semantic.min.css">
                <link rel="stylesheet" type="text/css" href="/css/style.css">
                <script src="/js/semantic.min.js"></script>
                <script src="/js/leaflet.js"></script>
                <script type="text/javascript">
                    """+ parameter_content +"""
                    $(document).ready(function(){
                    /*
                        var mymap = L.map('mapid').setView([51.505, -0.09], 13);

                        L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpandmbXliNDBjZWd2M2x6bDk3c2ZtOTkifQ._QA7i5Mpkd_m30IGElHziw', {
                            maxZoom: 18,
                            attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, ' +
                                '<a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>',
                                id: 'mapbox.streets'
                            }).addTo(mymap);
                        var bounds = [[54.559322, -5.767822], [56.1210604, -3.021240]];
                        L.rectangle(bounds, {color: "#ff7800", weight: 1}).addTo(map);
                        map.fitBounds(bounds);
                    */
                        $('#gridSelect').val('""" + name + """');
                        $('#parmSelect').val('""" + parm + """');
                        $('#levelSelect').val('""" + level + """');
                        $('#cycleSelect').val('""" + time + """');
                        $('.ui.search')
                            .search({
                            source: parameter_content,
                            minCharacters:3,
                            maxResults: 20,
                            onSelect: function(result,response) {
                                console.log(result.name);
                                window.location.href='/parm?parm='+result.name;
                            }

                            })
                        ;
                        $('.select')
                          .dropdown()
                        ;
                        $('.showcode').on('click', function(){
                            divname = '#'+$(this).attr("name")
                            $(divname).transition('fade down');
                            return false;
                        });
                        $("#gridSelect").change(function () {
                            location.href = "/grid?name=" + $(this).val();
                        });
                        $("#parmSelect").change(function () {
                            location.href = "/grid?name="""+name+"""&parm=" + $(this).val();
                        });
                        $("#levelSelect").change(function () {
                            location.href = "/grid?name=""" + name + """&parm=""" + parm + """&level=" + $(this).val();
                        });
                    });
                </script>
            </head>
            <body class="">

                <div class="ui sidebar inverted visible vertical left menu" style="width: 200px !important; height: 1813px !important; margin-top: 0px; left: 0px;">
                    <a class="item header" href="/">
                      <b>AWIPS Data Access</b>
                    </a>
                    <div class="item">
                        <a href="/grid?name="""+ name +""""><div class="header">""" + name + """</div></a>
                        <div class="menu">
                            """ + parmlist + """
                        </div>
                    </div>
                </div>
                <div class="pusher">
                    <div class="ui two column grid">
                        <div class="nine wide column">
                        %s
                        </div>
                        <div class="three wide column">
                        %s
                        </div>
                    </div>
                </div>

            </body>

        </html>
            """ % ( mainContent, sideContent )

if __name__ == '__main__':
    pattern = re.compile("^((ECMF|UKMET|QPE|MPE|FFG|GribModel|HFR|RFCqpf|ESTOFS|ETSS|GFSGuide|estofs|EPAC40))")
    DataAccessLayer.changeEDEXHost("edex.unidata.ucar.edu")
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
        }
    }
    #cherrypy.config.update(server_config)


    cherrypy.quickstart(Edex(), '/', config=server_config)

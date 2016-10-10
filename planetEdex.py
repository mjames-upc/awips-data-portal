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
from parms import parm_dict
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

        pattern = re.compile("^((ECMF|UKMET|QPE|MPE|FFG|GribModel|HFR))")

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

        for grid in available_grids:
            if not pattern.match(grid):
                gridCards += """<div class="card">
                                    <div class="image"></div>
                                    <div class="content">
                                        <div class="header"><a href="/grid?name=%s">%s</a></div>
                                        <div class="meta">Meta</div>
                                        <div class="description">Description</div>
                                    </div>
                                    <div class="extra content">
                                      <span class="right floated">
                                        Len by Width
                                      </span>
                                      <span>
                                        <i class="user icon"></i>
                                        75 parameters
                                      </span>
                                    </div>
                                </div>""" % (grid, grid)
        #gridSelect += '<div class=""><select class="ui select dropdown" id="parmSelect">'
        parameter_content = 'var parameter_content = ['
        parmDescription = ''

        previous = ''
        for gridparm in availableParms:
            for item in parm_dict:
                replaced = re.sub('[0-9]{1,2}hr', '', gridparm)
                if item == replaced and replaced <> previous:
                    previous = replaced
                    parmDescription = parm_dict[item][0]
                    parameter_content += "{ name: '"+replaced+"', title: '"+replaced+" - "+parmDescription+"'},"
                    #gridSelect += '<option value="%s">%s - %s</option>' % (replaced, replaced, parmDescription)
        #gridSelect += '</select></div>'
        gridCards += '</div>'
        parameter_content += '];'

        stringReturn = createpage("", "", "", "", gridSelect + gridCards,parameter_content)
        return stringReturn


    @cherrypy.expose
    def grid(self, name="RAP40", parm="", level=""):
        conn = None
        try:
            conn = psycopg2.connect("dbname = 'metadata' user = 'awips' host = 'localhost' password='awips'")
        except psycopg2.DatabaseError, ex:
            print 'I am unable to connect the database: ' + str(ex)
            sys.exit(1)

        cur = conn.cursor()
        cur.execute("select * from gridcoverage where id = "
                    "(select distinct location_id from grid_info where datasetid = '"+name+"');")
        columns = (
        'dtype', 'id', 'crs', 'dx', 'dy', 'firstgridpointcorner', 'the_geom',
        'la1','lo1','name','nx','ny','spacingunit','latin1','latin2','lov',
        'majoraxis','minoraxis','la2','latin','lo2', 'lad'
        )
        coverage = '<h1>Hey look, we can query postgres and dump to json...</h1>'
        results = []
        for row in cur.fetchall():
            results.append(dict(zip(columns, row)))
        coverage += json.dumps(results, indent=2)
        #coverage = ''
        #for res in results:
        #    coverage =+ res


        pattern = re.compile("^((ECMF|UKMET|QPE|MPE|FFG|GribModel|RFCqpf))")

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

        parmString = '<table class="ui single line table"><thead><tr><th>Parameter</th><th>Description</th><th>Unit</th><th>API</th></tr></thead>'
        lvlString = ''
        #gridSelect = '<div class=""><select class="ui select dropdown" id="gridSelect">'
        #for grid in available_grids:
        #    if not pattern.match(grid): gridSelect += '<option value="%s">%s</option>' % (grid, grid)
        #gridSelect += '</select></div>'

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
            parmString += '<tr><td><a href="/parm?parm='+ gridparm +'"><b>' + gridparm + '</b></a></td>' \
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
        latest_run = DataAccessLayer.getForecastRun(cycles[-1], times)

        dateString = str(latest_run[0:1][0])[0:19]
        hourdiff = datetime.datetime.utcnow() - datetime.datetime.strptime(dateString, '%Y-%m-%d %H:%M:%S')
        hour = hourdiff.seconds / 3600  # integer
        minute = str((hourdiff.seconds - (3600 * hour)) / 60)


        hourdiff = ''
        if hour > 0:
            hourdiff += str(hour) + "hr "
        hourdiff += str(minute) + "m ago"
        if hour > 24:
            days = hour / 24
            hourdiff = str(days) + " days ago"

        #hourdiff = str(int(round((datetime.datetime.utcnow() - datetime.datetime.strptime(dateString,
        #                                                                              '%Y-%m-%d %H:%M:%S')).total_seconds() / 60)))

        #hourdiff = datetime.datetime.utcnow() - datetime.datetime.strptime(dateString,'%Y-%m-%d %H:%M:%S')

        #cycleSelect = '<div class=""><select class="ui select dropdown" id="cycleSelect">'
        #for time in latest_run:
        #    cycleSelect += '<option value="%s">%s</option>' % (time, time)
        #cycleSelect += '</select></div><br><Br>'

        # CREATE IMAGE
        import scipy.ndimage
        gridImage = ''
        showImg = True

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
                cs = plt.contourf(rlons, rlats, rdata, 60, cmap=cmap,
                              transform=ccrs.PlateCarree(),
                              vmin=rdata.min(), vmax=rdata.max())
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
                # If we want to show all cycles/fcst hours
                #cycleTime = t[-1].getRefTime().getTime()/1000.0
                #fsctTime = t[-1].getValidPeriod()
                #showString = str(datetime.datetime.fromtimestamp(cycleTime).strftime('%Y-%m-%d %H%M')+" UTC")
                #linkString = str(datetime.datetime.fromtimestamp(cycleTime).strftime('%Y%m%d%H%M'))

        renderHtml =  """
<div class="ui grid">
  <div class="six wide column"><h1>"""+ name + """</h1>
    <p><b>Last run:</b> """+ dateString + """ (""" + hourdiff + """)</p>
    <p><b>Grid size:</b> """+ str(data.shape[0]) + "x" + str(data.shape[1]) +"""</p>
  </div>
  <div class="six wide column align right">"""+ parmSelect +"""
                 """+ levelSelect +"""</div>
</div>


<div class="ui grid">
  <div class="twelve wide column middle aligned">""" + gridImage + """</div>
</div>
                <pre class="small">"""+coverage +"""</pre>
                <h3 class="first">Grid Parameters</h3><p>"""+ parmString +"""</p>
                <h3 class="first">Grid Levels</h3><p><small>"""+ lvlString +"""</small></p>
                <p>Unit: """+ grid.getUnit() +"""</p>
                <p>Time: """+ str(latest_run[0]) +"""</p>"""


        parameter_content = 'var parameter_content = [];'
        stringReturn = createpage(name,parm,str(level),str(latest_run[0]),renderHtml,parameter_content)
        return stringReturn

    @cherrypy.expose
    def parm(self, name="", parm="", level=""):
        pattern = re.compile("^((ECMF|UKMET|QPE|MPE|FFG|GribModel))")
        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")
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

        gridString = ''
        for grid in available_grids:
            if not pattern.match(grid):
                gridString += '<h3><a href="/grid?name='+grid+'">'+grid+'</a></h3>'\
                        '<table class="ui single line table"><thead>' \
                        '<tr><th>Parameter</th><th>Description</th><th>Unit</th><th>Level</th><th>API</th></tr>' \
                        '</thead>'
                request.setLocationNames(grid)
                availableLevels = DataAccessLayer.getAvailableLevels(request)
                availableLevels.sort()
                for llevel in availableLevels:
                    idhash = hash(grid+parm+str(llevel))
                    gridString += '<tr><td><a href="/grid?name=' + grid + '&parm=' + parm + '">' + parm + '</a></td>' \
                            '<td> ' + parmDescription + '</td>' \
                            '<td>'+ parmUnit +'</td>' \
                            '<td><div class="small ui label">' + str(llevel) + '</div></td>' \
                            '<td><a class="showcode circular ui icon basic button" name="'+str(idhash)+'" ' \
                            'href="/json?name=' + grid + '&parm=' + parm + '&level=' + str(llevel) + '">' \
                             '<i class="code icon small"></i></a></td></tr>'


                    gridString += '''<tr id="'''+str(idhash)+'''" class="transition hidden"><td colspan=5><div class="ui instructive bottom attached segment"><pre><code class="code xml">request.setDatatype("grid")
request.setLocationNames("'''+grid+'''")
request.setParameters("'''+parm+'''")
request.setLevels("'''+str(llevel)+'''")

cycles = DataAccessLayer.getAvailableTimes(request, True)
times = DataAccessLayer.getAvailableTimes(request)
latest_run = DataAccessLayer.getForecastRun(cycles[-1],times)

response = DataAccessLayer.getGridData(request, latest_run)
for grid in response:
    data = grid.getRawData()
    lons, lats = grid.getLatLonCoords()</code></pre></div></td></tr>'''

                gridString += '</table>'

        # Build dropdowns
        lvlString = ''
        gridSelect = '<div class=""><select class="ui select dropdown" id="gridSelect">'
        for grid in available_grids:
            if not pattern.match(grid): gridSelect += '<option value="%s">%s</option>' % (grid, grid)
        gridSelect += '</select></div>'

        gridSelect += '<div class=""><select class="ui select dropdown" id="levelSelect">'
        for llevel in availableLevels:
            gridSelect += '<option value="%s">%s</option>' % (llevel, llevel)
        gridSelect += '</select></div>'

        # Forecast Cycles
        cycles = DataAccessLayer.getAvailableTimes(request, True)
        t = DataAccessLayer.getAvailableTimes(request)
        fcstRun = []
        for time in t:
            if str(time)[:19] == str(cycles[-1]):
                fcstRun.append(time)

        gridSelect += '<div class=""><select class="ui select dropdown" id="cycleSelect">'
        for time in fcstRun:
            gridSelect += '<option value="%s">%s</option>' % (time, time)
        gridSelect += '</select></div><br><Br>'
        gridSelect += '<h1 class="ui dividing header">' + parm + ' - ' + parmDescription + ' (' + parmUnit + ')</h1>' \
                  + '<p>' + gridString + '</p>'
        parameter_content = 'var parameter_content = [];'
        stringReturn = createpage(name,parm,str(level),"",gridSelect,parameter_content)
        return stringReturn


def createpage(name, parm, level, time, gridSelect,parameter_content):
    return """
        <html>
            <head>
                <script type="text/javascript" src="/js/jquery-1.11.3.min.js"></script>
                <link rel="stylesheet" type="text/css" href="/css/semantic.min.css">
                <link rel="stylesheet" type="text/css" href="/css/style.css">
                <script src="/js/semantic.min.js"></script>
                <script type="text/javascript">
                    """+ parameter_content +"""
                    $(document).ready(function(){
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
                    <a class="item">
                      <b>AWIPS Data Access</b>
                    </a>
                    <div class="item">
                        <div class="header">Available Data</div>
                        <div class="menu">
                            <a class="item">
                              Forecast & Analysis Grids
                            </a>
                            <a class="item">
                              Satellite Imagery
                            </a>
                            <a class="item">
                              Level 3 Radar
                            </a>
                            <a class="item">
                              Upper Air Soundings
                            </a>
                            <a class="item">
                              Text Obs
                            </a>
                            <a class="item">
                              Lightning
                            </a>
                            <a class="item">
                              Maps
                            </a>
                        </div>
                    </div>
                  </div>
                  <div class="pusher">
                    %s
                  </div>

            </body>

        </html>
            """ % ( gridSelect )

if __name__ == '__main__':
    DataAccessLayer.changeEDEXHost("edex-cloud.unidata.ucar.edu")
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

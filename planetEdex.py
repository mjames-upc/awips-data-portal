import sys, os, cStringIO

import cherrypy
from awips.dataaccess import DataAccessLayer
import matplotlib.tri as mtri
import matplotlib.pyplot as plt
import matplotlib
import cartopy.crs as ccrs
import numpy as np
from parms import parm_dict

class Edex:
    @cherrypy.expose
    def index(self, name="RAP40", parm="", level=""):
        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")
        # Grid names
        available_grids = DataAccessLayer.getAvailableLocationNames(request)
        available_grids.sort()
        request.setLocationNames(name)
        # Grid parameters
        availableParms = DataAccessLayer.getAvailableParameters(request)
        availableParms.sort()
        if parm == "": parm = availableParms[0]
        request.setParameters(parm)
        # Grid levels
        availableLevels = DataAccessLayer.getAvailableLevels(request)
        availableLevels.sort()

        if level == "": level = availableLevels[0]
        request.setLevels(level)

        # Build dropdowns
        parmString = '<table class="ui single line table"><thead><tr><th>Parameter</th><th>Description</th><th>Unit</th></tr></thead>'
        lvlString = ''
        gridSelect = '<div class=""><select class="ui select dropdown" id="gridSelect">'
        for grid in available_grids:
            gridSelect += '<option value="%s">%s</option>' % (grid, grid)
        gridSelect += '</select></div>'
        gridSelect += '<div class=""><select class="ui select dropdown" id="parmSelect">'
        for gridparm in availableParms:
            for item in parm_dict:
                if item == gridparm:
                    parmDescriptioon = parm_dict[item][0]
                    parmUnit = parm_dict[item][1]
            gridSelect += '<option value="%s">%s</option>' % (gridparm, gridparm)
            parmString += '<tr><td><a href="/parm?parm='+ gridparm +'"><b>' + gridparm + '</b></a></td><td>' + parmDescriptioon + '</td><td><div class="small ui label">' + parmUnit + '</div></td></tr>'
        gridSelect += '</select></div>'

        parmString += '</table>'




        parmDescriptioon = ''
        parmUnit = ''
        for item in parm_dict:
            if item == parm:
                parmDescriptioon = parm_dict[item][0]
                parmUnit = parm_dict[item][1]

        gridSelect += '<div class=""><select class="ui select dropdown" id="levelSelect">'
        for level in availableLevels:
            gridSelect += '<option value="%s">%s</option>' % (level, level)
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

        # CREATE IMAGE
        if len(fcstRun) != 0:
        # Request, receive, and interpolate grid
            response = DataAccessLayer.getGridData(request, fcstRun)
            grid = response[0]
            data = grid.getRawData()
            lons, lats = grid.getLatLonCoords()
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
            plt.figure(figsize=(7, 4), dpi=100)
            ax = plt.axes(projection=ccrs.PlateCarree())
            cs = plt.contourf(rlons, rlats, rdata, 60, cmap=cmap,
                          transform=ccrs.PlateCarree(),
                          vmin=rdata.min(), vmax=rdata.max())
            ax.gridlines()
            ax.coastlines()
            ax.set_aspect('auto', adjustable=None)
            cbar = plt.colorbar(orientation='horizontal')
            cbar.set_label(grid.getParameter() + " (" + grid.getUnit() + ")")
            # Write image to stream
            format = "png"
            sio = cStringIO.StringIO()
            plt.savefig(sio, format=format)
            print "Content-Type: image/%s\n" % format
            sys.stdout.write(sio.getvalue())
            gridSelect += '<img style="border: 0;" src="data:image/png;base64,'+sio.getvalue().encode("base64").strip()+'"/>'
            # If we want to show all cycles/fcst hours
            #cycleTime = t[-1].getRefTime().getTime()/1000.0
            #fsctTime = t[-1].getValidPeriod()
            #showString = str(datetime.datetime.fromtimestamp(cycleTime).strftime('%Y-%m-%d %H%M')+" UTC")
            #linkString = str(datetime.datetime.fromtimestamp(cycleTime).strftime('%Y%m%d%H%M'))
        gridSelect += '<h1 class="ui dividing header">' + name + '</h1>' \
                  + '<h3 class="first">Details</h3>' \
                  + '<p>Grid size: ' + str(data.shape) + '</p>' \
                  + '<h3 class="first">Selected Parameter</h3><p>' + parm + ' - ' + parmDescriptioon + ' (' + parmUnit + ')</p>' \
                  + '<h3 class="first">Grid Parameters</h3><p>' + parmString + '</p>' \
                  + '<h3 class="first">Grid Levels</h3><p><small>' + lvlString + '</small></p>' \
                  + '<p>Unit: ' + grid.getUnit() + '</p>' \
                  + '<p>Time: ' + str(fcstRun[0])  + '</p>'
        stringReturn = createpage(name,parm,level,str(fcstRun[0]),gridSelect)
        return stringReturn

    @cherrypy.expose
    def parm(self, name="", parm="", level=""):
        
        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")
        request.setParameters(parm)
        parmDescriptioon = ''
        parmUnit = ''
        for item in parm_dict:
            if item == parm:
                parmDescriptioon = parm_dict[item][0]
                parmUnit = parm_dict[item][1]
        
        # Grid names
        available_grids = DataAccessLayer.getAvailableLocationNames(request)
        available_grids.sort()

        gridString = ''
        for grid in available_grids:

            gridString += '<h3><a href="/?name='+grid+'">'+grid+'</a></h3><table class="ui single line table"><thead><tr><th>Parameter</th><th>Description</th><th>Unit</th><th>Level</th><th>API</th></tr></thead>'
            request.setLocationNames(grid)
            availableLevels = DataAccessLayer.getAvailableLevels(request)
            availableLevels.sort()
            for level in availableLevels:
                gridString += '<tr><td><a href="/?name=' + grid + '&parm=' + parm + '">' + parm + '</a></td>' \
                        '<td> ' + parmDescriptioon + '</td>' \
                        '<td>'+ parmUnit +'</td>' \
                        '<td><div class="small ui label">' + str(level) + '</div></td><td><a class="circular ui icon basic button" href="#"><i class="code icon small"></i></a></td></tr>'
            gridString += '</table>'

        # Build dropdowns
        lvlString = ''
        gridSelect = '<div class=""><select class="ui select dropdown" id="gridSelect">'
        for grid in available_grids:
            gridSelect += '<option value="%s">%s</option>' % (grid, grid)
        gridSelect += '</select></div>'

        gridSelect += '<div class=""><select class="ui select dropdown" id="levelSelect">'
        for level in availableLevels:
            gridSelect += '<option value="%s">%s</option>' % (level, level)
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
        gridSelect += '<h1 class="ui dividing header">' + parm + ' - ' + parmDescriptioon + ' (' + parmUnit + ')</h1>' \
                  + '<p>' + gridString + '</p>'
        stringReturn = createpage(name,parm,level,"",gridSelect)
        return stringReturn
    
    
def createpage(name, parm, level, time, gridSelect):
    return """
        <html>
            <head>
                <script type="text/javascript" src="/js/jquery-1.11.3.min.js"></script>
                <link rel="stylesheet" type="text/css" href="/css/semantic.min.css">
                <link rel="stylesheet" type="text/css" href="/css/style.css">
                <script src="/js/semantic.min.js"></script>
                <script type="text/javascript">
                    $(document).ready(function(){
                        $('#gridSelect').val('""" + name + """');
                        $('#parmSelect').val('""" + parm + """');
                        $('#cycleSelect').val('""" + time + """');

                        $('.select')
                          .dropdown()
                        ;
                        $("#gridSelect").change(function () {
                            location.href = "/?name=" + $(this).val();
                        });
                        $("#parmSelect").change(function () {
                            location.href = "/?name=""" + name + """&parm=" + $(this).val();
                        });
                        $("#levelSelect").change(function () {
                            location.href = "/?name=""" + name + """&parm=""" + parm + """&level=" + $(this).val();
                        });
                    });
                </script>
            </head>
            <body class="">
                <div class="ui sidebar inverted visible vertical left menu" style="width: 200px !important; height: 1813px !important; margin-top: 0px; left: 0px;">
                    <a class="item">
                      <b>AWIPS</b>
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
    DataAccessLayer.changeEDEXHost("edex.westus.cloudapp.azure.com")
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
import sys, cStringIO

import cherrypy
from awips.dataaccess import DataAccessLayer
import matplotlib.tri as mtri
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import numpy as np

class Edex:
    @cherrypy.expose
    def grid(self, name="", parm="", level=""):
        gridTimeIndex = -1
        request = DataAccessLayer.newDataRequest()
        request.setDatatype("grid")

        # Grids
        available_grids = DataAccessLayer.getAvailableLocationNames(request)
        available_grids.sort()
        request.setLocationNames(name)

        # Grid Parameters
        availableParms = DataAccessLayer.getAvailableParameters(request)
        availableParms.sort()
        if parm == "": parm = availableParms[0]
        request.setParameters(parm)

        # Grid Levels
        availableLevels = DataAccessLayer.getAvailableLevels(request)
        availableLevels.sort()
        if level == "": level = availableLevels[0]
        request.setLevels(level)

        # Build dropdowns
        gridSelect = '<div class="col-lg-6"><select class="form-control" id="gridSelect" name="gridSelect">'
        for grid in available_grids:
            gridSelect += '<option value="%s">%s</option>' % (grid, grid)
        gridSelect += '</select></div>'
        gridSelect += '<div class="col-lg-6"><select class="form-control" id="parmSelect" name="parmSelect">'
        for gridparm in availableParms:
            gridSelect += '<option value="%s">%s</option>' % (gridparm, gridparm)
        gridSelect += '</select></div>'
        gridSelect += '<div class="col-lg-6"><select class="form-control" id="levelSelect" name="levelSelect">'
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

        gridSelect += '<div class="col-lg-6"><select class="form-control" id="cycleSelect" name="cycleSelect">'
        for time in fcstRun:
            gridSelect +=  '<option value="%s">%s</option>' % (time,time)
        gridSelect += '</select></div>'

        # CREATE IMAGE
        if len(fcstRun) != 0:
        # Request, receive, and interpolate grid
            response = DataAccessLayer.getGridData(request, fcstRun)
            grid = response[0]
            data = grid.getRawData()
            lons, lats = grid.getLatLonCoords()
            ngrid = data.shape[1]

        # Turn off mpl interpolation (takes too long with high res grids)
        if 1 == 2:
            rlons = np.repeat(np.linspace(np.min(lons), np.max(lons), ngrid),
                          ngrid).reshape(ngrid, ngrid)
            rlats = np.repeat(np.linspace(np.min(lats), np.max(lats), ngrid),
                          ngrid).reshape(ngrid, ngrid).T
            tli = mtri.LinearTriInterpolator(mtri.Triangulation(lons.flatten(),
                                               lats.flatten()), data.flatten())
            rdata = tli(rlons, rlats)

            # Create Map
            cmap = plt.get_cmap('rainbow')
            plt.figure(figsize=(7, 4), dpi=100)
            ax = plt.axes(projection=ccrs.PlateCarree())
            cs = plt.contourf(rlons, rlats, rdata, 60, cmap=cmap,
                          transform=ccrs.PlateCarree(),
                          vmin=rdata.min(), vmax=rdata.max())
            ax.gridlines()
            #ax.stock_img()
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

        gridSelect += "<div>" + name + "</div>" \
                  + "<div>Grid size: " + str(data.shape) + "</div>" \
                  + "<div>Parm: " + grid.getParameter() + "</div>" \
                  + "<div>Level: " + grid.getLevel() + "</div>" \
                  + "<div>Unit: " + grid.getUnit() + "</div>" \
                  + "<div>Time: " + str(fcstRun[0])  + "</div>"

        # Return page
        return """<html><head><link href="/static/css/style.css" rel="stylesheet"></head>
                <script type="text/javascript" src="https://code.jquery.com/jquery-1.11.3.min.js"></script>
                <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/js/bootstrap.min.js" integrity="sha384-0mSbJDEHialfmuBBQP6A4Qrprq5OVfW37PRR3j5ELqxss1yVqOtnepnHVP9aJ7xS" crossorigin="anonymous"></script>
                <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" integrity="sha384-1q8mTJOASx8j1Au+a5WDVnPi2lkFfwwEAa8hDDdjZlpLegxhjVME1fgjWPGmkzs7" crossorigin="anonymous">
                <script type="text/javascript">
                $(document).ready(function(){
                    $('#gridSelect').val('""" + name + """');
                    $('#parmSelect').val('""" + parm + """');
                    $('#cycleSelect').val('""" + str(fcstRun[0]) + """');
                    $("#gridSelect").change(function () {
                        location.href = "/grid?name=" + $(this).val();
                    });
                    $("#parmSelect").change(function () {
                        location.href = "/grid?name=""" + name + """&parm=" + $(this).val();
                    });
                    $("#levelSelect").change(function () {
                        location.href = "/grid?name=""" + name + """&parm=""" + parm + """&level=" + $(this).val();
                    });
                });
                </script>
                <body>
                <table width="" border="1">
                %s
                </table>
                </body>
                </html>""" % ( gridSelect )

if __name__ == '__main__':
    DataAccessLayer.changeEDEXHost("0.0.0.0")
    server_config={
	'server.socket_host': '0.0.0.0',
	'server.socker_port': 8080
    }
    cherrypy.config.update(server_config)
    cherrypy.quickstart(Edex())
window.addEventListener("load", function(event) {
    $('.masthead').visibility({
        once: false,
        onBottomPassed: function() {
            $('.fixed.menu').transition('fade in');
        },
        onBottomPassedReverse: function() {
            $('.fixed.menu').transition('fade out');
        }
    });
    $('.ui.sidebar').sidebar('attach events', '.toc.item');
    $('.menu .item').tab();
    $('.ui.search').search({
        source: parameter_content,
        minCharacters:3,
        maxResults: 20,
        onSelect: function(result,response) {
            window.location.href='/parm?parm='+result.name;
        }
    });
    $('.select').dropdown();
    $('.showcode').on('click', function(){
        divname = '#'+$(this).attr("name")
        $(divname).transition('fade down');
        return false;
    });
    createGeoJSON();
});

var temperatureColorScale = ['#ffffff', '#28394b', '#3a5775', '#4ca4bd', '#6bd1cb', '#73bf4d', '#91e447', '#edde34', '#dea942', '#b76534', '#893333', '#4f0138'];
var colormaps = {'temperatureColorScale': function(array) {
    return d3.scaleLinear().domain(getDomain(array, temperatureColorScale.length)).range(temperatureColorScale);
}};
var createNodes = function(html, parent) {
    while (parent.lastChild) {
        parent.removeChild(parent.lastChild);
    }
    return parent.appendChild(document.importNode(new DOMParser().parseFromString(html, 'text/html').body.childNodes[0], true));
};
var mapConfig = function(colormaps, container) {
    var colormap = colormaps['temperatureColorScale'];
    var jsonMap = dataMap.map({
        el: container,
        scrollWheelZoom: true,
        colormap: colormap
    }).init();
    return {
        jsonMap: jsonMap
    };
};
var dataMap = (function() {
    var layer = function() {
        var colormap = null;
        var map = null;
        var overlay = null;
        var previous = null;
        var canvas = L.DomUtil.create('canvas', 'data-map');
        canvas.style.display = 'none';
        document.body.appendChild(canvas);
        var layerData = {};
        layerData.render = function(_data) {
            var data = _data || previous;
            previous = data;
            if (!data) {
                return layerData;
            }
            var bounds = map.getBounds();
            var size = map.getSize();
            if (map.getPixelOrigin().y < 0) {
                size.y = map.getPixelWorldBounds().max.y - map.getPixelWorldBounds().min.y;
            }
            var lat = data.lats;
            var lon = data.lons;
            var values = data.values;
            canvas.width = size.x;
            canvas.height = size.y;
            var ctx = canvas.getContext('2d');
            ctx.globalAlpha = 0.5;
            var numlon = lon.length; // 151
            var numlat = lon[0].length; // 113
            //debugger;
            //var points = new Array();
            //for (var i = 0; i < lat.length; i++) {
            //    for (var j = 0; j < lat[i].length; j++) {
            //        var ptArray = new Array(lat[i][j],lon[i][j],values[i][j])
            //        points.push(ptArray);
            //    }
            //}
            //var heat = L.heatLayer(points).addTo(map);


            //console.log(lat[0][0] + "," + lon[0][0]); // TOP RIGHT
            //console.log(lat[numlon-1][0] + "," + lon[numlon-1][0]); // TOP LEFT
            //console.log(lat[0][numlat-1] + "," + lon[0][numlat-1]); // BOTTOM RIGHT
            //console.log(lat[numlon-1][numlat-1] + "," + lon[numlon-1][numlat-1]); // BOTTOM LEFT

            var nwPoint = map.latLngToContainerPoint(L.latLng(lat[numlon-1][0], lon[numlon-1][0]));
            var nwPointNextLon = map.latLngToContainerPoint(L.latLng(lat[numlon-2][0], lon[numlon-2][0]));
            var w = Math.ceil(Math.max(nwPointNextLon.x - nwPoint.x, 1)) + 2;
            var image = ctx.getImageData(0, 0, size.x, size.y);
            var buf = new ArrayBuffer(image.data.length);
            var buf8 = new Uint8ClampedArray(buf);
            var data = new Uint32Array(buf);
            var colorInt, imgIndex, x, y;
            var point, value, latIndex, nextLatIndex, lonIndex;

            var idwData = [];

            for (var i = 0; i < numlat; i++) {
                latIndex = Math.max(i, 0);
                nextLatIndex = Math.min(latIndex + 1, numlat - 1);
                for (var j = 0; j < numlon; j++) {
                    idwData.push([lat[j][i],lon[j][i],values[j][i]]);
                    //var firstPointAtCurrentLat = map.latLngToContainerPoint(L.latLng(lat[i][j], lon[i][j]));
                    //console.log(lat[i][j], lon[i][j]);
                    var firstPointAtCurrentLat = map.latLngToContainerPoint(L.latLng(lat[j][i], lon[j][i]));
                    var firstPointAtNextLat = map.latLngToContainerPoint(L.latLng(lat[j][nextLatIndex], lon[j][i]));
                    var h = Math.ceil(Math.max(firstPointAtNextLat.y - firstPointAtCurrentLat.y, 1) + 1);
                    //if (w > 3) console.log(w+","+h);
                    point = map.latLngToContainerPoint(L.latLng(lat[j][i], lon[j][i]));
                    if (map.getPixelOrigin().y < 0) {
                        point.y = point.y + map.getPixelOrigin().y;
                    }
                    value = values[j][i];
                    if (value !== -999 && value !== null && !isNaN(value) && i % 1 === 0 && j % 1 === 0) {
                        var colorHex = utils.rgb2hex(colormap(value)).substring(1);
                        colorInt = parseInt(colorHex, 16);

                        for (x = 0; x < w; x++) {
                            for (y = 0; y < h; y++) {
                                imgIndex = (~~point.y + y - ~~(h / 2)) * size.x + Math.min(Math.max(~~point.x + x - ~~(w / 2), 0), size.x - 1);
                                data[imgIndex] = (255 << 24) | (colorInt << 16) | (((colorInt >> 8) & 255) << 8) | (colorInt >> 16) & 255;
                            }
                        }

                    }
                }
            }
            //var idw = JSON.stringify(idwData);
            //console.log("[[" + idwData.join("],[") + "]]");
            //var idw = L.idwLayer("[[" + idwData.join("],[") + "]]", {opacity: 0.3, cellSize: 10, exp: 2, max: 350}).addTo(map);


            image.data.set(buf8);
            ctx.putImageData(image, 0, 0);

            if (overlay) {
                overlay.removeFrom(map);
            }
            overlay = L.imageOverlay(canvas.toDataURL('image/png'), bounds).addTo(map);
            overlay.setOpacity(0.9);
            return layerData;
        };
        layerData.setColorMap = function(_colormap) {
            colormap = _colormap;
            return layerData;
        };
        layerData.setData = function(data) {
            layerData.render(data);
            return layerData;
        };
        layerData.addTo = function(_map) {
            map = _map;
            map.on('moveend', function(d) {
                var imgNode = d.target._panes.overlayPane.querySelector('img');
                if (imgNode) {
                    var imgNodeStyle = imgNode.style;
                    var transform3D = imgNodeStyle.transform;
                    if (transform3D) {
                        var xy = transform3D.match(/\((.*)\)/)[1].split(',').slice(0, 2);
                        imgNodeStyle.transform = 'translate(' + xy + ')';
                    }
                }
                if (map.getZoom() < 6) layerData.render();
            });
            return layerData;
        };
        return layerData;
    };
    var map = function(_config) {
        var map, grid, geojsonLayer, tooltip, gridData, prevBbox;
        var config = {
            el: _config.el,
            scrollWheelZoom: _config.scrollWheelZoom,
            colormap: _config.colormap
        };
        var events = {
            click: utils.eventListeners(),
            mousemove: utils.eventListeners(),
            mouseenter: utils.eventListeners(),
            mouseleave: utils.eventListeners()
        }
        function init() {
            var bounds = [
                [-90, -180],
                [90, 180]
            ];
            map = L.map(config.el, {
                crs: L.CRS.EPSG3857,
                maxBounds: bounds,
                maxZoom: 13,
                minZoom: 0,
                zoomSnap: 0.1,
                attributionControl: false,
                scrollWheelZoom: config.scrollWheelZoom,
                fadeAnimation: false,
                tileLayer: {
                    noWrap: true,
                    continuousWorld: false
                }
            }).fitWorld().on('click', function(e) {
                events.click({
                    lat: e.latlng.lat,
                    lon: e.latlng.lng
                });
            }).on('mousedown', function(e) {
                config.el.classList.add('grab');
            }).on('mouseup', function(e) {
                config.el.classList.remove('grab');
            }).on('mousemove', function(e) {
                if (gridData) {
                    /* Draw tooltip overlay on hover */
                    var numlon = gridData.lons.length;
                    var numlat = gridData.lons[0].length;
                    var closest = {};
                    closest.distance = 9999999;
                    for (var i = 0; i < numlat; i++){
                        for (var j = 0; j < numlon; j++) {
                            var comp = utils.distance(e.latlng.lat,e.latlng.lng,gridData.lats[j][i],gridData.lons[j][i]);
                            if (comp < closest.distance){
                                closest.distance = comp;
                                closest.i = i;
                                closest.j = j;
                            }
                        }
                    }
                    //console.log(e.latlng.lat,e.latlng.lng);
                    //console.log(closest.i ,closest.j, closest.distance);
                    //console.log(gridData.lats[closest.j][closest.i],gridData.lons[closest.j][closest.i]);
                    //var latIndex = utils.bisectionReversed(gridData.lats[0], e.latlng.lat);
                    //var lonIndex = utils.bisection(gridData.lons[0], e.latlng.lng);
                    //var pLatIndex = Math.max(latIndex - 1, 0);
                    //var deltaLat = gridData.lats[0][pLatIndex] - gridData.lats[0][latIndex];
                    //if (e.latlng.lat > gridData.lats[0][latIndex] + deltaLat / 2) {
                    //    latIndex = pLatIndex;
                    //}
                    //var pLonIndex = Math.max(lonIndex - 1, 0);
                    //var deltaLon = gridData.lons[0][lonIndex] - gridData.lons[0][pLonIndex];
                    //if (e.latlng.lng < gridData.lons[0][lonIndex] - deltaLon / 2) {
                    //    lonIndex = pLonIndex;
                    //}
                    var value = gridData.values[closest.j][closest.i];
                    if (closest.distance < 30000 && value !== null && value !== -999) {
                        var formattedValue = L.Util.formatNum(value, 2);
                        tooltip.setTooltipContent(formattedValue + '').openTooltip([e.latlng.lat, e.latlng.lng]);
                    } else {
                        tooltip.closeTooltip();
                    }
                    events.mousemove({
                        x: e.containerPoint.x,
                        y: e.containerPoint.y,
                        value: value,
                        lat: e.latlng.lat,
                        lon: e.latlng.lng
                    });
                }
            }).on('mouseover', events.mouseenter).on('mouseout', events.mouseleave);

            map.createPane('labels');

            var basemap = L.tileLayer('http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                tileSize: 256,
                maxZoom: 19
            });
            var maplabel = L.tileLayer('http://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png', {
                attribution: 'Â©OpenStreetMap, Â©CartoDB',
                pane: 'labels'
            });
            basemap.addTo(map);
            maplabel.addTo(map);
            grid = layer().addTo(map);
            var tooltip = L.featureGroup().bindTooltip('').addTo(map);
            return this;
        }
        function zoomToBounds(polygon) {
            console.log("zoomToBounds");
            console.log(polygon);
            var geojson = L.geoJson(polygon);
            map.fitBounds(geojson.getBounds());
            prevBbox = polygon;
            return this;
        }
        function drawPolygon(polygon) {
            geojsonLayer = L.geoJson(polygon).addTo(map);
            return this;
        }
        function drawImage(data,metadata) {
            gridData = data;
            var dataSorted = data.uniqueValues.sort(function(a, b) {
                return a - b;
            });
            var colormap = config.colormap(dataSorted);
            grid.setColorMap(colormap).setData(data);
            var boundBox = metadata.coverage;
            var imageBounds = [[boundBox.latmax, boundBox.lonmin],[boundBox.latmin, boundBox.lonmax]];
            map.fitBounds(imageBounds);
            return this;
        }
        return {
            init: init,
            zoomToBounds: zoomToBounds,
            drawPolygon: drawPolygon,
            events: events,
            drawImage: drawImage,
            _getMap: function() {
                return map;
            }
        };
    };
    Number.prototype.toRad = function() {
        return this * Math.PI / 180;
    }
    var utils = {
        distance: function(lat1,lon1,lat2,lon2) {
            var R = 6371000;
            var φ1 = lat1.toRad();
            var φ2 = lat2.toRad();
            var Δφ = (lat2-lat1).toRad();
            var Δλ = (lon2-lon1).toRad();
            var a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
                Math.cos(φ1) * Math.cos(φ2) *
                Math.sin(Δλ/2) * Math.sin(Δλ/2);
            var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
            var d = R * c;
            return d;
        },
        eventListeners: function(value) {
            var listeners;
            function property(newValue) {
                if (arguments.length === 1) {
                    value = newValue;
                    if (listeners) {
                        for (var i = 0; i < listeners.length; i++) {
                            listeners[i](value);
                        }
                    }
                    return this;
                }
                return value;
            }
            property.on = function(listener) {
                if (!listeners) {
                    listeners = [];
                }
                listeners.push(listener);
                if (typeof value !== "undefined" && value !== null) {
                    listener(value);
                }
                return listener;
            };
            property.off = function(listenerToRemove) {
                if (listeners) {
                    listeners = listeners.filter(function(listener) {
                        return listener !== listenerToRemove;
                    });
                }
            };
            return property;
        },
        bisection: function(array, x, isReversed) {
            var mid, low = 0,
                high = array.length - 1;
            while (low < high) {
                mid = (low + high) >> 1;
                if ((isReversed && x >= array[mid]) || (!isReversed && x < array[mid])) {
                    high = mid;
                } else {
                    low = mid + 1;
                }
            }
            return low;
        },
        bisectionReversed: function(array, x) {
            return utils.bisection(array, x, true);
        },
        rgb2hex: function(rgb) {
            rgb = rgb.match(/^rgba?[\s+]?\([\s+]?(\d+)[\s+]?,[\s+]?(\d+)[\s+]?,[\s+]?(\d+)[\s+]?/i);
            return (rgb && rgb.length === 4) ? "#" +
            ("0" + parseInt(rgb[1],10).toString(16)).slice(-2) +
            ("0" + parseInt(rgb[2],10).toString(16)).slice(-2) +
            ("0" + parseInt(rgb[3],10).toString(16)).slice(-2) : '';
        }
    };
    return {
        map: map,
        utils: utils
    };
})();
var getGeoJSON = function(url,cb) {
    jQuery.getJSON(url, function(json) {
        json.values = json.values.map(function(d, i) {
            return d.map(function(b) {
                if (b === -999) {return null;}
                return b
            });
        });
        json.uniqueValues = unique(json.values).sort();
        cb({
            json: json
        });
    });
    return this;
};
var getGeoJSONBounds = function(url,cb) {
    jQuery.getJSON(url, function(json) {
        cb({
            json: json
        });
    });
    return this;
};
var unique = function(data) {
    var uniques = [];
    var values, value, i, j;
    var u = {};
    for (i = 0; i < data.length; i++) {
        values = data[i];
        for (j = 0; j < values.length; j++) {
            value = values[j];
            if (u.hasOwnProperty(value) || value === null) {
                continue;
            }
            u[value] = 1;
        }
    }
    uniques = Object.keys(u).map(function(d, i) {
        return +d;
    });;
    return uniques;
};

var getDomain = function(array, sliceCount) {
    var stepWidth = (d3.max(array) - d3.min(array)) / sliceCount;
    return d3.range(sliceCount).map(function(d, i) {
        return d3.min(array) + i * stepWidth;
    });
}
var geoJsonPolygonFeature = function(poly) {
    return {
        "type": "Feature",
        "properties": {},
        "geometry": {
            "type": poly.type,
            "coordinates": poly.coordinates
        }
    }
}

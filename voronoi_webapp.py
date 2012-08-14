from flask import Flask, render_template, flash, g, redirect, session
from flask import request, redirect, url_for, send_from_directory, abort
from contextlib import closing
import os
import numpy as np
import pygeoip
import socket
import sqlite3
import time

# py_geo_voronoi: https://github.com/Softbass/py_geo_voronoi
import voronoi_poly 

from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import matplotlib.nxutils as nx

# configuration
DATABASE = 'serverlist.db'
DATABASE_SUBNETS = "subnetlist.db"
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

CWD = os.getcwd()

app = Flask(__name__)
app.config.from_object(__name__)
records = ['cernvm_cdn', 'cernvm_cdn_host', 'cernvm_cvmfs2', 'cernvm_grid_ui_version', 'cernvm_organization_list', 'cernvm_repository_list', 'cernvm_repository_map', 'cmtprojectpath', 'cmtroot', 'cmtsite', 'cvsroot', 'exportvars', 'filecachesize', 'fileprotocol', 'fileserver', 'hepsoft_platform', 'hepsoft_version', 'httpproxy', 'localsite', 'mysiteroot', 'na49_level', 'notifyemail', 'platformlist', 'siteroot', 'vo_atlas_sw_dir', 'vo_cms_sw_dir']


def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def readPointsFromFile():
    f = open( "location-with-url", "r" )
    PointsMap = {}
    for line in f.readlines():
        info = line.split()
        name = info[ 0 ]
        lon = info[ 1 ]
        lat = info[ 2 ]
        urlStr = info[3]
        PointsMap[ name ] = ( lon, lat, urlStr[1:] )
    f.close()
    return PointsMap
    
def readMergedPointsFromFile():
    f = open( "location_duplicates_merged", "r" )
    PointsMapMerged = {}
    for line in f.readlines():
        info = line.split( '(' )
        complexName = info[0]
        loc = info[1].split( ',' )
        lon = loc[0]
        lat = loc[1].strip()[:-1]
        PointsMapMerged[ complexName ] = ( lon, lat )
    f.close()
    return PointsMapMerged

def init_db():
    
    # Getting all servers names and locations from file
    #PointsMapMerged = readMergedPointsFromFile()
    PointsMap = readPointsFromFile()
    defaultPriority = 10
    defaultWeight = 10
    defaultPort = 3128
    
    # Executing sqlite queries to create database serverlist.db
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

        # Writing the mirror servers' information to a database serverlist.db
        query = 'insert into servers (serverName, lon, lat, serverAdd, priority, weight, port) values (?, ?, ?, ?, ?, ?, ?)'
        for complexName, locTuple in PointsMap.iteritems():
            db.execute( query, [ complexName, locTuple[0], locTuple[1], locTuple[2], defaultPriority, defaultWeight, defaultPort ])
            db.commit()

# For later use: When separating the merged server entries
def generateSimplePointsMap( PointsMap ):
    index = 0
    simplePointsMap = {}
    for names, locTuple in PointsMap.iteritems():
        nameList = names.split( ',' )
        for name in nameList:
            simplePointsMap[ name ] = [ index, locTuple ]
            index += 1

    return simplePointsMap

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    g.db.close()

def readGeoListFromDatabase():
    PointsMap={}
    cur = g.db.execute(
        'select serverName, lon, lat from servers order by id desc')
    for row in cur.fetchall():
        PointsMap[ row[0] ] = ( row[1], row[2] )
    return PointsMap

def readGeoListFromDatabaseForBIND():
    serverNameAddr={}
    cur = g.db.execute(
        'select serverName, serverAdd from servers order by id desc')
    for row in cur.fetchall():
        serverNameAddr[ row[0] ] = row[1]
    return serverNameAddr

def mergeDuplicates( PointsMap ):

    uniquePointsMap = {}
    blackList = frozenset( [ ] )
    for name, coordinates in PointsMap.items():
        # Checking if we blacklisted this name before
        if name in blackList:
            continue

        finalName = name

        for name1, coordinates1 in PointsMap.items():
            if name == name1:
                continue
            if coordinates[0] == coordinates1[0] and \
            coordinates[1] == coordinates1[1]:
                # Add this name to blacklist so that
                # we don't consider it again
                blackList = blackList.union( [ name1 ] )
                finalName = finalName + ", " + name1

        uniquePointsMap[ finalName ] = coordinates

    return uniquePointsMap

def plotDiagramFromLattice( ax, voronoiLattice, map ):

    # Has the form {serialNo: Polygon}
    voronoiPolygons = {}

    # Has the form {serialNo: compoundName }
    voronoiSitesMergedNames = {}

    # Plotting the Polygons returned by py_geo_voronoi
    N = len( voronoiLattice.items() )
    for x in range( N ):
        data = voronoiLattice[ x ]
        serialNo = x
        polygon_data = data[ 'obj_polygon']
        compoundName = data[ 'info' ]
        pointList = []

        for point in list( polygon_data.exterior.coords ):
            pointMap = map( point[0], point[1] )
            pointList.append( pointMap )

        ax.add_patch( Polygon( pointList, fill=0, edgecolor='black' ))
        voronoiPolygons[ serialNo ] = np.array( pointList )
        voronoiSitesMergedNames[ serialNo ] = compoundName
    
    return voronoiPolygons, voronoiSitesMergedNames

def getNetworkLocations( map ):

    networkLatLon = {}
    connection = sqlite3.connect( DATABASE_SUBNETS )
    cursor = connection.cursor()
    allCsvData = cursor.execute("select * from subnets")
    for entry in allCsvData:
        networkLatLon[ entry[0] ] = \
            { 'xCoord': entry[3], 'yCoord': entry[2], 'cidr': entry[1] }

    return networkLatLon

def mapMergedSitesToReal( voronoiSitesMergedNames ):

    # { serialNo : Name } form
    simplePointsMap = {}

    mapMergedSitesDict = {}
    serialNoFinal = 0
    for entry in voronoiSitesMergedNames.items():
        serialNo = entry[0]
        compoundName = entry[1]
        names = compoundName.split( ',' )
        listOfSerialNos = []
        for name in names:
            simplePointsMap[ serialNoFinal ] = name
            serialNoFinal += 1
            listOfSerialNos.append( serialNoFinal )
        mapMergedSitesDict[ serialNo ] = listOfSerialNos

    return mapMergedSitesDict, simplePointsMap

def processSiteName( name ):
    name = name.split( '/' )[-1]
    name = name.lower()
    namelets = name.split( '_' )
    firstPart = '_'.join( namelets[2:] )
    finalName = '.'.join( [ firstPart, namelets[0], namelets[1] ] )
    return finalName

def generateBINDFile():
    mirrorDict = readGeoListFromDatabaseForBIND( )

    f = open( "pdns-bind", "w" )
    for info in mirrorDict.iteritems():
        name = info[0]
        urlStr = info[1]
        urls = urlStr.split( ',' )
        finalName = processSiteName( name )

        for url in urls:
            # The 10s and 3128 is hardcoded for this test
            f.write( finalName + '\t\t' + 'SRV' + '\t' + '10' + '\t' 
                     + '10' + '\t' + '3128' + '\t' + url[7:] + '.' + '\n' )
    f.close()

def generateGeoRRMaps( PointsMap ):
    # To Fix: Have not yet added default entry at number 0
    ORIGIN = "sites.cdn.cernvm.org."
    os.system( "mkdir geo-rr-maps" )
    for record in records:
        RECORD = record
        fileName = "geo-rr-maps/" + record
        f = open( fileName, "w" )
        f.write( "$RECORD" + ' ' + RECORD + "\n" )
        f.write( "$ORIGIN" + ' ' + ORIGIN + "\n" )
        for server in PointsMap.iteritems():
            serialNo = server[ 0 ]
            complexName = server[ 1 ]
            simpleName = processSiteName( complexName )
            f.write( str( serialNo ) + '  ' + RECORD + '.' + simpleName + '\n' )
        f.close()
        
@app.route( '/voronoi', methods=[ 'GET', 'POST' ] )
def voronoi():

    PointsMap = readGeoListFromDatabase()

    # Backing up the original for future use
    backupPointsMap = PointsMap

    PointsMap = mergeDuplicates( PointsMap )

    # Method provided by py_geo_voronoi, returns a dictionary
    # of dictionaries, each sub-dictionary carrying information 
    # about a polygon in the Voronoi diagram.
    # PlotMap=False prevents the function from plotting the
    # polygons on its own, so that the printing can be handled 
    # here, on a Basemap.
    voronoiLattice = voronoi_poly.VoronoiPolygons(
        PointsMap, BoundingBox="W", PlotMap=False )

    numVoronoiCells = len( voronoiLattice.keys() )

    serverNames = []
    serialNum = []
    lat = []
    lon = []
    # Getting server names and lat, lon in order
    for x in range( numVoronoiCells ):
        serialNum.append( x )
        serverNames.append( voronoiLattice[ x ][ 'info' ] )
        lat.append( voronoiLattice[ x ][ 'coordinate' ][ 1 ] )
        lon.append( voronoiLattice[ x ][ 'coordinate' ][ 0 ] )

    # Creating a Basemap object with mill projection
    map = Basemap(projection='mill',lon_0=0,resolution='c')    
    
    # Filling colors in the continents and water region
    map.fillcontinents( color='white',lake_color='#85A6D9' )
    
    # Drawing coastlines and countries
    map.drawcoastlines( color='#6D5F47', linewidth=.7 )
    map.drawcountries( color='#6D5F47', linewidth=.7 )

    map.drawmapboundary( fill_color='#85A6D9' )

    # Drawing latitudes and longitude lines
    map.drawmeridians(np.arange(-180, 180, 30), color='#bbbbbb')
    map.drawparallels(np.arange(-90, 90, 30), color='#bbbbbb')
    
    # Preparing the data for a scatter plot of server locations
    x,y = map( lon, lat )
    X = np.array( x )
    Y = np.array( y )

    # Plotting all the servers with a scatter plot
    map.scatter( x, y, c='black', marker='.', zorder = 2)

    ax = plt.gca()
    # Plotting the Polygons returned by py_geo_voronoi
    voronoiPolygons, voronoiSitesMergedNames = \
        plotDiagramFromLattice( ax, voronoiLattice, map )

    plt.title( 'Server Locations Across the Globe' )
    plt.savefig( 'voronoi-py.png' )

    # Getting a dictionary of form {serialNo: compoundName}
    # These are approximately 67 entries
    voronoiSitesMergedNames = {}
    for serial, polygon in voronoiLattice.items():
        voronoiSitesMergedNames[ serial ] = polygon[ 'info' ]

    # Creating an map from the merged enntries to single server entries
    mapMergedSitesDict, simplePointsMap = mapMergedSitesToReal( voronoiSitesMergedNames )

    #print voronoiLattice
    #print voronoiPolygons

    now = time.time()
    # Processing networks from Whois database
    # and getting each network's lat, long
    # Also get the cidr notation
    networkLatLon = getNetworkLocations( map )

    print 'Time taken to get CIDR info ' + str( time.time() - now )

    histogramData = {}
    histogramData = histogramData.fromkeys( 
        range( 0, len( serverNames ) ), 0 )
    
    pdnsFile = open( "pdns-config", "w" )
    import random

    for sNo, netDetail in networkLatLon.iteritems():
        net = np.array( [ [ netDetail[ 'xCoord' ], netDetail[ 'yCoord' ] ] ] )
        for serialNo, polygon in voronoiPolygons.items():
            if nx.points_inside_poly( net, polygon ):
                histogramData[ serialNo ] += 1
                cidrs = netDetail[ 'cidr' ].split('\n')
                for cidr_net in cidrs:
                    if cidr_net == u'':
                        continue
                    possibleMirrors = mapMergedSitesDict[ serialNo ]
                    chosenSerialNo = random.choice( possibleMirrors )
                    pdnsFile.write( str( cidr_net ) + ' :' + 
                                    '127.0.0.' + str( chosenSerialNo ) + "\n" )
                break
    pdnsFile.close()

    # This method generates the BIND files
    generateBINDFile()

    # Generate geo-rr-maps directory for all records
    generateGeoRRMaps( simplePointsMap )

    return '''
    <!doctype html>
    <title>Voronoi Plot</title>
    <h1><center>Voronoi Diagram</center></h1>
    <center>
    <img src="voronoi-py.png" />
    </center>
    '''

@app.route( '/voronoi-py.png' )
def image():
    return send_from_directory( CWD, 'voronoi-py.png' )

@app.route('/')
def show_entries():
    cur = g.db.execute('select serverName, serverAdd from servers order by id desc')
    entries = [dict(serverName=row[0], serverAdd=row[1]) for row in cur.fetchall()]
    entries = sorted( entries, key=lambda k: k['serverName'] )
    return render_template('show_entries.html', entries=entries)

@app.route('/add', methods=['POST'])
def add_entry():

    if not session.get('logged_in'):
        abort(401)
    reqServerName = request.form[ 'serverName' ]
    reqServerURL = request.form[ 'serverAdd' ]
    priority = request.form[ 'priority' ]
    weight = request.form[ 'weight' ]
    port = request.form[ 'port' ]

    gi = pygeoip.GeoIP( "/usr/local/share/GeoIP/GeoIPCity.dat",
                        pygeoip.STANDARD )
    gir = None
    try:
        gir = gi.record_by_name( reqServerURL )
    except socket.gaierror:
        pass
    except pygeoip.GeoIPError:
        pass
    if gir == None:
            return redirect(url_for('show_entries'))
    print reqServerURL, reqServerName

    reqServerLon = gir[ 'longitude' ]
    reqServerLat = gir[ 'latitude' ]

    query = 'insert into servers (serverName, serverAdd, lon, lat, priority, weight, port) values (?, ?, ?, ?, ?, ?, ?)'
    g.db.execute( query, [reqServerName, reqServerURL, reqServerLon, reqServerLat, priority, weight, port])
    g.db.commit()
    flash('New server was successfully added')
    return redirect(url_for('show_entries'))

@app.route('/delete', methods=['POST'])
def delete_entry():
    cur = g.db.execute('select serverName, serverAdd from servers order by id desc')
    entries = [dict(serverName=row[0], serverAdd=row[1]) for row in cur.fetchall()]

    for entry in entries:
        name = entry[ 'serverName' ]
        if name in request.form:
            sql = 'delete from servers where serverName="%s"' % name
            g.db.execute( sql )
            g.db.commit()

    flash('Server entry was successfully deleted')
    return redirect(url_for('show_entries'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))

if __name__ == '__main__':
    app.run( debug=True )

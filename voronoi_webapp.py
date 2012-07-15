from flask import Flask, render_template, flash, g, redirect, session
from flask import request, redirect, url_for, send_from_directory, abort
from contextlib import closing
import os
import numpy as np
import pygeoip

# py_geo_voronoi: https://github.com/Softbass/py_geo_voronoi
import voronoi_poly 

from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import matplotlib.nxutils as nx

import sqlite3

# configuration
DATABASE = '/tmp/serverlist.db'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'

CWD = os.getcwd()

app = Flask(__name__)
app.config.from_object(__name__)

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()
        f = open( "geolist_new", "r" )
        for line in f.readlines():
            info = line.split()
            db.execute('insert into servers (serverName, lon, lat) values (?, ?, ?)', [info[0], info[1], info[2]])
            db.commit()

init_db()

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    g.db.close()

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


def readGeolistFromDatabase():
    PointsMap={}
    lat = []
    lon = []
    # List of all server names
    serverName = []

    cur = g.db.execute(
        'select serverName, lon, lat from servers order by id desc')
    for row in cur.fetchall():
        flash( row )
        PointsMap[ row[0] ] = ( row[1], row[2] )

def plotDiagramFromLattice( ax, voronoiLattice, map ):
    voronoiPolygons = {}

    # Plotting the Polygons returned by py_geo_voronoi
    N = len( voronoiLattice.items() )
    for x in range( N ):
        data = voronoiLattice[ x ]
        serialNo = x
        polygon_data = data[ 'obj_polygon']
        pointList = []

        for point in list( polygon_data.exterior.coords ):
            pointMap = map( point[0], point[1] )
            pointList.append( pointMap )

        ax.add_patch( Polygon( pointList, fill=0, edgecolor='black' ))
        voronoiPolygons[ serialNo ] = np.array( pointList )
    
    return voronoiPolygons

@app.route( '/voronoi', methods=[ 'GET', 'POST' ] )
def voronoi():

    PointsMap = readGeolistFromDatabase()

    # Many server sites map to the same latitude and longitudes
    # Lets merge the duplicates
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
    voronoiPolygons = plotDiagramFromLattice( ax, voronoiLattice, map )

    plt.title( 'Server Locations Across the Globe' )
    plt.savefig( 'voronoi-py.png' )

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
    return render_template('show_entries.html', entries=entries)

@app.route('/add', methods=['POST'])
def add_entry():

    if not session.get('logged_in'):
        abort(401)
    g.db.execute('insert into servers (serverName, serverAdd) values (?, ?)',
                 [request.form['serverName'], request.form['serverAdd']])
    g.db.commit()
    flash('New server was successfully added')
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

'''@app.route('/', methods=['GET'])
def index():
    
    return
    <!doctype html>
    <title>Generate Voronoi Plot</title>
    <h1><center>Plot Voronoi Diagram</center></h1>
    <center>
    <form action="/voronoi" method=post enctype=multipart/form-data>
        <input type=submit value="Plot Defaults">
    </form>
    </center>

'''
if __name__ == '__main__':
    app.run( debug=True )

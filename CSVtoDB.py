#!/usr/bin/python2
import sqlite3
from flask import g, Flask
from contextlib import closing
import os
from subprocess import Popen, PIPE
import pygeoip
from mpl_toolkits.basemap import Basemap

DATABASE = '/tmp/subnetlist.db'

app = Flask(__name__)
app.config.from_object(__name__)

def connect_db():
    return sqlite3.connect('DATABASE')

def init_db( ):

    connection = sqlite3.connect( DATABASE )
    cursor = connection.cursor()
    sqlFile = open( 'whois-schema.sql' )

    #for line in sqlFile:
    #    print 'line', line
    #    cursor.execute( line )
    cursor.executescript( sqlFile.read() )
    connection.commit()

    map = Basemap(projection='mill',lon_0=0,resolution='c')    

    f1 = open( "GeoIPCountryWhois.csv", "r" )

    for i in range(160000):
        try:
            whois = f1.readline().split(",")
        except EOFError:
            break
        networkFromIP = whois[0].strip( '"' )
        networkToIP = whois[1].strip( '"' )
        
        if networkFromIP == networkToIP:
            continue

        ip_range = str( networkFromIP ) + "-" + str( networkToIP )
        command = 'echo %s | perl range2cidr.pl' % ip_range
        cidr_list = Popen([command], stdout=PIPE, shell=True).communicate()[0]

        gi = pygeoip.GeoIP( "/usr/local/share/GeoIP/GeoIPCity.dat",
                            pygeoip.STANDARD )
        try:
            gir = gi.record_by_addr( networkFromIP )
        except pygeoip.GeoIPError:
            print 'Error in:', networkFromIP
        if gir != None:
            x,y = map( gir[ 'longitude' ], gir[ 'latitude' ] )

        # Populating the database with server names and locations
        cursor.execute('insert into subnets (subnet, lon, lat) values (?, ?, ?)', [cidr_list, y, x ])
        
        connection.commit()
        
    cursor.close()
    f1.close()

if __name__ == "__main__":
    init_db()
                       
                     
    

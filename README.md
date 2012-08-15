## Dependencies
Here are the list of things you need to install to get this application running:

* _Flask_: A micro web development framework. The installation instructions are [here] (http://flask.pocoo.org/docs/installation/).

* Pygeoip: A Python API for querying MaxMind GeoIP databases. [Here] (http://code.google.com/p/pygeoip/wiki/Install) are the installation instructions.
* numpy: A Python library for a variety of mathematical work. [Here] (http://docs.scipy.org/doc/numpy/user/install.html) are the installation instructions for numpy.
* Matplotlib Toolkits: This toolkits provides many interesting APIs including Basemap which plots maps. This application is using the Basemap module for plotting the world map. [Here] (http://matplotlib.github.com/basemap/users/installing.html) are the installation instructions for matplotlib toolkit.
* I have also used a library py_geo_voronoi. [Here] (https://github.com/Softbass/py_geo_voronoi) is the Github page for this project. I have included py_geo_voronoi's files within my repository. Thanks to the author for the API!

## File by File Description

* voronoi_webapp.py: This is the main Python file which has all the Web application specific code. This application provides an interface for adding/removing mirror servers into the existing list of mirror servers. Any changes made to the list of the servers are reflected in the underlying SQLite database: `serverlist.db`. From this application, a Voronoi map depicting the partitioning of space by the mirror servers can also be generated. Along with the map, the config files required by PowerDNS also get generated.

* voronoi-py.png: This is the image shows the Voronoi diagram (with mirror servers as sites) on a world map.

* schema.sql: This file contains SQL statements which define the schema of the SQLite database in which all the information about the mirror servers is stored.

* serverlist.db: This is SQLite database generated by executing `schema.sql`. The web application goes on to add entries to this database.

* voronoi.py, voronoi_poly.py, globalmaptiles.pyc: These files are taken from the source of [py_geo_voronoi](https://github.com/Softbass/py_geo_voronoi) API. Thanks to the author of this API, I did not have to write a few hundred lines of code.

* rangetocidr.pl: This is the Perl script I made use of to convert IP ranges to CIDR format. Thanks to the authors of the script!

* GeoIPCountryWhois.csv: This is Maxmind's GeoIP database which lists ranges of IP for subnetworks in the world.

* CSVtoDB.py: This file has a history behind it. We were making use of Maxmind's Whois database to obtain a list of subnets across the globe. This database was in CSV format and accessing it was taking a few hours because of its huge size. So, as an optimization, we wrote the CSVtoDB.py script to get the data from thee Whois database into a SQLite database. For more details about this optimization, see [this](http://racheesingh.github.com/2012/08/01/generating-pdns-config-file-optimization/) post.

* whois-schema.sql: This file contains SQL statements to create the database mentioned in the previous point.

* subnetlist.db: This is the SQLite database of all the subnets across the globe as read from the Maxmind Whois database.

* pdns-bind: generated PowerDNS config file.

* pdns-config: generated PowerDNS config file.

## How to Run
Prior to running the application, go to the interactive Python shell and type:
      	 
      	 $ import voronoi_webapp.py
      	 $ voronoi_webapp.init_db()

This is so that the init_db method in voronoi_webapp.py initializes the database that will be used. This has to be done only once. Running the init_db method re-initializes the database with the default server details. 

Now, run the command:

        $ python2 voronoi_webapp.py

And check the results on http://127.0.0.1:5000/ in your web browser.

For being able to add/remove servers, you are required to log in. Here are the login details:

        username: admin
    	password: default

## Credits
* Thanks to [py_geo_voronoi](https://github.com/Softbass/py_geo_voronoi) for their API!
* Thanks to rice.net for the Perl script I used to convert IP address ranges to CIDR notation. Here [ftp://ftp.ripe.net/ripe/stats/issued/range2cidr.pl)] is the full script.

## About
This web application uses [Flask](http://flask.pocoo.org/) web development framework. The applications reads a file containing server locations and names and populates an SQL database with those details. It also allows for adding more server locations and removing any that might not be needed. It plots a Voronoi diagram of the servers sites on a World map. Along with plotting the Voronoi diagram it also generates PowerDNS config files for a geo-backend.
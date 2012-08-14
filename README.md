## Dependencies
Here are the list of things you need to install to get this application running:

* Flask: A micro web development framework. The installation instructions are [here] (http://flask.pocoo.org/docs/installation/).

* Pygeoip: A Python API for querying MaxMind GeoIP databases. [Here] (http://code.google.com/p/pygeoip/wiki/Install) are the installation instructions.
* numpy: A Python library for a variety of mathematical work. [Here] (http://docs.scipy.org/doc/numpy/user/install.html) are the installation instructions for numpy.
* Matplotlib Toolkits: This toolkits provides many interesting APIs including Basemap which plots maps. This application is using the Basemap module for plotting the world map. [Here] (http://matplotlib.github.com/basemap/users/installing.html) are the installation instructions for matplotlib toolkit.
* I have also used a library py_geo_voronoi. [Here] (https://github.com/Softbass/py_geo_voronoi) is the Github page for this project. I have included py_geo_voronoi's files within my repository. Thanks to the author for the API!

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
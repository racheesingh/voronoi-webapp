## How to Run
   $ python2 voronoi_webapp.py

And check the results on http://127.0.0.1:5000/ in your web browser.

## About
This web application uses [Flask](http://flask.pocoo.org/) web development framework. Currently it takes reads a file containing server locations and names and plots the Voronoi diagram on a World map. This is assumed to be the default behavior. In the next few steps, it would allow for adding more server locations and removing any that might not be needed. Also, a RESTful web API will be implemented.
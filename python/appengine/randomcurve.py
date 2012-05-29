import json
import random

import webapp2
from google.appengine.ext import ndb

class Curve(ndb.Model):
  formula = ndb.TextProperty()
  points = ndb.IntegerProperty()


class RandomCurveHandler(webapp2.RequestHandler):
  def get(self):
    curve_key = random.choice(Curve.query().fetch(keys_only=True, batch_size=1000))
    curve = curve_key.get()
    
    self.response.headers['Content-Type'] = 'application/json'
    self.response.write(json.dumps({
        'formula': curve.formula,
        'points': curve.points,
    }))


app = webapp2.WSGIApplication([
  ('/random', RandomCurveHandler),
])

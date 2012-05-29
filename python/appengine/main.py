import webapp2
from google.appengine.ext import ndb
from webapp2_extras import jinja2

import piclang
import model

class BaseHandler(webapp2.RequestHandler):
    @webapp2.cached_property
    def jinja2(self):
        return jinja2.get_jinja2(app=self.app)
    
    def render_template(self, filename, **template_args):
        self.response.write(self.jinja2.render_template(filename, **template_args))


class IndividualHandler(BaseHandler):
  def get(self, id):
    individual = model.Individual.get_by_id(int(id))
    if not individual:
        self.error(404)
        return
    genome = []
    for instruction in individual.genome:
        if isinstance(instruction, type) and issubclass(instruction, piclang.Curve):
            genome.append(instruction.__name__)
        else:
            genome.append(repr(instruction))
    genome = ' '.join(genome)
    self.render_template('individual.html', individual=individual, genome=genome)


app = webapp2.WSGIApplication([
  (r'/individual/(\d+)', IndividualHandler),
])

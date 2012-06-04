import logging
import random
import threading
import webapp2
from google.appengine.api import memcache
from google.appengine.ext.deferred import defer
from google.appengine.ext import ndb
from webapp2_extras import jinja2

import evolve
import piclang
import model

organism_generation = None
all_organisms = None
organisms_lock = threading.Lock()

def get_random_organisms(generation, num=1):
    global organism_generation, all_organisms

    if organism_generation is None or generation != organism_generation:
        
        with organisms_lock:
            organism_generation = generation
            all_organisms = model.Individual.query(model.Individual.generation == generation).fetch()
    
    return random.sample(all_organisms, num)


class BaseHandler(webapp2.RequestHandler):
    @webapp2.cached_property
    def jinja2(self):
        return jinja2.get_jinja2(app=self.app)
    
    def render_template(self, filename, **template_args):
        self.response.write(self.jinja2.render_template(filename, **template_args))

def genome_repr(g):
    genome = []
    for instruction in g:
        if isinstance(instruction, type) and issubclass(instruction, piclang.Curve):
            genome.append(instruction.__name__)
        elif isinstance(instruction, float):
            genome.append("%.3f" % instruction)
        elif isinstance(instruction, tuple):
            genome.append("(%.3f, %.3f)" % instruction)
        elif instruction == piclang.boustro:
            genome.append("boustro")
        else:
            genome.append(repr(instruction))
    return ' '.join(genome)

class IndividualHandler(BaseHandler):
  def get(self, id):
    individual = model.Individual.get_by_id(int(id))
    if not individual:
        self.error(404)
        return
    children = model.Individual.query(model.Individual.parents == individual.key).fetch(keys_only=True)
    genome = genome_repr(individual.genome)
    expression = piclang.stackparse(individual.genome)
    self.render_template('individual.html', individual=individual, genome=genome, expression=expression, children=children)

class HomepageHandler(BaseHandler):
    def get(self):
        generation = memcache.get('current_generation')
        if not generation:
            generation = model.Generation.query().order(-model.Generation.number).get().number
            memcache.set('current_generation', generation)
        
        winner = int(self.request.GET.get('winner', 0))
        loser = int(self.request.GET.get('loser', 0))
        if winner and loser:
            model.Vote.record(ndb.Key(model.Individual, loser), ndb.Key(model.Individual, winner), generation)
        
        i1, i2 = get_random_organisms(generation, 2)
        self.render_template('index.html', generation=generation, i1=i1, i2=i2, winner=winner)

class CronNextGenHandler(webapp2.RequestHandler):
    def get(self):
        last_generation = model.Generation.query().order(-model.Generation.number).get()
        votes = model.Vote.query(model.Vote.generation == last_generation.number).fetch()
        num_votes = sum(v.count for v in votes)
        logging.debug("Counted %d votes for %d individuals.", num_votes, last_generation.num_individuals)
        if num_votes > last_generation.num_individuals * 5:
            defer(evolve.next_generation)
        

app = webapp2.WSGIApplication([
  (r'/individual/(\d+)', IndividualHandler),
  (r'/', HomepageHandler),
  (r'/_ah/cron/nextgen', CronNextGenHandler),
])

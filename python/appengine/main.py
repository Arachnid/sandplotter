import datetime
import hashlib
import hmac
import json
import logging
import os
import random
import time
import threading
import webapp2
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext.deferred import defer
from google.appengine.ext import ndb
from webapp2_extras import jinja2

import config
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
    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        self._generation = None

    @webapp2.cached_property
    def jinja2(self):
        return jinja2.get_jinja2(app=self.app)
    
    def render_template(self, filename, **template_args):
        self.response.write(self.jinja2.render_template(filename, **template_args))

    @property
    def generation(self):
        if not self._generation:
            self._generation = memcache.get('current_generation')
            if not self._generation:
                self._generation = model.Generation.query().order(-model.Generation.number).get().number
                memcache.set('current_generation', self._generation)
        return self._generation


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
    parents = ndb.get_multi(individual.parents)
    children = model.Individual.query(model.Individual.parents == individual.key).fetch()
    genome = genome_repr(individual.genome)
    expression = piclang.stackparse(individual.genome)
    self.render_template('individual.html',
        individual=individual,
        genome=genome,
        expression=expression,
        children=children,
        parents=parents)


class HomepageHandler(BaseHandler):
    def get(self):
        self.render_template('index.html', active='home')


class MatchupHandler(BaseHandler):
    def get_auth_token(self, id1, id2, generation, nonce=None):
        if id1 > id2:
            id1, id2 = id2, id1
        if nonce is None:
            nonce = os.urandom(8).encode('base64')
        token_text = "%d,%d,%d,%s" % (id1, id2, generation, nonce)
        token_hash = hmac.new(config.token_key, token_text, hashlib.sha1).hexdigest()
        return "%s,%s" % (token_hash, nonce)

    def verify_token(self, token, id1, id2, generation):
        token_hash, nonce = token.split(",")
        return token == self.get_auth_token(id1, id2, generation, nonce=nonce)

    def record_vote(self, winner, loser, generation, auth_token):
        if not self.verify_token(auth_token, winner, loser, generation):
            logging.warn("Discarded vote (%d -> %d) with invalid token %s", loser, winner, auth_token)
            return
        if not memcache.add(auth_token, True):
            logging.warn("Discarded vote (%d -> %d) with already used token %s", loser, winner, auth_token)
            return
        model.Vote.record(ndb.Key(model.Individual, loser), ndb.Key(model.Individual, winner), generation)
        vote_total = memcache.incr("votes", 1)
        if vote_total is None or vote_total > 500:
            # Vote counter has been evicted, or we're ready for a new generation
            interval = datetime.datetime.now().replace(second=0, microsecond=0)
            try:
                defer(evolve.check_vote_count, _name="check_vote_count-%s" % interval.strftime("%Y%m%d%H%M"))
            except (taskqueue.TaskAlreadyExistsError, taskqueue.TombstonedTaskError), e:
                pass
        logging.info("Recorded vote %d -> %d", loser, winner)
        return vote_total

    def post(self):
        time.sleep(2)
        winner = int(self.request.POST.get('winner', 0))
        loser = int(self.request.POST.get('loser', 0))
        if winner and loser:
            num_votes = self.record_vote(winner, loser, self.generation, self.request.POST.get('auth_token'))
        else:
            num_votes = memcache.get("votes")
        
        i1, i2 = get_random_organisms(self.generation, 2)
        self.response.write(json.dumps({
            'auth_token': self.get_auth_token(i1.key.id(), i2.key.id(), self.generation),
            'generation': self.generation,
            'i1': i1.as_dict(512),
            'i2': i2.as_dict(512),
            'progress': num_votes and "%.1f" % (min(num_votes / 500.0, 1.0) * 100,)
        }))


class BestHandler(BaseHandler):
    def get_best(self, generation, count):
        return model.Individual.query(model.Individual.generation == generation).order(model.Individual.rank).fetch(count)
        
    def get(self):
        bests = [(gen, self.get_best(gen, 5)) for gen in range(self.generation - 1, 0, -1)]
        self.render_template('best.html', bests=bests, active='best')


app = webapp2.WSGIApplication([
  (r'/', HomepageHandler),
  (r'/matchup', MatchupHandler),
  (r'/individual/(\d+)', IndividualHandler),
  (r'/best', BestHandler),
])

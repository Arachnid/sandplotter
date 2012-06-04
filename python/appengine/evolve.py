import bisect
import collections
import logging
import math
import random

from google.appengine.api import memcache
from google.appengine.ext import ndb

import ga
import model

ERROR_THRESHOLD = 0.01
DAMPING_FACTOR = 0.85

def pagerank(scores, edges):
    new_scores = dict((k, 0.0) for k in scores.keys())
    residual_score = (1 - DAMPING_FACTOR)
    for owner, score in scores.iteritems():
        score *= DAMPING_FACTOR
        links = edges[owner]
        if not links:
            # Sink
            residual_score += score
        else:
            total_weight = float(sum(x[1] for x in links))
            for target, weight in links:
                new_scores[target] += (weight / total_weight) * score
    residual_score /= len(new_scores)
    for owner in new_scores:
        new_scores[owner] += residual_score
    return new_scores

def rms_error(a, b):
    total_error = 0.0
    count = 0
    for k in a:
        count += 1
        total_error += math.sqrt(abs(b[k] - a[k]))
    return (total_error / count) ** 2

def score_generation(generation_id):
    """Scores and ranks a generation of individuals."""
    individuals = model.Individual.query(model.Individual.generation == generation_id).fetch()
    individuals = dict((x.key, x) for x in individuals)
    scores = dict((i.key, i.score or 0) for i in individuals.values())

    votes = model.Vote.query(model.Vote.generation == generation_id).fetch()
    edges = collections.defaultdict(list)
    for vote in votes:
        edges[vote.loser].append((vote.winner, vote.count))

    new_scores = pagerank(scores, edges)
    steps = 1
    while rms_error(scores, new_scores) > ERROR_THRESHOLD:
        scores = new_scores
        new_scores = pagerank(scores, edges)
        steps += 1
    logging.debug("Scores stabilized after %d steps", steps)
    score_rank = sorted(new_scores.items(), key=lambda (k, v): v, reverse=True)
    for rank, (key, score) in enumerate(score_rank):
        individuals[key].rank = rank
        individuals[key].score = score
    ndb.put_multi(individuals.values())
    return individuals.values()

class WeightedRandomGenerator(object):
    def __init__(self, weights):
        self.totals = []
        running_total = 0
        
        for w in weights:
            running_total += w
            self.totals.append(running_total)
    
    def next(self):
        rnd = random.random() * self.totals[-1]
        return bisect.bisect_right(self.totals, rnd)


def new_generation(next_generation_id, num_individuals, individuals=None):
    if not individuals:
        individuals = model.Individual.query(model.Individual.generation == next_generation_id - 1).fetch()
    weights = WeightedRandomGenerator(i.score for i in individuals)

    nextgen = []
    while len(nextgen) < num_individuals:
        i1 = individuals[weights.next()]
        i2 = individuals[weights.next()]
        for genome in ga.crossbreed(i1.genome, i2.genome):
            child = model.Individual.create(
                genome=genome,
                generation=next_generation_id,
                parents=[i1.key, i2.key])
            if child:
                nextgen.append(child)
        logging.debug("Generated %d individuals", len(nextgen))
    
    generation = model.Generation(id=next_generation_id, number=next_generation_id, num_individuals=len(nextgen))
    nextgen.append(generation)
    ndb.put_multi(nextgen)
    memcache.set('current_generation', next_generation_id)


def next_generation():
    last_generation = model.Generation.query().order(-model.Generation.number).get()
    individuals = score_generation(last_generation.number)
    new_generation(last_generation.number + 1, 100, individuals=individuals)

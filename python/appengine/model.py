import random

from google.appengine.api import files
from google.appengine.api import images
from google.appengine.ext import ndb

import piclang

class Individual(ndb.Model):
    genome = ndb.PickleProperty(compressed=True)
    generation = ndb.IntegerProperty(required=True)
    parents = ndb.KeyProperty(kind='Individual', repeated=True)
    score = ndb.FloatProperty() # Fitness score within this generation
    rank = ndb.IntegerProperty() # Rank within this generation
    image = ndb.BlobKeyProperty(required=True)
    random = ndb.ComputedProperty(lambda self: random.random())

    @classmethod
    def create(cls, genome, generation, parents, store=False):
        fun = piclang.stackparse(genome)
        if piclang.is_atom(fun):
            return None
        image = piclang.render(fun, points=8192)
        if not image:
            return None
        filename = files.blobstore.create(mime_type='image/png')
        with files.open(filename, 'a') as f:
            image.save(f, "PNG")
        files.finalize(filename)
        blob_key = files.blobstore.get_blob_key(filename)
        individual = cls(
            genome=genome,
            generation=generation,
            parents=parents,
            image=blob_key
        )
        if store:
            individual.put()
        return individual

    def image_url(self, size=None):
        return images.get_serving_url(self.image, size=size)

    def as_dict(self, size=None):
        return {'id': self.key.id(), 'image': self.image_url(size)}


class Vote(ndb.Model):
    loser = ndb.KeyProperty(kind=Individual, required=True)
    winner = ndb.KeyProperty(kind=Individual, required=True)
    generation = ndb.IntegerProperty(required=True)
    count = ndb.IntegerProperty(default=0)

    @classmethod
    def record(cls, loser, winner, generation):
        def _tx():
            id = "%d/%d" % (loser.id(), winner.id())
            vote = cls.get_by_id(id)
            if not vote:
                vote = cls(id=id, loser=loser, winner=winner, generation=generation)
            vote.count += 1
            vote.put()
        ndb.transaction(_tx)


class Generation(ndb.Model):
    number = ndb.IntegerProperty(required=True)
    num_individuals = ndb.IntegerProperty(required=True)

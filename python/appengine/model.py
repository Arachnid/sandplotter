from google.appengine.api import files
from google.appengine.api import images
from google.appengine.ext import ndb

import piclang

class Individual(ndb.Model):
    genome = ndb.PickleProperty(compressed=True)
    generation = ndb.IntegerProperty(required=True)
    parents = ndb.KeyProperty(kind='Individual', repeated=True)
    fitness = ndb.IntegerProperty(default=1500)
    matches = ndb.IntegerProperty(default=0)
    image = ndb.BlobKeyProperty(required=True)

    @classmethod
    def create(cls, genome, generation, parents):
        fun = piclang.stackparse(genome)
        image = piclang.render(fun, points=8192)
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
        individual.put()
        return individual

    @property
    def image_url(self):
        return images.get_serving_url(self.image)

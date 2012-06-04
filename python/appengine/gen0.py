import evolve
import model
from piclang import *

gen0_genomes = [
    [circle, line, scale], # Spiral
    [circle, circle, 20, repeat, scale], # Crosshatched diamond
    [circle, line, scale, boustro, 30, repeat, circle, 30, step, rotate], # In/Out spiral
    [circle, 29, repeat, line, boustro, 30, repeat, scale], # Hypnotic spirograph pattern
    [line, boustro, 32, repeat, circle, 5, repeat, rotate, 0.7, scale], # Lotus spirograph pattern
    [circle, 5, repeat, line, scale, circle, 5, repeat, line, scale, circle, 5, repeat, line, scale, scale, scale], # circle^3 spiral
    [circle, (1, 0), scale, line, (0, 1), scale, translate], # Sine wave
    [circle, circle, (1, 0), scale, circle, (0, 1), rotate, (0, 1), scale, translate, 8, repeat, 1.9, translate, scale, 1/2.8, scale],
    [circle, 20, repeat, line, translate, (-1, -1), translate], # Diagnonal row of circles
    [circle, 2, repeat, line, 0.3, scale, 0.1, translate, scale, circle, 50, repeat, line, 0.05, scale, 0.05, translate, scale, translate], # Nautilus spiral
    [circle, (0, 1), scale, 20, step, line, 2, scale, -1, translate, 20, repeat, scale, line, (1, 0), scale, translate], # Sine wave zigzag
    [circle, 5, repeat, (0, 1), scale, circle, 3, repeat, (1, 0), scale, translate], # Oscilloscope pattern
    [circle, 30, repeat, 0.8, scale, circle, 61, repeat, 0.2, scale, translate], # Spirograph
    [circle, 30, repeat, 0.8, scale, circle, 61, repeat, line, 0.5, scale, 0.2, translate, scale, translate], # Spirograph spiral
    [circle, (0.2, 0), scale, (1, 0), translate, 40, repeat, circle, rotate, 0.5, scale], # Zigzag circle
    [circle, (0.2, 0), scale, (1, 0), translate, 400, repeat, circle, 10, repeat, line, 0.1, translate, scale, rotate, 0.8, scale], # Zigzag circle spiral
]

def init():
    for genome in gen0_genomes:
        model.Individual.create(genome=genome, generation=0, parents=[]).put()
    model.Generation(number=0, num_individuals=len(gen0_genomes)).put()
    evolve.next_generation()
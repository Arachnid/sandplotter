import inspect
import random

import piclang

ATOM_MUTATION_RATE = 1.0 # Atom mutations per organism
OP_MUTATION_RATE = 0.5 # Operator mutations per organism
CHANGE_TYPE_PROBABILITY = 0.1 # Chance an atom will change type

def cut_and_splice(g1, g2):
    p1 = random.randrange(len(g1))
    p2 = random.randrange(len(g2))
    return g1[:p1] + g2[p2:], g2[:p2] + g1[p1:]

def mutate(genome):
    atom_probability = ATOM_MUTATION_RATE / len(genome)
    op_probability = OP_MUTATION_RATE / len(genome)
    for i in range(len(genome)):
        if isinstance(genome[i], (int, float, tuple, piclang.PlatonicCircle, piclang.PlatonicLine)):
            if random.random() < atom_probability:
                genome[i] = mutate_atom(genome[i])
        else:
            if random.random() < op_probability:
                genome[i] = mutate_op(genome[i])
    return genome

def mutate_atom(instruction):
    if random.random() < CHANGE_TYPE_PROBABILITY:
        return random_atom(instruction)
    if isinstance(instruction, (int, float)):
        return mutate_number(instruction)
    if isinstance(instruction, tuple):
        if random.random < 0.5:
            return (instruction[0], mutate_number(instruction[1]))
        else:
            return (mutate_number(instruction[0]), instruction[1])
    atom_curves = (piclang.PlatonicCircle, piclang.PlatonicLine)
    if isinstance(instruction, atom_curves):
        return random.choice(atom_curves)()
    return instruction

def random_atom(old_atom=None):
    typ = random.choice([float, tuple, piclang.PlatonicCircle, piclang.PlatonicLine])
    if typ == float:
        return random.random()
    if typ == tuple:
        return (random.random(), random.random())
    return typ()

def mutate_number(num):
    if random.random() < 0.5:
        # Smaller
        return num * (1 - random.random() * 0.5)
    else:
        # Bigger
        return num * (1 + random.random())

def mutate_op(instruction):
    ops = [piclang.translate, piclang.scale, piclang.rotate, piclang.reverse, piclang.concat, piclang.repeat, piclang.step]
    return random.choice(ops)

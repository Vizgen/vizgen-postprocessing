from enum import Flag


class Entity(Flag):
    Unknown = 0
    Nucleus = 1
    Cells = 2


def parse_entity(name: str) -> Entity:
    name = name.lower()
    if name == 'cell' or name == 'cells':
        return Entity.Cells
    if name == 'nuclei' or name == 'nucleus':
        return Entity.Nucleus
    return Entity.Unknown

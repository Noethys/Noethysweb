from django import template

register = template.Library()

@register.simple_tag
def dict_get_item_2d(dictionary, famille_id, structure_id):
    """
    Retourne dictionary[(famille_id, structure_id)] s'il existe, sinon 0 ou None
    """
    return dictionary.get((famille_id, structure_id), 0)

@register.simple_tag
def dict_get_item_3d(dictionary, famille_id, structure_id, individu_id):
    """
    Retourne dictionary[(famille_id, structure_id, individu_id)] s'il existe, sinon 0 ou None
    """
    return dictionary.get((famille_id, structure_id, individu_id), 0)
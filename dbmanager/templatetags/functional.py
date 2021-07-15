from django import template

register = template.Library()


@register.filter(name='map')
def map_elements(value, f):
    f = str(f)

    def map_element(x):
        if hasattr(x, f):
            attr = getattr(x, f)
            return attr() if callable(attr) else attr
        elif f in globals():
            return globals()[f](x)
        else:
            raise ValueError('No function {} found for value of type {}'.format(f, type(x)))

    #for x in value:
    #    yield map_element(x)
    return map(map_element, value)


@register.filter(name='tolist')
def tolist(values):
    return list(values)


@register.filter(name='except')
def Except(value, exception):
    for x in value:
        if x != exception:
            yield x

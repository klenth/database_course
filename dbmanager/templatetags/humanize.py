from django import template

register = template.Library()

PREFIXES = (
    'bytes',
    'kiB',
    'MiB',
    'GiB',
    'TiB',
    'PiB',
    'EiB',
    'ZiB',
    'YiB'
)


@register.filter(name='filesize', is_safe=True)
def filesize(value):
    try:
        bytes = int(value)
        level = 0

        while bytes >= 1024 and level + 1 < len(PREFIXES):
            bytes /= 1024
            level += 1

        result = '{:.1f} {}'.format(bytes, PREFIXES[level])
        print('{} -> {}'.format(value, result))
        return result
    except TypeError:
        return ''

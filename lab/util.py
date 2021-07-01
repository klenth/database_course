import re

_COPY_PREFIX_PATTERN = re.compile(r'^Copy( \d+)? of (.*)$')


def unique_duplicate_name(base_name, existing_names):
    """Returns a unique name for a duplicate.
        base_name: the name of the item being duplicated
        existing_names: an iterable of names that the generated name must not conflict with.

    The returned name is guaranteed to never be the same as base_name or any of the existing_names. The generated name
    will be in the form of 'Copy of {base_name}', 'Copy 2 of {base_name}', etc. If base_name is already in this form,
    numbering will continue from its current form (base_name of 'Copy of Test' may be 'Copy 2 of Test' but not
    'Copy of Copy of Test').
    """
    count = 1

    existing_names = set([n.lower() for n in existing_names])

    m = _COPY_PREFIX_PATTERN.match(base_name)
    if m:
        base_name = m.group(2)
        if m.group(1):
            count = int(m.group(1).strip()) + 1
        else:
            count = 2

    def copy_name(n):
        return f'Copy of {base_name}' if n == 1 else f'Copy {n} of {base_name}'

    candidate_name = copy_name(count)
    while candidate_name.lower() in existing_names:
        count += 1
        candidate_name = copy_name(count)

    return candidate_name


def validate_password(password):
    has_lower, has_upper, has_digit, has_nonalpha, has_noncased = (False,) * 5
    for c in password:
        if c.islower():
            has_lower = True
        if c.isupper():
            has_upper = True
        if '0' <= c <= '9':
            has_digit = True
        if not c.isalpha():
            has_nonalpha = True
        if c.isalpha() and not c.islower() and not c.isupper():
            has_noncased = True

    count = sum(map(lambda b: int(b), (has_lower, has_upper, has_digit, has_nonalpha, has_noncased)))
    return len(password) >= 8 and count >= 3

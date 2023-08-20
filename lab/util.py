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


def separate_mysql_statements(text):
    """Tokenizes MySQL code into statements (by splitting on ; characters). Treats ; characters inside comments/strings
correctly. Returns a generator of strings."""

    while len(text) > 0:
        delimiter_index = find_mysql_statement_delimiter(text)
        statement = text[:delimiter_index].strip()
        if statement:
            yield statement
        text = text[(delimiter_index+1):]


def find_mysql_statement_delimiter(text):
    from enum import Enum

    class State(Enum):
        General = 1
        MaybeLineComment1 = 21          # have seen '-'
        MaybeLineComment2 = 22          # have seen '--'
        LineComment = 23                # have seen '-- '
        MaybeBlockComment = 31          # have seen '/'
        BlockComment = 32               # have seen '/*'
        MaybeBlockCommentEnd = 33       # have seen '/* ... *'
        SingleQuotedString = 41         # have seen "'"
        MaybeSingleQuotedStringEnd = 42 # have seen "'...'"
        SingleQuotedEscape = 43         # have seen "'...\"
        DoubleQuotedString = 51         # have seen '"'
        MaybeDoubleQuotedStringEnd = 52 # have seen '"..."'
        DoubleQuotedEscape = 53         # have seen '"...\'
        End = 100                       # have seen ;

    _ = State
    transitions = {
        (_.General, '-'):               _.MaybeLineComment1,
        (_.General, '/'):               _.MaybeBlockComment,
        (_.General, "'"):               _.SingleQuotedString,
        (_.General, '"'):               _.DoubleQuotedString,
        (_.General, ';'):               _.End,
        (_.General, None):              _.General,

        (_.MaybeLineComment1, '-'):     _.MaybeLineComment2,
        (_.MaybeLineComment1, '\n'):    _.General,
        (_.MaybeLineComment1, None):    _.General,

        (_.MaybeLineComment2, ' '):     _.LineComment,
        (_.MaybeLineComment2, '\n'):    _.General,
        (_.MaybeLineComment2, None):    _.General,

        (_.LineComment, '\n'):          _.General,
        (_.LineComment, None):          _.LineComment,

        (_.MaybeBlockComment, '*'):     _.BlockComment,
        (_.MaybeBlockComment, None):    _.General,

        (_.BlockComment, '*'):          _.MaybeBlockCommentEnd,
        (_.BlockComment, None):         _.BlockComment,

        (_.MaybeBlockCommentEnd, '/'):  _.General,
        (_.MaybeBlockCommentEnd, '*'):  _.MaybeBlockCommentEnd,
        (_.MaybeBlockCommentEnd, None): _.BlockComment,

        (_.SingleQuotedString, "'"):    _.MaybeSingleQuotedStringEnd,
        (_.SingleQuotedString, "\\"):   _.SingleQuotedEscape,
        (_.SingleQuotedString, "\n"):   _.General,
        (_.SingleQuotedString, None):   _.SingleQuotedString,

        (_.MaybeSingleQuotedStringEnd, "'"):    _.SingleQuotedString,
        (_.MaybeSingleQuotedStringEnd, ';'):    _.End,
        (_.MaybeSingleQuotedStringEnd, None):   _.General,

        (_.SingleQuotedEscape, '\n'):           _.General,
        (_.SingleQuotedEscape, None):           _.SingleQuotedString,

        (_.DoubleQuotedString, '"'):            _.MaybeDoubleQuotedStringEnd,
        (_.DoubleQuotedString, '\\'):           _.DoubleQuotedEscape,
        (_.DoubleQuotedString, '\n'):           _.General,
        (_.DoubleQuotedString, None):           _.DoubleQuotedString,

        (_.MaybeDoubleQuotedStringEnd, '"'):    _.DoubleQuotedString,
        (_.MaybeDoubleQuotedStringEnd, ';'):    _.End,
        (_.MaybeDoubleQuotedStringEnd, None):   _.General,

        (_.DoubleQuotedEscape, '\n'):           _.General,
        (_.DoubleQuotedEscape, None):           _.DoubleQuotedString,
    }

    state = State.General
    index = len(text)
    for i in range(len(text)):
        c = text[i]
        if (state, c) in transitions:
            state = transitions[(state, c)]
        elif (state, None) in transitions:
            state = transitions[(state, None)]
        else:
            raise RuntimeError(f'No transition for ({state}, c)!')

        if state == _.End:
            index = i
            break

    return index

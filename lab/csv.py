class CsvReader:

    def __init__(self, input):
        self.input = input

    def __iter__(self):
        return self

    def __next__(self):
        line = self.input.readline()
        if line == '':
            raise StopIteration

        if line[-2:] == '\r\n':
            line = line[:-2]
        elif line[-1] == '\n':
            line = line[:-1]

        start_index = 0
        fields = []
        while start_index < len(line):
            end_index = self._find_next_field(line, start_index) or len(line)
            field_raw = line[start_index:end_index]

            if field_raw == '\\N':
                fields.append(None)
            else:
                fields.append(CsvReader._unescape(field_raw))

            start_index = end_index + 1

        return fields

    def _find_next_field(self, line, start_index):
        i = start_index
        inside_quotes = False
        while i < len(line):
            c = line[i]
            if c == '"':
                inside_quotes = not inside_quotes
            elif c == ',' and not inside_quotes:
                return i
            elif c == '\\':
                if i + 1 == len(line):
                    break
                elif line[i + 1] == '"':
                    i += 1
            i += 1

        return None

    @staticmethod
    def _unescape(s):
        if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
            s = s[1:-1]

        u = ''
        i = 0
        while i < len(s):
            if s[i] == '\\' and i + 1 < len(s):
                i += 1
            u += s[i]
            i += 1

        return u


class CsvWriter:

    def __init__(self, output):
        self.output = output

    @staticmethod
    def _field_str(f):
        if f is None:
            return '\\N'
        elif isinstance(f, str):
            needs_quotes = False
            s = ''
            for c in f:
                if c == '"':
                    needs_quotes = True
                    s += '\\"'
                elif c == '\\':
                    s += '\\\\'
                elif c == ',':
                    needs_quotes = True
                    s += ','
                else:
                    s += c
            if needs_quotes:
                return f'"{s}"'
            else:
                return s
        else:
            return str(f)

    def writerow(self, row):
        print(','.join([CsvWriter._field_str(f) for f in row]), file=self.output, end='\n')

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

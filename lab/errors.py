# An error that occurred in the database connection or code executed on it
class SqlError(RuntimeError):
    pass


# An error that signifies an error with the problem configuration
class ProblemError(RuntimeError):
    pass


# An error that signifies an error with student code
class StudentCodeError(RuntimeError):
    pass


class DataFileMissingError(RuntimeError):
    pass

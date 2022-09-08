from util import separate_mysql_statements


def test_separate_mysql_statements():
    TEST_STRINGS = (
        """A""",
        """SELECT x FROM Table""",
        """SELECT x FROM Table;""",
        """A; B; C""",
        """A; B; C;""",
        """SELECT ';', x FROM Table""",
        """-- C;
SELECT 'first;!';
-- C;
SELECT 'second;!';""",
        """SELECT ''';'""",
        """SELECT '';'""",
    )

    for text in TEST_STRINGS:
        print('--- New test ---')
        print('Input:')
        print(text)
        print('-')

        i = 0
        for statement in separate_mysql_statements(text):
            print(f'[Statement {i}]')
            print(statement.strip())
            i += 1
        print()


if __name__ == '__main__':
    test_separate_mysql_statements()

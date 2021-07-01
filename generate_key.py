#!/usr/bin/env python3

def main():
    import random
    import string

    CHARS = string.ascii_letters + string.digits + string.punctuation
    print(''.join([random.choice(CHARS) for _ in range(50)]))


if __name__ == '__main__':
    main()

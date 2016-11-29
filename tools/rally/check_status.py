#!/usr/bin/env python

from __future__ import print_function

import json
import sys


def main():
    data = json.loads(sys.stdin.read())
    if data["failures"] == 0:
        print("Tests succeeded")
        sys.exit(0)
    else:
        print("Tests failed: %d" % data["failures"])
        sys.exit(1)


if __name__ == "__main__":
    main()

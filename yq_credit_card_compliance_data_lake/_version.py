# -*- coding: utf-8 -*-

from importlib.metadata import version

from .paths import PACKAGE_NAME

__version__ = version(PACKAGE_NAME)

if __name__ == "__main__":
    print(__version__)

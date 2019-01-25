# coding=utf-8
from __future__ import unicode_literals

import collections
import re

__version__ = "1.1.8a0"
__author__ = "Artist Growth"
__contact__ = "dev@artistgrowth.com"
__homepage__ = "https://artistgrowth.com"

version_info_t = collections.namedtuple("version_info_t", (
    "major", "minor", "build", "modifier",
))

_temp = re.match(
    r"(\d+)\.(\d+).(\d+)((?:-).+)?", __version__).groups()
VERSION = version_info = version_info_t(
    int(_temp[0]), int(_temp[1]), int(_temp[2]), _temp[3] or "")

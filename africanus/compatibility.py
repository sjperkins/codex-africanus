# -*- coding: utf-8 -*-
# flake8: noqa

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import functools
import sys

PY3 = sys.version_info[0] == 3
PY2 = sys.version_info[0] == 2

if PY3:
    import builtins
    range = range
    reduce = functools.reduce
    zip = zip
    unicode = str
    string_types = (str,)
elif PY2:
    import __builtin__ as builtins
    range = xrange
    reduce = reduce
    from itertools import izip as zip
    unicode = unicode
    string_types = (basestring,)

else:
    raise ValueError("Unknown python version %s" % (sys.version_info,))

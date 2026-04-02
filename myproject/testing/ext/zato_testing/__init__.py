# -*- coding: utf-8 -*-

"""
Copyright (C) 2025, Zato Source s.r.o. https://zato.io

Licensed under AGPLv3, see LICENSE.txt for terms and conditions.
"""

# Zato
from zato_testing._version import __version__
from zato_testing.importer import install_zato_importer as _install
from zato_testing.service import Model, Service
from zato_testing.test_case import ServiceTestCase

_install()

__all__ = [
    '__version__',
    'Model',
    'Service',
    'ServiceTestCase',
]

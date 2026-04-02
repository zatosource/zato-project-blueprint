# -*- coding: utf-8 -*-

"""
Copyright (C) 2025, Zato Source s.r.o. https://zato.io

Licensed under AGPLv3, see LICENSE.txt for terms and conditions.
"""

# stdlib
import sys
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from inspect import isclass
from types import ModuleType

# ################################################################################################################################
# ################################################################################################################################

if 0:
    from zato_testing.typing_ import any_, strnone, type_

# ################################################################################################################################
# ################################################################################################################################

_finder_installed = False
_service_registry:'dict' = {}

# ################################################################################################################################
# ################################################################################################################################

class ZatoTestingLoader(Loader):
    """ Loader for fake Zato modules.
    """

    def __init__(self, zato_testing_module:'ModuleType') -> 'None':
        self._zato_testing_module = zato_testing_module

# ################################################################################################################################

    def create_module(self, spec:'ModuleSpec') -> 'ModuleType':
        return self._zato_testing_module

# ################################################################################################################################

    def exec_module(self, module:'ModuleType') -> 'None':
        pass

# ################################################################################################################################
# ################################################################################################################################

class ZatoImportFinder(MetaPathFinder):
    """ Finder for fake Zato modules.
    """
    _zato_modules = {
        'zato.server.service': None,
        'zato.common.marshal_.api': None,
    }

    def __init__(self) -> 'None':
        self._fake_modules:'dict' = {}
        self._setup_fake_modules()

# ################################################################################################################################

    def _setup_fake_modules(self) -> 'None':
        from zato_testing import service as service_module
        from zato_testing import model as model_module
        from zato_testing import adapters as adapters_module

        zato_server_service = ModuleType('zato.server.service')
        zato_server_service.Service = service_module.Service  # type: ignore
        zato_server_service.Model = model_module.Model  # type: ignore
        zato_server_service.RESTAdapter = adapters_module.RESTAdapter  # type: ignore

        zato_common_marshal = ModuleType('zato.common.marshal_.api')
        zato_common_marshal.Model = model_module.Model  # type: ignore

        from zato_testing import exception as exception_module

        zato_common_exception = ModuleType('zato.common.exception')
        zato_common_exception.ZatoException = exception_module.ZatoException  # type: ignore
        zato_common_exception.BadRequest = exception_module.BadRequest  # type: ignore
        zato_common_exception.Conflict = exception_module.Conflict  # type: ignore
        zato_common_exception.Forbidden = exception_module.Forbidden  # type: ignore
        zato_common_exception.MethodNotAllowed = exception_module.MethodNotAllowed  # type: ignore
        zato_common_exception.NotFound = exception_module.NotFound  # type: ignore
        zato_common_exception.Unauthorized = exception_module.Unauthorized  # type: ignore
        zato_common_exception.TooManyRequests = exception_module.TooManyRequests  # type: ignore
        zato_common_exception.InternalServerError = exception_module.InternalServerError  # type: ignore
        zato_common_exception.ServiceUnavailable = exception_module.ServiceUnavailable  # type: ignore
        zato_common_exception.Inactive = exception_module.Inactive  # type: ignore
        zato_common_exception.Reportable = exception_module.Reportable  # type: ignore

        from zato_testing import typing_ as typing_module

        zato_common_typing = ModuleType('zato.common.typing_')
        for name in dir(typing_module):
            if not name.startswith('_'):
                setattr(zato_common_typing, name, getattr(typing_module, name))

        self._fake_modules['zato'] = ModuleType('zato')
        self._fake_modules['zato.server'] = ModuleType('zato.server')
        self._fake_modules['zato.server.service'] = zato_server_service
        self._fake_modules['zato.common'] = ModuleType('zato.common')
        self._fake_modules['zato.common.exception'] = zato_common_exception
        self._fake_modules['zato.common.typing_'] = zato_common_typing
        self._fake_modules['zato.common.marshal_'] = ModuleType('zato.common.marshal_')
        self._fake_modules['zato.common.marshal_.api'] = zato_common_marshal

        self._fake_modules['zato'].server = self._fake_modules['zato.server']  # type: ignore
        self._fake_modules['zato'].common = self._fake_modules['zato.common']  # type: ignore
        self._fake_modules['zato.server'].service = zato_server_service  # type: ignore
        self._fake_modules['zato.common'].marshal_ = self._fake_modules['zato.common.marshal_']  # type: ignore
        self._fake_modules['zato.common.marshal_'].api = zato_common_marshal  # type: ignore

# ################################################################################################################################

    def find_spec(
        self,
        fullname:'str',
        path:'any_',
        target:'any_'=None
        ) -> 'ModuleSpec | None':
        if fullname in self._fake_modules:
            return ModuleSpec(
                fullname,
                ZatoTestingLoader(self._fake_modules[fullname]),
                is_package=('.' not in fullname or fullname.endswith('_')),
            )
        return None

# ################################################################################################################################
# ################################################################################################################################

def install_zato_importer() -> 'None':
    """ Installs the Zato import finder.
    """
    global _finder_installed
    if not _finder_installed:
        finder = ZatoImportFinder()
        sys.meta_path.insert(0, finder)
        for name, module in finder._fake_modules.items():
            sys.modules[name] = module
        _finder_installed = True

# ################################################################################################################################

def uninstall_zato_importer() -> 'None':
    """ Uninstalls the Zato import finder.
    """
    global _finder_installed
    global _service_registry
    if _finder_installed:
        sys.meta_path = [item for item in sys.meta_path if not isinstance(item, ZatoImportFinder)]
        for name in list(sys.modules.keys()):
            if name.startswith('zato.'):
                del sys.modules[name]
        if 'zato' in sys.modules:
            del sys.modules['zato']
        _finder_installed = False
        _service_registry = {}

# ################################################################################################################################

def register_service(service_class:'type_') -> 'None':
    """ Registers a service class by its name.
    """
    from zato_testing.service import Service
    if isclass(service_class) and issubclass(service_class, Service) and service_class is not Service:
        name = service_class.get_name()
        _service_registry[name] = service_class

# ################################################################################################################################

def get_service_class(name:'str') -> 'type_ | None':
    """ Returns a service class by its name.
    """
    return _service_registry.get(name)

# ################################################################################################################################

def scan_module_for_services(module:'ModuleType') -> 'None':
    """ Scans a module for Service subclasses and registers them.
    """
    from zato_testing.service import Service
    for name in dir(module):
        obj = getattr(module, name)
        if isclass(obj) and issubclass(obj, Service) and obj is not Service:
            register_service(obj)

# ################################################################################################################################
# ################################################################################################################################

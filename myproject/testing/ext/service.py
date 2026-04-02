# -*- coding: utf-8 -*-

"""
Copyright (C) 2025, Zato Source s.r.o. https://zato.io

Licensed under AGPLv3, see LICENSE.txt for terms and conditions.
"""

# stdlib
import logging

# Zato
from zato_testing.bunch import Bunch
from zato_testing.outgoing import Outgoing
from zato_testing.request import Request
from zato_testing.response import Response

# ################################################################################################################################
# ################################################################################################################################

if 0:
    from zato_testing.typing_ import any_, anydict, boolnone, intnone, strnone

# ################################################################################################################################
# ################################################################################################################################

class CryptoManager:
    """ Provides cryptographic utilities.
    """

    def generate_secret(self, bits:'int'=256) -> 'str':
        """ Generates a random secret string.
        """
        import secrets
        return secrets.token_urlsafe(bits // 8)

# ################################################################################################################################
# ################################################################################################################################

class Cache:
    """ A simple in-memory cache for testing.
    """

    def __init__(self) -> 'None':
        self._data:'dict' = {}

    def get(self, key:'str') -> 'any_':
        """ Gets a value from the cache.
        """
        item = self._data.get(key)
        if item is None:
            return None
        return item['value']

    def set(self, key:'str', value:'any_', expiry:'int'=0) -> 'None':
        """ Sets a value in the cache.
        """
        self._data[key] = {'value': value, 'expiry': expiry}

    def delete(self, key:'str') -> 'None':
        """ Deletes a value from the cache.
        """
        if key in self._data:
            del self._data[key]

    def clear(self) -> 'None':
        """ Clears all values from the cache.
        """
        self._data = {}

# ################################################################################################################################
# ################################################################################################################################

class CacheManager:
    """ Manages cache instances.
    """

    def __init__(self) -> 'None':
        self._caches:'dict' = {}
        self.default = Cache()

    def get_cache(self, cache_type:'str', name:'str') -> 'Cache':
        """ Gets or creates a named cache.
        """
        key = (cache_type, name)
        if key not in self._caches:
            self._caches[key] = Cache()
        return self._caches[key]

# ################################################################################################################################
# ################################################################################################################################

from zato_testing.model import Model

# ################################################################################################################################
# ################################################################################################################################

class ChannelSecurityInfo:
    """ Contains information about a security definition assigned to a channel.
    """

    def __init__(
        self,
        id:'intnone'=None,
        name:'strnone'=None,
        type:'strnone'=None,
        username:'strnone'=None,
        impl:'any_'=None
        ) -> 'None':
        self.id = id
        self.name = name
        self.type = type
        self.username = username
        self.impl = impl

# ################################################################################################################################

    def to_dict(self, needs_impl:'bool'=False) -> 'dict':
        out = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'username': self.username,
        }
        if needs_impl:
            out['impl'] = self.impl
        return out

# ################################################################################################################################
# ################################################################################################################################

class ChannelInfo:
    """ Conveys information about the channel that a service is invoked through.
    """

    def __init__(
        self,
        id:'intnone'=None,
        name:'strnone'=None,
        type:'strnone'=None,
        data_format:'strnone'=None,
        is_internal:'boolnone'=None,
        match_target:'any_'=None,
        security:'ChannelSecurityInfo'=None,
        impl:'any_'=None,
        gateway_service_list:'strnone'=None
        ) -> 'None':
        self.id = id
        self.name = name
        self.type = type
        self.data_format = data_format
        self.is_internal = is_internal
        self.match_target = match_target
        self.impl = impl
        self.security = self.sec = security
        self.gateway_service_list = gateway_service_list

# ################################################################################################################################

    def to_dict(self, needs_impl:'bool'=False) -> 'dict':
        out = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'data_format': self.data_format,
            'is_internal': self.is_internal,
            'match_target': self.match_target,
            'gateway_service_list': self.gateway_service_list,
            'security': self.security.to_dict(needs_impl) if self.security else None,
        }
        if needs_impl:
            out['impl'] = self.impl
        return out

# ################################################################################################################################
# ################################################################################################################################

class Service:
    """ A base class for all services deployed on Zato servers.
    """
    name = None
    has_sio = False
    call_hooks = True
    invokes = []
    http_method_handlers = {}

    def __init__(self, *args:'any_', **kwargs:'any_') -> 'None':
        self.cid = ''
        self.in_reply_to = ''
        self.data_format = ''
        self.transport = ''
        self.wsgi_environ = {}
        self.job_type = ''
        self.environ = Bunch()
        self.request = Request(self)
        self.request.input = Bunch()
        self.response = Response()
        self.config = Bunch()
        self.user_config = Bunch()
        self.logger = logging.getLogger(self.__class__.__name__)

        self._outgoing = Outgoing()
        self.out = self._outgoing
        self.outgoing = self._outgoing
        self.rest = self._outgoing.rest

        from zato_testing.outgoing import CloudFacade
        self.cloud = CloudFacade()

        self.channel = self.chan = ChannelInfo()

        self.server = None
        self.broker_client = None

        from zato_testing.time_ import TimeUtil
        self.time = TimeUtil()
        self.crypto = CryptoManager()
        self.cache = CacheManager()

# ################################################################################################################################

    @classmethod
    def get_name(cls) -> 'str':
        if cls.name:
            return cls.name
        return f'{cls.__module__}.{cls.__name__}'

# ################################################################################################################################

    @classmethod
    def get_impl_name(cls) -> 'str':
        return f'{cls.__module__}.{cls.__name__}'

# ################################################################################################################################

    def handle(self) -> 'None':
        raise NotImplementedError('Should be overridden by subclasses')

# ################################################################################################################################

    def invoke(self, service:'any_', payload:'any_'=None, **kwargs:'any_') -> 'any_':
        """ Invokes another service and returns its response payload.
        """
        from inspect import isclass
        from zato_testing.importer import get_service_class, register_service

        # Get the service class
        if isinstance(service, str):
            service_class = get_service_class(service)
            if service_class is None:
                raise ValueError(f'No service registered with name `{service}`')
        elif isclass(service) and issubclass(service, Service):
            service_class = service
            register_service(service_class)
        else:
            raise ValueError(f'service must be a class or a string, got `{type(service)}`')

        # Create and invoke the service
        instance = service_class()
        instance.cid = self.cid

        if payload:
            from zato_testing.bunch import Bunch
            if isinstance(payload, dict):
                instance.request.input = Bunch(payload)
            instance.request.payload = payload
            instance.request.raw_request = payload

        # Copy REST response registry from current service
        instance._outgoing.rest._response_registry = self._outgoing.rest._response_registry

        # Copy config from current service
        instance.config = self.config

        # Copy cache from current service
        instance.cache = self.cache

        # Handle class-level input definition
        if hasattr(service_class, 'input') and service_class.input is not None:
            input_class = service_class.input
            if payload is not None:
                if isinstance(payload, input_class):
                    instance.request.input = payload
                elif isinstance(payload, dict):
                    input_instance = input_class()
                    for key, value in payload.items():
                        if hasattr(input_instance, key):
                            setattr(input_instance, key, value)
                    instance.request.input = input_instance
                else:
                    instance.request.input = payload

        instance.handle()
        return instance.response.payload

# ################################################################################################################################

    def invoke_async(self, service:'any_', payload:'any_'=None, **kwargs:'any_') -> 'str':
        self.invoke(service, payload, **kwargs)
        return 'async-cid-12345'

# ################################################################################################################################

    def before_handle(self) -> 'None':
        pass

# ################################################################################################################################

    def after_handle(self) -> 'None':
        pass

# ################################################################################################################################

    def validate_input(self) -> 'None':
        pass

# ################################################################################################################################

    def validate_output(self) -> 'None':
        pass

# ################################################################################################################################
# ################################################################################################################################

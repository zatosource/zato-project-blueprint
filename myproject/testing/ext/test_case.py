# -*- coding: utf-8 -*-

"""
Copyright (C) 2025, Zato Source s.r.o. https://zato.io

Licensed under AGPLv3, see LICENSE.txt for terms and conditions.
"""

# stdlib
import unittest
from inspect import isclass

# Zato
from zato_testing.bunch import Bunch
from zato_testing.importer import get_service_class, register_service
from zato_testing.outgoing import RESTResponse
from zato_testing.service import Service

# ################################################################################################################################
# ################################################################################################################################

if 0:
    from zato_testing.typing_ import any_, anydict, type_

# ################################################################################################################################
# ################################################################################################################################

class ServiceTestCase(unittest.TestCase):
    """ Base class for testing Zato services.
    """
    config:'str' = None  # type: ignore

    def setUp(self) -> 'None':
        super().setUp()
        self._rest_responses:'dict' = {}
        self._ldap_responses:'dict' = {}
        self._conn_types:'dict' = {}  # Maps conn_name to 'rest' or 'ldap'
        self._config:'dict' = {}
        self._cache = None
        self._load_class_config()

# ################################################################################################################################

    def _create_service_instance(
        self,
        service_class:'type_[Service]',
        input_data:'anydict'=None,
        raw_request:'any_'=None
        ) -> 'Service':
        """ Creates a service instance with optional input data.
        """
        service = service_class()
        service.cid = 'test-cid-12345'

        # Apply config
        service.config = self._build_config_bunch(self._config)

        # Share cache across invocations
        if self._cache is None:
            from zato_testing.service import CacheManager
            self._cache = CacheManager()
        service.cache = self._cache

        # Handle class-level input definition
        if hasattr(service_class, 'input') and service_class.input is not None:
            input_def = service_class.input
            # Check if input is a class (Model) or a string/tuple (SimpleIO-style)
            if isinstance(input_def, type):
                if input_data is not None:
                    if isinstance(input_data, input_def):
                        service.request.input = input_data
                    elif isinstance(input_data, dict):
                        input_instance = input_def()
                        for key, value in input_data.items():
                            if hasattr(input_instance, key):
                                setattr(input_instance, key, value)
                        service.request.input = input_instance
                    else:
                        service.request.input = input_data
                    service.request.payload = input_data
            else:
                # String or tuple input definition - just use Bunch
                if input_data is not None:
                    if isinstance(input_data, dict):
                        service.request.input = Bunch(input_data)
                    else:
                        service.request.input = input_data
                    service.request.payload = input_data
        elif input_data:
            if isinstance(input_data, dict):
                service.request.input = Bunch(input_data)
            else:
                service.request.input = input_data
            service.request.payload = input_data

        if raw_request is not None:
            service.request.raw_request = raw_request
        elif input_data:
            service.request.raw_request = input_data

        # Handle class-level output definition
        if hasattr(service_class, 'output') and service_class.output is not None:
            output_def = service_class.output
            # Check if output is a class (Model) or a string/tuple (SimpleIO-style)
            if not isinstance(output_def, type):
                # String or tuple output definition - initialize payload as Bunch
                service.response.payload = Bunch()

        for (conn_name, method), response_data in self._rest_responses.items():
            service.rest.set_response(conn_name, method, response_data['response'], response_data['status_code'], response_data['headers'])
            service.out.rest.set_response(conn_name, method, response_data['response'], response_data['status_code'], response_data['headers'])

        for (conn_name, method, request_key), response_data in getattr(self, '_rest_responses_when', {}).items():
            handler = service.rest._response_registry.get((conn_name, method))
            if not handler:
                from zato_testing.outgoing import ResponseHandler
                handler = ResponseHandler({}, response_data['status_code'], response_data['headers'])
                handler._mode = 'request_match'
                service.rest._response_registry[(conn_name, method)] = handler
                service.out.rest._response_registry[(conn_name, method)] = handler
            handler._request_map[request_key] = response_data['response']

        for conn_name, response_data in self._ldap_responses.items():
            ldap_conn = service.out.ldap[conn_name]
            ldap_conn.conn._conn._entries = response_data['response']

        for path, response_data in getattr(self, '_ms365_responses', {}).items():
            service.cloud.ms365.set_response(path, response_data['response'], response_data['request'])

        return service

# ################################################################################################################################

    def _build_config_bunch(self, config_dict:'dict') -> 'Bunch':
        """ Recursively builds a Bunch from a config dict.
        """
        result = Bunch()
        for key, value in config_dict.items():
            if isinstance(value, dict):
                setattr(result, key, self._build_config_bunch(value))
            else:
                setattr(result, key, value)
        return result

# ################################################################################################################################

    def _load_class_config(self) -> 'None':
        """ Loads config from class attribute if set.
        """
        if self.config is not None:
            self.set_config(self.config)

# ################################################################################################################################

    def set_config(self, path:'str', value:'any_'=None) -> 'None':
        """ Sets a config value.

        If path ends with '.ini' and is an existing file, reads the ini file.
        Otherwise, path is a dot-notation string like 'isavia.azure_blob.account_url'.

        Example:
            self.set_config('isavia.azure_blob.account_url', 'https://...')
            self.set_config('/path/to/config.ini')
        """
        import os
        if path.endswith('.ini') and os.path.isfile(path):
            self._load_ini_file(path)
        else:
            parts = path.split('.')
            current = self._config
            for key in parts[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[parts[-1]] = value

# ################################################################################################################################

    def _load_ini_file(self, path:'str') -> 'None':
        """ Loads an ini file into the config.
        """
        import configparser
        parser = configparser.ConfigParser()
        parser.read(path)

        for section in parser.sections():
            section_parts = section.split('.')
            current = self._config
            for part in section_parts:
                if part not in current:
                    current[part] = {}
                current = current[part]

            for key, value in parser.items(section):
                current[key] = value

# ################################################################################################################################

    def invoke(
        self,
        service:'any_',
        input_data:'anydict'=None,
        raw_request:'any_'=None
        ) -> 'Service':
        """ Invokes a service and returns it.

        service can be:
        - A service class (e.g. MyService)
        - A service name string (e.g. 'my.service.name')
        """
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

        instance = self._create_service_instance(service_class, input_data, raw_request)
        instance.handle()
        return instance

# ################################################################################################################################

    def set_response(
        self,
        conn_name:'str',
        response:'any_'=None,
        *,
        method:'str'='GET',
        status_code:'int'=200,
        headers:'anydict'=None,
        request:'any_'=None
        ) -> 'None':
        """ Sets the response for a REST outgoing connection.

        response can be:
        - A single value (dict, string, etc.) - returned on every call
        - A list - each call returns the next item in the list

        request - if provided, the response is only returned when the request matches
                - can be a dict for single request matching
                - can be a list of dicts for multiple requests matching same response
        """
        # Detect MS365 by dot-separated method chain (e.g., O365.Sharepoint.sharepoint.get_site)
        if '.' in conn_name and conn_name.count('.') >= 2:
            if not hasattr(self, '_ms365_responses'):
                self._ms365_responses:'dict' = {}
            self._ms365_responses[conn_name] = {
                'response': response,
                'request': request,
            }
            return

        # Parse connection type prefix if present
        conn_type = 'rest'
        actual_conn_name = conn_name
        has_explicit_prefix = False
        if ':' in conn_name:
            prefix, actual_conn_name = conn_name.split(':', 1)
            if prefix in ('rest', 'ldap'):
                conn_type = prefix
                has_explicit_prefix = True

        # Check for conflicts (only when no explicit prefix)
        if not has_explicit_prefix and actual_conn_name in self._conn_types:
            existing_type = self._conn_types[actual_conn_name]
            if existing_type != conn_type:
                raise ValueError(
                    f"Connection name '{actual_conn_name}' already registered as '{existing_type}'. "
                    f"Use '{existing_type}:{actual_conn_name}' or '{conn_type}:{actual_conn_name}' to disambiguate."
                )

        if not has_explicit_prefix:
            self._conn_types[actual_conn_name] = conn_type

        if conn_type == 'ldap':
            self._ldap_responses[actual_conn_name] = {
                'response': response,
                'status_code': status_code,
                'headers': headers or {},
            }
        elif request is not None:
            if not hasattr(self, '_rest_responses_when'):
                self._rest_responses_when:'dict' = {}

            # Support list of requests matching same response
            if isinstance(request, list):
                requests_to_match = request
            else:
                requests_to_match = [request]

            for req in requests_to_match:
                request_key = tuple(sorted(req.items()))
                self._rest_responses_when[(actual_conn_name, method.upper(), request_key)] = {
                    'response': response,
                    'status_code': status_code,
                    'headers': headers or {},
                }
        else:
            self._rest_responses[(actual_conn_name, method.upper())] = {
                'response': response,
                'status_code': status_code,
                'headers': headers or {},
            }

# ################################################################################################################################

    def assertResponsePayload(self, service:'Service', expected:'any_') -> 'None':
        self.assertEqual(service.response.payload, expected)

# ################################################################################################################################

    def assertResponseStatusCode(self, service:'Service', expected:'int') -> 'None':
        self.assertEqual(service.response.status_code, expected)

# ################################################################################################################################
# ################################################################################################################################

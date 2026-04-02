# -*- coding: utf-8 -*-

"""
Copyright (C) 2025, Zato Source s.r.o. https://zato.io

Licensed under AGPLv3, see LICENSE.txt for terms and conditions.
"""

# ################################################################################################################################
# ################################################################################################################################

if 0:
    from zato_testing.typing_ import any_, anydict

# ################################################################################################################################
# ################################################################################################################################

class RESTResponse:
    """ A REST response object for testing.
    """

    def __init__(
        self,
        data:'any_'=None,
        status_code:'int'=200,
        headers:'anydict'=None,
        text:'str'=''
        ) -> 'None':
        self.data = data
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text
        self._json = data if isinstance(data, (dict, list)) else None

# ################################################################################################################################

    def json(self) -> 'any_':
        return self._json

# ################################################################################################################################
# ################################################################################################################################

class RESTInvoker:
    """ Invokes REST connections in tests.
    """

    def __init__(self, name:'str', response_registry:'dict') -> 'None':
        self.name = name
        self._response_registry = response_registry
        self.conn = self  # For compatibility with self.out.rest['name'].conn pattern

# ################################################################################################################################

    def _call(self, method:'str', *args:'any_', **kwargs:'any_') -> 'RESTResponse':
        key = (self.name, method.upper())
        if key in self._response_registry:
            handler = self._response_registry[key]
            return handler.get_response(*args, **kwargs)
        raise KeyError(f'No response set for connection `{self.name}` method `{method}`')

# ################################################################################################################################

    def get(self, *args:'any_', **kwargs:'any_') -> 'RESTResponse':
        return self._call('GET', *args, **kwargs)

# ################################################################################################################################

    def post(self, *args:'any_', **kwargs:'any_') -> 'RESTResponse':
        return self._call('POST', *args, **kwargs)

# ################################################################################################################################

    def put(self, *args:'any_', **kwargs:'any_') -> 'RESTResponse':
        return self._call('PUT', *args, **kwargs)

# ################################################################################################################################

    def patch(self, *args:'any_', **kwargs:'any_') -> 'RESTResponse':
        return self._call('PATCH', *args, **kwargs)

# ################################################################################################################################

    def delete(self, *args:'any_', **kwargs:'any_') -> 'RESTResponse':
        return self._call('DELETE', *args, **kwargs)

# ################################################################################################################################

    def head(self, *args:'any_', **kwargs:'any_') -> 'RESTResponse':
        return self._call('HEAD', *args, **kwargs)

# ################################################################################################################################

    def options(self, *args:'any_', **kwargs:'any_') -> 'RESTResponse':
        return self._call('OPTIONS', *args, **kwargs)

# ################################################################################################################################

    def send(self, *args:'any_', **kwargs:'any_') -> 'RESTResponse':
        return self.post(*args, **kwargs)

# ################################################################################################################################

    def ping(self, *args:'any_', **kwargs:'any_') -> 'RESTResponse':
        return self._call('PING', *args, **kwargs)

# ################################################################################################################################

    def rest_call(
        self,
        cid:'str',
        *,
        data:'any_'='',
        model:'any_'=None,
        callback:'any_'=None,
        params:'any_'=None,
        headers:'any_'=None,
        method:'str'='GET',
        sec_def_name:'any_'=None,
        auth_scopes:'any_'=None,
        log_response:'bool'=True,
        max_retries:'int'=0,
        retry_sleep_time:'int'=2,
        retry_backoff_threshold:'int'=3,
    ) -> 'tuple':
        """ Called by RESTAdapter.rest_call(). Returns (data, raw_response) tuple.
        """
        response = self._call(method, data=data, params=params, headers=headers)

        result_data = response.data

        # If there's a model, instantiate it from the response data
        if model is not None:
            if isinstance(result_data, dict):
                instance = model()
                for key, value in result_data.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)
                result_data = instance

        # If there's a callback (map_response), call it
        if callback is not None:
            result_data = callback(result_data)

        return (result_data, response)

# ################################################################################################################################
# ################################################################################################################################

class ResponseHandler:
    """ Handles response generation for a connection and method.
    """

    def __init__(self, responses:'any_', status_code:'int'=200, headers:'anydict'=None) -> 'None':
        self._responses = responses
        self._status_code = status_code
        self._headers = headers or {}
        self._call_index = 0
        self._request_map:'dict' = {}

        # Dict with integer keys = sequential responses
        if isinstance(responses, dict) and responses:
            first_key = next(iter(responses.keys()))
            if isinstance(first_key, int):
                self._mode = 'sequential'
                self._min_key = min(responses.keys())
                self._sequential_list = [responses[k] for k in sorted(responses.keys())]
                self._call_index = self._min_key
            elif isinstance(first_key, tuple):
                self._mode = 'request_match'
                for key, value in responses.items():
                    self._request_map[key] = value
            else:
                self._mode = 'single'
        else:
            self._mode = 'single'

# ################################################################################################################################

    def get_response(self, *args:'any_', **kwargs:'any_') -> 'RESTResponse':
        """ Returns the appropriate response based on mode.
        """
        if self._mode == 'sequential':
            idx = self._call_index - self._min_key
            if idx < len(self._sequential_list):
                data = self._sequential_list[idx]
                self._call_index += 1
            else:
                data = self._sequential_list[-1] if self._sequential_list else None
            return RESTResponse(data=data, status_code=self._status_code, headers=self._headers)

        elif self._mode == 'request_match':
            # Build a tuple from kwargs for matching
            request_key = tuple(sorted(kwargs.items()))
            if request_key in self._request_map:
                data = self._request_map[request_key]
            else:
                # Try partial match
                for key, value in self._request_map.items():
                    key_dict = dict(key)
                    if all(kwargs.get(k) == v for k, v in key_dict.items()):
                        data = value
                        break
                else:
                    data = None
            return RESTResponse(data=data, status_code=self._status_code, headers=self._headers)

        else:
            return RESTResponse(data=self._responses, status_code=self._status_code, headers=self._headers)

# ################################################################################################################################
# ################################################################################################################################

class RESTFacade:
    """ A facade for REST connections in tests.
    """

    def __init__(self) -> 'None':
        self._response_registry:'dict' = {}
        self._connections:'dict' = {}

# ################################################################################################################################

    def set_response(self, conn_name:'str', method:'str', response:'any_', status_code:'int'=200, headers:'anydict'=None) -> 'None':
        """ Sets the response for a connection and method.
        """
        key = (conn_name, method.upper())
        self._response_registry[key] = ResponseHandler(response, status_code, headers)

# ################################################################################################################################

# ################################################################################################################################

    def __getitem__(self, name:'str') -> 'RESTInvoker':
        if name not in self._connections:
            self._connections[name] = RESTInvoker(name, self._response_registry)
        return self._connections[name]

# ################################################################################################################################

    def __getattr__(self, name:'str') -> 'RESTInvoker':
        if name.startswith('_'):
            raise AttributeError(name)
        return self[name]

# ################################################################################################################################
# ################################################################################################################################

class LDAPConnection:
    """ Mock LDAP connection for testing.
    """

    def __init__(self) -> 'None':
        self._entries = []

    def search(self, search_base:'str', filter:'str', attributes:'any_'=None) -> 'bool':
        return True

    @property
    def entries(self) -> 'list':
        return self._entries

    def set_entries(self, entries:'list') -> 'None':
        self._entries = entries

    def __enter__(self) -> 'LDAPConnection':
        return self

    def __exit__(self, *args:'any_') -> 'None':
        pass

# ################################################################################################################################

class LDAPConnectionWrapper:
    """ Wrapper that provides .get() context manager for LDAP connections.
    """

    def __init__(self) -> 'None':
        self._conn = LDAPConnection()

    def get(self) -> 'LDAPConnection':
        return self._conn

# ################################################################################################################################

class LDAPInvoker:
    """ Invokes LDAP connections in tests.
    """

    def __init__(self, name:'str') -> 'None':
        self.name = name
        self.conn = LDAPConnectionWrapper()

# ################################################################################################################################

class LDAPFacade:
    """ A facade for LDAP connections in tests.
    """

    def __init__(self) -> 'None':
        self._connections:'dict' = {}

    def __getitem__(self, name:'str') -> 'LDAPInvoker':
        if name not in self._connections:
            self._connections[name] = LDAPInvoker(name)
        return self._connections[name]

# ################################################################################################################################
# ################################################################################################################################

class SQLSession:
    """ Mock SQL session for testing.
    """

    def __init__(self) -> 'None':
        self._results = []

    def execute(self, query:'str') -> 'list':
        return self._results

    def set_results(self, results:'list') -> 'None':
        self._results = results

    def close(self) -> 'None':
        pass

# ################################################################################################################################

class SQLConnection:
    """ Mock SQL connection for testing.
    """

    def __init__(self, name:'str') -> 'None':
        self.name = name
        self._session = SQLSession()

    def session(self) -> 'SQLSession':
        return self._session

# ################################################################################################################################

class SQLFacade:
    """ A facade for SQL connections in tests.
    """

    def __init__(self) -> 'None':
        self._connections:'dict' = {}

    def get(self, name:'str') -> 'SQLConnection':
        if name not in self._connections:
            self._connections[name] = SQLConnection(name)
        return self._connections[name]

    def __getitem__(self, name:'str') -> 'SQLConnection':
        return self.get(name)

# ################################################################################################################################
# ################################################################################################################################

class JiraClient:
    """ Mock Jira client for testing.
    """

    def __init__(self) -> 'None':
        self._jql_results:'dict' = {}

    def jql(self, jql:'str', fields:'list'=None) -> 'dict':
        return self._jql_results

    def set_jql_results(self, results:'dict') -> 'None':
        self._jql_results = results

    def __enter__(self) -> 'JiraClient':
        return self

    def __exit__(self, *args:'any_') -> 'None':
        pass

# ################################################################################################################################

class JiraConnectionWrapper:
    """ Wrapper for Jira connection.
    """

    def __init__(self) -> 'None':
        self._client = JiraClient()

    def client(self) -> 'JiraClient':
        return self._client

# ################################################################################################################################

class JiraInvoker:
    """ Invokes Jira connections in tests.
    """

    def __init__(self, name:'str') -> 'None':
        self.name = name
        self.conn = JiraConnectionWrapper()

# ################################################################################################################################

class JiraFacade:
    """ A facade for Jira connections in tests.
    """

    def __init__(self) -> 'None':
        self._connections:'dict' = {}

    def __getitem__(self, name:'str') -> 'JiraInvoker':
        if name not in self._connections:
            self._connections[name] = JiraInvoker(name)
        return self._connections[name]

# ################################################################################################################################
# ################################################################################################################################

class MS365ResponseRegistry:
    """ Registry for MS365 mock responses.
    """

    def __init__(self) -> 'None':
        self._responses:'dict' = {}
        self._request_responses:'dict' = {}

    def set_response(self, path:'str', response:'any_', request:'any_'=None) -> 'None':
        if request is not None:
            if isinstance(request, list):
                for req in request:
                    request_key = tuple(sorted(req.items())) if isinstance(req, dict) else req
                    self._request_responses[(path, request_key)] = response
            else:
                request_key = tuple(sorted(request.items())) if isinstance(request, dict) else request
                self._request_responses[(path, request_key)] = response
        else:
            self._responses[path] = response

    def get_response(self, path:'str', request_data:'any_'=None) -> 'tuple':
        if request_data is not None and isinstance(request_data, dict):
            plain_dict = {k: v for k, v in request_data.items() if not k.startswith('_')}
            request_key = tuple(sorted(plain_dict.items()))
            key = (path, request_key)
            if key in self._request_responses:
                return (True, self._request_responses[key])

        if path in self._responses:
            return (True, self._responses[path])

        if self._has_child_responses(path):
            return (False, None)

        raise ValueError(
            f"No MS365 response configured for '{path}'. "
            f"Use set_response('{path}', <response>) to configure it."
        )

    def _has_child_responses(self, path:'str') -> 'bool':
        prefix = path + '.'
        for key in self._responses:
            if key.startswith(prefix):
                return True
        for key, _ in self._request_responses:
            if key.startswith(prefix):
                return True
        return False

    def has_response(self, path:'str') -> 'bool':
        return path in self._responses or any(p[0] == path for p in self._request_responses)

# ################################################################################################################################

class MS365Proxy:
    """ Dynamic proxy that records method chain and returns configured responses.
    """

    def __init__(self, registry:'MS365ResponseRegistry', path:'str') -> 'None':
        self._registry = registry
        self._path = path

    def __getattr__(self, name:'str') -> 'MS365Proxy':
        new_path = f'{self._path}.{name}' if self._path else name
        return MS365Proxy(self._registry, new_path)

    def __call__(self, *args:'any_', **kwargs:'any_') -> 'any_':
        request_data = None
        if args:
            request_data = args[0] if len(args) == 1 else args
        elif kwargs:
            request_data = kwargs

        found, response = self._registry.get_response(self._path, request_data)

        if not found:
            return MS365Proxy(self._registry, self._path)

        if isinstance(response, dict) and not self._registry.has_response(self._path + '.'):
            return MS365DictProxy(response, self._registry, self._path)

        return response

    def __enter__(self) -> 'MS365Proxy':
        return self

    def __exit__(self, *args:'any_') -> 'None':
        pass

# ################################################################################################################################

class MS365DictProxy:
    """ Proxy for dict responses that allows attribute access.
    """

    def __init__(self, data:'dict', registry:'MS365ResponseRegistry', path:'str') -> 'None':
        self._data = data
        self._registry = registry
        self._path = path

    def __getattr__(self, name:'str') -> 'any_':
        if name.startswith('_'):
            raise AttributeError(name)
        if name in self._data:
            return self._data[name]
        new_path = f'{self._path}.{name}'
        return MS365Proxy(self._registry, new_path)

    def __getitem__(self, key:'str') -> 'any_':
        return self._data[key]

    def get(self, key:'str', default:'any_'=None) -> 'any_':
        return self._data.get(key, default)

    def items(self) -> 'any_':
        return self._data.items()

    def keys(self) -> 'any_':
        return self._data.keys()

    def values(self) -> 'any_':
        return self._data.values()

    def __iter__(self) -> 'any_':
        return iter(self._data)

    def __len__(self) -> 'int':
        return len(self._data)

# ################################################################################################################################

class MS365Client:
    """ Mock MS365 client that provides access to impl proxy.
    """

    def __init__(self, registry:'MS365ResponseRegistry', conn_name:'str') -> 'None':
        self._registry = registry
        self._conn_name = conn_name
        self.impl = MS365Proxy(registry, conn_name)

    def __enter__(self) -> 'MS365Client':
        return self

    def __exit__(self, *args:'any_') -> 'None':
        pass

# ################################################################################################################################

class MS365ConnectionWrapper:
    """ Wrapper for MS365 connection.
    """

    def __init__(self, registry:'MS365ResponseRegistry', conn_name:'str') -> 'None':
        self._registry = registry
        self._conn_name = conn_name

    def client(self) -> 'MS365Client':
        return MS365Client(self._registry, self._conn_name)

# ################################################################################################################################

class MS365Connection:
    """ Mock MS365 connection.
    """

    def __init__(self, registry:'MS365ResponseRegistry', conn_name:'str') -> 'None':
        self._registry = registry
        self._conn_name = conn_name
        self.conn = MS365ConnectionWrapper(registry, conn_name)

# ################################################################################################################################

class MS365Facade:
    """ A facade for MS365 connections in tests.
    """

    def __init__(self) -> 'None':
        self._connections:'dict' = {}
        self._registry = MS365ResponseRegistry()

    def get(self, name:'str') -> 'MS365Connection':
        if name not in self._connections:
            self._connections[name] = MS365Connection(self._registry, name)
        return self._connections[name]

    def __getitem__(self, name:'str') -> 'MS365Connection':
        return self.get(name)

    def set_response(self, path:'str', response:'any_', request:'any_'=None) -> 'None':
        self._registry.set_response(path, response, request)

# ################################################################################################################################
# ################################################################################################################################

class CloudFacade:
    """ Encapsulates cloud connections (Jira, etc).
    """

    def __init__(self) -> 'None':
        self.jira = JiraFacade()
        self.ms365 = MS365Facade()

# ################################################################################################################################
# ################################################################################################################################

class Outgoing:
    """ Encapsulates outgoing connections.
    """

    def __init__(self) -> 'None':
        self.rest = RESTFacade()
        self.plain_http = self.rest
        self.soap = RESTFacade()
        self.ldap = LDAPFacade()
        self.sql = SQLFacade()
        self.ftp = None
        self.amqp = None
        self.jms_wmq = None
        self.zmq = None

# ################################################################################################################################
# ################################################################################################################################

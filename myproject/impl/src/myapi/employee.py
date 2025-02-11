# -*- coding: utf-8 -*-

# Zato
from zato.server.service import Service

class GetEmployee(Service):

    name = 'api.employee.get'

    def handle(self):
        self.logger.info('%s has been invoked', self.name)
        self.response.payload = {'Hello': 'Employee'}

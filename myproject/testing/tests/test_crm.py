# -*- coding: utf-8 -*-

# zato-testing
from zato_testing import ServiceTestCase

# Our code
from api.crm import GetCustomer

class TestGetCustomer(ServiceTestCase):

    def test_returns_customer_details(self):

        # Prepare test data ..
        name = 'Alice Johnson'
        email = 'alice@example.com'
        customer_id = 'CUST-001'

        # .. connection the service uses ..
        conn_name = 'crm.api'

        # .. tell the framework to make use of that data ..
        self.set_response(conn_name, {
            'contact_name': name,
            'account_email': email,
        })

        # .. invoke the service ..
        service = self.invoke(GetCustomer, {'customer_id': customer_id})

        # .. and run our assertions.
        self.assertEqual(service.response.payload.name, name)
        self.assertEqual(service.response.payload.email, email)

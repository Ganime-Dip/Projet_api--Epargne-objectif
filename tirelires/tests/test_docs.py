from rest_framework.test import APITestCase


class DocumentationTests(APITestCase):
    def test_schema_openapi_accessible(self):
        response = self.client.get('/api/schema/')
        self.assertEqual(response.status_code, 200)

    def test_swagger_ui_accessible(self):
        response = self.client.get('/api/docs/')
        self.assertEqual(response.status_code, 200)
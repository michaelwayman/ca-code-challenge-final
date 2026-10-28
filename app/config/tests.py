from django.db import connection
from django.test import TestCase


class SchemaTests(TestCase):
    def test_no_role_or_password_column(self):
        # C2/R13: roles and passwords live only in the auth service database.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name, column_name FROM information_schema.columns"
                " WHERE table_schema = 'public'"
                " AND (column_name ILIKE '%%role%%' OR column_name ILIKE '%%password%%')"
            )
            self.assertEqual(cursor.fetchall(), [])

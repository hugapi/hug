"""This is the test module for the Localrouter class, 
made by Marwan Amrhar & Yahia Noeman & Ayoub Bouazza & Sajeed Bouzziane.
It covers the functions:
    Localrouter.init
    Localrouter.directives
    Localrouter.validate
    Localrouter.version
    Localrouter.call"""

import unittest
from unittest.mock import patch
import hug

from hug.routing import LocalRouter

class TestLocalRouter(unittest.TestCase):

    def setUp(self):
        self.router = LocalRouter(api="test_api")

    ## localrouter.init
    def test_initialization_with_defaults(self):
        """Test LocalRouter initialization with default parameters"""
        instance = LocalRouter()
        self.assertNotIn("version", instance.route)
        self.assertNotIn("skip_directives", instance.route)
        self.assertNotIn("skip_validation", instance.route)

    def test_initialization_with_version(self):
        """Test LocalRouter initialization with version set"""
        instance = LocalRouter(version=1)
        self.assertEqual(instance.route.get("version"), 1)
        self.assertNotIn("skip_directives", instance.route)
        self.assertNotIn("skip_validation", instance.route)

    def test_initialization_with_skip_directives(self):
        """Test LocalRouter initialization with directives=False"""
        instance = LocalRouter(directives=False)
        self.assertNotIn("version", instance.route)
        self.assertTrue(instance.route.get("skip_directives"))

    def test_initialization_with_skip_validation(self):
        """Test LocalRouter initialization with validate=False"""
        instance = LocalRouter(validate=False)
        self.assertNotIn("version", instance.route)
        self.assertNotIn("skip_directives", instance.route)
        self.assertTrue(instance.route.get("skip_validation"))

    def test_initialization_with_all_parameters(self):
        """Test LocalRouter initialization with all parameters"""
        instance = LocalRouter(directives=False, validate=False, version=1)
        self.assertEqual(instance.route.get("version"), 1)
        self.assertTrue(instance.route.get("skip_directives"))
        self.assertTrue(instance.route.get("skip_validation"))

    ## localrouter.directives
    def test_directives_method(self):
        """Test LocalRouter directives method"""
        result = self.router.directives(use=False)
        self.assertIsInstance(result, LocalRouter)
        self.assertIn("skip_directives", result.route)
        self.assertTrue(result.route["skip_directives"])

    ## localrouter.validate
    def test_validate_method(self):
        """Test LocalRouter validate method"""
        result = self.router.validate(enforce=False)
        self.assertIsInstance(result, LocalRouter)
        self.assertIn("skip_validation", result.route)
        self.assertTrue(result.route["skip_validation"])

    ## localrouter.version
    def test_version_method(self):
        """Test LocalRouter version method"""
        result = self.router.version(supported=2)
        self.assertIsInstance(result, LocalRouter)
        self.assertEqual(result.route["version"], 2)

    ## localrouter.call
    def test_call_method(self):
        """Test LocalRouter __call__ method"""
        def mock_function():
            pass
        with patch('hug.interface.Local') as mock_local:
            self.router(mock_function)
            mock_local.assert_called_once_with(self.router.route, mock_function)

if __name__ == '__main__':
    unittest.main()
    
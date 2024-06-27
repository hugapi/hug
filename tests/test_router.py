"""This is the test module for the Router class, 
made by Marwan Amrhar & Yahia Noeman & Ayoub Bouazza & Sajeed Bouzziane
It covers the function:
    Router.__init__"""

import unittest
from hug.routing import Router

class TestRouterInit(unittest.TestCase):
    def test_router_init_with_all_parameters(self):
        """Test Router initialization with all parameters"""
        transform = lambda x: x
        output = "output_format"
        validate = "validate_function"
        api = "api_object"
        requires = ("requirement1", "requirement2")
        map_params = {"param1": "mapped_param1"}
        args = ["arg1", "arg2"]

        router = Router(
            transform=transform,
            output=output,
            validate=validate,
            api=api,
            requires=requires,
            map_params=map_params,
            args=args,
        )

        self.assertEqual(router.route["transform"], transform)
        self.assertEqual(router.route["output"], output)
        self.assertEqual(router.route["validate"], validate)
        self.assertEqual(router.route["api"], api)
        self.assertEqual(router.route["requires"], requires)
        self.assertEqual(router.route["map_params"], map_params)
        self.assertEqual(router.route["args"], args)

    def test_router_init_with_default_parameters(self):
        """Test Router initialization with default parameters"""
        router = Router()

        self.assertNotIn("transform", router.route)
        self.assertNotIn("output", router.route)
        self.assertNotIn("validate", router.route)
        self.assertNotIn("api", router.route)
        self.assertEqual(router.route.get("requires", ()), ())
        self.assertNotIn("map_params", router.route)
        self.assertNotIn("args", router.route)

    def test_router_init_with_single_requirement(self):
        """Test Router initialization with a single requirement"""
        router = Router(requires="requirement1")

        self.assertEqual(router.route["requires"], ("requirement1",))

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRouterInit))
    return suite

if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    runner.run(test_suite())
    
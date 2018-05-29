import sys

from marshmallow.decorators import post_dump

import hug
from marshmallow import fields, Schema
import pytest


module = sys.modules[__name__]


class RequirementFailed(object):

    def __str__(self):
        return "requirement failed"


class CustomException(Exception):
    pass


class TestContextFactoryLocal(object):

    def test_lack_requirement(self):
        self.custom_context = dict(test='context')

        @hug.context_factory()
        def return_context(**kwargs):
            return self.custom_context

        @hug.delete_context()
        def delete_context(context, exception=None, errors=None, lacks_requirement=None):
            assert context == self.custom_context
            assert not exception
            assert not errors
            assert lacks_requirement
            assert isinstance(lacks_requirement, RequirementFailed)
            self.custom_context['launched_delete_context'] = True

        def test_local_requirement(**kwargs):
            assert 'context' in kwargs
            assert kwargs['context'] == self.custom_context
            self.custom_context['launched_requirement'] = True
            return RequirementFailed()

        @hug.local(requires=test_local_requirement)
        def requirement_local_function():
            self.custom_context['launched_local_function'] = True

        requirement_local_function()
        assert 'launched_local_function' not in self.custom_context
        assert 'launched_requirement' in self.custom_context
        assert 'launched_delete_context' in self.custom_context

    def test_directive(self):
        custom_context = dict(test='context')

        @hug.context_factory()
        def return_context(**kwargs):
            return custom_context

        @hug.delete_context()
        def delete_context(context, **kwargs):
            pass

        @hug.directive()
        def custom_directive(**kwargs):
            assert 'context' in kwargs
            assert kwargs['context'] == custom_context
            return 'custom'

        @hug.local()
        def directive_local_function(custom: custom_directive):
            assert custom == 'custom'

        directive_local_function()

    def test_validation(self):
        custom_context = dict(test='context', not_valid_number=43)

        @hug.context_factory()
        def return_context(**kwargs):
            return custom_context

        @hug.delete_context()
        def delete_context(context, exception=None, errors=None, lacks_requirement=None):
            assert context == custom_context
            assert not exception
            assert errors
            assert not lacks_requirement
            custom_context['launched_delete_context'] = True

        def test_requirement(**kwargs):
            assert 'context' in kwargs
            assert kwargs['context'] == custom_context
            custom_context['launched_requirement'] = True
            return RequirementFailed()

        @hug.type(extend=hug.types.number, accept_context=True)
        def custom_number_test(value, context):
            assert context == custom_context
            if value == context['not_valid_number']:
                raise ValueError('not valid number')
            return value

        @hug.local()
        def validation_local_function(value: custom_number_test):
            custom_context['launched_local_function'] = value

        validation_local_function(43)
        assert not 'launched_local_function' in custom_context
        assert 'launched_delete_context' in custom_context

    def test_transform(self):
        custom_context = dict(test='context', test_number=43)

        @hug.context_factory()
        def return_context(**kwargs):
            return custom_context

        @hug.delete_context()
        def delete_context(context, exception=None, errors=None, lacks_requirement=None):
            assert context == custom_context
            assert not exception
            assert not errors
            assert not lacks_requirement
            custom_context['launched_delete_context'] = True

        class UserSchema(Schema):
            name = fields.Str()

            @post_dump()
            def check_context(self, data):
                assert self.context['test'] == 'context'
                self.context['test_number'] += 1

        @hug.local()
        def validation_local_function() -> UserSchema():
            return {'name': 'test'}

        validation_local_function()
        assert 'test_number' in custom_context and custom_context['test_number'] == 44
        assert 'launched_delete_context' in custom_context

    def test_exception(self):
        custom_context = dict(test='context')

        @hug.context_factory()
        def return_context(**kwargs):
            return custom_context

        @hug.delete_context()
        def delete_context(context, exception=None, errors=None, lacks_requirement=None):
            assert context == custom_context
            assert exception
            assert isinstance(exception, CustomException)
            assert not errors
            assert not lacks_requirement
            custom_context['launched_delete_context'] = True

        @hug.local()
        def exception_local_function():
            custom_context['launched_local_function'] = True
            raise CustomException()

        with pytest.raises(CustomException):
            exception_local_function()

        assert 'launched_local_function' in custom_context
        assert 'launched_delete_context' in custom_context

    def test_success(self):
        custom_context = dict(test='context')

        @hug.context_factory()
        def return_context(**kwargs):
            return custom_context

        @hug.delete_context()
        def delete_context(context, exception=None, errors=None, lacks_requirement=None):
            assert context == custom_context
            assert not exception
            assert not errors
            assert not lacks_requirement
            custom_context['launched_delete_context'] = True

        @hug.local()
        def success_local_function():
            custom_context['launched_local_function'] = True

        success_local_function()

        assert 'launched_local_function' in custom_context
        assert 'launched_delete_context' in custom_context


class TestContextFactoryCLI(object):

    def test_lack_requirement(self):
        custom_context = dict(test='context')

        @hug.context_factory()
        def return_context(**kwargs):
            return custom_context

        @hug.delete_context()
        def delete_context(context, exception=None, errors=None, lacks_requirement=None):
            assert context == custom_context
            assert not exception
            assert not errors
            assert lacks_requirement
            assert isinstance(lacks_requirement, RequirementFailed)
            custom_context['launched_delete_context'] = True

        def test_requirement(**kwargs):
            assert 'context' in kwargs
            assert kwargs['context'] == custom_context
            custom_context['launched_requirement'] = True
            return RequirementFailed()

        @hug.cli(requires=test_requirement)
        def requirement_local_function():
            custom_context['launched_local_function'] = True

        hug.test.cli(requirement_local_function)
        assert 'launched_local_function' not in custom_context
        assert 'launched_requirement' in custom_context
        assert 'launched_delete_context' in custom_context

    def test_directive(self):
        custom_context = dict(test='context')

        @hug.context_factory()
        def return_context(**kwargs):
            return custom_context

        @hug.delete_context()
        def delete_context(context, **kwargs):
            pass

        @hug.directive()
        def custom_directive(**kwargs):
            assert 'context' in kwargs
            assert kwargs['context'] == custom_context
            return 'custom'

        @hug.cli()
        def directive_local_function(custom: custom_directive):
            assert custom == 'custom'

        hug.test.cli(directive_local_function)

    def test_validation(self):
        custom_context = dict(test='context', not_valid_number=43)

        @hug.context_factory()
        def return_context(**kwargs):
            return custom_context

        @hug.delete_context()
        def delete_context(context, exception=None, errors=None, lacks_requirement=None):
            assert not exception
            assert context == custom_context
            assert errors
            assert not lacks_requirement
            custom_context['launched_delete_context'] = True

        def test_requirement(**kwargs):
            assert 'context' in kwargs
            assert kwargs['context'] == custom_context
            custom_context['launched_requirement'] = True
            return RequirementFailed()

        @hug.type(extend=hug.types.number, accept_context=True)
        def new_custom_number_test(value, context):
            assert context == custom_context
            if value == context['not_valid_number']:
                raise ValueError('not valid number')
            return value

        @hug.cli()
        def validation_local_function(value: hug.types.number):
            custom_context['launched_local_function'] = value
            return 0

        with pytest.raises(SystemExit):
            hug.test.cli(validation_local_function, 'xxx')
        assert 'launched_local_function' not in custom_context
        assert 'launched_delete_context' in custom_context

    def test_transform(self):
        custom_context = dict(test='context', test_number=43)

        @hug.context_factory()
        def return_context(**kwargs):
            return custom_context

        @hug.delete_context()
        def delete_context(context, exception=None, errors=None, lacks_requirement=None):
            assert not exception
            assert context == custom_context
            assert not errors
            assert not lacks_requirement
            custom_context['launched_delete_context'] = True

        class UserSchema(Schema):
            name = fields.Str()

            @post_dump()
            def check_context(self, data):
                assert self.context['test'] == 'context'
                self.context['test_number'] += 1

        @hug.cli()
        def transform_cli_function() -> UserSchema():
            custom_context['launched_cli_function'] = True
            return {'name': 'test'}

        hug.test.cli(transform_cli_function)
        assert 'launched_cli_function' in custom_context
        assert 'launched_delete_context' in custom_context
        assert 'test_number' in custom_context
        assert custom_context['test_number'] == 44

    def test_exception(self):
        custom_context = dict(test='context')

        @hug.context_factory()
        def return_context(**kwargs):
            return custom_context

        @hug.delete_context()
        def delete_context(context, exception=None, errors=None, lacks_requirement=None):
            assert context == custom_context
            assert exception
            assert isinstance(exception, CustomException)
            assert not errors
            assert not lacks_requirement
            custom_context['launched_delete_context'] = True

        @hug.cli()
        def exception_local_function():
            custom_context['launched_local_function'] = True
            raise CustomException()

        hug.test.cli(exception_local_function)

        assert 'launched_local_function' in custom_context
        assert 'launched_delete_context' in custom_context

    def test_success(self):
        custom_context = dict(test='context')

        @hug.context_factory()
        def return_context(**kwargs):
            return custom_context

        @hug.delete_context()
        def delete_context(context, exception=None, errors=None, lacks_requirement=None):
            assert context == custom_context
            assert not exception
            assert not errors
            assert not lacks_requirement
            custom_context['launched_delete_context'] = True

        @hug.cli()
        def success_local_function():
            custom_context['launched_local_function'] = True

        hug.test.cli(success_local_function)

        assert 'launched_local_function' in custom_context
        assert 'launched_delete_context' in custom_context


class TestContextFactoryHTTP(object):

    def test_lack_requirement(self):
        custom_context = dict(test='context')

        @hug.context_factory()
        def return_context(**kwargs):
            return custom_context

        @hug.delete_context()
        def delete_context(context, exception=None, errors=None, lacks_requirement=None):
            assert context == custom_context
            assert not exception
            assert not errors
            assert lacks_requirement
            custom_context['launched_delete_context'] = True

        def test_requirement(**kwargs):
            assert 'context' in kwargs
            assert kwargs['context'] == custom_context
            custom_context['launched_requirement'] = True
            return 'requirement_failed'

        @hug.get('/requirement_function', requires=test_requirement)
        def requirement_http_function():
            custom_context['launched_local_function'] = True

        hug.test.get(module, '/requirement_function')
        assert 'launched_local_function' not in custom_context
        assert 'launched_requirement' in custom_context
        assert 'launched_delete_context' in custom_context

    def test_directive(self):
        custom_context = dict(test='context')

        @hug.context_factory()
        def return_context(**kwargs):
            return custom_context

        @hug.delete_context()
        def delete_context(context, **kwargs):
            pass

        @hug.directive()
        def custom_directive(**kwargs):
            assert 'context' in kwargs
            assert kwargs['context'] == custom_context
            return 'custom'

        @hug.get('/directive_function')
        def directive_http_function(custom: custom_directive):
            assert custom == 'custom'

        hug.test.get(module, '/directive_function')

    def test_validation(self):
        custom_context = dict(test='context', not_valid_number=43)

        @hug.context_factory()
        def return_context(**kwargs):
            return custom_context

        @hug.delete_context()
        def delete_context(context, exception=None, errors=None, lacks_requirement=None):
            assert context == custom_context
            assert not exception
            assert errors
            assert not lacks_requirement
            custom_context['launched_delete_context'] = True

        def test_requirement(**kwargs):
            assert 'context' in kwargs
            assert kwargs['context'] == custom_context
            custom_context['launched_requirement'] = True
            return RequirementFailed()

        @hug.type(extend=hug.types.number, accept_context=True)
        def custom_number_test(value, context):
            assert context == custom_context
            if value == context['not_valid_number']:
                raise ValueError('not valid number')
            return value

        @hug.get('/validation_function')
        def validation_http_function(value: custom_number_test):
            custom_context['launched_local_function'] = value

        hug.test.get(module, '/validation_function', 43)
        assert 'launched_local_function ' not in custom_context
        assert 'launched_delete_context' in custom_context

    def test_transform(self):
        custom_context = dict(test='context', test_number=43)

        @hug.context_factory()
        def return_context(**kwargs):
            return custom_context

        @hug.delete_context()
        def delete_context(context, exception=None, errors=None, lacks_requirement=None):
            assert context == custom_context
            assert not exception
            assert not errors
            assert not lacks_requirement
            custom_context['launched_delete_context'] = True

        class UserSchema(Schema):
            name = fields.Str()

            @post_dump()
            def check_context(self, data):
                assert self.context['test'] == 'context'
                self.context['test_number'] += 1

        @hug.get('/validation_function')
        def validation_http_function() -> UserSchema():
            custom_context['launched_local_function'] = True

        hug.test.get(module, '/validation_function', 43)
        assert 'launched_local_function' in custom_context
        assert 'launched_delete_context' in custom_context
        assert 'test_number' in custom_context
        assert custom_context['test_number'] == 44

    def test_exception(self):
        custom_context = dict(test='context')

        @hug.context_factory()
        def return_context(**kwargs):
            return custom_context

        @hug.delete_context()
        def delete_context(context, exception=None, errors=None, lacks_requirement=None):
            assert context == custom_context
            assert exception
            assert isinstance(exception, CustomException)
            assert not errors
            assert not lacks_requirement
            custom_context['launched_delete_context'] = True

        @hug.get('/exception_function')
        def exception_http_function():
            custom_context['launched_local_function'] = True
            raise CustomException()

        with pytest.raises(CustomException):
            hug.test.get(module, '/exception_function')

        assert 'launched_local_function' in custom_context
        assert 'launched_delete_context' in custom_context

    def test_success(self):
        custom_context = dict(test='context')

        @hug.context_factory()
        def return_context(**kwargs):
            return custom_context

        @hug.delete_context()
        def delete_context(context, exception=None, errors=None, lacks_requirement=None):
            assert context == custom_context
            assert not exception
            assert not errors
            assert not lacks_requirement
            custom_context['launched_delete_context'] = True

        @hug.get('/success_function')
        def success_http_function():
            custom_context['launched_local_function'] = True

        hug.test.get(module, '/success_function')

        assert 'launched_local_function' in custom_context
        assert 'launched_delete_context' in custom_context

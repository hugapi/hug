import hug


def test_context_global_decorators(hug_api):
    custom_context = dict(context='global', factory=0, delete=0)

    @hug.context_factory(apply_globally=True)
    def create_context(*args, **kwargs):
        custom_context['factory'] += 1
        return custom_context

    @hug.delete_context(apply_globally=True)
    def delete_context(context, *args, **kwargs):
        assert context == custom_context
        custom_context['delete'] += 1

    @hug.get(api=hug_api)
    def made_up_hello():
        return 'hi'

    @hug.extend_api(api=hug_api, base_url='/api')
    def extend_with():
        import tests.module_fake_simple
        return (tests.module_fake_simple, )

    assert hug.test.get(hug_api, '/made_up_hello').data == 'hi'
    assert custom_context['factory'] == 1
    assert custom_context['delete'] == 1
    assert hug.test.get(hug_api, '/api/made_up_hello').data == 'hello'
    assert custom_context['factory'] == 2
    assert custom_context['delete'] == 2

import hug


@hug.cli_object(name='git', version='1.0.0')
class GIT(object):
    """An example of command like calls via an Object"""

    @hug.cli_object()
    def push(self, branch='master'):
        return 'Pushing {}'.format(branch)

    @hug.cli_object()
    def pull(self, branch='master'):
        return 'Pulling {}'.format(branch)


if __name__ == '__main__':
    GIT.cli()

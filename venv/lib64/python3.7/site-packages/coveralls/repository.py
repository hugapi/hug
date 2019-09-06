
import sys
import os

try:
    from subprocess32 import check_output
except ImportError:
    from subprocess import check_output

FORMAT = '%n'.join(['%H', '%aN', '%ae', '%cN', '%ce', '%s'])


def gitrepo(root):
    tmpdir = os.getcwd()
    os.chdir(root)
    gitlog = check_output(['git', '--no-pager', 'log', '-1', '--pretty=format:%s' % FORMAT], universal_newlines=True).split('\n', 5)
    branch = (os.environ.get('CIRCLE_BRANCH') or
              os.environ.get('TRAVIS_BRANCH', check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], universal_newlines=True).strip()))
    remotes = [x.split() for x in filter(lambda x: x.endswith('(fetch)'), check_output(['git', 'remote', '-v'], universal_newlines=True).strip().splitlines())]
    os.chdir(tmpdir)
    return {
        "head": {
            "id": gitlog[0],
            "author_name": gitlog[1],
            "author_email": gitlog[2],
            "committer_name": gitlog[3],
            "committer_email": gitlog[4],
            "message": gitlog[5].strip(),
        },
        "branch": branch,
        "remotes": [{'name': remote[0], 'url': remote[1]} for remote in remotes]
    }


HGLOG = """{node}
{author|person}
{author|email}
{author|person}
{author|email}
{desc}"""


def hgrepo(root):
    hglog = check_output(['hg', 'log', '-l', '1', '--template=%s' % HGLOG],
                         universal_newlines=True).split('\n', 5)
    branch = (os.environ.get('CIRCLE_BRANCH') or
              os.environ.get('TRAVIS_BRANCH',
                             check_output(['hg', 'branch'],
                                          universal_newlines=True).strip()))
    remotes = [x.split(' = ') for x in
               check_output(['hg', 'paths'],
                            universal_newlines=True).strip().splitlines()]
    return {
        'head': {
            'id': hglog[0],
            'author_name': hglog[1],
            'author_email': hglog[2],
            'committer_name': hglog[3],
            'committer_email': hglog[4],
            'message': hglog[5].strip(),
        },
        'branch': branch,
        'remotes': [{
            'name': remote[0], 'url': remote[1]
        } for remote in remotes]
    }


def repo(root):
    if '.git' in os.listdir(root):
        return gitrepo(root)
    if '.hg' in os.listdir(root):
        return hgrepo(root)

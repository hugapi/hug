__author__ = 'Andrea De Marco <24erre@gmail.com>'
__version__ = '2.9.2'
__classifiers__ = [
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: Apache Software License',
    'Operating System :: OS Independent',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Topic :: Internet :: WWW/HTTP',
    'Topic :: Software Development :: Libraries',
]
__copyright__ = "2013, %s " % __author__
__license__ = """
   Copyright %s.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either expressed or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
""" % __copyright__

__docformat__ = 'restructuredtext en'

__doc__ = """
:abstract: Python interface to coveralls.io API
:version: %s
:author: %s
:contact: http://z4r.github.com/
:date: 2012-02-08
:copyright: %s
""" % (__version__, __author__, __license__)


def parse_args():
    import os
    import yaml
    import argparse
    parser = argparse.ArgumentParser(prog='coveralls')
    parser.add_argument('--coveralls_url', '-u', help='coveralls.io api url', default='https://coveralls.io/api/v1/jobs')
    parser.add_argument('--base_dir', '-b', help='project root directory', default='.')
    parser.add_argument('--data_file', '-d', help='coverage file name', default=None)
    parser.add_argument('--config_file', '-c', help='coverage config file name', default=None)
    parser.add_argument('--coveralls_yaml', '-y', help='coveralls yaml file name', default='.coveralls.yml')
    parser.add_argument('--ignore-errors', '-i', help='ignore errors while reading source files', action='store_true', default=False)
    parser.add_argument('--merge_file', '-m', help='json file containing coverage data to be merged (for merging javascript coverage)', default=None)
    parser.add_argument('--nogit', help='do not gather git repo info', action='store_true', default=False)
    parser.add_argument('--skip_ssl_verify', help='skip ssl certificate verification when communicating with the coveralls server', action='store_true', default=False)
    args = parser.parse_args()
    args.base_dir = os.path.abspath(args.base_dir)
    args.data_file = os.path.join(args.base_dir, args.data_file) if args.data_file else None
    args.config_file = os.path.join(args.base_dir, args.config_file) if args.config_file else True
    args.coveralls_yaml = os.path.join(args.base_dir, args.coveralls_yaml)
    args.merge_file = os.path.join(args.base_dir, args.merge_file) if args.merge_file else None
    yml = {}
    try:
        with open(args.coveralls_yaml, 'r') as fp:
            yml = yaml.load(fp)
    except:
        pass
    yml = yml or {}
    args.repo_token = yml.get('repo_token') or os.environ.get('COVERALLS_REPO_TOKEN') or ''
    args.service_name = yml.get('service_name') or os.environ.get('COVERALLS_SERVICE_NAME') or 'travis-ci'
    args.service_job_id = os.environ.get('TRAVIS_JOB_ID', '')
    args.parallel = yml.get('parallel', os.environ.get('COVERALLS_PARALLEL', False))
    return args


def wear(args=None):
    from coveralls.control import coveralls
    from coveralls.repository import repo
    from coveralls.api import post
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('coveralls')
    args = args or parse_args()
    coverage = coveralls(data_file=args.data_file, config_file=args.config_file)
    coverage.load()
    response = post(
        url=args.coveralls_url,
        repo_token=args.repo_token,
        service_job_id=args.service_job_id,
        service_name=args.service_name,
        git=repo(args.base_dir) if not args.nogit else {},
        source_files=coverage.coveralls(args.base_dir, ignore_errors=args.ignore_errors, merge_file=args.merge_file),
        parallel=args.parallel,
        skip_ssl_verify=args.skip_ssl_verify,
    )
    logger.info(response.status_code)
    logger.info(response.text)
    return 1 if 'error' in response.json() else 0

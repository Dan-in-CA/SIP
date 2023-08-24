#! /usr/bin/env python3
# Requires Python 3.6+
# pylint: disable=invalid-name
"""Configuration of Sphinx documentation generator."""

from pathlib import Path
import sys


# Make in-tree extension importable in non-tox setups/envs, like RTD.
# Refs:
# https://github.com/readthedocs/readthedocs.org/issues/6311
# https://github.com/readthedocs/readthedocs.org/issues/7182
sys.path.insert(0, str(Path(__file__).parent.resolve()))


extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.extlinks',
    'sphinx.ext.intersphinx',
    # Third-party extensions:
    'jaraco.packaging.sphinx',
    'sphinx_tabs.tabs',
    'sphinxcontrib.apidoc',
]

# Conditional third-party extensions:
try:
    import sphinxcontrib.spelling as _sphinxcontrib_spelling
except ImportError:
    extensions.append('spelling_stub_ext')
else:
    del _sphinxcontrib_spelling  # noqa: WPS100
    extensions.append('sphinxcontrib.spelling')

# Tree-local extensions:
extensions.append('scm_tag_titles_ext')

master_doc = 'index'

apidoc_excluded_paths = []
apidoc_extra_args = [
    '--implicit-namespaces',
    '--private',  # include “_private” modules
]
apidoc_module_dir = '../cheroot'
apidoc_module_first = False
apidoc_output_dir = 'pkg'
apidoc_separate_modules = True
apidoc_toc_file = None

spelling_ignore_acronyms = True
spelling_ignore_importable_modules = True
spelling_ignore_pypi_package_names = True
spelling_ignore_python_builtins = True
spelling_ignore_wiki_words = True
spelling_show_suggestions = True
spelling_word_list_filename = [
    'spelling_wordlist.txt',
]

scm_version_title_settings = {
    'scm': 'git',
    'date_format': '%d %b %Y',
}

github_url = 'https://github.com'
github_repo_org = 'cherrypy'
github_repo_name = 'cheroot'
github_repo_slug = f'{github_repo_org}/{github_repo_name}'
github_repo_url = f'{github_url}/{github_repo_slug}'
cp_github_repo_url = f'{github_url}/{github_repo_org}/cherrypy'
github_sponsors_url = f'{github_url}/sponsors'

extlinks = {
    'issue': (f'{github_repo_url}/issues/%s', '#'),
    'pr': (f'{github_repo_url}/pull/%s', 'PR #'),
    'commit': (f'{github_repo_url}/commit/%s', ''),
    'cp-issue': (f'{cp_github_repo_url}/issues/%s', 'CherryPy #'),
    'cp-pr': (f'{cp_github_repo_url}/pull/%s', 'CherryPy PR #'),
    'gh': (f'{github_url}/%s', 'GitHub: '),
    'user': (f'{github_sponsors_url}/%s', '@'),
}

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'python2': ('https://docs.python.org/2', None),
    # Ref: https://github.com/cherrypy/cherrypy/issues/1872
    'cherrypy': (
        'https://docs.cherrypy.dev/en/latest',
        ('https://cherrypy.rtfd.io/en/latest', None),
    ),
    'trustme': ('https://trustme.readthedocs.io/en/latest/', None),
    'ddt': ('https://ddt.readthedocs.io/en/latest/', None),
    'pyopenssl': ('https://www.pyopenssl.org/en/latest/', None),
}

linkcheck_ignore = [
    r'http://localhost:\d+/',  # local URLs
    r'https://codecov\.io/gh/cherrypy/cheroot/branch/master/graph/badge\.svg',
    r'https://github\.com/cherrypy/cheroot/actions',  # 404 if no auth

    # Too many links to GitHub so they cause
    # "429 Client Error: too many requests for url"
    # Ref: https://github.com/sphinx-doc/sphinx/issues/7388
    r'https://github\.com/cherrypy/cheroot/issues',
    r'https://github\.com/cherrypy/cheroot/pull',
    r'https://github\.com/cherrypy/cherrypy/issues',
    r'https://github\.com/cherrypy/cherrypy/pull',

    # Requires a more liberal 'Accept: ' HTTP request header:
    # Ref: https://github.com/sphinx-doc/sphinx/issues/7247
    r'https://github\.com/cherrypy/cheroot/workflows/[^/]+/badge\.svg',

    # Has an ephemeral anchor (line-range) but actual HTML has separate per-
    # line anchors.
    r'https://github\.com'
    r'/python/cpython/blob/c39b52f/Lib/poplib\.py#L297-L302',
    r'https://github\.com'
    r'/python/cpython/blob/c39b52f/Lib/poplib\.py#user-content-L297-L302',

    # The domain is currently down. TODO: Revisit after Aug 3, 2021.
    # Ref: https://github.com/cherrypy/cherrypy/issues/1872
    r'https://cheroot\.cherrypy\.org',
    r'https://docs\.cherrypy\.org',
    r'https://www\.cherrypy\.org',
]
linkcheck_workers = 25

nitpicky = True

# NOTE: consider having a separate ignore file
# Ref: https://stackoverflow.com/a/30624034/595220
nitpick_ignore = [
    ('py:data', 'SIGINT'),
    ('py:const', 'socket.SO_PEERCRED'),
    ('py:class', '_pyio.BufferedWriter'),
    ('py:class', '_pyio.BufferedReader'),
    ('py:class', 'unittest.case.TestCase'),
    ('py:meth', 'cheroot.connections.ConnectionManager.get_conn'),

    # Ref: https://github.com/pyca/pyopenssl/issues/1012
    ('py:class', 'pyopenssl:OpenSSL.SSL.Context'),
]

# Ref:
# * https://github.com/djungelorm/sphinx-tabs/issues/26#issuecomment-422160463
sphinx_tabs_valid_builders = ['linkcheck']  # prevent linkcheck warning


# Ref: https://github.com/python-attrs/attrs/pull/571/files\
#      #diff-85987f48f1258d9ee486e3191495582dR82
default_role = 'any'


html_theme = 'furo'

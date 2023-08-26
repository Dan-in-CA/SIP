#! /usr/bin/env python3
# Requires Python 3.6+
"""Sphinx extension for making titles with dates from Git tags."""


import subprocess
from typing import List

from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nodes

import dateutil.parser

from cheroot import __version__


_SCM_COMMANDS = {
    'hg': (
        'hg', 'log',
        '-l', '1',
        '--template', '{date|isodate}',
        '-r',
    ),
    'git': (
        'git', 'log',
        '-1', '--format=%aI',
    ),
}


def _get_scm_timestamp_for(commitish, *, scm=None):
    """Retrieve the tag date from SCM."""
    if scm is None:
        scm = 'git'

    try:
        ts = subprocess.check_output(
            _SCM_COMMANDS[scm] + (commitish,),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except subprocess.SubprocessError:
        raise ValueError(
            f'There is no `{commitish}` in {scm.title()}',
        ) from None

    return dateutil.parser.parse(ts)


class version_subtitle(nodes.subtitle, nodes.Element):
    """Version subtitle node."""


def _visit_version_subtitle(self, node):
    """Inject an opening tag."""
    self.visit_title(node)


def _depart_version_subtitle(self, node):
    """Inject a closing tag."""
    self.depart_title(node)


class SCMVersionTitle(SphinxDirective):
    """Definition of the scm-version-title directive."""

    has_content = True  # False

    def run(self) -> List[nodes.Node]:
        """Generate the node tree in place of the directive."""
        env = self.state.document.settings.env
        ext_conf = env.config.scm_version_title_settings
        # conf_py_path = pathlib.Path(conf._raw_config['__file__'])

        self.assert_has_content()
        first_line = self.content[:1]
        inner_content = self.content[1:]

        version_tag = ''.join(first_line)
        try:
            version_date = _get_scm_timestamp_for(
                version_tag,
                scm=ext_conf['scm'],
            )
        except (ValueError, RuntimeError):
            release_date = '(no Git tag matched)'
        else:
            release_date = f'{{:{ext_conf["date_format"]}}}'.format(
                version_date,
            )

        release_section = nodes.section()
        release_section.tagname = 'div'
        release_section['ids'] = [version_tag.replace('.', '-')]
        release_section['class'] = ['section']

        release_section += version_subtitle(version_tag, version_tag)
        release_section += nodes.paragraph(release_date, release_date)

        self.state.nested_parse(
            inner_content, self.content_offset,
            release_section,
        )
        return [release_section]


def setup(app: Sphinx) -> None:
    """Initialize the extension."""
    app.add_config_value(
        'scm_version_title_settings',
        {
            'scm': 'git',
            'date_format': '%d %b %Y',
        },
        'html',
    )
    app.add_node(
        version_subtitle,
        html=(
            _visit_version_subtitle,
            _depart_version_subtitle,
        ),
    )
    app.add_directive(
        'scm-version-title', SCMVersionTitle,
    )

    return {
        'parallel_read_safe': True,
        'version': __version__,
    }

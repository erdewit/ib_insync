extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinxcontrib.napoleon',
    'sphinx_autodoc_typehints',
    ]

templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = 'ib_insync'
copyright = '2019, Ewald de Wit'
author = 'Ewald de Wit'

__version__ = None
exec(open('../ib_insync/version.py').read())
version = '.'.join(__version__.split('.')[:2])
release = __version__

language = None
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
pygments_style = 'sphinx'
todo_include_todos = False
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'canonical_url': 'https://ib_insync.readthedocs.io',
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    # Toc options
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}
github_url = 'https://github.com/erdewit/ib_insync'

autoclass_content = 'both'
autodoc_member_order = "bysource"
autodoc_default_options = {
    'members': True,
    'undoc-members': True
    }


def onDocstring(app, what, name, obj, options, lines):
    if not lines:
        return
    if lines[0].startswith('Alias for field number'):
        # strip useless namedtuple number fields
        del lines[:]


def setup(app):
    app.connect('autodoc-process-docstring', onDocstring),

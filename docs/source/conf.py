# Configuration file for the Sphinx documentation builder.

import posixpath
from urllib.parse import urljoin

# -- Project information

project = 'i.MX RT GUI'
copyright = '2024, Ran'
author = 'Ran'

release = '0.1'
version = '0.1.1'
language = 'zh_CN'

# -- General configuration

extensions = [
    'sphinx.ext.duration',
    'sphinx.ext.doctest',
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'myst_parser',
]

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

exclude_patterns = ['en/**']

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}
intersphinx_disabled_domains = ['std']

templates_path = ['_templates']

# -- Options for HTML output

# html_theme = 'sphinx_rtd_theme'
html_theme = "furo"
html_static_path = ['_static']
html_css_files = ['language-switch.css']

# -- Options for EPUB output
epub_show_urls = 'footnote'


def add_language_switch(app, pagename, templatename, context, doctree):
    english = app.config.language == 'en'
    page_uri = app.builder.get_target_uri(pagename)
    target_uri = '../' + page_uri if english else 'en/' + page_uri
    context['language_switch_url'] = posixpath.relpath(
        target_uri, posixpath.dirname(page_uri) or '.'
    )
    context['language_switch_label'] = '\u4e2d\u6587' if english else 'English'
    context['language_switch_lang'] = 'zh-CN' if english else 'en'
    context['language_switch_description'] = (
        '\u9605\u8bfb\u672c\u9875\u7684\u4e2d\u6587\u7248' if english
        else 'Read this page in English'
    )
    if english and app.config.html_baseurl:
        context['pageurl'] = urljoin(
            app.config.html_baseurl.rstrip('/') + '/', 'en/' + page_uri
        )


def setup(app):
    app.connect('html-page-context', add_language_switch)

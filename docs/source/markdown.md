# Writing Markdown

This site accepts both Markdown (`.md`) and reStructuredText (`.rst`).
Markdown is parsed by MyST-Parser and uses the same Furo theme as the existing
documentation.

## Add an article

1. Create a Markdown file under the documentation source directory.
2. Start the article with one level-one heading, such as `# GUI overview`.
3. Add its path, without the file extension, to the homepage's `toctree`.
4. Build the HTML documentation and check the article and its navigation.

For example, a new article named `gui-overview.md` can be added to the existing
reStructuredText homepage as follows:

```rst
.. toctree::

   usage
   api
   markdown
   gui-overview
```

For articles in a subdirectory, use a relative entry such as
`imxrt-gui/01-overview`.

```{note}
Existing reStructuredText pages do not need to be converted. Do not create
both `gui-overview.rst` and `gui-overview.md` in the same directory: Sphinx uses
their shared basename as the document name.
```

## Basic Markdown

Use headings, paragraphs, **bold text**, inline `code`, and lists as usual.
Tables and fenced code blocks are also supported.

| Buffer | Purpose |
| --- | --- |
| Draw buffer | Receives rendered pixels |
| Frame buffer | Supplies pixels for display scanning |

```c
uint16_t red = 0xF800U;
```

Fenced blocks are displayed as examples; they are not executed during the
HTML build.

## Links and images

Use relative paths rather than local absolute filesystem paths. MyST resolves
links to source documents into links to the corresponding HTML pages.

These links point to existing reStructuredText documents:

- [Documentation homepage](index.rst)
- [Usage](usage.rst)

The following is example syntax for another Markdown article and an image:

```markdown
[Next article](02-platform-selection.md)
![Display data path](images/display-data-path.png)
```

Keep referenced images inside the documentation source tree, at paths relative
to the article. Add each article to a `toctree`; ordinary hyperlinks alone do
not include a page in the site's navigation.

## Build and publish

Install the project's documentation requirements before building. From the
repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r docs\requirements.txt
.\.venv\Scripts\python.exe -m sphinx -W --keep-going -b html docs\source docs\build\html
```

Create the local virtual environment first if it does not exist, using
`python -m venv .venv`. Activation is not required when using its Python
executable directly.

Read the Docs already installs the same requirements and uses the existing
Sphinx configuration. No hosting change is required; publishing still follows
the project's existing Git and Read the Docs workflow.

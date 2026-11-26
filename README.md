# i.MX RT GUI

This repository publishes a Chinese article series about GUI development on
i.MX RT, from display interfaces and memory to PXP/GPU acceleration and LVGL.
It uses Sphinx, MyST-Parser and the Furo theme with Read the Docs hosting.
Both reStructuredText (`.rst`) and Markdown (`.md`) are supported.

## GUI series

The [series outline](docs/source/imxrt-gui/README.md) covers 24 planned articles.
The following full articles are available:

1. [GUI system overview](docs/source/imxrt-gui/01-gui-system-overview.md)
2. [Platform selection](docs/source/imxrt-gui/02-platform-selection.md)
3. [Memory and bandwidth](docs/source/imxrt-gui/03-memory-and-bandwidth.md)
4. [SPI and QSPI displays](docs/source/imxrt-gui/04-spi-qspi-display.md)

The articles were copied from the SDK project's documentation without removing
the originals. This repository now contains the publishing copy; edit articles
here when preparing website updates.

## Local setup and build

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r docs\requirements.txt
.\.venv\Scripts\python.exe -m sphinx -W --keep-going -b html docs\source docs\build\html
```

Open `docs\build\html\index.html` after a successful build. The virtual
environment does not need to be activated when its Python executable is used
directly.

## Writing Markdown

- Add GUI articles to the [series directory](docs/source/imxrt-gui/).
- Include each article in the [homepage's toctree](docs/source/index.rst),
  using its relative path without the extension.
- Update the [series outline](docs/source/imxrt-gui/README.md) and the previous
  article's navigation when adding a new chapter.
- Use relative links between articles and to images.
- Keep existing reStructuredText documents; conversion is not required.

See the [Markdown writing guide](docs/source/markdown.md) for tables, code
blocks, links and navigation examples.

Markdown support is configured in [conf.py](docs/source/conf.py).
[The requirements](docs/requirements.txt) pin MyST-Parser to version 3.0.1,
which is compatible with the existing Sphinx 7.1.2 and RTD theme dependency
constraints. Upgrade the documentation toolchain together rather than
installing an unconstrained parser version.

## Read the Docs

[The existing hosting configuration](.readthedocs.yaml) already installs the
documentation requirements and loads the Sphinx configuration. No hosting
configuration change is needed to parse Markdown.

Local changes are not automatically published. Use the existing Git and Read
the Docs workflow when ready to publish.

## References

- [Read the Docs tutorial](https://docs.readthedocs.io/en/stable/tutorial/)
- [Sphinx Markdown support](https://www.sphinx-doc.org/en/master/usage/markdown.html)
- [MyST-Parser](https://myst-parser.readthedocs.io/)

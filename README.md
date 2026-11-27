# i.MX RT GUI

This repository publishes a Chinese and English article series about GUI development on
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

The [English outline](docs/source/en/imxrt-gui/README.md) links to complete
English translations. Each website page has a language button that opens its
counterpart, not the other language's homepage.

The articles were copied from the SDK project's documentation without removing
the originals. This repository now contains the publishing copy; edit articles
here when preparing website updates.

## Local setup and build

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r docs\requirements.txt
.\.venv\Scripts\python.exe docs\build_bilingual.py
```

Open `docs\build\html\index.html` for Chinese or
`docs\build\html\en\index.html` for English after a successful build. The virtual
environment does not need to be activated when its Python executable is used
directly.

## Writing Markdown

- Add GUI articles to the [series directory](docs/source/imxrt-gui/).
- Add the matching English article under [the English source tree](docs/source/en/),
  using the same relative path and basename.
- Include each article in both the [Chinese homepage](docs/source/index.rst)
  and [English homepage](docs/source/en/index.rst) toctrees,
  using its relative path without the extension.
- Update both series outlines and both previous articles' navigation when
  adding a new chapter.
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

[The hosting configuration](.readthedocs.yaml) installs the documentation
requirements and runs [the bilingual builder](docs/build_bilingual.py).
The default Chinese URLs remain unchanged; the English site lives under `en/`
within the same Read the Docs version. No separate translation project is needed.

The builder checks that both source trees contain matching document names and
fails if a counterpart is missing. It builds both languages with warnings
treated as errors. Each language has its own Sphinx navigation and search index;
only the shared theme, configuration and language-switch styling are reused.

Use the bilingual builder for website publishing. A direct `sphinx-build`
command builds only the selected source tree and does not produce both sites.

Local changes are not automatically published. Use the existing Git and Read
the Docs workflow when ready to publish.

## References

- [Read the Docs tutorial](https://docs.readthedocs.io/en/stable/tutorial/)
- [Sphinx Markdown support](https://www.sphinx-doc.org/en/master/usage/markdown.html)
- [MyST-Parser](https://myst-parser.readthedocs.io/)

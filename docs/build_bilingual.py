"""Build paired Chinese and English Sphinx sites."""

import argparse
from pathlib import Path
import subprocess
import sys


DOCS_DIR = Path(__file__).resolve().parent


def document_names(source, excluded=None):
    return {
        path.relative_to(source).with_suffix("").as_posix()
        for path in source.rglob("*")
        if path.is_file()
        and path.suffix in {".md", ".rst"}
        and (excluded is None or excluded not in path.parents)
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=DOCS_DIR / "build" / "html"
    )
    args = parser.parse_args()
    source = DOCS_DIR / "source"
    english_source = source / "en"
    chinese_docs = document_names(source, excluded=english_source)
    english_docs = document_names(english_source)

    if chinese_docs != english_docs:
        missing = ", ".join(sorted(chinese_docs - english_docs)) or "none"
        extra = ", ".join(sorted(english_docs - chinese_docs)) or "none"
        parser.error(
            f"English document coverage differs: missing [{missing}], extra [{extra}]. "
            "Add matching documents in both source trees before publishing."
        )

    output = args.output.resolve()
    for language, source_dir, output_dir in [
        ("zh_CN", source, output),
        ("en", english_source, output / "en"),
    ]:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "sphinx",
                "-W",
                "--keep-going",
                "-a",
                "-b",
                "html",
                "-c",
                str(source),
                "-d",
                str(output.parent / f"doctrees-{language}"),
                "-D",
                f"language={language}",
                str(source_dir),
                str(output_dir),
            ],
            check=True,
        )


if __name__ == "__main__":
    main()

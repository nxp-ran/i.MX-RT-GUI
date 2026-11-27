import contextlib
import io
from pathlib import Path
import posixpath
import runpy
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from docs import build_bilingual


class LanguageSwitchTests(unittest.TestCase):
    def test_switches_to_same_page_in_both_directions(self):
        configure = runpy.run_path(
            str(build_bilingual.DOCS_DIR / "source" / "conf.py")
        )["add_language_switch"]
        builder = SimpleNamespace(get_target_uri=lambda page: f"{page}.html")

        for page in ["index", "imxrt-gui/03-memory-and-bandwidth", "search"]:
            for language, current_root, target_root in [
                ("zh_CN", "", "en"),
                ("en", "en", ""),
            ]:
                with self.subTest(page=page, language=language):
                    app = SimpleNamespace(
                        builder=builder,
                        config=SimpleNamespace(language=language, html_baseurl=""),
                    )
                    context = {}
                    configure(app, page, "page.html", context, None)
                    current = posixpath.join(current_root, f"{page}.html")
                    destination = posixpath.normpath(
                        posixpath.join(
                            posixpath.dirname(current), context["language_switch_url"]
                        )
                    )
                    self.assertEqual(
                        destination, posixpath.join(target_root, f"{page}.html")
                    )

    def test_english_canonical_url_stays_in_the_english_site(self):
        configure = runpy.run_path(
            str(build_bilingual.DOCS_DIR / "source" / "conf.py")
        )["add_language_switch"]
        app = SimpleNamespace(
            builder=SimpleNamespace(get_target_uri=lambda page: f"{page}.html"),
            config=SimpleNamespace(
                language="en", html_baseurl="https://docs.example/zh_CN/latest/"
            ),
        )
        context = {"pageurl": "https://docs.example/zh_CN/latest/imxrt-gui/README.html"}
        configure(app, "imxrt-gui/README", "page.html", context, None)
        self.assertEqual(
            context["pageurl"],
            "https://docs.example/zh_CN/latest/en/imxrt-gui/README.html",
        )


class BilingualBuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.docs = Path(self.temporary.name) / "docs"
        source = self.docs / "source"
        (source / "en").mkdir(parents=True)
        (source / "index.rst").write_text("Home\n====\n", encoding="utf-8")
        (source / "en" / "index.rst").write_text("Home\n====\n", encoding="utf-8")

    def run_build(self):
        with mock.patch.object(build_bilingual, "DOCS_DIR", self.docs):
            with mock.patch("sys.argv", ["build_bilingual.py"]):
                build_bilingual.main()

    def test_missing_translation_blocks_publishing(self):
        (self.docs / "source" / "new-article.md").write_text(
            "# New article\n", encoding="utf-8"
        )
        errors = io.StringIO()
        with mock.patch.object(build_bilingual.subprocess, "run") as run:
            with contextlib.redirect_stderr(errors):
                with self.assertRaises(SystemExit) as failure:
                    self.run_build()
        self.assertEqual(failure.exception.code, 2)
        self.assertIn("new-article", errors.getvalue())
        run.assert_not_called()

    def test_sphinx_failure_is_not_reported_as_success(self):
        with mock.patch.object(
            build_bilingual.subprocess,
            "run",
            side_effect=subprocess.CalledProcessError(1, "sphinx"),
        ) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                self.run_build()
        self.assertEqual(run.call_count, 1)


if __name__ == "__main__":
    unittest.main()

import os
import unittest
import tempfile

from OMAP import CodebaseCartographer


class TestCodebaseCartographer(unittest.TestCase):
    def test_python_imports_resolve_to_exact_candidates(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.makedirs(os.path.join(tmp_dir, "foo"), exist_ok=True)
            with open(os.path.join(tmp_dir, "foo", "__init__.py"), "w", encoding="utf-8") as f:
                f.write("# package init\n")
            with open(os.path.join(tmp_dir, "foo", "bar.py"), "w", encoding="utf-8") as f:
                f.write("VALUE = 1\n")
            with open(os.path.join(tmp_dir, "main.py"), "w", encoding="utf-8") as f:
                f.write("import foo.bar\n")

            cartographer = CodebaseCartographer(root_dir=tmp_dir)
            cartographer.scan()

            links = {(link["source"], link["target"]) for link in cartographer.links}
            self.assertIn(("main.py", "foo/bar.py"), links)

    def test_cpp_includes_match_normalized_relative_paths(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.makedirs(os.path.join(tmp_dir, "include"), exist_ok=True)
            with open(os.path.join(tmp_dir, "include", "foo.h"), "w", encoding="utf-8") as f:
                f.write("#pragma once\n")
            with open(os.path.join(tmp_dir, "main.cpp"), "w", encoding="utf-8") as f:
                f.write('#include "include/foo.h"\n')

            cartographer = CodebaseCartographer(root_dir=tmp_dir)
            cartographer.scan()

            links = {(link["source"], link["target"]) for link in cartographer.links}
            self.assertIn(("main.cpp", "include/foo.h"), links)


if __name__ == "__main__":
    unittest.main()

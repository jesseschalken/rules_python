import argparse
import json
import tempfile
import unittest
from pathlib import Path
from textwrap import dedent

from pip._internal.req.req_install import InstallRequirement

from python.pip_install.extract_wheels.parse_requirements_to_bzl import (
    generate_parsed_requirements_contents,
    parse_install_requirements,
    parse_whl_library_args,
)


class TestParseRequirementsToBzl(unittest.TestCase):
    maxDiff = None

    def test_generated_requirements_bzl(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            requirements_lock = Path(temp_dir) / "requirements.txt"
            comments_and_flags = "#comment\n--require-hashes True\n"
            requirement_string = "foo==0.0.0 --hash=sha256:hashofFoowhl"
            requirements_lock.write_bytes(
                bytes(comments_and_flags + requirement_string, encoding="utf-8")
            )
            args = argparse.Namespace()
            args.requirements_lock = str(requirements_lock.resolve())
            args.repo_prefix = "pip_install_deps_pypi__"
            extra_pip_args = ["--index-url=pypi.org/simple"]
            pip_data_exclude = ["**.foo"]
            args.extra_pip_args = json.dumps({"arg": extra_pip_args})
            args.pip_data_exclude = json.dumps({"arg": pip_data_exclude})
            args.python_interpreter = "/custom/python3"
            args.python_interpreter_target = "@custom_python//:exec"
            args.environment = json.dumps({"arg": {}})
            whl_library_args = parse_whl_library_args(args)
            contents = generate_parsed_requirements_contents(
                requirements_lock=args.requirements_lock,
                repo_prefix=args.repo_prefix,
                whl_library_args=whl_library_args,
            )
            library_target = "@pip_install_deps_pypi__foo//:pkg"
            whl_target = "@pip_install_deps_pypi__foo//:whl"
            all_requirements = 'all_requirements = ["{library_target}"]'.format(
                library_target=library_target
            )
            all_whl_requirements = 'all_whl_requirements = ["{whl_target}"]'.format(
                whl_target=whl_target
            )
            self.assertIn(all_requirements, contents, contents)
            self.assertIn(all_whl_requirements, contents, contents)
            self.assertIn(requirement_string, contents, contents)
            all_flags = extra_pip_args + ["--require-hashes", "True"]
            self.assertIn(
                "'extra_pip_args': {}".format(repr(all_flags)), contents, contents
            )
            self.assertIn(
                "'pip_data_exclude': {}".format(repr(pip_data_exclude)),
                contents,
                contents,
            )
            self.assertIn("'python_interpreter': '/custom/python3'", contents, contents)
            self.assertIn(
                "'python_interpreter_target': '@custom_python//:exec'",
                contents,
                contents,
            )
            # Assert it gets set to an empty dict by default.
            self.assertIn("'environment': {}", contents, contents)

    def test_parse_install_requirements_with_args(self):
        # Test requirements files with varying arguments
        for requirement_args in ("", "--index-url https://index.python.com"):
            with tempfile.TemporaryDirectory() as temp_dir:
                requirements_lock = Path(temp_dir) / "requirements.txt"
                requirements_lock.write_text(
                    dedent(
                        """\
                    {}

                    wheel==0.37.1 \\
                        --hash=sha256:4bdcd7d840138086126cd09254dc6195fb4fc6f01c050a1d7236f2630db1d22a \\
                        --hash=sha256:e9a504e793efbca1b8e0e9cb979a249cf4a0a7b5b8c9e8b65a5e39d49529c1c4
                        # via -r requirements.in
                    setuptools==58.2.0 \\
                        --hash=sha256:2551203ae6955b9876741a26ab3e767bb3242dafe86a32a749ea0d78b6792f11 \
                        --hash=sha256:2c55bdb85d5bb460bd2e3b12052b677879cffcf46c0c688f2e5bf51d36001145
                        # via -r requirements.in
                    """.format(
                            requirement_args
                        )
                    )
                )

                install_req_and_lines = parse_install_requirements(
                    str(requirements_lock), ["-v"]
                )

                # There should only be two entries for the two requirements
                self.assertEqual(len(install_req_and_lines), 2)

                # The first index in each tuple is expected to be an `InstallRequirement` object
                self.assertIsInstance(install_req_and_lines[0][0], InstallRequirement)
                self.assertIsInstance(install_req_and_lines[1][0], InstallRequirement)

                # Ensure the requirements text is correctly parsed with the trailing arguments
                self.assertTupleEqual(
                    install_req_and_lines[0][1:],
                    (
                        "wheel==0.37.1     --hash=sha256:4bdcd7d840138086126cd09254dc6195fb4fc6f01c050a1d7236f2630db1d22a     --hash=sha256:e9a504e793efbca1b8e0e9cb979a249cf4a0a7b5b8c9e8b65a5e39d49529c1c4",
                    ),
                )
                self.assertTupleEqual(
                    install_req_and_lines[1][1:],
                    (
                        "setuptools==58.2.0     --hash=sha256:2551203ae6955b9876741a26ab3e767bb3242dafe86a32a749ea0d78b6792f11                         --hash=sha256:2c55bdb85d5bb460bd2e3b12052b677879cffcf46c0c688f2e5bf51d36001145",
                    ),
                )


if __name__ == "__main__":
    unittest.main()

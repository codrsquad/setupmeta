import argparse
import io
import logging
import os
import shutil
import tempfile

import setupmeta
from setupmeta.content import load_contents

if __name__ == "__main__":
    import conftest
else:
    from . import conftest


SCENARIOS = os.path.join(conftest.TESTS, "scenarios")
EXAMPLES = os.path.join(conftest.PROJECT_DIR, "examples")

SCENARIO_COMMANDS = ["explain -c180 -r", "explain -d", "explain --expand", "check", "entrypoints", "version"]


def valid_scenarios(folder):
    result = []
    for name in os.listdir(folder):
        full_path = os.path.join(folder, name)
        setup_py = os.path.join(full_path, "setup.py")
        if os.path.isdir(full_path) and os.path.isfile(setup_py):
            if not setupmeta.WINDOWS or not os.path.exists(os.path.join(full_path, ".hooks")):
                result.append(conftest.relative_path(full_path))
    return result


def scenario_paths():
    """ Available scenario names """
    return valid_scenarios(SCENARIOS) + valid_scenarios(EXAMPLES)


def copytree(src, dst):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            if os.path.isdir(d):
                copytree(s, d)
            else:
                shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)


class Scenario:

    folder = None       # type: str # Folder where scenario is defined
    commands = None     # type: list[str] # setup.py commands to run
    target = None       # type: str # Folder where to run the scenario (temp folder for full git modification support)

    temp = None         # type: str # Optional temp folder used
    origin = None       # type: str # Temp SCM origin to use

    def __init__(self, folder):
        self.folder = os.path.join(conftest.PROJECT_DIR, folder)
        self.commands = []
        self.commands.extend(SCENARIO_COMMANDS)
        self.target = folder
        extra_commands = os.path.join(folder, ".commands")
        if os.path.isfile(extra_commands):
            self.target = None
            with io.open(extra_commands, "rt") as fh:
                for line in fh:
                    line = conftest.decode(line).strip()
                    if line:
                        self.commands.append(line)

    def __repr__(self):
        return conftest.relative_path(self.folder)

    def run_git(self, *args, **kwargs):
        cwd = kwargs.pop("cwd", self.target)
        # git requires a user.email configured, which is usually done in ~/.gitconfig, however under tox, we don't have $HOME defined
        output = setupmeta.run_program(
            "git", "-c", "user.email=tess@test.com", *args,
            cwd=cwd,
            capture=kwargs.pop("capture", True),
            fatal=kwargs.pop("fatal", True),
            **kwargs
        )
        return output

    def prepare(self):
        if self.target:
            os.environ[setupmeta.SCM_DESCRIBE] = "v2.3.0-3-g1234abc"
            return

        # Create a temp origin and clone folder
        self.temp = tempfile.mkdtemp()
        self.origin = os.path.join(self.temp, "origin.git")
        self.target = os.path.join(self.temp, "work")

        os.makedirs(self.origin)
        self.run_git("init", "--bare", self.origin, cwd=self.temp)
        self.run_git("clone", self.origin, self.target, cwd=self.temp)
        copytree(self.folder, self.target)
        self.run_git("add", ".")
        self.run_git("commit", "-m", "Initial commit")
        self.run_git("push", "origin", "master")
        self.run_git("tag", "-a", "v1.2.3", "-m", "Initial tag at v1.2.3")
        self.run_git("push", "--tags", "origin", "master")

    def clean(self):
        if not self.temp:
            del os.environ[setupmeta.SCM_DESCRIBE]
            return

        try:
            shutil.rmtree(self.temp)
        except PermissionError:
            pass

    def replay(self):
        try:
            self.prepare()
            result = []
            for command in self.commands:
                output = ":: %s\n%s" % (command, conftest.run_setup_py(self.target, *command.split()))
                result.append(output)

            return "\n\n".join(result)

        finally:
            self.clean()

    def expected_path(self):
        return os.path.join(self.folder, "expected.txt")

    def expected_contents(self):
        content = load_contents(self.expected_path())
        return content and content.strip()

    def refresh_example(self, dryrun):
        logging.info("Refreshing %s" % self)
        output = self.replay()
        if dryrun:
            print(output)
            return
        with io.open(self.expected_path(), "wt") as fh:
            fh.write("%s\n" % output)


def main():
    """
    Refresh tests/scenarios/*/expected.txt and examples/*/expected.txt
    """
    parser = argparse.ArgumentParser(description=main.__doc__.strip())
    parser.add_argument("--debug", action="store_true", help="Show debug info")
    parser.add_argument("--dryrun", "-n", action="store_true", help="Print output rather, don't update expected.txt")
    parser.add_argument("scenario", nargs="*", help="Scenarios to regenerate (default: all)")
    args = parser.parse_args()

    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=level)
    logging.root.setLevel(level)

    if not args.scenario:
        args.scenario = scenario_paths()

    os.chdir(conftest.PROJECT_DIR)

    for folder in args.scenario:
        scenario = Scenario(folder)
        scenario.refresh_example(args.dryrun)


if __name__ == "__main__":
    main()

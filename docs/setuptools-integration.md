# setuptools integration

The entry points are declared in `ENTRY_POINTS` in our [setup.py](../setup.py) (see
[bootstrap](./bootstrap.md) for why they're explicit), and all land in `setupmeta/hook.py`:

1. `finalize_dist()` runs as a `setuptools.finalize_distribution_options` hook, with
   `order = -100` so it runs before other finalizers. It does nothing unless `setup_requires`
   mentions `setupmeta`: projects that merely have setupmeta installed are left alone.
   It runs *before* `setup.cfg` is read, so it only does `SetupMeta.preprocess()`: resolving
   `install_requires="@file"` style values, which must become lists before setuptools
   validates them.
2. It then swaps in our `parse_command_line()` on that one `Distribution` instance. That runs
   after config files were read and before any command, which is when `SetupMeta.finalize()`
   does the real auto-fill. This is why values from `setup.cfg` count as explicit.
3. `register_keyword()` registers the `versioning` keyword, and retries step 1 for contexts
   where `setup_requires` gets populated late.

`MetaDefs.set_field()` writes values to both `dist.metadata` and `dist`: setuptools 68.2+ reads
some fields from one and some from the other.

The project directory is not the cwd: `SetupMeta.find_project_dir()` finds the `setup.py`
being run from the call stack (or `sys.argv`), and stores it in `MetaDefs.project_dir`, which
every file lookup goes through (`setupmeta.project_path()`).

Commands are classes decorated with `@MetaCommand` (`setupmeta/commands.py`), which gives them
`self.setupmeta`. It is `None` when the project doesn't use setupmeta; `check` then falls back to
setuptools' own behavior, since we override that command for everyone who has us installed.

setuptools deprecated `setup_requires` (it warns about `fetch_build_eggs`), so this activation
mechanism is on borrowed time, see [known gaps](./known-gaps.md).

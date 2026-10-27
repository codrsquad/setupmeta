# Bootstrap

setupmeta uses itself (`setup_requires="setupmeta"`, `versioning="dev"`), which only works once
its own entry points are registered, ie: once `setupmeta.egg-info/` exists. Our
[setup.py](../setup.py) handles that chicken-and-egg problem:

- With no `setupmeta.egg-info/` yet, it runs `setup.py egg_info` twice as a subprocess, without
  self-reference. The second pass is needed so the version gets computed by setupmeta itself.
- A lone `egg_info` command is the bootstrap mode: plain setuptools metadata only.
- Once bootstrapped, `complete_args()` adds the self-reference.

That's also why `entry_points`, `packages` and `name` are stated explicitly instead of
auto-filled: they must be right before setupmeta can run.

Changes here can break installing setupmeta itself: get maintainer review.

Auto-fill for dependency requirements
=====================================

This only applies if you let setupmeta auto-fill your **install_requires**.
If you specify that section explicitly as in::

    setup(
        ...
        install_requires=... whatever you want ...
        ...
    )

Then setupmeta will **not** auto-fill anything.

It's recommended that you let setupmeta auto-fill your requirements
if the following applies to you:

- you don't have complex dependencies (like 99% of projects out there)

- you like to `not repeat yourself`_

- you agree with this `community recommendation`_, ie:

  - in general your **install_requires** should not be pinning dependencies to specific versions

  - you may want to pin to specific versions when building/packaging (in ``requirements.txt``)


How it works
============

Setupmeta auto-fills dependency/requirements from the contents of the following files:

- **install_requires** from:

  - ``requirements.in`` (if present, ``.in`` files are NOT abstracted, used as-is)

  - ``requirements.txt`` (recommended)

  - ``pinned.txt`` (deprecated... some old projects used that convention for some reason, will be removed)


Note: **tests_require** was auto-filled up to setupmeta 3.2.0, but setuptools seems to have
abandoned that idea, the `setuptools documentation`_ doesn't even mention that field any more.
A future version of setupmeta will stop auto-filling this useless field.

Your requirement file is parsed and used to auto-fill the **install_requires**:

- ``.in`` files are used as-is, not abstracted by default

- comments are stripped, but used as hints as to how to auto-fill

- there are 3 categories of dependencies that setupmeta will consider:

  - **abstract**: (default) minimal dependency, not bound to any specific version,
    example: ``requests``

  - **pinned**: explicit dependency, example: ``requests==2.19.1``

  - **indirect**: transitive dependency, not mentioned in **install_requires**,
    but will be pinned to a specific version when building/packaging

- abstracting away applies only to simple ``==`` pinning, and nothing else, ie:

  - ``click==6.7`` will be abstracted as click

  - however ``click>=6.7`` will not be abstracted in any case

- sections of ``requirements.txt`` (or equivalent) can be marked via a comment line,
  all entries below that line (and up to next section) will have the stated category,
  for example::

    # pinned
    arrow==0.12.1
    click==6.7

- you can also quickly mark any given line explicitly, such as::

    arrow==0.12.1
    click==6.7  # pinned


- by default (if no hint comments are specified), dependencies are considered **abstract**



Example
-------

``requirements.txt``::

    arrow==0.12.1
    click==6.7
    requests==2.19.1    # pinned
    retry>=0.9

    # pinned
    attrs==18.1.0
    boto3==1.7.48

    # indirect
    botocore==1.10.48

In the above example, we have:

- the first section is considered **abstract** by default,
  so ``arrow`` and ``click`` will be auto-filled without their pinned versions

- ``requests==2.19.1`` will be auto-filled as pinned,
  due to the ``# pinned`` explicit comment on that line

- ``retry>=0.9`` will be auto-filled as-is, since it's not a simple ``==`` pin
  (even though it is in the default abstract section)

- ``attrs==18.1.0`` and ``boto3==1.7.48`` will be auto-filled as pinned
  due to them being under the ``# pinned`` section

- finally, ``botocore`` will not be auto-filled, due it appearing in a **indirect** section


.. _not repeat yourself: https://en.wikipedia.org/wiki/Don%27t_repeat_yourself

.. _community recommendation: https://packaging.python.org/discussions/install-requires-vs-requirements/

.. _setuptools documentation: https://setuptools.readthedocs.io/en/latest/setuptools.html

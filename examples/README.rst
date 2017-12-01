Examples
========

This folder contains example ``setup.py``'s.

See each subfolder's README for more info on each example.


Test cases
==========

These examples are also used as test case scenarios, ran by `test_examples`_.

Those tests consist of running commands ``explain`` and ``entrypoints`` on each example, and verifying that the output matches the corresponding ``expected.txt``

Use the `refresh.py`_ script to regenerate those ``expected.txt`` files, then ``git diff`` them to validate they look good.


.. _test_examples: ../tests/test_examples.py

.. _refresh.py: ./refresh.py

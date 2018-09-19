readmes: foo

No useful short description on 1st line here

This scenario tests edge cases around finding a suitable short description from a README file

We look at all the READMEs in this folder in this order:
- README.rst: restructured text is historically favorite on pypi
- README.md: markdown being popular, it started being supported as well
- the rest is then examined in alphabetical order

In this test, we're going to:
- README.rst: skipped because no useful short description, and is very short (< 512 chars)
- README.md: will be used as long description (>= 512 chars)
- README: a usable short description is found there
- README1: ignored as prior READMEs got us all the info

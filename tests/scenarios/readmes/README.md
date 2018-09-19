readmes: foo

No useful short description on 1st line here

This scenario tests edge cases around finding a suitable short description from a README file

We look at all the READMEs in this folder in this order:
- README.rst: restructured text is historically favorite on pypi
- README.md: markdown being popular, it started being supported as well
- the rest is then examined in alphabetical order:
    - README: this one will finally have a usable short description (in this project)
    - README1: will be ignored, because we found a suitable short description in README

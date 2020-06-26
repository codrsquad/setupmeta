from setuptools import setup


setup(
    name="via_req_files",
    setup_requires="setupmeta",
    install_requires="@requirements.txt",
    tests_require="@requirements.txt",
    extras_require={
        "feature": "@requirements.txt",
        "extra": "@requirements-extra.txt",
        "missing": "@requirements-missing.txt",
    },
)

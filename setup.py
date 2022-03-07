from setuptools import find_packages, setup


def get_long_description():
    return open("README.md", "r", encoding="utf8").read()


setup(
    name="mangum",
    version="0.14.1",
    packages=find_packages(exclude=["tests*"]),
    license="MIT",
    url="https://github.com/jordaneremieff/mangum",
    description="AWS Lambda support for ASGI applications",
    long_description=get_long_description(),
    python_requires=">=3.7",
    install_requires=["typing_extensions"],
    package_data={"mangum": ["py.typed"]},
    long_description_content_type="text/markdown",
    author="Jordan Eremieff",
    author_email="jordan@eremieff.com",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)

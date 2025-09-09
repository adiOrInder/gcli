import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="gcli",
    version="0.1.0",
    author="adi",
    author_email="your.email@example.com",
    description="A CLI tool for streamlined GitHub workflows with AI-powered commits.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/adiorinder/gcli",  
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Version Control :: Git",
        "Environment :: Console",
    ],
    python_requires='>=3.6',
    install_requires=[
        'PyGithub',
        'descope',
        'requests',
    ],
    entry_points={
        'console_scripts': [
            'gcli = gcli.main:main',
        ],
    },
)
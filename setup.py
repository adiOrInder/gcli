from setuptools import setup, find_packages

setup(
    name='gcli',
    version='0.1.0',
    packages=find_packages(),
    author='adi',
    author_email='your.email@example.com',
    description='A CLI for GitHub with AI-powered commits.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/adiorinder/gcli', # Replace with your repo URL
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    install_requires=[
        'PyGithub',
        'descope',
        'requests',
        'urllib3',
    ],
    entry_points={
        'console_scripts': [
            'gcli=gcli.main:main',
        ],
    },
)
import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

with open("requirements.txt", "r") as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="enochecker_async",
    version="0.0.8",
    author="Trolldemorted",
    author_email="benediktradtke@gmail.com",
    description="Library to build async checker scripts for the EnoEngine A/D CTF Framework in Python",
    long_description=long_description,
    url="https://github.com/enowars/enochecker_async",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        # 'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.7',

    ]
)

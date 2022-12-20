import os
import setuptools

CLASSIFIERS = [
    "Development Status :: 4 - Beta",
    "Natural Language :: English",
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS :: MacOS X",
    "Operating System :: Microsoft :: Windows",
    "License :: OSI Approved :: Apache Software License",
    "Topic :: Scientific/Engineering :: Image Processing",
    "Topic :: Scientific/Engineering :: Bio-Informatics",
    # "Programming language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10"
]

install_requires = [line.rstrip() for line in open(
    os.path.join(os.path.dirname(__file__), "requirements.txt"))]

print("Installation Requirements")
for i, req in enumerate(install_requires):
    print(f"\t{str(i).rjust(3, ' ')}: {req}")

packages = setuptools.find_packages(include=['vpt*'])

_version_ = "0.2.0"

setuptools.setup(
    name="vpt",
    version=_version_,
    long_description="""# Markdown supported!\n\n* Cheer\n* Celebrate\n""",
    long_description_content_type='text/markdown',
    description="Command line tool for highly parallelized processing of Vizgen data",
    author="Vizgen",
    author_email="techsupport@vizgen.com",
    license='Apache Software License',
    license_files=('LICENSE.md',),
    url="https://github.com/Vizgen/vizgen-postprocessing-internal",
    packages=packages,
    install_requires=install_requires,
    package_data={},
    include_package_data=True,
    entry_points={
        'console_scripts': [
            "vpt=vpt.vizgen_postprocess:entry_point"
        ]
    },
    classifiers=CLASSIFIERS,
    python_requires=">=3.9",
)

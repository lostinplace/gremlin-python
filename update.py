#! python3
from typing import Dict, Any, Tuple

from git import Repo

repo_name = "tinkerpop"
repo_url = "https://github.com/apache/tinkerpop.git"
repo_destination_path = f"/tmp/{repo_name}"
python_package_path = f"/tmp/{repo_name}/gremlin-python/src/main/python/"
pom_xml_path = f"/tmp/{repo_name}/gremlin-python/pom.xml"
version_file_path = "./gremlin_python/__version__.py"
setup_py_path = "./setup.py"

project_keys = {
    'authors',
    'classifiers',
    'dependencies',
    'description',
    'dynamic',
    'entry-points',
    'gui-scripts',
    'keywords',
    'license',
    'maintainers',
    'name',
    'optional-dependencies',
    'readme',
    'requires-python',
    'scripts',
    'urls',
    'version',
}

setuptools_keys = {
    'platforms',
    'zip-safe',
    'eager-resources',
    'py-modules',
    'packages',
    'package-dir',
    'namespace-packages',
    'package-data',
    'include-package-data',
    'exclude-package-data',
    'license-files',
    'data-files',
    'script-files',
    'provides',
    'obsoletes',
}


def get_version_from_pom():
    import xml.etree.ElementTree as et
    tree = et.parse(pom_xml_path)
    root = tree.getroot()
    package_version = root.find('.//{http://maven.apache.org/POM/4.0.0}version').text
    import time
    now_stamp = int(time.time() * 1000) / 1000
    version_string = package_version.replace('-SNAPSHOT', '.dev-%d' % now_stamp)
    return version_string, now_stamp


def write_version_file(version_string, timestamp):
    version_line = f"version   = '{version_string}'\n"
    timestamp_line = f"timestamp = {timestamp}\n"
    with open(version_file_path, 'w') as f:
        f.write(version_line)
        f.write(timestamp_line)


def get_setup_py_args():
    """
    monkeypatch the setup() function in setuptools to get the dependencies
    :return:
    """
    import setuptools
    result = {}

    def setup_replacement(**kwargs):
        nonlocal result
        result = kwargs

    setuptools.setup = setup_replacement
    import setup
    return result


def separate_arg_sections(setup_args) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    project_args = {}
    setuptools_args = {}
    other_args = {}
    for key, value in setup_args.items():
        if key in setuptools_keys:
            setuptools_args[key] = value
        elif key in project_keys:
            project_args[key] = value
        else:
            other_args[key] = value
    return project_args, setuptools_args, other_args


def update_pyproject_toml(setup_args):
    import toml
    with open("pyproject.toml", "r") as f:
        pyproject = toml.load(f)
    setup_args['data_files'] = setup_args['data_files'][0][1]
    setup_args['dependencies'] = setup_args['install_requires']
    setup_args['license'] = {'text': setup_args['license']}
    project_args, setuptools_args, other_args = separate_arg_sections(setup_args)
    setuptools_args['packages'] = setup_args['packages']

    pyproject["project"] = project_args
    pyproject["legacy"] = other_args
    pyproject['tool']['setuptools'] = setuptools_args

    pyproject["tool"]["poetry"]["version"] = setup_args['version']

    build_system = {
        "requires": ["setuptools", "setuptools-scm"],
        "build-backend": "setuptools.build_meta"
    }
    pyproject['build-system'] = build_system

    with open("pyproject.toml", "w") as f:
        toml.dump(pyproject, f)


def replace_setup_py():
    new_content = """
from setuptools import setup
setup()
"""
    with open(setup_py_path, "w") as f:
        f.write(new_content)


def adjust_readme():
    with open("README.rst", "r") as f:
        readme = f.read()
    first_line = """

This is a fork of the apache package found here: 
https://github.com/apache/tinkerpop/tree/master/gremlin-python/src/main/python

it is reformatted to work better with other packages

maintenance script is defined in update.py
    
    """

    readme = first_line + readme
    with open("README.rst", "w") as f:
        f.write(readme)


def do_update():
    import shutil

    try:
        shutil.rmtree(repo_destination_path)
    except FileNotFoundError:
        pass

    Repo.clone_from(repo_url, repo_destination_path)

    shutil.copytree(python_package_path, "./", dirs_exist_ok=True)

    setup_py_args = get_setup_py_args()
    version_string, timestamp = get_version_from_pom()
    setup_py_args['version'] = version_string
    write_version_file(version_string, timestamp)

    update_pyproject_toml(setup_py_args)
    replace_setup_py()
    adjust_readme()
    shutil.rmtree(repo_destination_path)


if __name__ == '__main__':
    do_update()

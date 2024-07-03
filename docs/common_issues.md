# Common issues

## I get an error "ModuleNotFoundError: No module named '_ctypes'".

If you are using Linux, you are probably missing the libffi-dev package on your system. You need to install that package using your distribution's package manager. For example `sudo apt-get install libffi-dev` or `sudo yum install libffi-dev`, then re-run `make setup`.

## During the build step, I get an error that the md5sum command is not found.

On MacOS, the md5sum command is not available by default. If you are using homebrew, you can install [the coreutils formula](https://formulae.brew.sh/formula/coreutils) which contains md5sum.

## I get "python-build: definition not found: 3.9.7" on make setup.

Python 3.9.7 is a supported target since [pyenv 2.0.6](https://github.com/pyenv/pyenv/releases/tag/v2.0.6). Make sure you are using version 2.0.6 or newer of Pyenv.

You can verify the version of pyenv by typing `pyenv --version`. If you have the [pyenv-update plugin](https://github.com/pyenv/pyenv-update), you can run `pyenv update` to update it to the latest version.
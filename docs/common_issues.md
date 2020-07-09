# Common issues

## I get an error "ModuleNotFoundError: No module named '_ctypes'".

If you are using Linux, you are probably missing the libffi-dev package on your system. You need to install that package using your distribution's package manager. For example `sudo apt-get install libffi-dev` or `sudo yum install libffi-dev`, then re-run `make setup`.

## During the build step, I get an error that the md5sum command is not found.

On MacOS, the md5sum command is not available by default. If you are using homebrew, you can install [the coreutils formula](https://formulae.brew.sh/formula/coreutils) which contains md5sum.
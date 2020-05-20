# Common issues

## During the packaging step, I get an error that the S3 bucket does not exist or an access denied error.

To package the artifacts, you need to have an S3 bucket with write access and within the same AWS region as where you want to deploy this project.

1. Create or ensure that you have an S3 bucket with write access that you can use to store artifacts (Lambda function code packages, CloudFormation templates, etc.).
2. Set the environment variable `S3_BUCKET` to that bucket name: `export S3_BUCKET=replace-me-with-your-bucket-name`

## I get an error "ModuleNotFoundError: No module named '_ctypes'".

If you are using Linux, you are probably missing the libffi-dev package on your system. You need to install that package using your distribution's package manager. For example `sudo apt-get install libffi-dev` or `sudo yum install libffi-dev`, then re-run `make setup`.

## During the build step, I get an error that the md5sum command is not found.

On MacOS, the md5sum command is not available by default. If you are using homebrew, you can install [the coreutils formula](https://formulae.brew.sh/formula/coreutils) which contains md5sum.
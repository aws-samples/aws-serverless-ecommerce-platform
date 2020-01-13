NAME=ecommerce-platform
PYENV:=$(shell which pyenv)
SPECCY:=$(shell which speccy)
PYTHON_VERSION=3.8.1

validate: validate-pyenv validate-speccy

validate-pyenv:
ifndef PYENV
	$(error Make sure pyenv is accessible in your path. You can install pyenv by following the instructions at 'https://github.com/pyenv/pyenv-installer'.)
endif
ifndef PYENV_SHELL
	$(error Add 'pyenv init' to your shell to enable shims and autocompletion.)
endif
ifndef PYENV_VIRTUALENV_INIT
	$(error Add 'pyenv virtualenv-init' to your shell to enable shims and autocompletion.)
endif

validate-speccy:
ifndef SPECCY
	$(error 'speccy' not found. You can install speccy by following the instructions at 'https://github.com/wework/speccy'.)
endif

# setup: configure tools
setup: validate
	$(info [*] Download and install python $(PYTHON_VERSION))
	@pyenv install $(PYTHON_VERSION)
	@pyenv local $(PYTHON_VERSION)
	$(info [*] Create virtualenv $(NAME) using python $(PYTHON_VERSION))
	@pyenv virtualenv $(PYTHON_VERSION) $(NAME)
	@$(MAKE) activate
	@$(MAKE) requirements

activate: validate-pyenv
	$(info [*] Activate virtualenv $(NAME))
	$(shell eval "$$(pyenv init -)" && eval "$$(pyenv virtualenv-init -)" && pyenv activate $(NAME) && pyenv local $(NAME))
requirements:
	$(info [*] Install requirements)
	@pip install -r requirements.txt
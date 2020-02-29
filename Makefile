# Setup variables
NAME = ecommerce-platform
PYENV := $(shell which pyenv)
SPECCY := $(shell which speccy)
PYTHON_VERSION = 3.8.1

# Service variables
SERVICES = $(shell tools/pipeline services)
export DOMAIN ?= ecommerce
export ENVIRONMENT ?= dev

###################
# SERVICE TARGETS #
###################

# Run CI on services
ci: ci-${SERVICES}
ci-%: lint-% clean-% build-% tests-unit-%

# Run pipeline on services
all: all-${SERVICES}
all-%: lint-% clean-% build-% tests-unit-% package-% deploy-% tests-integ-%

# Build services
build: build-${SERVICES}
build-%:
	@echo "[*] Build $*"
	@make -C $* build

# Check-deps services
check-deps: check-deps-${SERVICES}
clean-%:
	@echo "[*] Check deps $*"
	@make -C $* check-deps

# Clean services
clean: clean-${SERVICES}
clean-%:
	@echo "[*] Clean $*"
	@make -C $* clean

deploy: deploy-${SERVICES}
deploy-%:
	@echo "[*] Deploy $*"
	@make -C $* deploy

# Lint services
lint: lint-$(SERVICES)
lint-%:
	@echo "[*] Lint $*"
	@make -C $* lint

# Package services
package: package-${SERVICES}
package-%:
	@echo "[*] Package $*"
	@make -C $* package

# Integration tests
tests-integ: tests-integ-${SERVICES}
tests-integ-%:
	@echo "[*] Integration tests $*"
	@make -C $* tests-integ

# Unit tests
tests-unit: tests-unit-${SERVICES}
tests-unit-%:
	@echo "[*] Unit tests $*"
	@make -C $* tests-unit

#################
# SETUP TARGETS #
#################

# Validate that necessary tools are installed
validate: validate-pyenv validate-speccy

# Validate that pyenv is installed
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

# Validate that speccy is installed
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

# Activate the virtual environment
activate: validate-pyenv
	$(info [*] Activate virtualenv $(NAME))
	$(shell eval "$$(pyenv init -)" && eval "$$(pyenv virtualenv-init -)" && pyenv activate $(NAME) && pyenv local $(NAME))

# Install python dependencies
requirements:
	$(info [*] Install requirements)
	@pip install -r requirements.txt

# Bootstrap all resources on AWS
bootstrap-prod: bootstrap-services bootstrap-repository

# Bootstrap just the dev environment
bootstrap-dev:
	$(info [*] Bootstrap services)
	@for service in $(shell tools/pipeline services --env-only) ; \
		do tools/toolbox $$service all --env dev --quiet yes || exit 1 ; \
		done

# Bootstrap services in non-dev environment
bootstrap-services:
	$(info [*] Bootstrap services)
	@for service in $(shell tools/pipeline services) ; \
		do tools/toolbox $$service all --env tests --quiet yes || exit 1 ; \
		done

# Push data into the CodeCommit repository
bootstrap-repository:
	$(info [*] Bootstrap repository)
	@git remote add aws $(shell aws ssm get-parameter --name /ecommerce/pipeline/repository/url | jq -r '.Parameter.Value')
	@git push aws HEAD:master
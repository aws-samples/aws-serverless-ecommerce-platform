# Setup variables
NAME = ecommerce-platform
PYENV := $(shell which pyenv)
SPECCY := $(shell which speccy)
PYTHON_VERSION = 3.8.1

# Service variables
SERVICES = $(shell tools/pipeline services)
export DOMAIN ?= ecommerce
export ENVIRONMENT ?= dev

# Colors
ccblue = \033[0;96m
ccend = \033[0m

###################
# SERVICE TARGETS #
###################

# Run CI on services
ci: ci-${SERVICES}
ci-%:
	@${MAKE} lint-$*
	@${MAKE} clean-$*
	@${MAKE} build-$*
	@${MAKE} tests-unit-$*

# Run pipeline on services
all: all-${SERVICES}
all-%: 
	@${MAKE} lint-$*
	@${MAKE} clean-$*
	@${MAKE} build-$*
	@${MAKE} tests-unit-$*
	@${MAKE} package-$*
	@${MAKE} deploy-$*
	@${MAKE} tests-integ-$*

# Build services
build: build-${SERVICES}
build-%:
	@echo "[*] $(ccblue)build $*$(ccend)"
	@make -C $* build

# Check-deps services
check-deps: check-deps-${SERVICES}
check-deps-%:
	@echo "[*] $(ccblue)check-deps $*$(ccend)"
	@make -C $* check-deps

# Clean services
clean: clean-${SERVICES}
clean-%:
	@echo "[*] $(ccblue)clean $*$(ccend)"
	@make -C $* clean

deploy: deploy-${SERVICES}
deploy-%:
	@echo "[*] $(ccblue)deploy $*$(ccend)"
	@make -C $* deploy

# Lint services
lint: lint-$(SERVICES)
lint-%:
	@echo "[*] $(ccblue)lint $*$(ccend)"
	@make -C $* lint

# Package services
package: package-${SERVICES}
package-%:
	@echo "[*] $(ccblue)package $*$(ccend)"
	@make -C $* package

# Integration tests
tests-integ: tests-integ-${SERVICES}
tests-integ-%:
	@echo "[*] $(ccblue)tests-integ $*$(ccend)"
	@make -C $* tests-integ

# Unit tests
tests-unit: tests-unit-${SERVICES}
tests-unit-%:
	@echo "[*] $(ccblue)tests-unit $*$(ccend)"
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
	@echo "[*] Download and install python $(PYTHON_VERSION)"
	@pyenv install $(PYTHON_VERSION)
	@pyenv local $(PYTHON_VERSION)
	@echo "[*] Create virtualenv $(NAME) using python $(PYTHON_VERSION)"
	@pyenv virtualenv $(PYTHON_VERSION) $(NAME)
	@$(MAKE) activate
	@$(MAKE) requirements

# Activate the virtual environment
activate: validate-pyenv
	@echo "[*] Activate virtualenv $(NAME)"
	$(shell eval "$$(pyenv init -)" && eval "$$(pyenv virtualenv-init -)" && pyenv activate $(NAME) && pyenv local $(NAME))

# Install python dependencies
requirements:
	@echo "[*] Install requirements"
	@pip install -r requirements.txt

# # Bootstrap all resources on AWS
# bootstrap-prod: bootstrap-services bootstrap-repository

# # Bootstrap just the dev environment
# bootstrap-dev:
# 	@echo "[*] Bootstrap services"
# 	@for service in $(shell tools/pipeline services --env-only) ; \
# 		do tools/toolbox $$service all --env dev --quiet yes || exit 1 ; \
# 		done

# # Bootstrap services in non-dev environment
# bootstrap-services:
# 	@echo "[*] Bootstrap services"
# 	@for service in $(shell tools/pipeline services) ; \
# 		do tools/toolbox $$service all --env tests --quiet yes || exit 1 ; \
# 		done

# # Push data into the CodeCommit repository
# bootstrap-repository:
# 	@echo "[*] Bootstrap repository"
# 	@git remote add aws $(shell aws ssm get-parameter --name /ecommerce/pipeline/repository/url | jq -r '.Parameter.Value')
# 	@git push aws HEAD:master
# Setup variables
NAME = ecommerce-platform
PYENV := $(shell which pyenv)
JQ := $(shell which jq)
PYTHON_VERSION = 3.9.7
MAKEOPTS += -j4

# Service variables
SERVICES = $(shell tools/services 2>/dev/null)
SERVICES_ENVONLY = $(shell tools/services --env-only 2>/dev/null)
export DOMAIN ?= ecommerce
export ENVIRONMENT ?= dev

# Colors
ccblue = \033[0;96m
ccend = \033[0m

###################
# SERVICE TARGETS #
###################

# Run pipeline on services
all:
	@for service_line in $(shell tools/services --graph --env-only); do \
		${MAKE} ${MAKEOPTS} $$(echo all-$$service_line | sed 's/,/ all-/g') QUIET=true || exit 1 ; \
	done
all-%: 
	@${MAKE} lint-$*
	@${MAKE} build-$*
	@${MAKE} tests-unit-$*
	@${MAKE} check-deps-$*
	@${MAKE} package-$*
	@${MAKE} deploy-$*
	@${MAKE} tests-integ-$*

# Run CI on services
ci: $(foreach service,${SERVICES}, ci-${service})
ci-%:
	@${MAKE} lint-$*
	@${MAKE} build-$*
	@${MAKE} tests-unit-$*

# All but for dependencies
deps-%:
	@for service_line in $(shell tools/services --graph --env-only --deps-of $*); do \
		${MAKE} ${MAKEOPTS} $$(echo all-$$service_line | sed 's/,/ all-/g') QUIET=true || exit 1 ; \
	done

# Artifacts services
artifacts: $(foreach service,${SERVICES_ENVONLY}, all-${service})
artifacts-%:
	@echo "[*] $(ccblue)artifacts $*$(ccend)"
	@${MAKE} -C $* artifacts

# Build services
build: $(foreach service,${SERVICES}, build-${service})
build-%:
	@echo "[*] $(ccblue)build $*$(ccend)"
	@${MAKE} -C $* build

# Check-deps services
check-deps: $(foreach service,${SERVICES_ENVONLY}, check-deps-${service})
check-deps-%:
	@echo "[*] $(ccblue)check-deps $*$(ccend)"
	@${MAKE} -C $* check-deps

# Clean services
clean: $(foreach service,${SERVICES}, clean-${service})
clean-%:
	@echo "[*] $(ccblue)clean $*$(ccend)"
	@${MAKE} -C $* clean

deploy: $(foreach service,${SERVICES_ENVONLY}, deploy-${service})
deploy-%:
	@echo "[*] $(ccblue)deploy $*$(ccend)"
	@${MAKE} -C $* deploy

# Lint services
lint: $(foreach service,${SERVICES}, lint-${service})
lint-%:
	@echo "[*] $(ccblue)lint $*$(ccend)"
	@${MAKE} -C $* lint

# Package services
package: $(foreach service,${SERVICES_ENVONLY}, package-${service})
package-%:
	@echo "[*] $(ccblue)package $*$(ccend)"
	@${MAKE} -C $* package

# Teardown services
teardown:
	@for service_line in $(shell tools/services --graph --reverse --env-only); do \
		${MAKE} ${MAKEOPTS} $$(echo teardown-$$service_line | sed 's/,/ teardown-/g') QUIET=true || exit 1 ; \
	done
teardown-%:
	@echo "[*] $(ccblue)teardown $*$(ccend)"
	@${MAKE} -C $* teardown

# Integration tests
tests-integ: $(foreach service,${SERVICES_ENVONLY}, tests-integ-${service})
tests-integ-%:
	@echo "[*] $(ccblue)tests-integ $*$(ccend)"
	@${MAKE} -C $* tests-integ

# Unit tests
tests-unit: $(foreach service,${SERVICES}, tests-unit-${service})
tests-unit-%:
	@echo "[*] $(ccblue)tests-unit $*$(ccend)"
	@${MAKE} -C $* tests-unit

# End-to-end tests
tests-e2e:
	@tools/tests-e2e

# Performance tests
tests-perf:
	@tools/tests-perf

#################
# SETUP TARGETS #
#################

# Validate that necessary tools are installed
validate: validate-pyenv validate-jq

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

# Validate that jq is installed
validate-jq:
ifndef JQ
	$(error 'jq' not found. You can install jq by following the instructions at 'https://stedolan.github.io/jq/download/'.)
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
	@$(MAKE) npm-install

# setup for Cloud9 environments
setup-cloud9:
	@echo "[*] Install required libraries"
	sudo yum install -y @development zlib-devel bzip2 bzip2-devel readline-devel sqlite sqlite-devel openssl-devel xz xz-devel libffi-devel findutils jq
	@echo "[*] Resize Cloud 9 volume"
	aws ec2 modify-volume --volume-id $$(aws ec2 describe-instances --instance-id $$(curl http://169.254.169.254/latest/meta-data/instance-id) | jq -r .Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId) --size 20
	while [ "$$(aws ec2 describe-volumes-modifications --volume-id $$(aws ec2 describe-instances --instance-id $$(curl http://169.254.169.254/latest/meta-data/instance-id) | jq -r .Reservations[0].Instances[0].BlockDeviceMappings[0].Ebs.VolumeId) --filters Name=modification-state,Values="optimizing","completed" | jq '.VolumesModifications | length')" != "1" ]; do sleep 1; done
	if [ $$(readlink -f /dev/xvda) = "/dev/xvda" ]; then sudo growpart /dev/xvda 1; else sudo growpart /dev/nvme0n1 1; fi
	sudo xfs_growfs -d /
	@echo "[*] Install pyenv"
	curl https://pyenv.run | bash
	echo -e 'export PYENV_ROOT="$$HOME/.pyenv"\nexport PATH="$$PYENV_ROOT/bin:$$PATH"\neval "$$(pyenv init --path)"' >> ~/.profile
	echo -e 'eval "$$(pyenv init -)"\neval "$$(pyenv virtualenv-init -)"' >> ~/.bashrc
	@echo "[*] Install node 12"
	sudo yum remove -y nodejs npm
	curl -sL https://rpm.nodesource.com/setup_12.x | sudo bash -
	sudo yum install -y nodejs
	@echo "****************************"
	@echo "* BEFORE CONTINUING PLEASE *"
	@echo "* RUN THESE COMMANDS:      *"
	@echo
	@echo "  source ~/.profile         "
	@echo "  exec /bin/bash            "
	@echo
	@echo "* THEN CONTINUE WITH THE   *"
	@echo "* FOLLOWING COMMAND:       *"
	@echo
	@echo "  make setup                "
	@echo
	@echo "****************************"

# Activate the virtual environment
activate: validate-pyenv
	@echo "[*] Activate virtualenv $(NAME)"
	$(shell eval "$$(pyenv init -)" && eval "$$(pyenv virtualenv-init -)" && pyenv activate $(NAME) && pyenv local $(NAME))

# Install python dependencies
requirements:
	@echo "[*] Install Python requirements"
	@pip install -r requirements.txt

# Install npm dependencies
npm-install:
	@echo "[*] Install NPM tools"
	@npm install -g speccy

# Create the entire pipeline
bootstrap-pipeline:
	# Deploy in different environments
	@${MAKE} all ENVIRONMENT=tests
	@${MAKE} all ENVIRONMENT=staging
	@${MAKE} all ENVIRONMENT=prod
	# Deploy the pipeline
	@${MAKE} all-pipeline
	# Seed the git repository
	@echo "[*] seed repository"
	@git remote add aws $(shell aws ssm get-parameter --name /ecommerce/pipeline/repository/url | jq -r '.Parameter.Value')
	@git push aws HEAD:main

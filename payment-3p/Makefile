export DOMAIN ?= ecommerce
export ENVIRONMENT ?= dev
export ROOT ?= $(shell dirname ${CURDIR})
export SERVICE ?= $(shell basename ${CURDIR})
export service_dir ?= ${ROOT}/${SERVICE}

export AWS_SDK_LOAD_CONFIG = true

_install:
	npm install

artifacts:
	@${ROOT}/tools/artifacts cloudformation ${SERVICE}

build: _install
	# Copy files to the build folder
	if [ ! -d build/ ]; then \
		mkdir build/ ; \
	fi
	cp -rp src/ build/src/
	npx cdk synth --verbose > build/template.yaml

	# Install packages and transpile to Javascript for each Lambda function
	for function_folder in build/src/* ; do \
		cd $$function_folder ; \
		npm i ; \
		cd ${CURDIR} ; \
		npx tsc -p $$function_folder ; \
	done

	# Package artifacts
	if [ ! -d build/artifacts/ ]; then \
        mkdir build/artifacts/ ; \
    fi

	${ROOT}/tools/helpers/build_artifacts . build/artifacts/
.PHONY: build

check-deps:
	@${ROOT}/tools/check-deps cloudformation ${SERVICE}

clean:
	@${ROOT}/tools/clean ${SERVICE}

deploy:
	@${ROOT}/tools/deploy cloudformation ${SERVICE}

lint: _install
	npm run tests-cdk

package:
	@${ROOT}/tools/package cloudformation ${SERVICE}

teardown:
	@${ROOT}/tools/teardown cloudformation ${SERVICE}

tests-integ: _install
	if yq -r ' .'${ENVIRONMENT}'.flags["can-tests-e2e"] | if . == null then true else . end ' ${ROOT}/environments.yaml | grep -q true; then \
		npm run tests-integ ; \
	else \
		echo "The environment ${ENVIRONMENT} does not support tests. Skipping" ; \
	fi

tests-unit:
	npm run tests-unit
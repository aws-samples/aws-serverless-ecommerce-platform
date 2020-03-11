export DOMAIN ?= ecommerce
export ENVIRONMENT ?= dev
export ROOT ?= $(shell dirname ${CURDIR})
export SERVICE ?= $(shell basename ${CURDIR})
export service_dir ?= ${ROOT}/${SERVICE}

artifacts:
	$(error "Target $@ is not implemented.")

build:
	mkdir build/
	cp -rp src/ build/src/
	cdk synth > build/template.yaml
	tsc -p build/src/
.PHONY: build

check-deps:
	@${ROOT}/tools/check-deps cloudformation ${SERVICE}

clean:
	@${ROOT}/tools/clean ${SERVICE}

deploy:
	@${ROOT}/tools/deploy cloudformation ${SERVICE}

lint:
	npm run test

package:
	@${ROOT}/tools/package cloudformation ${SERVICE}

teardown:
	@${ROOT}/tools/teardown cloudformation ${SERVICE}

tests-integ:
	$(error "Target $@ is not implemented.")

tests-unit:
	$(error "Target $@ is not implemented.")
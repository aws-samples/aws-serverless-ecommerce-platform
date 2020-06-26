export DOMAIN ?= ecommerce
export ENVIRONMENT ?= dev
export ROOT ?= $(shell dirname ${CURDIR})
export SERVICE ?= $(shell basename ${CURDIR})

artifacts:
	@${ROOT}/tools/artifacts cloudformation ${SERVICE}

build:
	@${ROOT}/tools/build resources ${SERVICE}
	@${ROOT}/tools/build openapi ${SERVICE}
	@${ROOT}/tools/build python3 ${SERVICE}
	@${ROOT}/tools/build cloudformation ${SERVICE}
.PHONY: build

check-deps:
	@${ROOT}/tools/check-deps cloudformation ${SERVICE}

clean:
	@${ROOT}/tools/clean ${SERVICE}

deploy:
	@${ROOT}/tools/deploy cloudformation ${SERVICE}

lint:
	@${ROOT}/tools/lint cloudformation ${SERVICE}
	@${ROOT}/tools/lint python3 ${SERVICE}
	@${ROOT}/tools/lint openapi ${SERVICE}

package:
	@${ROOT}/tools/package cloudformation ${SERVICE}

teardown:
	@${ROOT}/tools/teardown cloudformation ${SERVICE}

tests-integ:
	@${ROOT}/tools/tests-integ cloudformation ${SERVICE}

tests-unit:
	@${ROOT}/tools/tests-unit python3 ${SERVICE}
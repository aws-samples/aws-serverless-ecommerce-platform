export DOMAIN ?= ecommerce
export ENVIRONMENT ?= dev
export ROOT ?= $(shell dirname ${CURDIR})
export SERVICE ?= $(shell basename ${CURDIR})
export STACK_NAME ?= ${DOMAIN}-${ENVIRONMENT}-${SERVICE}

build:
	@${ROOT}/tools/build resources ${SERVICE}
	@${ROOT}/tools/build openapi ${SERVICE}
	@${ROOT}/tools/build python3 ${SERVICE}
	@${ROOT}/tools/build cloudformation ${SERVICE}
.PHONY: build

# TODO
check-deps:
	@${ROOT}/tools/check-deps ${SERVICE}

clean:
	@${ROOT}/tools/clean ${SERVICE}

# TODO
deploy:
	@${ROOT}/tools/deploy cloudformation ${SERVICE}

lint:
	@${ROOT}/tools/lint cloudformation ${SERVICE}
	@${ROOT}/tools/lint python3 ${SERVICE}
	@${ROOT}/tools/lint openapi ${SERVICE}

# TODO
package:
	@${ROOT}/tools/package cloudformation ${SERVICE}

# TODO
tests-integ:
	@${ROOT}/tools/tests-integ cloudformation ${SERVICE}

tests-unit:
	@${ROOT}/tools/tests-unit python3 ${SERVICE}
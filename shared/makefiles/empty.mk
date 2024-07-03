export DOMAIN ?= ecommerce
export ENVIRONMENT ?= dev
export ROOT ?= $(shell dirname ${CURDIR})
export SERVICE ?= $(shell basename ${CURDIR})

artifacts:
	$(error "Target $@ is not implemented.")

build:
	$(error "Target $@ is not implemented.")
.PHONY: build

check-deps:
	$(error "Target $@ is not implemented.")

clean:
	$(error "Target $@ is not implemented.")

deploy:
	$(error "Target $@ is not implemented.")

lint:
	$(error "Target $@ is not implemented.")

package:
	$(error "Target $@ is not implemented.")

teardown:
	$(error "Target $@ is not implemented.")

tests-integ:
	$(error "Target $@ is not implemented.")

tests-unit:
	$(error "Target $@ is not implemented.")
SHELL := /bin/bash

setup: env-setup module-setup

remove: env-remove

env-setup:
	conda env create -f environment.yml
	conda activate reddit-tipbot

env-remove:
	conda env remove -n reddit-tipbot -y

module-setup:
	pip install -e src

test:
	pytest -x

black:
	black --check ./




SHELL := /bin/bash

setup: env-setup module-setup

remove: env-remove

env-setup:
	conda env create reddit-tipbot
	conda activate reddit-tipbot
	conda env update -f environment.yml

env-remove:
	conda env remove -n reddit-tipbot -y

module-setup:
	pip install -e src

test:
	pytest -x

black:
	black --check ./




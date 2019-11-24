SHELL := /bin/bash

setup: env-setup module-setup

remove: env-remove

env-setup:
	conda env create -f environment.yml

env-remove:
	conda env remove -n reddit-tipbot -y

module-setup:
	source activate reddit-tipbot && pip install -e src
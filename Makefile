setup: env-setup

remove: env-remove

env-setup:
	conda env create -f environment.yml

env-remove:
	conda env remove -n reddit-tipbot -y
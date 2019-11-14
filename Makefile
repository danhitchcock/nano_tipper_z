setup: env-setup

remove: env-remove

env-setup:
	conda env update -f environment.yml
	source activate reddit-tipbot && python -m ipykernel install --user --name reddit-tipbot

env-remove:
	conda env remove -n reddit-tipbot -y
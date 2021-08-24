#TODO: setup docker commands to isolate $HOME akin to Singularity

.openwpm: | OpenWPM
	cd OpenWPM; docker build -f Dockerfile -t openwpm .
	touch .openwpm

.notebook:
	docker build -f Dockerfile.notebook -t notebook .
	touch .notebook

notebook: .notebook
	-docker container stop notebook
	docker run -d --rm -p $(NOTEBOOK_PORT):8888 --name notebook -v $(CURDIR)/data:/home/jovyan/work --user $(shell id -u) --group-add $(GROUP) $(SSL) \
	notebook start-notebook.sh --NotebookApp.password=$(NOTEBOOK_PASS)

define crawl
	docker run --shm-size=2g \
	-v $(CURDIR)/crawl:/opt/crawl \
	-v $(CURDIR)/data:/opt/data \
	-v $(CURDIR)/logs:/opt/logs \
	--group-add $(GROUP) \
	-it --rm openwpm python /opt/crawl/$(1) $(2)
endef


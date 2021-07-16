include Config

setup-openwpm-submodule:
	git submodule add $(OPENWPM_REPO) OpenWPM
	cd OpenWPM; git checkout $(OPENWPM_VERSION)

.openwpm: | OpenWPM
	cd OpenWPM; docker build -f Dockerfile -t openwpm .
	touch .openwpm

.notebook:
	docker build -f Dockerfile.notebook -t notebook .
	touch .notebook

SSL=
ifeq ($(NOTEBOOK_HTTPS),1)
	SSL=-e GEN_CERT\=yes
endif
notebook: .notebook
	-docker container stop notebook
	docker run -d --rm -p $(NOTEBOOK_PORT):8888 --name notebook -v $(CURDIR)/data:/home/jovyan/work --user $(shell id -u) --group-add $(GROUP) $(SSL) \
	notebook start-notebook.sh --NotebookApp.password=$(NOTEBOOK_PASS)

setup:
	git submodule init
	git submodule update
	make .openwpm
	make directories

data:
	-mkdir data
	-setfacl -d -m g::rwX data

logs:
	-mkdir logs
	-setfacl -d -m g::rwX logs

directories: | data logs

fix-permissions:
	sudo chown -R $(shell id -u):$(GROUP) data
	sudo find data/ -type d -exec chmod 2775 {} \+
	sudo find data/ -type f -exec chmod 664 {} \+

define crawl
	docker run --shm-size=2g \
	-v $(CURDIR)/crawl:/opt/crawl \
	-v $(CURDIR)/data:/opt/data \
	-v $(CURDIR)/logs:/opt/logs \
	--group-add $(GROUP) \
	-it --rm openwpm python /opt/crawl/$(1) $(2)
endef

precrawl:directories .openwpm
	$(call crawl,precrawl.py,all)

precrawl-small:directories .openwpm
	$(call crawl,precrawl.py,fire)

precrawl-test:directories .openwpm
	$(call crawl,precrawl.py,test)

crawl:directories .openwpm
	echo "This will run a full crawl including deep links harvested during precrawl. Not yet implemented."

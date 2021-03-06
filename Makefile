include Config

ifeq ($(CONTAINER_TYPE),docker)
	include docker.mk
endif
ifeq ($(CONTAINER_TYPE),singularity)
	include singularity.mk
endif

SSL=
ifeq ($(NOTEBOOK_HTTPS),1)
	SSL=-e GEN_CERT\=yes
endif

ifdef CMP
	CMP=--cmp
endif

ifdef COOKIES
	COOKIES=--cookies
endif

setup-openwpm-submodule:
	git submodule add $(OPENWPM_REPO) OpenWPM
	cd OpenWPM; git checkout $(OPENWPM_VERSION)
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

crawl:directories .openwpm
	$(call crawl,crawl.py,full)

crawl-small:directories .openwpm
	$(call crawl,crawl.py,small)

crawl-test:directories .openwpm
	$(call crawl,crawl.py,test)

precrawl:directories .openwpm
	$(call crawl,precrawl-reject.py,full)

precrawl-small:directories .openwpm
	$(call crawl,precrawl.py,small)

precrawl-test:directories .openwpm
	$(call crawl,precrawl.py,test)

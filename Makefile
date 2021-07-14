OPENWPM_REPO=https://github.com/mozilla/OpenWPM.git
OPENWPM_VERSION=v0.16.0

setup-openwpm-submodule:
	git submodule add $(OPENWPM_REPO) OpenWPM
	cd OpenWPM; git checkout $(OPENWPM_VERSION)

build-docker-image:
	cd OpenWPM; docker build -f Dockerfile -t openwpm .

build-notebook-image:
	docker build -f Dockerfile.notebook -t notebook .

notebook:
	-docker container stop notebook
	docker run -d --rm -p 8889:8888 --name notebook -v $(CURDIR)/data:/home/jovyan/work --user 1001 --group-add users -e GEN_CERT=yes \
	notebook start-notebook.sh --NotebookApp.password='argon2:$$argon2id$$v=19$$m=10240,t=10,p=8$$Jl7whmIEtW7USolMH6w0MQ$$fS5qc3oookfChh146si8Ng'

notebook-http:
	docker run -d --rm -p 8888:8888 --name notebook -v $(CURDIR)/data:/home/jovyan/work --user 1000 --group-add users \
	notebook start-notebook.sh --NotebookApp.password='argon2:$$argon2id$$v=19$$m=10240,t=10,p=8$$Jl7whmIEtW7USolMH6w0MQ$$fS5qc3oookfChh146si8Ng'

setup:
	git submodule init
	git submodule update
	make build-docker-image

.PHONY:directories
	mkdir data logs
	setfacl -d -m g::rwX data logs

define crawl
	docker run --shm-size=2g \
	-v $(CURDIR)/crawl:/opt/crawl \
	-v $(CURDIR)/data:/opt/data \
	-v $(CURDIR)/logs:/opt/logs \
	-it --rm openwpm python /opt/crawl/$(1) $(2)
endef

precrawl:directories
	$(call crawl,precrawl.py,all)

precrawl small:directories
	$(call crawl,precrawl.py,fire)

precrawl test:directories
	$(call crawl,precrawl.py,test)

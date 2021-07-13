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
	docker run -d --rm -p 8888:8888 --name notebook -v $(CURDIR)/data:/home/jovyan/work --user 1000 --group-add users -e GEN_CERT=yes \
	-e PASSWORD='argon2:$argon2id$v=19$m=10240,t=10,p=8$Jl7whmIEtW7USolMH6w0MQ$fS5qc3oookfChh146si8Ng' notebook start-notebook.sh

notebook-http:
	docker run -d --rm -p 8888:8888 --name notebook -v $(CURDIR)/data:/home/jovyan/work --user 1000 --group-add users \
	-e PASSWORD='argon2:$argon2id$v=19$m=10240,t=10,p=8$Jl7whmIEtW7USolMH6w0MQ$fS5qc3oookfChh146si8Ng' notebook start-notebook.sh

setup:
	git submodule init
	git submodule update
	make build-docker-image

.PHONY:directories
	mkdir data logs
	setfacl -d -m g::rwX data logs

precrawl:directories
	docker run --shm-size=2g \
	-v $(CURDIR)/crawl:/opt/crawl \
	-v $(CURDIR)/data:/opt/data \
	-v $(CURDIR)/logs:/opt/logs \
	-it openwpm python /opt/crawl/precrawl.py

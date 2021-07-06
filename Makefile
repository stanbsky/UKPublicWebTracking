OPENWPM_REPO=https://github.com/mozilla/OpenWPM.git
OPENWPM_VERSION=v0.16.0

setup-openwpm-submodule:
	git submodule add $(OPENWPM_REPO) OpenWPM
	cd OpenWPM; git checkout $(OPENWPM_VERSION)

build-docker-image:
	cd OpenWPM; docker build -f Dockerfile -t openwpm .

setup:
	git submodule init
	git submodule update
	make build-docker-image

export SINGULARITY_CACHEDIR := $(SINGULARITY_CACHEDIR)
export SINGULARITY_TMPDIR := $(SINGULARITY_TMPDIR)

export:
	./test_export.sh

.openwpm:
	make openwpm.sif
	touch .openwpm

openwpm.sif: | OpenWPM
	singularity build --remote openwpm.sif docker://stanbsky/openwpm:$(OPENWPM_DOCKER_TAG)

notebook.sif:
	spython recipe Dockerfile.notebook notebook.def
	singularity build --remote notebook.sif notebook.def

notebook: notebook.sif
	-singularity instance stop notebook
	singularity instance start \
	-H $(CURDIR)/.notebook_home \
	-B $(CURDIR)/data:/home/jovyan/work \
    notebook.sif notebook
	singularity exec instance://notebook start-notebook.sh \
	--NotebookApp.notebook_dir=/home/jovyan/work \
    --NotebookApp.password=$(NOTEBOOK_PASS) \
    --NotebookApp.port=$(NOTEBOOK_PORT)

define crawl
	singularity exec \
	-B $(CURDIR)/crawl:/opt/crawl \
	-B $(CURDIR)/data:/opt/data \
	-B $(CURDIR)/logs:/opt/logs \
	-B /run:/run \
	--pwd /opt/OpenWPM \
	openwpm.sif python /opt/crawl/$(1) \
	--type $(2) --browsers $(BROWSERS) --display $(DISPLAY) \
	--data $(DATA_DIR) --logs $(LOGS_DIR) --lists $(LISTS_DIR) \
	--urls $(PRECRAWL_URLS) --screenshots $(SCREENSHOTS) $(CMP)
endef

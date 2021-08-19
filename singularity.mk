export SINGULARITY_CACHEDIR := $(SINGULARITY_CACHEDIR)
export SINGULARITY_TMPDIR := $(SINGULARITY_TMPDIR)

export:
	./test_export.sh

.openwpm:
	make openwpm.sif
	touch .openwpm

openwpm.sif: | OpenWPM
	singularity pull openwpm.sif docker://openwpm/openwpm:$(OPENWPM_DOCKER_TAG)

notebook.sif:
	spython recipe Dockerfile.notebook notebook.def
	singularity build --remote notebook.sif notebook.def

notebook: notebook.sif
	-singularity instance stop notebook
	singularity instance start \
	-B $(CURDIR)/data:/home/jovyan \
    --no-home notebook.sif notebook
	singularity exec instance://notebook start-notebook.sh \
    --NotebookApp.password=$(NOTEBOOK_PASS) \
    --NotebookApp.port=$(NOTEBOOK_PORT)

define crawl
	singularity exec --no-home \
	-B $(CURDIR)/crawl:/opt/crawl \
	-B $(CURDIR)/data:/opt/data \
	-B $(CURDIR)/logs:/opt/logs \
	-B /run:/run \
	--pwd /opt/OpenWPM \
	openwpm.sif python /opt/crawl/$(1) $(2)
endef


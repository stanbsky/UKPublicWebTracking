# UKPublicWebTracking

Perform a crawl and spin up a Jupyter Notebook to analyse the results with just a couple `make` commands.

__Step 1:__ Install Docker on your system. Most Linux distributions have Docker
in their repositories. It can also be installed from
[docker.com](https://www.docker.com/). For Ubuntu you can use:
`sudo apt-get install docker.io`

You can test the installation with: `sudo docker run hello-world`

_Note,_ in order to run Docker without root privileges, add your user to the
`docker` group (`sudo usermod -a -G docker $USER`). You will have to
logout-login for the change to take effect, and possibly also restart the
Docker service.

__Step 2:__ Modify `Config` as necessary. Options such as a password for the Jupyter Notebook can be set.

__Step 3:__ Run `make setup` to setup the directory for running crawls.

`make precrawl` will execute the precrawl script, using the URLs listed in `crawl/lists/urls.json`. Records full responses for HTML and JS files in LevelDB as well as full and partial viewport screenshots.

`make notebook` will spin up a docker container accessible at the port specified in `Config` with the crawl data accessible.

*NB:* you may need to run `make fix-permissions` to access some of the data in the notebook. This is because OpenWPM requires to be run as root inside its container, with the corresponding permissions on the files it writes in data/ .

~~make crawl~~ not yet implemented.

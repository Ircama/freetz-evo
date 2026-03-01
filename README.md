# Welcome to Freetz-EVO

```
    ______               __             _______    ______
   / ____/_______  ___  / /_____       / ____/ |  / / __ \
  / /_  / ___/ _ \/ _ \/ __/_  /______/ __/  | | / / / / /
 / __/ / /  /  __/  __/ /_  / //_____/ /___  | |/ / /_/ /
/_/   /_/   \___/\___/\__/ /___/    /_____/  |___/\____/

```

Freetz-EVO is a fork of [Freetz-NG](https://github.com/Freetz-NG/freetz-ng). More features - less bugs!

Compared to Freetz-NG, Freetz-EVO includes GCC on-device compilation, nginx, rtorrent, ruTorrent, PHP,
aria2, AI translation for foreign languages, more explicit error/warning messages, an advanced GitHub
Action for testing new developments, and many other new packages.

### Basic infos:
  * A web interface will be started on [port :81](http://fritz.box:81/), credentials: `admin`/`freetz`<br>
  * Default credentials for shell/ssh/telnet access are: `root`/`freetz`<br>
  * For more see: [ircama.github.io/freetz-evo](https://ircama.github.io/freetz-evo/)

### Requirements:
  * You need an up to date Linux System with some [prerequisites](docs/prerequisites/README.md).
  * Or download a ready-to-use VM like Gismotro's [Freetz-Linux](https://freetz.digital-eliteboard.com/?dir=Teamserver/Freetz/Freetz-VM/VirtualBox/) (user & pass: `freetz`).
  * There are also Docker images available like [pfichtner-freetz](https://hub.docker.com/r/pfichtner/freetz) ([README](https://github.com/pfichtner/pfichtner-freetz#readme)).

### Clone the main branch:
```
  git clone https://github.com/Ircama/freetz-evo ~/freetz-evo
```

### Or clone a single [tag](../../tags):
```
  git clone https://github.com/Ircama/freetz-evo ~/freetz-evo --single-branch --branch TAGNAME
```

### Install prerequisites:
```
  cd ~/freetz-evo
  tools/prerequisites install # -y
```

### Build firmware:
```
  cd ~/freetz-evo
  make menuconfig
  make
  # make help
```

### Flash firmware:
```
  cd ~/freetz-evo
  tools/push_firmware -h
```

### Show GIT states:
```
  git status
  git diff --no-prefix # --cached # > file.patch
  git log --graph # --oneline
```

### Delete local changes:
```
  git checkout master ; git fetch --all --prune ; git reset --hard origin/HEAD ; git clean -fd
```

### Update GIT:
```
  git pull
```

### Checkout old revision:
```
  git checkout HASH-OF-COMMIT # -b NEW-BRANCH
```
### Checkout another branch:
```
  git checkout EXISTING-BRANCH
```

### Mirrors:
```
  git clone https://github.com/Ircama/freetz-evo ~/freetz-evo
```

### Documentation:
See [https://ircama.github.io/freetz-evo/](https://ircama.github.io/freetz-evo/) (or [docs/](docs/README.md)).


<details>
  <summary>Testing your Documentation changes localy</summary>

When working on this repo, it is advised that you review your changes locally before committing them. The `mkdocs serve` command can be used to live preview your changes (as you type) on your local machine.

Please make sure you fork the repo and change the clone URL in the example below for your fork:

- Linux Mint / Ubuntu 20.04 LTS / 23.10 and later:
    - Preparations (only required once):

    ```bash
    git clone https://github.com/YOUR-USERNAME/freetz-evo
    cd freetz-evo
    sudo apt install python3-pip python3-venv
    python3 -m venv .venv
    source .venv/bin/activate
    pip3 install -r .github/mkdocs/requirements.txt
    ```

    - Enter the virtual environment (if exited):

    ```bash
    source .venv/bin/activate
    ```

    - Running the docs server:

    ```bash
    mkdocs serve --dev-addr 0.0.0.0:8000 --config-file .github/mkdocs/mkdocs.yml
    ```

- Fedora Linux instructions (tested on Fedora Linux 28):
    - Preparations (only required once):

    ```bash
    git clone https://github.com/YOUR-USERNAME/freetz-evo
    cd freetz-evo
    pip install --user -r .github/mkdocs/requirements.txt
    ```

    - Running the docs server:

    ```bash
    mkdocs serve --dev-addr 0.0.0.0:8000 --config-file .github/mkdocs/mkdocs.yml
    ```

After these commands, the current branch is accessible through your favorite browser at <http://localhost:8000>

</details>

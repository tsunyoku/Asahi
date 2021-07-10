[![Discord](https://discordapp.com/api/guilds/833325274934411274/widget.png?style=shield)](https://discord.gg/d62tzSYv3z)
# Asahi

avatar, bancho & /web/ server & Discord bot hybrid for osu! 😎

Note: This has only been tested on Ubuntu 18.04 LTS. If you would like to use it on a distro other than Ubuntu or a version greater than 18.04, you can make Asahi work by changing the minimum TLS version in the nginx config (to my belief atleast).
Note 2: In the rare case you edit the packet reader/writer, you will need to rebuild the cython files upon any edits. You can find instructions further below on how to build them if you do change it.

## Setup

First install any requirements:
```bash
sudo add-apt-repository ppa:deadsnakes/ppa # for python 3.9
sudo apt update
sudo apt install python3.9 python3.9-dev python3.9-distutils nginx build-essential certbot postgresql postgresql-contrib redis-server
wget https://bootstrap.pypa.io/get-pip.py
python3.9 get-pip.py && rm get-pip.py
python3.9 -m pip install -r ext/requirements.txt
git submodule init && git submodule update
```

You can find the database structure in ext/db.sql, you may want to import that before you advance. (Note: we use postgresql not mysql! You will also need to edit the sql file for use with your postgre user)

Now, edit your nginx config (found in ext/nginx.conf), here we will generate the certificate for your nginx config and reload:
```bash
sudo certbot certonly --manual --preferred-challenges=dns --email your@email.com --server https://acme-v02.api.letsencrypt.org/directory --agree-tos -d *.your.domain -d your.domain # change your.domain & email to your own
sudo ln ext/nginx.conf /etc/nginx/sites-enabled/asahi.conf # make a link between nginx folder and asahi's folder so you can easy edit the config as needed
sudo nginx -s reload # reload nginx config
```

Now, copy the config file and edit the config:
```bash
cp ext/config.sample.py config.py
```

We also want to compile the pp systems & packet handlers:
```bash
chmod +x ext/osu-tools.sh
./ext/osu-tools.sh
chmod +x oppai-ng/libbuild
./oppai-ng/libbuild
cd packets && python3.9 setup.py build_ext --inplace && cd ..
```

Finally, start up Asahi:
```bash
./main.py
```

## Useful Tools

- [Asahi Migration Tool](https://github.com/tsunyoku/asahiMigration) - Migrate your ripple/gulag database to Asahi.
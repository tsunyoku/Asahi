[![Discord](https://discordapp.com/api/guilds/833325274934411274/widget.png?style=shield)](https://discord.gg/d62tzSYv3z)
# Asahi

avatar, bancho & /web/ server hybrid for osu! 😎

Note: This has only been tested on Ubuntu 18.04 LTS and other operating systems may have unpredicted behaviour

Note 2: This is a very experimental project mainly for my own learning and I don't suggest in any world using this on your own server in its current state for the forseeable future.

## Setup

First install any requirements:
```bash
sudo add-apt-repository ppa:deadsnakes/ppa # for python 3.9
sudo apt update
sudo apt install python3.9 python3.9-dev python3.9-distutils nginx build-essential certbot postgresql postgresql-contrib redis-server
python3.9 -m pip install -r ext/requirements.txt
wget https://bootstrap.pypa.io/get-pip.py
python3.9 get-pip.py && rm get-pip.py
```

You can find the database structure in ext/db.sql, you may want to import that before you advance. (Note: we use postgresql not mysql! You will also need to edit the sql file for use with your postgre user)
I will sadly not provide support with postgre setup as I still don't even understand it myself, lol.

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

We also want to compile the pp system:
```bash
chmod +x ext/osu-tools.sh
./ext/osu-tools.sh
```

Finally, startup Asahi using hypercorn:
```bash
hypercorn main.py -b unix:/tmp/asahi.sock --reload --log-level error
```

## Related Projects

None of these projects are worked on by me and any issues with them should not be redirected to me, these are simply Asahi-related projects.

- [asahi-web](https://github.com/7ez/asahi-web)

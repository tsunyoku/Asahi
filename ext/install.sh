#!/bin/bash
echo "Starting install script"
echo "Please understand that while this script is written to make the install process easy, you still need basic linux and python knowledge to use Asahi. While I (tsunyoku) am open to helping people, if you have no clue what you are doing that isn't my problem and I won't provide support for this! If you are aware of this and would like to continue, press 'Y', else, press 'N' to exit now."
read understand

if [ $understand = "N" ]
then
  exit 0
fi

echo "This script is also untested so errors may arise. If this happens, please join the Asahi Discord and report them so I can fix them. Thanks!"
echo "This script is written with assumption you are using Ubuntu 18.04. If you are not please edit this script to install the correct Microsoft package! If you are not using Ubuntu 18.04, exit now by typing 'N'. Otherwise, type 'Y' to continue!"
read cont

if [ $cont = "N" ]
then
  exit 0
fi

echo "Installing dependencies... You may be asked to enter your password as we are using sudo, please do so."
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.9 python3.9-dev python3.9-distutils nginx build-essential certbot mariadb-server redis-server
wget https://bootstrap.pypa.io/get-pip.py
python3.9 get-pip.py && rm get-pip.py
python3.9 -m pip install -r ext/requirements.txt
git submodule init && git submodule update

echo "Creating certificate... You will need to follow the instructions in console!"
echo "Please enter your server domain!"
read domain
echo "Please enter your email!"
read email
sudo certbot certonly --manual --preferred-challenges=dns --email $email --server https://acme-v02.api.letsencrypt.org/directory --agree-tos -d *.$domain -d $domain # change your.domain & email to your own

echo "Do you already have a database user created? (Y/N)"
read create_user

if [ $create_user = "N" ]
then
  echo "Creating user..."
  echo "Please enter your desired username"
  read username
  echo "Please read your desired password"
  read password

  sudo mariadb -e "CREATE USER IF NOT EXISTS $username IDENTIFIED BY "$password;""
  sudo mariadb -e "GRANT ALL PRIVILEGES ON *.* TO $username;"
fi

echo "Creating and importing database..."
echo "Please enter your desired database name"
read db

sudo mariadb -e "CREATE DATABASE IF NOT EXISTS $db"
sudo mariadb $db < ext/db.sql

sed -i -e "s/tsunyoku.xyz/$domain/g" ext/nginx.conf
read dm tld <<<$(IFS="."; echo $domain)
sed -i -e "s/DOMAIN/$dm/g" ext/nginx.conf
sed -i -e "s/TLD/$tld/g" ext/nginx.conf
sudo ln ext/nginx.conf /etc/nginx/sites-enabled/asahi.conf
sudo nginx -s reload

pkgs='apt-transport-https dotnet-sdk-5.0'
install=false
for pkg in $pkgs; do
  status="$(dpkg-query -W --showformat='${db:Status-Status}' "$pkg" 2>&1)"
  if [ ! $? = 0 ] || [ ! "$status" = installed ]; then
    install=true
    break
  fi
done
if "$install"; then
  wget https://packages.microsoft.com/config/ubuntu/18.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
  sudo dpkg -i packages-microsoft-prod.deb
  sudo apt-get update; \
    sudo apt-get install -y apt-transport-https && \
    sudo apt-get update && \
    sudo apt-get install -y dotnet-sdk-5.0
fi

if [ ! -d "./osu-tools" ]
then
  echo "There was an error getting submodules. I will try to get them again..."
  git submodule init && git submodule update
fi

cd osu-tools
dotnet restore
dotnet publish -r linux-x64 PerformanceCalculator -c Release -o compiled/ /p:PublishSingleFile=true
cd ..
rm -rf packages-microsoft-prod.deb

chmod +x oppai-ng/libbuild
./oppai-ng/libbuild
cd packets && python3.9 setup.py build_ext --inplace && cd ..

cp ext/config.sample.py config.py
echo "Installer complete! Please edit config.py and you will be good to go. You can start Asahi by running ./main.py"

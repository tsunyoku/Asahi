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
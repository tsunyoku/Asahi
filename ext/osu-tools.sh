wget https://packages.microsoft.com/config/ubuntu/18.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
sudo apt-get update; \
  sudo apt-get install -y apt-transport-https && \
  sudo apt-get update && \
  sudo apt-get install -y dotnet-sdk-5.0

cd osu-tools
dotnet restore
dotnet publish -r  linux-x64 PerformanceCalculator -c Release -o compiled/ /p:PublishSingleFile=true
rm -rf packages-microsoft-prod.deb

## Setting Up Docker Across Platforms
This guide covers the installation of [Docker](https://www.docker.com/) and how to run your first container image on Linux, macOS, and Windows.
## 1. Installation
The easiest way to get started on Windows and Mac is Docker Desktop, while Linux users typically install the Docker Engine directly. 
## Windows

   1. Download: Get the installer from [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/).
   2. Install: Run the .exe. Ensure WSL 2 (Windows Subsystem for Linux) is selected during setup.
   3. Start: Launch Docker Desktop from the Start menu. 

## macOS

   1. Download: Choose the correct version (Intel or Apple Silicon) at Docker Desktop for Mac.
   2. Install: Open the .dmg and drag the Docker icon to your Applications folder.
   3. Start: Open Docker from Applications and allow the necessary permissions.

## Linux (Ubuntu/Debian)
Run these commands in your terminal to install the native engine:

sudo apt update
sudo apt install docker.io
sudo systemctl start docker
sudo systemctl enable docker

# Optional: Run docker without sudo
sudo usermod -aG docker $USER# Log out and back in for changes to take effect

## 2. Verify Installation
Open your terminal (PowerShell on Windows, Terminal on Mac/Linux) and run: 

docker --version

## 3. Running a Docker Image
To test your setup, download and run the classic "Hello World" image. This command automatically "pulls" (downloads) the image if you don't have it locally.

# Test command
docker run hello-world
# Pull a specific image (e.g., Nginx server)
docker pull nginx
# Run an image in the background (detached mode)
docker run -d -p 8080:80 nginx

## 4. Basic CLI Management

| Action  | Command |
|---|---|
| List Running Containers | docker ps |
| List All Containers | docker ps -a |
| List Downloaded Images | docker image ls |
| Stop a Container | docker stop <container_id> |
| Remove a Container | docker rm <container_id> |
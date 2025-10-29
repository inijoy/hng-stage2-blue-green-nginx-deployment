Blue-Green NGINX Deployment with Docker Compose
This project demonstrates a Blue-Green Deployment strategy using NGINX and Docker Compose. The setup ensures zero downtime when deploying new versions of an application by running two identical environments  Blue & Green and switching traffic between them seamlessly.
Project Overview
Blue-Green deployment is a DevOps technique that reduces downtime and risk during deployment. Two identical environments are maintained:

Blue Environment: The currently active, production version of the application.

Green Environment: The new version, prepared and tested before switching traffic.

Once the Green version is verified, NGINX updates its configuration to route all traffic to Green. If anything goes wrong, we can easily roll back to Blue.
Architecture

The system consists of:

Component	                 Description
NGINX Reverse Proxy	      Acts as a load balancer and traffic switch between Blue and Green.
Blue Container	          Hosts version 1 of the web application.
Green Container	          Hosts version 2 of the web application.
generate-nginx-conf.sh	  Script that dynamically updates NGINX configuration to switch between Blue and Green pools.
docker-compose.yml	      Orchestrates the creation and connection of all containers.

Project Structure
blue-green-nginx/
├── blue/
│   ├── Dockerfile
│   └── index.html
├── green/
│   ├── Dockerfile
│   └── index.html
├── nginx/
│   ├── nginx.conf
│   ├── nginx.conf.template
│   └── default.conf
├── docker-compose.yml
├── generate-nginx-conf.sh
├── .env
└── README.md

Prerequisites
Ensure you have the following installed:

Docker Desktop or Docker Engine

Docker Compose

Git Bash or PowerShell (for Windows users)

VS Code (for editing)

Setup Instructions
1️⃣ Clone the repository
git clone https://github.com/inijoy/hng-stage2-blue-green-nginx-deployment.git
cd hng-stage2-blue-green-nginx-deployment

2️⃣ Build and run the containers
docker-compose up --build -d

3️⃣ Verify containers are running
docker ps
You should see:
blue
green
nginx

4️⃣ Access the Application

Open your browser and go to:http://localhost:8080
You should see the active version of the application (either Blue or Green).

Switching Traffic Between Blue and Green

To switch traffic manually:

Step 1: Run the generate-nginx-conf.sh script
bash generate-nginx-conf.sh

Step 2: Restart the NGINX container
docker-compose restart nginx

Step 3: Verify the switch

Reload the browser — the active page should change to the other environment.

Testing Locally

You can simulate traffic switch and failover by testing both environments:

Start your containers:

docker-compose up -d


Confirm both apps are healthy:

curl http://localhost:8080
curl http://localhost:8081


Trigger failover (switch from Blue → Green or vice versa):
bash generate-nginx-conf.sh
docker-compose restart nginx
Open in browser:

arduino
Copy code
http://localhost:8080
You’ll see the new version served by the alternate container.

Deployment on AWS EC2

To deploy on AWS:

Launch an Ubuntu EC2 instance and SSH into it.

Install Docker and Docker Compose:

sudo apt update
sudo apt install docker.io docker-compose -y


Clone your GitHub repo:
git clone https://github.com/inijoy/hng-stage2-blue-green-nginx-deployment.git
cd hng-stage2-blue-green-nginx-deployment
Run:

sudo docker-compose up -d


Test from your browser using:

http://<EC2-Public-IP>:8080

Clean Up

To stop and remove all containers:

docker-compose down


To remove unused images and networks:

docker system prune -a

Troubleshooting
Issue	                                         Possible Cause	                                                Fix
NGINX not routing correctly	                Incorrect template or environment variable	             Re-run generate-nginx-conf.sh and restart NGINX
Port conflict	                              8080 or 8081 already in use	                             Update docker-compose.yml ports
Containers not starting	                    Docker daemon not running	                               Restart Docker service
“Permission denied” running script	        Missing execute permission	                             Run chmod +x generate-nginx-conf.sh



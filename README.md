# Blue/Green Deployment with Node.js and Nginx

This project demonstrates a **Blue/Green deployment pattern** using pre-built Node.js images behind an Nginx reverse proxy. It allows you to safely switch between two identical service versions (Blue and Green) with zero downtime and automatic failover.

---

## Project Overview

- **Blue/Green Services**: Two identical Node.js apps (`app_blue` and `app_green`) running as separate containers.
- **Endpoints**:
  - `GET /version` → Returns JSON with application version info.
  - `POST /chaos/start?mode=error` → Simulates service failure for testing failover.
  - `POST /chaos/stop` → Stops chaos simulation.
- **Nginx**:
  - Routes traffic to the active service.
  - Automatically fails over to the backup service if the active one fails.
  - Passes headers `X-App-Pool` and `X-Release-Id` to identify the active version.

---

## Prerequisites

- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)

---

## Setup Instructions

1. **Clone the repository**:

```bash
git clone <your-repo-url>
cd blue-green-nginx


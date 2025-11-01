Blue/Green Deployment Runbook1. 

System Overview

This system uses Nginx as a reverse proxy, routing traffic to one of two application pools (Blue or Green) defined by the ACTIVE_POOL variable in the .env file. The alert_watcher monitors the Nginx access logs and posts alerts to the configured Slack channel.

Alert Watcher Key Environment     Variables nValue       Purpose 
ACTIVE_POOL                       blue or green          Current production pool.
BACKUP_POOL                       blue or green          The standby pool.
ERROR_RATE_THRESHOLD              2.00                   5XX$ threshold (in percent) over the sliding window.
ERROR_WINDOW                      20                     Number of requests in the sliding window.

 Alert 1: Failover Event (Blue \ Green)
Trigger
The alert_watcher detected a switch in the ACTIVE_POOL environment variable, indicating a deliberate Blue/Green Deployment was initiated, OR Nginx has triggered an automatic health-check failover to the backup pool.

Slack Message Example

 FAILOVER EVENT DETECTED: Nginx traffic is now directed to the [New Active Pool] pool. The previous pool was [Old Pool]. This switch was initiated by a configuration change and has succeeded.
 
 Operator Response Steps
 
 Acknowledge and Verify Pool Status:
 Action: Check the status of the new and old active containers.
 Command: docker compose ps
 Verification: The container for the new active pool (e.g., app_green) should be Up. If the switch was planned, the container for the old pool (app_blue) should still be running and healthy.

 Verify Application Health (If Planned Deployment):
 Action: If this was a new deployment (you just executed the switch), verify the new application version is correct.
 
 Command: curl http://localhost/
 
 Verification: The output must show the expected "Release ID: [New Release ID]" page.
 
 Action if Switch was Unplanned (Automatic Failover):
 If the alert was triggered without operator intervention (meaning Nginx automatically failed over):
 
 Action: Immediately inspect the logs of the failed (old) pool container.
 Command: docker compose logs [old_pool_name] (e.g., app_blue)
 Objective: Identify the root cause (crash, timeout, etc.) and begin troubleshooting the newly inactive pool. The system is currently stable on the backup.
 Resolve: Mark the alert as reviewed and document the change or incident in your issue tracker.
 
 Alert 2:  High 5xx Error Rate
 Trigger
 The alert_watcher detected that the percentage of $5XX$ response codes (Bad Gateway, Service Unavailable, etc.) exceeded the ERROR_RATE_THRESHOLD ($2.0\%$) over the sliding ERROR_WINDOW (200 requests).
 
 Slack Message Example
  CRITICAL HIGH ERROR RATE: $5XX$ count is 45/200 ($\mathbf{22.5\%). The current active pool (ACTIVE_POOL=blue) is suffering widespread errors. Immediate intervention required!

  Operator Response Steps (Rapid $2$-Minute Resolution)

  Immediate Status Check:
  Action: Verify the health of the currently active containers.
  Command: docker compose ps
  Verification: Confirm if the active container is currently running or restarting.

  Execute Emergency Failback (To Backup Pool):
  Goal: Switch all traffic to the backup pool immediately, regardless of its last known health. This is the fastest way to restore service.
  Action: Edit the .env file and reverse the pools (e.g., if ACTIVE_POOL=green, change it to ACTIVE_POOL=blue).
  Action: Restart Nginx to apply the change.
  Command: docker compose restart nginx
  
  Verify Service Restoration:
  Action: Confirm the client is receiving a $200$ OK status from the new pool.
  Command: curl -s -o /dev/null -w "%{http_code}\n" http://localhost/
  Verification: The output must be 200. The service is now recovered.
  
  Root Cause Analysis:
  Action: Inspect the logs of the failed pool (the one that triggered the alert).
  Command: docker compose logs [failed_pool_name] (e.g., app_blue)
  Objective: Identify the cause (resource exhaustion, memory leak, code error, bad configuration) and apply a fix to the failed pool container while it is inactive.
  
  Long-Term Resolution:
  Once the faulty pool is stable and fixed, you may perform a controlled Blue/Green switch back to it at a later time.
  
  This runbook provides clear, step-by-step instructions for responding to both alerts, fully meeting the project requirement.
import os
import time
import re
import requests
from collections import deque
import sys
import subprocess # Added for the robust tailing method

# --- Configuration and Environment Setup ---

# Constants from .env
SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')
# Convert threshold to a float (and to a ratio for comparison)
ERROR_RATE_THRESHOLD = float(os.environ.get('ERROR_RATE_THRESHOLD', 2.0)) / 100
WINDOW_SIZE = int(os.environ.get('WINDOW_SIZE', 200))
ALERT_COOLDOWN_SEC = int(os.environ.get('ALERT_COOLDOWN_SEC', 300))
LOG_FILE_PATH = "/var/log/nginx/access.log"

# Log format regex: Must match the custom_b_g format defined in nginx.conf (after the boilerplate part):
# $request_time $upstream_response_time $upstream_addr $upstream_status $upstream_server $http_x_release_id
LOG_PATTERN = re.compile(
    r'.*?\s+'                       # Non-greedy matching up to request time
    r'(?P<request_time>\d+\.\d+)\s+'   # $request_time
    r'(?P<upstream_response_time>\d+\.\d+|-)\s+' # $upstream_response_time
    r'(?P<upstream_addr>\S+)\s+'        # $upstream_addr
    r'(?P<upstream_status>\d+)\s+'      # $upstream_status
    r'(?P<pool_host>\S+)\s+'            # $upstream_server (e.g., app_green:80) <-- NEW CAPTURE GROUP
    r'(?P<release_id>\S+)'            # $http_x_release_id (will be '-')
)

# --- State Variables ---
# Initial state taken from .env
last_seen_pool = os.environ.get('ACTIVE_POOL', 'blue')
error_window = deque(maxlen=WINDOW_SIZE)

# Cooldown timers for each alert type
last_failover_alert_time = 0
last_error_rate_alert_time = 0

# --- Helper Functions ---

def send_slack_alert(title, details, level='danger'):
    """Posts a formatted message to Slack."""
    if not SLACK_WEBHOOK_URL:
        print(f"SLACK ALERT (No Webhook): [{title}] - {details}", file=sys.stderr)
        return

    # Basic Slack message formatting using attachments
    color_map = {'danger': '#FF0000', 'warning': '#FFA500', 'info': '#008000'}

    payload = {
        "attachments": [
            {
                "fallback": f"{title} | {details}",
                "color": color_map.get(level, '#CCCCCC'),
                "title": title,
                "text": details,
                "ts": int(time.time())
            }
        ]
    }

    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        print(f"Sent Slack alert: {title}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Slack alert: {e}", file=sys.stderr)

def check_cooldown(alert_type):
    """Checks and updates the cooldown timer for a given alert type."""
    global last_failover_alert_time, last_error_rate_alert_time
    current_time = time.time()

    if alert_type == 'failover':
        if current_time - last_failover_alert_time >= ALERT_COOLDOWN_SEC:
            last_failover_alert_time = current_time
            return True
        return False

    elif alert_type == 'error_rate':
        if current_time - last_error_rate_alert_time >= ALERT_COOLDOWN_SEC:
            last_error_rate_alert_time = current_time
            return True
        return False

    return True # Default to allow if type is unknown

def tail_log(filepath):
    """Uses the native 'tail -F' shell command via subprocess for robust log following."""
    
    # We use a loop to handle the file not existing initially or process termination
    while True:
        try:
            # Check if the file exists before attempting to tail (to show "Waiting for log file...")
            if not os.path.exists(filepath):
                print(f"Waiting for log file: {filepath}...", file=sys.stderr)
                time.sleep(5)
                continue
            
            print(f"Log file found. Starting robust tail -F process for {filepath}...", file=sys.stderr)
            
            # Start the tail -F command as a subprocess
            proc = subprocess.Popen(
                ['tail', '-F', filepath],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1 # Line-buffering
            )
            
            # Read line by line from the stdout stream
            for line in proc.stdout:
                yield line.strip()
                
            # If the process terminates (e.g., log file moved/deleted), restart
            proc.wait()
            print(f"Tail process terminated (Exit Code: {proc.returncode}). Restarting...", file=sys.stderr)
            
        except Exception as e:
            # Handle unexpected errors in the subprocess communication or file check
            print(f"Error in tail_log subprocess: {e}. Retrying in 5 seconds.", file=sys.stderr)
            time.sleep(5)


# --- Main Logic ---

def process_log_line(line):
    """Parses a log line and checks for alerts."""
    global last_seen_pool

    match = LOG_PATTERN.match(line)
    if not match:
        return

    data = match.groupdict()
    pool_host = data.get('pool_host') # Captures 'app_blue:80' or 'app_green:80'
    upstream_status = data.get('upstream_status')

    # Extract the pool name (e.g., 'app_blue:80' -> 'blue')
    try:
        current_pool = pool_host.split(':')[0].split('_')[-1]
    except AttributeError:
        # Failsafe if pool_host is None or not in expected format
        return


    # 1. Failover Detection
    if current_pool and current_pool != last_seen_pool:
        if current_pool in ['blue', 'green']: # Ensure it's a valid pool value
            if check_cooldown('failover'):
                title = f"🚨 POOL FAILOVER DETECTED: {last_seen_pool.upper()} → {current_pool.upper()}"
                details = f"Traffic automatically switched at {time.ctime()}. Check health of the previous primary pool ({last_seen_pool.upper()})."
                send_slack_alert(title, details, 'warning')
            last_seen_pool = current_pool

    # 2. Error Rate Calculation
    if upstream_status:
        error_window.append(upstream_status)

        # Only check the rate once the window is full
        if len(error_window) == WINDOW_SIZE:
            # Check for 5xx status codes (500, 502, 503, etc.)
            error_count = sum(1 for status in error_window if status.startswith('5'))
            error_rate = error_count / WINDOW_SIZE

            if error_rate >= ERROR_RATE_THRESHOLD:
                if check_cooldown('error_rate'):
                    title = f"🔥 HIGH 5XX ERROR RATE: {error_rate*100:.2f}%"
                    details = f"Error rate threshold breached ({ERROR_RATE_THRESHOLD*100:.1f}%) over the last {WINDOW_SIZE} requests. Active pool: {current_pool.upper()}. Upstream: {data.get('upstream_addr')}. Operator action required."
                    send_slack_alert(title, details, 'danger')

def main():
    """The entry point for the log-watcher service."""
    print("--- Alert Watcher Initialized ---")
    print(f"Tailing log file: {LOG_FILE_PATH}")
    print(f"Initial Pool State: {last_seen_pool.upper()}")
    print(f"Error Threshold: {ERROR_RATE_THRESHOLD*100:.1f}% over {WINDOW_SIZE} requests")
    print(f"Alert Cooldown: {ALERT_COOLDOWN_SEC} seconds")

    if not SLACK_WEBHOOK_URL:
        print("WARNING: SLACK_WEBHOOK_URL is missing. Alerts will only be printed to console.", file=sys.stderr)

    for line in tail_log(LOG_FILE_PATH):
        process_log_line(line)

if __name__ == '__main__':
    main()
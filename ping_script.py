import csv
import os
import time
import json
import sys
from datetime import datetime
from scapy.all import IP, ICMP, sr1

# Function to perform ping and log results
def log_ping_results(streams, csv_file):
    try:
        print(f"Current working directory: {os.getcwd()}")
        print(f"Attempting to open the file: {csv_file}")

        with open(csv_file, mode='a', newline='') as file:  # Open file in append mode
            writer = csv.writer(file)

            # Write header if file is empty
            if os.stat(csv_file).st_size == 0:
                writer.writerow(['Timestamp', 'Latency (ms)', 'Success', 'Target IP Address', 'DSCP', 'Label'])

            print(f"Appending to {csv_file}")

            while True:  # Run indefinitely
                for stream in streams:
                    destination = stream['destination']
                    dscp = stream['dscp']
                    label = stream['label']
                    interval = stream['interval']

                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    try:
                        pkt = IP(dst=destination, tos=dscp << 2) / ICMP()
                        start_time = time.time()
                        reply = sr1(pkt, timeout=1, verbose=False)
                        end_time = time.time()

                        if reply:
                            latency = (end_time - start_time) * 1000  # Convert to milliseconds
                            writer.writerow([timestamp, round(latency, 2), 'Success', destination, dscp, label])
                            print(f"{timestamp}, {round(latency, 2)}, Success, {destination}, DSCP: {dscp}, Label: {label}")
                        else:
                            writer.writerow([timestamp, '', 'Failure', destination, dscp, label])
                            print(f"{timestamp}, , Failure, {destination}, DSCP: {dscp}, Label: {label}")

                    except Exception as e:
                        print(f"An error occurred: {e}")
                        writer.writerow([timestamp, '', 'Error', destination, dscp, label])
                        print(f"{timestamp}, , Error, {destination}, DSCP: {dscp}, Label: {label}")

                    file.flush()  # Ensure data is written to the file
                    time.sleep(interval)

    except Exception as e:
        print(f"Failed to open or write to the file: {e}")

# Main script execution
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python ping_script.py <config_file>")
        sys.exit(1)

    config_file_path = sys.argv[1]

    with open(config_file_path) as config_file:
        config = json.load(config_file)

    streams = config['streams']
    csv_file = os.path.join(os.getcwd(), 'ping_results.csv')  # Specify full path
    log_ping_results(streams, csv_file)

import subprocess
import threading
import queue

# Function to read subprocess output and put it in a queue
def enqueue_output(out, queue):
    for line in iter(out.readline, ''):
        queue.put(line)
    out.close()

# Start the executable as a subprocess
proc = subprocess.Popen(['./Mancala.exe'],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        bufsize=1)  # Use line buffering

# Create a queue to hold the output lines
output_queue = queue.Queue()

# Start a thread to collect output from the subprocess
output_thread = threading.Thread(target=enqueue_output, args=(proc.stdout, output_queue))
output_thread.daemon = True
output_thread.start()

def send_input(input_string):
    """
    Sends a string to the standard input of the subprocess.
    """
    print(f"Sending: {input_string}")
    proc.stdin.write(input_string + "\n")
    proc.stdin.flush()

def receive_output(timeout=None):
    """
    Attempts to retrieve output from the queue up to a specified timeout.
    Returns the output if available, or None if timed out.
    """
    try:
        output = output_queue.get(timeout=timeout)
        print(f"Received: {output.strip()}")
        return output
    except queue.Empty:
        print("Timeout reached, no output.")
        return None

# Example usage
send_input("Hello, C++ program!")
output = receive_output(timeout=5)  # Wait for 5 seconds for the response

# If you're done with the process, don't forget to clean up
proc.stdin.close()
proc.stdout.close()
proc.terminate()
proc.wait()

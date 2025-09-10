import subprocess
import os
import sys

def free_port_windows(port: int = 8000):
    """Free up a port by killing any process using it."""
    try:
        # Check if the port is in use
        result = subprocess.check_output(f'netstat -aon | findstr :{port}', shell=True).decode()
        lines = result.strip().split('\n')

        pids = set()
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 5:
                pid = parts[-1]
                pids.add(pid)

        # Kill any processes occupying the port
        for pid in pids:
            print(f"Killing PID {pid} on port {port}")
            os.system(f'taskkill /PID {pid} /F')

        print(f"Port {port} should now be free.")

    except subprocess.CalledProcessError:
        print(f"Port {port} is not in use. No need to kill any processes.")
    except Exception as e:
        print(f"Error while freeing port {port}: {e}", file=sys.stderr)

def run_uvicorn(port: int = 8000):
    """Run the Uvicorn server on a specified port."""
    try:
        # Run Uvicorn with the given port
        command = [
            "uvicorn",
            "main:app",
            "--host", "0.0.0.0",
            "--port", str(port),
            "--reload"
        ]
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running Uvicorn: {e}", file=sys.stderr)

def main(port: int = 8000):
    """Free port and run the Uvicorn server."""
    free_port_windows(port)  # Free the port
    run_uvicorn(port)        # Run Uvicorn server

if __name__ == "__main__":
    port_to_use = 8000  # You can change this to any port you want
    main(port_to_use)

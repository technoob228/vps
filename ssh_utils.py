import paramiko
import time

def wait_for_ssh(ip, username, password, max_retries=15, timeout=10):
    """
    Wait for SSH to become available with exponential backoff
    
    Returns: (success: bool, attempts: int)
    """
    # Exponential backoff schedule (seconds)
    wait_times = [5, 5, 10, 10, 15, 15, 20, 20, 30, 30, 30, 30, 60, 60, 60]
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    for attempt in range(min(max_retries, len(wait_times))):
        try:
            print(f"⏳ SSH connection attempt {attempt + 1}/{max_retries}...")
            ssh.connect(ip, username=username, password=password, timeout=timeout)
            ssh.close()
            print(f"✅ SSH connected on attempt {attempt + 1}")
            return True, attempt + 1
        except Exception as e:
            print(f"   Failed: {str(e)[:100]}")
            if attempt < max_retries - 1:
                wait_time = wait_times[attempt]
                print(f"   Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
    
    return False, max_retries

def create_ssh_client(ip, username, password, timeout=30):
    """
    Create and return connected SSH client
    
    Returns: SSHClient or raises exception
    """
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=username, password=password, timeout=timeout)
    return ssh

def exec_command_with_output(ssh, command, timeout=900):
    """
    Execute command and stream output
    
    Returns: (exit_code, output_lines)
    """
    channel = ssh.get_transport().open_session()
    channel.settimeout(timeout)
    channel.exec_command(command)
    
    output_lines = []
    
    # Read output in real-time
    while True:
        if channel.recv_ready():
            data = channel.recv(1024).decode('utf-8', errors='ignore')
            for line in data.split('\n'):
                if line.strip():
                    output_lines.append(line.strip())
                    print(f"   {line.strip()}")
        
        if channel.exit_status_ready():
            # Read remaining output
            while channel.recv_ready():
                data = channel.recv(1024).decode('utf-8', errors='ignore')
                for line in data.split('\n'):
                    if line.strip():
                        output_lines.append(line.strip())
                        print(f"   {line.strip()}")
            break
        
        time.sleep(0.5)
    
    exit_code = channel.recv_exit_status()
    channel.close()
    
    return exit_code, output_lines

def check_docker_installed(ssh):
    """Check if Docker is already installed"""
    stdin, stdout, stderr = ssh.exec_command('which docker')
    return stdout.channel.recv_exit_status() == 0

def check_container_running(ssh, container_name):
    """Check if container is running"""
    stdin, stdout, stderr = ssh.exec_command(f'docker ps | grep {container_name}')
    output = stdout.read().decode().strip()
    return bool(output)

def get_container_logs(ssh, container_name, lines=100):
    """Get container logs"""
    stdin, stdout, stderr = ssh.exec_command(f'docker logs --tail {lines} {container_name} 2>&1')
    return stdout.read().decode()

def upload_file_content(ssh, content, remote_path):
    """Upload file content to remote server via SSH"""
    sftp = ssh.open_sftp()
    try:
        remote_file = sftp.file(remote_path, 'w')
        remote_file.write(content)
        remote_file.close()
    finally:
        sftp.close()

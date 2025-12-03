"""
Universal provisioner - install any Docker app from various sources
Supports: docker-compose URL, docker image, GitHub repo
"""

import requests
import secrets
import string
from pathlib import Path
from ssh_utils import create_ssh_client, exec_command_with_output, check_docker_installed, check_container_running
from resource_checker import ResourceChecker
from compose_parser import ComposeParser


class UniversalProvisionerException(Exception):
    """Base exception for universal provisioner"""
    pass


class InsufficientResourcesError(UniversalProvisionerException):
    """Server doesn't have enough resources"""
    pass


class PortConflictError(UniversalProvisionerException):
    """Required ports are already in use"""
    pass


class SourceDownloadError(UniversalProvisionerException):
    """Failed to download source"""
    pass


def setup_universal(
    ip: str,
    username: str,
    password: str,
    source_type: str,
    source_url: str,
    app_name: str,
    custom_domain: str = None,
    job_id: str = None,
    max_memory_mb: int = 2048,
    max_cpu: float = 2.0,
    ports: dict = None,
    env_vars: dict = None,
    dockerfile_path: str = None
):
    """
    Universal provisioner - install any Docker application

    Args:
        ip: Server IP address
        username: SSH username
        password: SSH password
        source_type: "docker-compose" | "docker-image" | "github-repo"
        source_url: URL to source (compose file, image name, or repo)
        app_name: Name for the application
        custom_domain: Optional custom domain
        job_id: Job ID for tracking
        max_memory_mb: Maximum memory limit per service (default 2048MB)
        max_cpu: Maximum CPU limit per service (default 2.0 cores)
        ports: Optional port mappings dict {"host": "container"}
        env_vars: Optional environment variables dict
        dockerfile_path: Path to Dockerfile in repo (for github-repo type)

    Returns:
        Result dictionary with installation details

    Raises:
        InsufficientResourcesError: Not enough resources on server
        PortConflictError: Required ports already in use
        SourceDownloadError: Failed to download source
    """

    print(f"🚀 Universal provisioner: {source_type} -> {app_name}")
    print(f"   Source: {source_url}")

    ssh = create_ssh_client(ip, username, password)

    try:
        # Step 1: Check Docker installed
        print("🔍 Checking Docker installation...")
        if not check_docker_installed(ssh):
            print("📦 Docker not installed, installing...")
            install_docker(ssh)

        # Step 2: Initialize resource checker
        print("📊 Checking server resources...")
        checker = ResourceChecker(ssh)
        server_status = checker.get_full_status()

        print(f"   RAM: {server_status['memory']['available_mb']}MB available")
        print(f"   Disk: {server_status['disk']['available_gb']}GB available")
        print(f"   CPU: {server_status['cpu']['cores']} cores")

        # Step 3: Process based on source type
        if source_type == "docker-compose":
            result = provision_from_compose(
                ssh, checker, source_url, app_name, ip, custom_domain,
                max_memory_mb, max_cpu, env_vars
            )

        elif source_type == "docker-image":
            result = provision_from_image(
                ssh, checker, source_url, app_name, ip, custom_domain,
                max_memory_mb, max_cpu, ports, env_vars
            )

        elif source_type == "github-repo":
            result = provision_from_github(
                ssh, checker, source_url, app_name, ip, custom_domain,
                max_memory_mb, max_cpu, ports, env_vars, dockerfile_path
            )

        else:
            raise UniversalProvisionerException(f"Unknown source_type: {source_type}")

        print(f"✅ {app_name} installed successfully!")
        return result

    finally:
        ssh.close()


def provision_from_compose(
    ssh, checker, compose_url, app_name, ip, custom_domain,
    max_memory_mb, max_cpu, env_vars
):
    """Install from docker-compose.yml URL"""

    print(f"📥 Downloading docker-compose.yml from {compose_url}...")

    try:
        response = requests.get(compose_url, timeout=30)
        response.raise_for_status()
        compose_content = response.text
    except Exception as e:
        raise SourceDownloadError(f"Failed to download compose file: {e}")

    print("📋 Parsing docker-compose.yml...")
    parser = ComposeParser(compose_content)
    analysis = parser.get_analysis()

    print(f"   Services: {', '.join(analysis['services'])}")
    print(f"   Required RAM: ~{analysis['required_memory_mb']}MB")
    print(f"   Required disk: ~{analysis['required_disk_gb']}GB")
    print(f"   Required ports: {analysis['required_ports']}")

    # Check security warnings
    if analysis['security_warnings']:
        print("⚠️  Security warnings:")
        for warning in analysis['security_warnings']:
            print(f"   {warning}")

    # Check resources
    print("🔍 Checking if server has enough resources...")
    can_allocate, details = checker.can_allocate_resources(
        analysis['required_memory_mb'],
        analysis['required_disk_gb']
    )

    if not can_allocate:
        error_msg = f"Insufficient resources:\n"
        error_msg += f"  {details['memory']['verdict']}\n"
        error_msg += f"  {details['disk']['verdict']}"
        raise InsufficientResourcesError(error_msg)

    # Check ports
    print("🔍 Checking if ports are available...")
    ports_ok, conflicts = checker.check_ports_available(analysis['required_ports'])

    if not ports_ok:
        raise PortConflictError(f"Ports already in use: {conflicts}")

    print("✅ Resource check passed!")

    # Add safety limits
    print("🛡️  Adding safety resource limits...")
    safe_compose = parser.add_safety_limits(max_memory_mb, max_cpu)

    # Create app directory
    app_dir = f"/opt/{app_name}"
    ssh.exec_command(f"mkdir -p {app_dir}")

    # Upload docker-compose.yml
    print("📤 Uploading docker-compose.yml to server...")
    upload_content(ssh, safe_compose, f"{app_dir}/docker-compose.yml")

    # Add environment variables if provided
    if env_vars:
        env_content = "\n".join([f"{k}={v}" for k, v in env_vars.items()])
        upload_content(ssh, env_content, f"{app_dir}/.env")

    # Start services
    print("🚀 Starting services...")
    exit_code, output = exec_command_with_output(
        ssh,
        f"cd {app_dir} && docker-compose up -d"
    )

    if exit_code != 0:
        raise UniversalProvisionerException(f"Docker compose failed: {output[-10:]}")

    # Get actual resource usage after start
    import time
    time.sleep(5)
    final_status = checker.get_full_status()

    return {
        "status": "success",
        "app": app_name,
        "source_type": "docker-compose",
        "source_url": compose_url,
        "services": analysis['services'],
        "ports": analysis['required_ports'],
        "location": app_dir,
        "resources_allocated": {
            "memory_limit_mb": max_memory_mb * len(analysis['services']),
            "cpu_limit": max_cpu
        },
        "server_status": {
            "memory_used_mb": final_status['memory']['used_mb'],
            "memory_available_mb": final_status['memory']['available_mb'],
            "disk_used_gb": final_status['disk']['used_gb']
        },
        "notes": f"Installed {len(analysis['services'])} services with safety limits"
    }


def provision_from_image(
    ssh, checker, image_url, app_name, ip, custom_domain,
    max_memory_mb, max_cpu, ports, env_vars
):
    """Install from Docker image"""

    print(f"🐳 Installing from Docker image: {image_url}")

    # Check if container already running
    if check_container_running(ssh, app_name):
        print(f"⚠️  Container '{app_name}' already running")
        return {
            "status": "success",
            "app": app_name,
            "notes": "Container was already running",
            "source_type": "docker-image",
            "source_url": image_url
        }

    # Estimate resources for single container (default)
    required_memory_mb = max_memory_mb
    required_disk_gb = 5  # Default estimate

    # Check resources
    print("🔍 Checking server resources...")
    can_allocate, details = checker.can_allocate_resources(
        required_memory_mb,
        required_disk_gb
    )

    if not can_allocate:
        error_msg = f"Insufficient resources:\n"
        error_msg += f"  {details['memory']['verdict']}\n"
        error_msg += f"  {details['disk']['verdict']}"
        raise InsufficientResourcesError(error_msg)

    # Check ports if specified
    if ports:
        port_list = [int(host_port) for host_port in ports.keys()]
        print(f"🔍 Checking ports: {port_list}")
        ports_ok, conflicts = checker.check_ports_available(port_list)

        if not ports_ok:
            raise PortConflictError(f"Ports already in use: {conflicts}")

    print("✅ Resource check passed!")

    # Build docker run command
    docker_cmd = f"docker run -d --name {app_name}"

    # Add resource limits
    docker_cmd += f" --memory={max_memory_mb}m --cpus={max_cpu}"

    # Add restart policy
    docker_cmd += " --restart=on-failure:3"

    # Add ports
    if ports:
        for host_port, container_port in ports.items():
            docker_cmd += f" -p {host_port}:{container_port}"

    # Add environment variables
    if env_vars:
        for key, value in env_vars.items():
            # Escape quotes in value
            escaped_value = value.replace('"', '\\"')
            docker_cmd += f' -e {key}="{escaped_value}"'

    # Add image
    docker_cmd += f" {image_url}"

    print(f"🚀 Running container...")
    print(f"   Command: {docker_cmd}")

    exit_code, output = exec_command_with_output(ssh, docker_cmd)

    if exit_code != 0:
        raise UniversalProvisionerException(f"Docker run failed: {output[-10:]}")

    # Get actual resource usage
    import time
    time.sleep(5)
    final_status = checker.get_full_status()

    # Get mapped ports
    stdin, stdout, stderr = ssh.exec_command(
        f"docker port {app_name}"
    )
    port_output = stdout.read().decode().strip()

    return {
        "status": "success",
        "app": app_name,
        "source_type": "docker-image",
        "source_url": image_url,
        "ports": list(ports.keys()) if ports else [],
        "port_mappings": port_output,
        "resources_allocated": {
            "memory_limit_mb": max_memory_mb,
            "cpu_limit": max_cpu
        },
        "server_status": {
            "memory_used_mb": final_status['memory']['used_mb'],
            "memory_available_mb": final_status['memory']['available_mb'],
            "disk_used_gb": final_status['disk']['used_gb']
        },
        "notes": f"Container running with safety limits"
    }


def provision_from_github(
    ssh, checker, repo_url, app_name, ip, custom_domain,
    max_memory_mb, max_cpu, ports, env_vars, dockerfile_path
):
    """Install from GitHub repository"""

    print(f"🐙 Installing from GitHub: {repo_url}")

    # Estimate resources
    required_memory_mb = max_memory_mb
    required_disk_gb = 10  # Need space for repo + build

    # Check resources
    print("🔍 Checking server resources...")
    can_allocate, details = checker.can_allocate_resources(
        required_memory_mb,
        required_disk_gb
    )

    if not can_allocate:
        error_msg = f"Insufficient resources:\n"
        error_msg += f"  {details['memory']['verdict']}\n"
        error_msg += f"  {details['disk']['verdict']}"
        raise InsufficientResourcesError(error_msg)

    # Check ports if specified
    if ports:
        port_list = [int(host_port) for host_port in ports.keys()]
        print(f"🔍 Checking ports: {port_list}")
        ports_ok, conflicts = checker.check_ports_available(port_list)

        if not ports_ok:
            raise PortConflictError(f"Ports already in use: {conflicts}")

    print("✅ Resource check passed!")

    # Install git if needed
    stdin, stdout, stderr = ssh.exec_command("which git")
    if stdout.channel.recv_exit_status() != 0:
        print("📦 Installing git...")
        ssh.exec_command("apt update && apt install -y git")

    # Clone repository
    app_dir = f"/opt/{app_name}"
    print(f"📥 Cloning repository to {app_dir}...")

    # Remove old dir if exists
    ssh.exec_command(f"rm -rf {app_dir}")

    exit_code, output = exec_command_with_output(
        ssh,
        f"git clone {repo_url} {app_dir}"
    )

    if exit_code != 0:
        raise SourceDownloadError(f"Git clone failed: {output[-5:]}")

    # Determine Dockerfile path
    if dockerfile_path:
        full_dockerfile_path = f"{app_dir}/{dockerfile_path}"
    else:
        full_dockerfile_path = f"{app_dir}/Dockerfile"

    # Check if Dockerfile exists
    stdin, stdout, stderr = ssh.exec_command(f"test -f {full_dockerfile_path} && echo exists")
    if "exists" not in stdout.read().decode():
        raise UniversalProvisionerException(f"Dockerfile not found at {full_dockerfile_path}")

    # Build image
    print(f"🔨 Building Docker image...")
    build_context = Path(full_dockerfile_path).parent
    dockerfile_name = Path(full_dockerfile_path).name

    exit_code, output = exec_command_with_output(
        ssh,
        f"cd {build_context} && docker build -f {dockerfile_name} -t {app_name}:latest ."
    )

    if exit_code != 0:
        raise UniversalProvisionerException(f"Docker build failed: {output[-10:]}")

    # Run container (similar to docker-image)
    docker_cmd = f"docker run -d --name {app_name}"
    docker_cmd += f" --memory={max_memory_mb}m --cpus={max_cpu}"
    docker_cmd += " --restart=on-failure:3"

    if ports:
        for host_port, container_port in ports.items():
            docker_cmd += f" -p {host_port}:{container_port}"

    if env_vars:
        for key, value in env_vars.items():
            escaped_value = value.replace('"', '\\"')
            docker_cmd += f' -e {key}="{escaped_value}"'

    docker_cmd += f" {app_name}:latest"

    print(f"🚀 Running container...")
    exit_code, output = exec_command_with_output(ssh, docker_cmd)

    if exit_code != 0:
        raise UniversalProvisionerException(f"Docker run failed: {output[-10:]}")

    # Get final status
    import time
    time.sleep(5)
    final_status = checker.get_full_status()

    return {
        "status": "success",
        "app": app_name,
        "source_type": "github-repo",
        "source_url": repo_url,
        "built_from": dockerfile_path or "Dockerfile",
        "location": app_dir,
        "ports": list(ports.keys()) if ports else [],
        "resources_allocated": {
            "memory_limit_mb": max_memory_mb,
            "cpu_limit": max_cpu
        },
        "server_status": {
            "memory_used_mb": final_status['memory']['used_mb'],
            "memory_available_mb": final_status['memory']['available_mb'],
            "disk_used_gb": final_status['disk']['used_gb']
        },
        "notes": f"Built and running from GitHub repository"
    }


def install_docker(ssh):
    """Install Docker on the server"""
    print("📦 Installing Docker...")

    install_script = """
export DEBIAN_FRONTEND=noninteractive
apt update
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
systemctl start docker
systemctl enable docker
rm get-docker.sh

# Install Docker Compose plugin
DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
mkdir -p $DOCKER_CONFIG/cli-plugins
curl -SL https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-linux-x86_64 \
    -o $DOCKER_CONFIG/cli-plugins/docker-compose
chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
"""

    exit_code, output = exec_command_with_output(ssh, install_script)

    if exit_code != 0:
        raise UniversalProvisionerException(f"Docker installation failed: {output[-10:]}")

    print("✅ Docker installed successfully")


def upload_content(ssh, content, remote_path):
    """Upload text content to remote file"""
    from ssh_utils import upload_file_content
    upload_file_content(ssh, content, remote_path)

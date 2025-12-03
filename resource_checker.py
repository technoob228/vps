"""
Resource checker for VPS servers
Checks available RAM, disk, CPU, and ports before installation
"""

import re
from typing import Dict, List, Tuple


class ResourceChecker:
    """Check server resources via SSH"""

    def __init__(self, ssh_client):
        self.ssh = ssh_client

    def get_memory_info(self) -> Dict[str, int]:
        """
        Get memory information in MB

        Returns:
            {
                'total': 4096,      # Total RAM in MB
                'used': 1234,       # Used RAM in MB
                'free': 2862,       # Free RAM in MB
                'available': 3200   # Available for new processes (includes cache)
            }
        """
        stdin, stdout, stderr = self.ssh.exec_command('free -m')
        output = stdout.read().decode()

        # Parse: Mem: total used free shared buff/cache available
        lines = output.strip().split('\n')
        mem_line = lines[1]  # Second line has Mem: info

        parts = mem_line.split()

        return {
            'total': int(parts[1]),
            'used': int(parts[2]),
            'free': int(parts[3]),
            'available': int(parts[6]) if len(parts) > 6 else int(parts[3])
        }

    def get_disk_info(self, path='/') -> Dict[str, int]:
        """
        Get disk information in GB

        Returns:
            {
                'total': 50,    # Total disk in GB
                'used': 12,     # Used disk in GB
                'available': 38 # Available disk in GB
            }
        """
        stdin, stdout, stderr = self.ssh.exec_command(f'df -BG {path} | tail -1')
        output = stdout.read().decode().strip()

        # Parse: /dev/sda1 50G 12G 38G 24% /
        parts = output.split()

        return {
            'total': int(parts[1].rstrip('G')),
            'used': int(parts[2].rstrip('G')),
            'available': int(parts[3].rstrip('G'))
        }

    def get_cpu_info(self) -> Dict[str, any]:
        """
        Get CPU information

        Returns:
            {
                'cores': 2,
                'model': 'Intel(R) Xeon(R) CPU'
            }
        """
        stdin, stdout, stderr = self.ssh.exec_command('nproc')
        cores = int(stdout.read().decode().strip())

        stdin, stdout, stderr = self.ssh.exec_command('cat /proc/cpuinfo | grep "model name" | head -1')
        model_line = stdout.read().decode().strip()
        model = model_line.split(':')[1].strip() if ':' in model_line else 'Unknown'

        return {
            'cores': cores,
            'model': model
        }

    def get_used_ports(self) -> List[int]:
        """
        Get list of ports currently in use

        Returns:
            [22, 80, 443, 5432, ...]
        """
        stdin, stdout, stderr = self.ssh.exec_command(
            "ss -tulpn | awk '{print $5}' | grep -oE '[0-9]+$' | sort -u"
        )
        output = stdout.read().decode().strip()

        if not output:
            return []

        ports = []
        for line in output.split('\n'):
            try:
                port = int(line.strip())
                if 1 <= port <= 65535:
                    ports.append(port)
            except (ValueError, AttributeError):
                continue

        return ports

    def check_ports_available(self, required_ports: List[int]) -> Tuple[bool, List[int]]:
        """
        Check if required ports are available

        Args:
            required_ports: List of ports to check

        Returns:
            (all_available: bool, conflicts: List[int])
        """
        used_ports = set(self.get_used_ports())
        required_set = set(required_ports)

        conflicts = list(required_set & used_ports)

        return len(conflicts) == 0, conflicts

    def get_running_containers(self) -> List[str]:
        """Get list of running Docker containers"""
        stdin, stdout, stderr = self.ssh.exec_command(
            'docker ps --format "{{.Names}}"'
        )
        output = stdout.read().decode().strip()

        if not output:
            return []

        return [line.strip() for line in output.split('\n')]

    def check_docker_installed(self) -> bool:
        """Check if Docker is installed"""
        stdin, stdout, stderr = self.ssh.exec_command('which docker')
        return stdout.channel.recv_exit_status() == 0

    def estimate_safe_memory_limit(self) -> int:
        """
        Calculate safe memory limit for new containers (MB)
        Leaves 20% buffer for system
        """
        mem_info = self.get_memory_info()
        # Use 80% of available memory max
        safe_limit = int(mem_info['available'] * 0.8)
        return max(safe_limit, 256)  # Minimum 256MB

    def can_allocate_resources(self, required_memory_mb: int, required_disk_gb: int) -> Tuple[bool, Dict]:
        """
        Check if server can allocate requested resources

        Args:
            required_memory_mb: Required RAM in MB
            required_disk_gb: Required disk space in GB

        Returns:
            (can_allocate: bool, details: dict)
        """
        mem_info = self.get_memory_info()
        disk_info = self.get_disk_info()

        # Leave 20% buffer
        safe_memory = mem_info['available'] * 0.8
        safe_disk = disk_info['available'] * 0.8

        memory_ok = required_memory_mb <= safe_memory
        disk_ok = required_disk_gb <= safe_disk

        details = {
            'memory': {
                'required_mb': required_memory_mb,
                'available_mb': mem_info['available'],
                'safe_limit_mb': int(safe_memory),
                'ok': memory_ok,
                'verdict': f"✅ OK" if memory_ok else f"❌ Need {required_memory_mb}MB, only {int(safe_memory)}MB available"
            },
            'disk': {
                'required_gb': required_disk_gb,
                'available_gb': disk_info['available'],
                'safe_limit_gb': int(safe_disk),
                'ok': disk_ok,
                'verdict': f"✅ OK" if disk_ok else f"❌ Need {required_disk_gb}GB, only {int(safe_disk)}GB available"
            }
        }

        can_allocate = memory_ok and disk_ok

        return can_allocate, details

    def get_full_status(self) -> Dict:
        """Get complete server resource status"""
        mem_info = self.get_memory_info()
        disk_info = self.get_disk_info()
        cpu_info = self.get_cpu_info()
        used_ports = self.get_used_ports()
        containers = self.get_running_containers()

        return {
            'memory': {
                'total_mb': mem_info['total'],
                'used_mb': mem_info['used'],
                'available_mb': mem_info['available'],
                'usage_percent': int((mem_info['used'] / mem_info['total']) * 100)
            },
            'disk': {
                'total_gb': disk_info['total'],
                'used_gb': disk_info['used'],
                'available_gb': disk_info['available'],
                'usage_percent': int((disk_info['used'] / disk_info['total']) * 100)
            },
            'cpu': cpu_info,
            'ports_used': used_ports,
            'containers_running': len(containers),
            'container_names': containers
        }

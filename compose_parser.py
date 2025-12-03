"""
Docker Compose parser and safety modifier
Parses compose files, extracts resource requirements, and adds safety limits
"""

import yaml
import re
from typing import Dict, List, Tuple, Optional


class ComposeParser:
    """Parse and modify docker-compose.yml files"""

    def __init__(self, compose_content: str):
        """
        Args:
            compose_content: Raw docker-compose.yml content as string
        """
        self.raw_content = compose_content
        try:
            self.compose = yaml.safe_load(compose_content)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid docker-compose.yml: {e}")

        if not self.compose or 'services' not in self.compose:
            raise ValueError("Invalid docker-compose.yml: no services found")

    def get_services(self) -> List[str]:
        """Get list of service names"""
        return list(self.compose.get('services', {}).keys())

    def get_required_ports(self) -> List[int]:
        """
        Extract all host ports used by services

        Returns:
            List of host ports (e.g., [80, 443, 5432])
        """
        ports = []
        services = self.compose.get('services', {})

        for service_name, service in services.items():
            service_ports = service.get('ports', [])

            for port_mapping in service_ports:
                # Handle different formats:
                # - "80:80"
                # - "8080:80"
                # - "127.0.0.1:8080:80"
                # - 80 (just number)

                if isinstance(port_mapping, int):
                    ports.append(port_mapping)
                elif isinstance(port_mapping, str):
                    # Extract host port (first number)
                    match = re.search(r':?(\d+):', port_mapping)
                    if match:
                        ports.append(int(match.group(1)))
                    else:
                        # Format like "80" or "80/tcp"
                        match = re.search(r'^(\d+)', port_mapping)
                        if match:
                            ports.append(int(match.group(1)))

        return list(set(ports))  # Remove duplicates

    def get_required_memory(self) -> int:
        """
        Estimate required memory in MB
        Looks at existing limits or uses defaults

        Returns:
            Total required memory in MB
        """
        total_memory = 0
        services = self.compose.get('services', {})

        for service_name, service in services.items():
            # Check if memory limit already specified
            deploy = service.get('deploy', {})
            resources = deploy.get('resources', {})
            limits = resources.get('limits', {})

            memory_str = limits.get('memory', None)

            if memory_str:
                # Parse memory string like "512m", "2g", "1024M"
                memory_mb = self._parse_memory_string(memory_str)
            else:
                # Default estimate based on common services
                memory_mb = self._estimate_service_memory(service_name, service)

            total_memory += memory_mb

        return total_memory

    def get_required_disk(self) -> int:
        """
        Estimate required disk space in GB

        Returns:
            Estimated disk space in GB
        """
        # Count volumes and estimate
        volumes = self.compose.get('volumes', {})
        num_volumes = len(volumes)

        # Basic heuristic: 2GB per volume minimum
        disk_gb = max(num_volumes * 2, 5)

        return disk_gb

    def _parse_memory_string(self, memory_str: str) -> int:
        """
        Parse memory string to MB

        Examples:
            "512m" -> 512
            "2g" -> 2048
            "1024M" -> 1024
        """
        memory_str = memory_str.lower().strip()

        match = re.match(r'^(\d+(?:\.\d+)?)\s*([kmg]?)b?$', memory_str)
        if not match:
            return 512  # Default

        value = float(match.group(1))
        unit = match.group(2)

        if unit == 'g':
            return int(value * 1024)
        elif unit == 'k':
            return int(value / 1024)
        else:  # 'm' or no unit
            return int(value)

    def _estimate_service_memory(self, service_name: str, service: dict) -> int:
        """
        Estimate memory for service based on common patterns

        Args:
            service_name: Name of the service
            service: Service configuration dict

        Returns:
            Estimated memory in MB
        """
        image = service.get('image', '').lower()
        name_lower = service_name.lower()

        # Database services
        if any(db in image or db in name_lower for db in ['postgres', 'mysql', 'mariadb']):
            return 512
        elif 'mongo' in image or 'mongo' in name_lower:
            return 1024
        elif 'redis' in image or 'redis' in name_lower:
            return 256
        elif 'clickhouse' in image:
            return 1024

        # Heavy services
        elif any(heavy in image for heavy in ['gitlab', 'nextcloud', 'mattermost']):
            return 2048
        elif 'elasticsearch' in image:
            return 2048

        # Medium services
        elif any(med in image for med in ['nginx', 'apache', 'caddy', 'traefik']):
            return 128
        elif 'node' in image or 'npm' in image:
            return 512

        # Default for unknown services
        return 512

    def check_security_issues(self) -> List[str]:
        """
        Check for potential security issues

        Returns:
            List of warning messages
        """
        warnings = []
        services = self.compose.get('services', {})

        for service_name, service in services.items():
            # Check for privileged mode
            if service.get('privileged', False):
                warnings.append(f"⚠️  Service '{service_name}' uses privileged mode (security risk)")

            # Check for host network
            if service.get('network_mode') == 'host':
                warnings.append(f"⚠️  Service '{service_name}' uses host network (security risk)")

            # Check for dangerous volume mounts
            volumes = service.get('volumes', [])
            for volume in volumes:
                if isinstance(volume, str):
                    # Check for /var/run/docker.sock mounting
                    if 'docker.sock' in volume:
                        warnings.append(f"⚠️  Service '{service_name}' mounts docker.sock (security risk)")
                    # Check for root filesystem mounting
                    if volume.startswith('/:/') or volume.startswith('/:/host'):
                        warnings.append(f"⚠️  Service '{service_name}' mounts root filesystem (security risk)")

        return warnings

    def add_safety_limits(self, max_memory_mb: int = 2048, max_cpu: float = 2.0) -> str:
        """
        Add safety resource limits to all services

        Args:
            max_memory_mb: Maximum memory per service in MB
            max_cpu: Maximum CPU per service (cores)

        Returns:
            Modified docker-compose.yml as string
        """
        services = self.compose.get('services', {})

        for service_name, service in services.items():
            # Ensure deploy section exists
            if 'deploy' not in service:
                service['deploy'] = {}

            if 'resources' not in service['deploy']:
                service['deploy']['resources'] = {}

            # Add limits
            if 'limits' not in service['deploy']['resources']:
                service['deploy']['resources']['limits'] = {}

            limits = service['deploy']['resources']['limits']

            # Calculate memory for this service
            estimated = self._estimate_service_memory(service_name, service)
            service_memory = min(estimated, max_memory_mb)

            # Set memory limit if not already set
            if 'memory' not in limits:
                limits['memory'] = f"{service_memory}m"

            # Set CPU limit if not already set
            if 'cpus' not in limits:
                limits['cpus'] = str(max_cpu)

            # Set restart policy to prevent infinite restart loops
            if 'restart' not in service or service['restart'] == 'always':
                service['restart'] = 'on-failure:3'

        # Convert back to YAML
        return yaml.dump(self.compose, default_flow_style=False, sort_keys=False)

    def get_analysis(self) -> Dict:
        """
        Get complete analysis of the compose file

        Returns:
            Dictionary with all analysis results
        """
        return {
            'services': self.get_services(),
            'num_services': len(self.get_services()),
            'required_memory_mb': self.get_required_memory(),
            'required_disk_gb': self.get_required_disk(),
            'required_ports': self.get_required_ports(),
            'security_warnings': self.check_security_issues(),
            'volumes': list(self.compose.get('volumes', {}).keys()),
            'networks': list(self.compose.get('networks', {}).keys())
        }


def parse_memory_limit(memory_str: Optional[str]) -> int:
    """
    Helper function to parse memory limit strings

    Args:
        memory_str: Memory string like "512m", "2g", None

    Returns:
        Memory in MB
    """
    if not memory_str:
        return 512  # Default

    parser = ComposeParser(f"services:\n  temp:\n    deploy:\n      resources:\n        limits:\n          memory: {memory_str}")
    return parser._parse_memory_string(memory_str)

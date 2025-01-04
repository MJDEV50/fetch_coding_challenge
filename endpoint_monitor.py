# Standard library imports and third-party dependencies 
# Using asyncio for concurrent operations and aiohttp for non-blocking HTTP requests
import sys
import asyncio
import aiohttp
import yaml
import time
from typing import Dict, List, Optional
from urllib.parse import urlparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

@dataclass
class EndpointConfig:
    """
    Represents the configuration for a single HTTP endpoint.
    
    I wanted a dataclass here for several reasons:
    1. It automatically generates __init__, __repr__, and other special methods
    2. It provides clear type hints for all fields
    3. It makes the code more maintainable by reducing boilerplate
    
    The optional fields (method, headers, body) default to None or 'GET' to match
    the specification requirements. This allows me tohandle endpoints with minimal
    configuration while still supporting fully customized requests.
    """
    name: str
    url: str
    method: str = "GET"  # Default to GET as per requirements
    headers: Optional[Dict[str, str]] = None
    body: Optional[str] = None

    def get_domain(self) -> str:
        """
        Extracts the domain from a URL using urlparse.
        
        using urlparse instead of string manipulation because:
        1. It handles edge cases (ports, auth, etc.) correctly
        2. It's more reliable than regex or string splitting
        3. It's a standard library solution that's well-tested
        
        Example: https://api.example.com:8080/path -> api.example.com:8080
        """
        return urlparse(self.url).netloc


class ConfigurationParser:
    """
    Handles the parsing of YAML configuration files into structured endpoint configs.
    
    This class is separated from the endpoint configuration to maintain single
    responsibility principle. It handles all the file I/O and YAML parsing,
    leaving the EndpointConfig class to focus on representing the data structure.
    """
    def __init__(self, config_path: str):
        self.config_path = config_path
    
    def parse_config(self) -> List[EndpointConfig]:
        """
        Parses the YAML configuration file into EndpointConfig objects.
        
        I use yaml.safe_load instead of yaml.load for security reasons,
        as it prevents code execution exploits. The method implements early
        validation to fail fast if the configuration is invalid.
        
        Error handling uses sys.exit(1) because invalid configuration is
        a fatal error - we can't proceed with invalid endpoints.
        """
        try:
            with open(self.config_path, 'r') as file:
                config_data = yaml.safe_load(file)
            
            if not isinstance(config_data, list):
                raise ValueError("Configuration must be a YAML list")
            
            endpoints = []
            for item in config_data:
                # Using .get() with defaults for optional fields provides clean handling
                # of missing fields while ensuring required fields raise KeyError
                endpoint = EndpointConfig(
                    name=item['name'],
                    url=item['url'],
                    method=item.get('method', 'GET'),
                    headers=item.get('headers'),
                    body=item.get('body')
                )
                endpoints.append(endpoint)
            
            return endpoints
                
        except FileNotFoundError:
            print(f"Configuration file not found: {self.config_path}")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file: {e}")
            sys.exit(1)


@dataclass
class HealthCheckResult:
    """
    Stores the result of a single health check attempt.
    
    I use a separate class for results to:
    1. Keep the data structure clean and self-documenting
    2. Encapsulate the logic for determining UP/DOWN status
    3. Store timestamps for potential future features (history, trending)
    """
    endpoint_name: str
    domain: str
    response_time_ms: float
    status_code: int
    timestamp: datetime = datetime.now()

    @property
    def is_up(self) -> bool:
        """
        Implements the UP/DOWN logic specified in requirements:
        - Status code must be 2xx (200-299)
        - Response time must be < 500ms
        
        Using @property makes this logic reusable and encapsulated,
        while still being easily accessible.
        """
        return (200 <= self.status_code < 300 and 
                self.response_time_ms < 500)


class HealthChecker:
    """
    Manages the health checking of endpoints using async HTTP requests.
    
    This class handles concurrent health checks and maintains the results
    history. We use aiohttp for non-blocking HTTP requests to efficiently
    check multiple endpoints simultaneously.
    """
    def __init__(self, endpoints: List[EndpointConfig]):
        self.endpoints = endpoints
        # Using defaultdict to automatically initialize new domains
        self.results = defaultdict(list)
        # 5 second timeout is a reasonable default for health checks
        self.timeout = aiohttp.ClientTimeout(total=5)

    async def check_endpoint(self, session: aiohttp.ClientSession, 
                           endpoint: EndpointConfig) -> HealthCheckResult:
        """
        Checks a single endpoint's health asynchronously.
        
        We measure response time using time.time() for high precision.
        Any exception is treated as a DOWN status (status_code=0) to handle
        network errors, timeouts, etc. consistently.
        """
        start_time = time.time()
        try:
            async with session.request(
                method=endpoint.method,
                url=endpoint.url,
                headers=endpoint.headers,
                json=endpoint.body if endpoint.body else None,
                timeout=self.timeout
            ) as response:
                response_time = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    endpoint_name=endpoint.name,
                    domain=endpoint.get_domain(),
                    response_time_ms=response_time,
                    status_code=response.status
                )
        except Exception as e:
            # Any failure (timeout, connection error, etc.) counts as DOWN
            return HealthCheckResult(
                endpoint_name=endpoint.name,
                domain=endpoint.get_domain(),
                response_time_ms=float('inf'),
                status_code=0
            )

    async def check_all_endpoints(self):
        """
        Concurrently checks all endpoints using a single session.
        
        Using a single ClientSession for all requests because:
        1. It's more efficient (connection pooling)
        2. It's the recommended way to use aiohttp
        3. It properly manages resources
        """
        async with aiohttp.ClientSession() as session:
            tasks = [
                self.check_endpoint(session, endpoint)
                for endpoint in self.endpoints
            ]
            results = await asyncio.gather(*tasks)
            
            for result in results:
                self.results[result.domain].append(result)

    def get_availability_stats(self) -> Dict[str, float]:
        """
        Calculates availability percentages per domain.
        
        The calculation matches the specification:
        availability = (UP checks / total checks) * 100
        
        Results are rounded to whole numbers per requirements.
        """
        stats = {}
        for domain, checks in self.results.items():
            up_count = sum(1 for check in checks if check.is_up)
            total_count = len(checks)
            availability = (up_count / total_count * 100) if total_count > 0 else 0
            stats[domain] = round(availability)
        return stats


class MonitoringService:
    """
    Orchestrates the overall monitoring process.
    
    This class ties everything together and manages the continuous
    monitoring cycle. It's designed to be the main interface for
    running the monitoring system.
    """
    def __init__(self, config_path: str):
        parser = ConfigurationParser(config_path)
        self.endpoints = parser.parse_config()
        self.health_checker = HealthChecker(self.endpoints)
        self.running = False

    async def run_check_cycle(self):
        """
        Executes a single monitoring cycle.
        
        Each cycle:
        1. Checks all endpoints concurrently
        2. Calculates availability stats
        3. Prints results to console
        """
        await self.health_checker.check_all_endpoints()
        stats = self.health_checker.get_availability_stats()
        
        for domain, availability in stats.items():
            print(f"{domain} has {availability}% availability percentage")

    async def run(self):
        """
        Runs the monitoring service continuously.
        
        Uses asyncio.sleep for precise timing between cycles.
        The running flag enables clean shutdown on CTRL+C.
        """
        self.running = True
        while self.running:
            await self.run_check_cycle()
            await asyncio.sleep(15)  # Wait between cycles per requirements

    def stop(self):
        """
        Enables graceful shutdown of the service.
        """
        self.running = False


async def main():
    """
    Application entry point with argument validation.
    """
    if len(sys.argv) != 2:
        print("Usage: python monitor.py <config_file_path>")
        sys.exit(1)

    config_path = sys.argv[1]
    service = MonitoringService(config_path)
    
    try:
        await service.run()
    except KeyboardInterrupt:
        print("\nStopping monitoring service...")
        service.stop()


if __name__ == "__main__":
    asyncio.run(main())

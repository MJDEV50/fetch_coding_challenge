# HTTP Endpoint Monitoring System

## Overview
This Python application monitors HTTP endpoints and tracks their availability metrics in real-time. It performs periodic health checks on configured endpoints and calculates availability percentages based on response times and status codes.

## Features
- Asynchronous health checks for efficient monitoring of multiple endpoints
- Configurable endpoints via YAML configuration file
- Response time and status code monitoring
- Domain-based availability tracking
- Continuous monitoring with 15-second intervals
- Graceful shutdown handling

## Prerequisites
- Python 3.7 or higher
- pip (Python package installer)

## Installation
1. Clone this repository or download the source code
2. Install the required dependencies:
```bash
pip install pyyaml aiohttp
```

## Configuration
Create a YAML configuration file for your endpoints. The file should contain a list of endpoints with the following structure:

```yaml
- name: "Example Endpoint"
  url: "https://example.com/api"
  method: "GET"  # Optional, defaults to GET
  headers:       # Optional
    user-agent: "custom-monitor"
  body: '{"key": "value"}'  # Optional, must be valid JSON if provided

- name: "Another Endpoint"
  url: "https://another-example.com"
```

### Configuration Fields
- `name`: (Required) Identifier for the endpoint
- `url`: (Required) The URL to monitor
- `method`: (Optional) HTTP method to use (defaults to GET)
- `headers`: (Optional) HTTP headers to include in the request
- `body`: (Optional) JSON body for POST/PUT requests

## Usage
Run the monitoring system by providing the path to your configuration file:

```bash
python monitor.py config.yaml
```

The program will:
1. Load the configuration file
2. Start monitoring all configured endpoints
3. Print availability statistics every 15 seconds
4. Continue running until interrupted with Ctrl+C

## Availability Calculation
The system determines endpoint status as follows:
- UP: Response status code is 2xx (200-299) AND response time is less than 500ms
- DOWN: Any other condition (status code outside 2xx range, response time ≥ 500ms, or connection failure)

Availability percentage is calculated as:
```
availability = (number of UP checks / total number of checks) * 100
```

## Error Handling
The system handles various error conditions:
- Invalid configuration file format
- Network connectivity issues
- Request timeouts
- Invalid responses

## Testing
To test the monitoring system:
1. Create a test configuration file with your endpoints
2. Run the program
3. Verify that availability statistics are being reported
4. Test error conditions by temporarily disabling endpoints

## Limitations
- No persistent storage of metrics
- Fixed 15-second check interval
- No configuration of timeout values
- No authentication mechanism for protected endpoints

## Best Practices
- Keep configuration files in version control
- Monitor only endpoints that can handle the check frequency
- Use appropriate timeouts for your network conditions
- Consider the impact of headers and request bodies on endpoint performance

## Support
For issues, questions, or contributions, please submit an issue through the repository's issue tracker.

## License
This project is released under the MIT License. See the LICENSE file for details.

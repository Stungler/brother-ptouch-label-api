# Security policy

## Deployment guidance

This service intentionally has no built-in authentication. Anyone who can reach
it can submit print jobs, inspect registered printer addresses, and request
SNMP reboots. Run it on a trusted network, bind it to localhost, or place it
behind an authenticated reverse proxy.

Do not expose the API or printer TCP port 9100 directly to the internet.

SNMP v1 community strings are not encrypted. Supply read and write communities
through environment variables, restrict SNMP access at the printer and network
layer, and avoid putting real values in source files, API examples, screenshots,
or issue reports.

The registry file contains device names and addresses. Keep
`data/printers.json` out of version control and backups intended for public
distribution.

## Reporting a vulnerability

If this repository is hosted on GitHub, use the repository's private security
advisory feature when available. Otherwise contact the maintainer privately.
Do not open a public issue containing credentials, community strings, private
addresses, or a working exploit.

"""Read-only infrastructure monitoring for KSSH / BGSSH.

Nothing in this package changes device configuration. SNMP SET is not
implemented anywhere; only GET / GETNEXT / GETBULK and bounded WALK exist.
"""

__all__ = ["errors", "logutil", "monitor", "snmp_client", "snmp_interfaces", "snmp_adapters"]

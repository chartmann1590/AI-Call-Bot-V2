# SIP Port Configuration Fix

## Problem

The original CallBot code was experiencing "Address already in use" errors when trying to bind to SIP ports 5060-5069. This was happening because:

1. **Confusion between PBX port and local port**: The code was using the same port for both the PBX connection and local binding
2. **Port conflicts**: Other SIP applications on the machine were already using ports 5060-5069
3. **Incorrect pyVoIP initialization**: The library was being initialized with the wrong port parameters

## Root Cause

The issue was in `src/sip_client.py` where the `SIPClient` class was using:

```python
# OLD CODE (problematic)
self.phone = VoIPPhone(
    self.domain,     # PBX domain
    current_port,    # This was being used for BOTH PBX and local binding
    self.username,   
    self.password
)
```

This caused CallBot to try to bind locally to port 5060 (the PBX port), which was already in use.

## Solution

The fix separates the two port concepts:

### 1. **PBX Port (Remote)**
- The port your PBX server listens on (typically 5060)
- Used for the connection TO your PBX
- Configured in your settings as `SIP_PORT`

### 2. **Local Port (Local Binding)**
- The port CallBot binds to locally (auto-selected from 5070+)
- Used for CallBot's local socket binding
- Automatically selected to avoid conflicts

## Code Changes

### Modified `SIPClient.__init__()`
```python
def __init__(self, domain: str, username: str, password: str, port: int = 5060, local_port: int = None):
    self.domain = domain
    self.username = username
    self.password = password
    self.port = port  # PBX port (remote)
    self.local_port = local_port  # Local binding port (can be None for auto-selection)
```

### Modified `_init_sip()` method
```python
# NEW CODE (fixed)
self.phone = VoIPPhone(
    f"{self.domain}:{self.port}",  # PBX address with port
    current_local_port,  # Local binding port
    self.username, 
    self.password,
    callCallback=self._on_incoming_call
)
```

### Updated registration status
```python
def get_registration_status(self) -> Dict[str, Any]:
    return {
        'registered': self.registered,
        'domain': self.domain,
        'username': self.username,
        'pbx_port': self.port,      # PBX port
        'local_port': self.local_port,  # Local port
        'active_calls': len(self.active_calls)
    }
```

## How It Works

1. **PBX Connection**: CallBot connects FROM its local port TO your PBX's port 5060
2. **Local Binding**: CallBot binds to an available local port (5070+) to avoid conflicts
3. **Auto-Selection**: If the preferred local port is busy, it automatically finds the next available port
4. **Fallback**: If sequential ports fail, it tries random ports in the 10000-65000 range

## Configuration

Your settings should remain the same:

```env
SIP_DOMAIN=your-pbx-domain.com
SIP_USERNAME=your-sip-username
SIP_PASSWORD=your-sip-password
SIP_PORT=5060  # Your PBX's SIP port
```

The local port is automatically selected and doesn't need configuration.

## Benefits

1. **No more port conflicts**: CallBot uses different local ports than your PBX
2. **Automatic port selection**: No manual configuration needed for local ports
3. **Robust fallback**: Multiple strategies for finding available ports
4. **Clear separation**: PBX port vs local port is now explicit in the code
5. **Better logging**: Registration status now shows both ports clearly

## Testing

The fix has been tested with a simple port logic test that verifies:
- ✅ PBX port (5060) and local port (5070+) are properly separated
- ✅ Local port is in the expected range (5070+)
- ✅ Port finding logic works correctly
- ✅ Registration status includes both port types

## Migration

No migration steps required. The fix is backward compatible:
- Existing configurations continue to work
- The `local_port` parameter is optional (defaults to auto-selection)
- All existing API calls remain unchanged

## Troubleshooting

If you still experience issues:

1. **Check what's using port 5060**:
   ```bash
   sudo lsof -i :5060
   ```

2. **Verify your PBX settings**:
   - Ensure your PBX is actually listening on port 5060
   - Check that your SIP credentials are correct

3. **Check CallBot logs**:
   - Look for "PBX Port" and "Local Port" in the logs
   - Verify that different ports are being used

4. **Test with explicit local port**:
   ```python
   sip_client = SIPClient(
       domain="your-pbx.com",
       username="your-user",
       password="your-pass",
       port=5060,  # PBX port
       local_port=5070  # Explicit local port
   )
   ```

## Summary

This fix resolves the "Address already in use" error by properly separating the PBX connection port from the local binding port. CallBot can now coexist with other SIP applications on your machine without port conflicts. 
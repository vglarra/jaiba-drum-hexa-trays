# jaiba-drum-hexa-trays

## Blender live connection (BlenderMCP)

Blender can be controlled live via the BlenderMCP addon, which opens a raw TCP/JSON
socket on **port 9876** when running.

**At the start of every session/project, check the connection first**, before assuming
Blender state or running the script blind:

```powershell
$client = New-Object System.Net.Sockets.TcpClient
$client.Connect("localhost", 9876)
$stream = $client.GetStream()
$cmd = '{"type":"get_scene_info","params":{}}'
$bytes = [System.Text.Encoding]::UTF8.GetBytes($cmd)
$stream.Write($bytes, 0, $bytes.Length)
Start-Sleep -Milliseconds 500
$buffer = New-Object byte[] 65536
$read = $stream.Read($buffer, 0, $buffer.Length)
Write-Output ([System.Text.Encoding]::UTF8.GetString($buffer, 0, $read))
$client.Close()
```

- If this returns scene JSON (`"status": "success"`), the connection is live — proceed.
- **If the connection fails/times out (port closed), stop and tell the user to start the
  BlenderMCP addon in Blender** (open Blender, enable/start the addon's server so it
  listens on port 9876), then retry the check. Do not silently fall back to headless
  script execution when the intent was a live session.

### Sending commands

Once connected, commands are JSON objects sent over the same socket, e.g.:

```json
{"type": "execute_code", "params": {"code": "..."}}
{"type": "get_scene_info", "params": {}}
{"type": "get_object_info", "params": {"name": "SensorBase_TL"}}
```

Response is JSON with `"status": "success"` or `"status": "error"` and a `"result"`/`"message"` field.

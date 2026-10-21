// Route only T3 relay hostnames through the desktop SOCKS tunnel.
// Fallback to DIRECT so home/other networks still work if ssh-socks is down.
function FindProxyForURL(url, host) {
  if (
    shExpMatch(host, "*.t3coderelay.com") ||
    host === "t3coderelay.com"
  ) {
    return "SOCKS5 127.0.0.1:1080; DIRECT";
  }
  return "DIRECT";
}

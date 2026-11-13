# Laptop NPU models

The Ryzen AI 7 350 has an XDNA2 NPU. FastFlowLM runs NPU-specific models locally;
T3's **Laptop NPU** provider uses OpenCode as its coding harness. Choose it in a
new thread's provider selector, then choose **Qwen3.5 4B · NPU** for lighter tasks
or **Qwen3.5 9B · NPU** for more demanding work. These small models have a 32,768
token context and need more supervision than cloud coding models.
**Reasoning: None** is the default; **Thinking** enables longer internal
reasoning. FastFlowLM does not provide distinct low/medium/high reasoning budgets.

Internet tools remain available. Local inference works without internet once
the runtime, harness and models are installed; the models do not become cloud
models when online. Existing cloud providers and their defaults are separate.

## Install and configure

The kernel must expose `/dev/accel/accel0` through `amdxdna` and report firmware
1.1.0.0 or newer. The laptop already has kernel 7.2.15, driver 0.10 and firmware
1.1.2.64; no reboot or kernel replacement was needed.

```bash
sudo pacman -S --needed fastflowlm xrt xrt-plugin-amdxdna
```

Arch's XRT 2.25.0 and plugin 2.21.75 packages have an ABI mismatch. Install the
compatible local plugin package described in
[`../packages/aur-builds/xrt-plugin-amdxdna/README.md`](../packages/aur-builds/xrt-plugin-amdxdna/README.md)
before starting inference. Rebuild it against a changed XRT version; do not
replace the kernel driver to repair a userspace library error.

Download the prepared NPU models (about 3.2 GiB and 7.6 GiB):

```bash
FLM_DISABLE_UPDATE_CHECK=1 flm pull qwen3.5:4b
FLM_DISABLE_UPDATE_CHECK=1 flm pull qwen3.5:9b
bash scripts/install-npu-service.sh --apply humunkulud
node scripts/configure-npu-t3.mjs --apply
```

The system service runs as `humunkulud`, binds `127.0.0.1:52625`, and raises only
its own memory-lock limit. It starts without loading a model and loads/switches
models on demand. The model family's NPU backend is explicitly selected with
`--backend flm` (the similarly named `flm_npu` backend is not accepted by Qwen3.5).
Reapplying the service installer restarts inference; finish active turns first.
Models stay outside Git in `~/.config/flm/models`. The API is unauthenticated and
accessible to local processes; it is not bound to LAN or Tailscale interfaces.

The provider setup uses T3's supported local authentication CLI and settings API.
It issues a short-lived setup session and revokes it afterward. Its isolated
OpenCode configuration is embedded in the provider instance; normal OpenCode
configuration is unchanged. Registry refreshes, automatic updates, sharing and
automatic LSP downloads are disabled for this instance so disconnected startup
does not depend on them. Agent network tools remain enabled.

## Check and operate

```bash
systemctl status flm@humunkulud.service
curl --fail http://127.0.0.1:52625/v1/models
FLM_DISABLE_UPDATE_CHECK=1 flm list --filter installed
node scripts/configure-npu-t3.mjs --status
bash scripts/install-npu-service.sh --check humunkulud
journalctl -u flm@humunkulud.service -n 50
```

Interactive shells still have an 8 MiB memory-lock limit. That can make
`flm validate` or `xrt-smi examine` fail there while the service works. Verify
the service's limit with `systemctl show -p LimitMEMLOCK flm@humunkulud.service`.
Avoid starting another FastFlowLM server on the same port.

Stop inference and release the loaded model's RAM with:

```bash
sudo systemctl stop flm@humunkulud.service
sudo systemctl start flm@humunkulud.service
```

Models remain downloaded across service restarts and reboots. Start remains
enabled at boot. To remove the integration:

```bash
node scripts/configure-npu-t3.mjs --remove
sudo systemctl disable --now flm@humunkulud.service
sudo rm /etc/systemd/system/flm@.service
sudo systemctl daemon-reload
```

`flm remove qwen3.5:4b` and `flm remove qwen3.5:9b` remove their downloads if
wanted. Uninstalling the integration does not require removing XRT packages.

Powered by [FastFlowLM](https://github.com/ROCm/FastFlowLM). See the
[Linux NPU setup guide](https://lemonade-server.ai/flm_npu_linux.html) for the
supported hardware, firmware and driver requirements.

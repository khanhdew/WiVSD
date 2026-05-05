# CSI Reception with WiFi Provisioning Example

This example demonstrates how to create a dual-mode WiFi device using ESP32/ESP32-C6 that can:

1. **CSI Reception Mode**: Transmit as a WiFi SoftAP to collect CSI data
2. **WiFi Provisioning Mode**: Use BLE provisioning to configure WiFi credentials

## Features

- **Button Toggle**: Press GPIO button to switch between modes
- **Non-blocking**: Uses ISR (Interrupt Service Routine) for button handling
- **Provisioning**: WiFi credentials can be provisioned over BLE
- **NVS Persistence**: Stores WiFi credentials in flash
- **Event-driven**: Uses FreeRTOS event groups for clean state management

## Hardware Setup

### Components Required
- ESP32 or ESP32-C6 development board
- Push button connected between GPIO pin and GND
- Pulling up via internal pull-up (GPIO_PULLUP_ENABLE in config)

### GPIO Configuration
- Default: GPIO 9 (configurable via `menuconfig`)
- Connection: Button between GPIO9 and GND
- Pull-up: Internal pull-up enabled

## Build and Flash

### Prerequisites
- ESP-IDF (v5.0 or later recommended)
- ESP toolchain installed and configured

### Steps

1. **Clone and navigate to example**:
```bash
cd esp-csi/examples/csi_with_provisioning
```

2. **Set target** (e.g., ESP32-C6):
```bash
idf.py set-target esp32c6
```

3. **Configure** (optional, to customize GPIO, WiFi SSID, etc.):
```bash
idf.py menuconfig
```

4. **Build**:
```bash
idf.py build
```

5. **Flash**:
```bash
idf.py flash
```

6. **Monitor**:
```bash
idf.py monitor
```

## Operation

### Initial State
- Starts in **CSI Reception Mode**
- Device broadcasts as a WiFi access point (default SSID: "CSI-Device")
- CSI reception is enabled for monitoring

### Switching Modes
- **Press GPIO Button**: Device switches to the other mode
- Button debounce: 300ms minimum
- Mode switch is immediate when using ISR

### CSI Reception Mode
- Acts as a WiFi SoftAP with the configured SSID
- Collects Channel State Information from connected devices
- Maximum 4 simultaneous connections (configurable)

### Provisioning Mode
- Exposes a BLE provisioning service
- Uses WiFi Provisioning Manager (Legacy API)
- Clients can provision new WiFi credentials via Espressif provisioning app/tool
- Credentials are stored in NVS after successful provisioning

## Configuration Options

Use `idf.py menuconfig` to access configuration menu under "CSI Provisioning Example Configuration":

| Option | Default | Description |
|--------|---------|-------------|
| GPIO pin for button | GPIO 9 | Which GPIO pin triggers mode switch |
| WiFi SoftAP SSID | CSI-Device | SSID broadcast in both modes |
| WiFi SoftAP Password | csi12345 | Password for SoftAP (8+ characters) |
| Max STA connections | 4 | Maximum simultaneous WiFi connections |
| Provisioning security | 0 | Security level for provisioning (0-2) |

## Provisioning Security Levels

- **Security 0**: Plain text (no encryption) - Fastest, insecure
- **Security 1**: Proof-of-possession - Requires known shared secret
- **Security 2**: SRP6a - Strongest security, slowest provisioning

## Event Flow

### CSI Reception Mode
```
Button Pressed
    ↓
ISR sets MODE_SWITCH_EVENT_BIT
    ↓
Mode Manager switches to Provisioning Mode
    ↓
CSI task is deleted
    ↓
Provisioning task starts
```

### Provisioning Mode
```
Button Pressed
    ↓
ISR sets MODE_SWITCH_EVENT_BIT
    ↓
Mode Manager switches to CSI Reception Mode
    ↓
Provisioning Manager deinitialized
    ↓
CSI Reception task starts
```

## Serial Monitor Output Example

```
I (0) cpu_start: App partition offset 0x010000
I (38) csi_prov_example: CSI with WiFi Provisioning Example started
I (248) csi_prov_example: Button configured on GPIO 9
I (249) csi_prov_example: Starting CSI reception mode
I (250) csi_prov_example: CSI Reception: SoftAP configured - SSID: CSI-Device
I (251) csi_prov_example: CSI reception active. Press button to switch to provisioning mode.

[Button press detected]

I (5000) csi_prov_example: Switching mode to: Provisioning
I (5001) csi_prov_example: Starting WiFi provisioning mode
I (5002) csi_prov_example: Provisioning mode active. Press button to switch to CSI reception mode.
```

## Implementation Details

### Button Handler (ISR)
- Attached to GPIO pin with falling edge trigger
- 300ms debounce to prevent false triggers
- Sets event bit from ISR context (using `xEventGroupSetBitsFromISR`)

### Mode Manager
- Central task that listens for button press events
- Kills previous mode task before starting new one
- Provides 500ms delay for clean task transition

### CSI Reception Mode
- Configures WiFi as AP
- Enables CSI packet reception
- Runs until mode switch button pressed

### Provisioning Mode
- Uses WiFi Provisioning Manager
- BLE scheme for provisioning
- BLE service name is generated from MAC, e.g. `CSI_PROV_A1B2C3`
- Stores credentials to NVS upon success
- Cleans up manager when exiting mode

## Troubleshooting

### Button not working
- Check GPIO pin configuration in menuconfig
- Verify button is connected between GPIO and GND
- Check for correct pull-up setting

### Provisioning not starting
- Ensure `wifi_provisioning` component is available in ESP-IDF
- Ensure Bluetooth/BLE is enabled for your target
- Check that WiFi is properly initialized before provisioning
- Verify NVS is initialized and has free space

### CSI data not received
- Ensure WiFi is in correct mode (AP)
- Verify CSI configuration in code
- Check if connected devices support CSI

### Build Errors
- Update ESP-IDF to v5.0 or later
- Run `idf.py fullclean` if build artifacts seem stale
- Verify all components are available in your IDF installation

## Future Enhancements

- Add OTA firmware update capability
- Add status LED indicators for mode state
- Create mobile app for easier provisioning
- Add CSI data logging to SD card

## References

- [ESP32 CSI Documentation](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/network/esp_wifi_csi.html)
- [WiFi Provisioning Guide](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/provisioning/provisioning.html)
- [FreeRTOS Event Groups](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/system/freertos.html)

## License

This example code is in the public domain.

idf_component_register(SRCS "csi_provisioning_example.c"
                       INCLUDE_DIRS "."
                       REQUIRES esp_csi_gain_ctrl esp_wifi wifi_provisioning driver esp_netif esp_event bt nvs_flash)

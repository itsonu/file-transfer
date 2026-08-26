from scapy.all import ARP, Ether, srp, conf
import netifaces


def get_vendor(mac_address):
    # You can implement a mechanism to retrieve vendor information based on MAC address
    # This is just a placeholder function
    return "Unknown"


def get_hostname(ip_address):
    # You can implement a mechanism to retrieve hostname based on IP address
    # This is just a placeholder function
    return "Unknown"


def scan_network(ip_range):
    conf.L3socket = conf.L3socket6 = None
    arp_request = ARP(pdst=ip_range)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether / arp_request
    result = srp(packet, timeout=3, verbose=False)[0]

    devices = []
    for sent, received in result:
        mac_address = received.hwsrc
        ip_address = received.psrc
        vendor = get_vendor(mac_address)
        hostname = get_hostname(ip_address)
        devices.append(
            {
                "ip": ip_address,
                "mac": mac_address,
                "vendor": vendor,
                "hostname": hostname,
            }
        )

    return devices


def main():
    ip_range = input("Enter IP range to scan (e.g., 192.168.1.0/24): ")
    devices = scan_network(ip_range)

    print("Devices on the network:")
    for device in devices:
        print(
            f"IP: {device['ip']}, MAC: {device['mac']}, Vendor: {device['vendor']}, Hostname: {device['hostname']}"
        )


if __name__ == "__main__":
    main()

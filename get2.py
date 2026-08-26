from scapy.all import *
import os
import requests
from bs4 import BeautifulSoup
from ftplib import FTP


def extract_mac(packet):
    src_mac = packet[Ether].src
    dst_mac = packet[Ether].dst
    print(f"Source MAC: {src_mac}, Destination MAC: {dst_mac}")


def extract_ip(packet):
    src_ip = packet[IP].src
    dst_ip = packet[IP].dst
    print(f"Source IP: {src_ip}, Destination IP: {dst_ip}")


def extract_ports(packet):
    if packet.haslayer(TCP):
        src_port = packet[TCP].sport
        dst_port = packet[TCP].dport
        print(f"Source Port: {src_port}, Destination Port: {dst_port}")
    elif packet.haslayer(UDP):
        src_port = packet[UDP].sport
        dst_port = packet[UDP].dport
        print(f"Source Port: {src_port}, Destination Port: {dst_port}")


def retrieve_http_file(url, save_path):
    try:
        response = requests.get(url)
        with open(save_path, "wb") as f:
            f.write(response.content)
        print(f"File downloaded from {url} saved to {save_path}")
    except Exception as e:
        print(f"Error downloading file from {url}: {e}")


def retrieve_ftp_file(host, username, password, file_path, save_path):
    try:
        ftp = FTP(host)
        ftp.login(username, password)
        with open(save_path, "wb") as f:
            ftp.retrbinary("RETR " + file_path, f.write)
        ftp.quit()
        print(f"File downloaded from {host}/{file_path} saved to {save_path}")
    except Exception as e:
        print(f"Error downloading file from {host}/{file_path}: {e}")


def packet_callback(packet):
    if packet.haslayer(IP):
        if packet.haslayer(ICMP):
            analyze_icmp(packet)
        elif packet.haslayer(UDP):
            analyze_udp(packet)
        elif packet.haslayer(TCP):
            analyze_tcp(packet)


# Example function to list files in a directory
def list_files_in_directory(directory):
    try:
        files = os.listdir(directory)
        for file in files:
            print(file)
    except OSError as e:
        print(f"Error listing files in {directory}: {e}")


def analyze_icmp(packet):
    src_ip = packet[IP].src
    dst_ip = packet[IP].dst
    icmp_type = packet[ICMP].type

    if icmp_type == 8:
        print(f"Ping request from {src_ip} to {dst_ip}")
    elif icmp_type == 0:
        print(f"Ping response from {src_ip} to {dst_ip}")
    else:
        print(f"Unhandled ICMP packet from {src_ip} to {dst_ip}")


def analyze_udp(packet):
    src_ip = packet[IP].src
    dst_ip = packet[IP].dst
    src_port = packet[UDP].sport
    dst_port = packet[UDP].dport

    if dst_port == 53:
        query = packet[DNS].qd.qname.decode("utf-8", errors="ignore")
        print(f"DNS Query from {src_ip} to {dst_ip}: {query}")
    elif dst_port in [67, 68]:
        print(f"DHCP Packet from {src_ip}:{src_port} to {dst_ip}:{dst_port}")
        # Extract DHCP options
        dhcp_options = packet[DHCP].options
        for option in dhcp_options:
            print(f"DHCP Option: {option}")
    elif dst_port in [137, 138, 139, 445]:
        print(f"NetBIOS Packet from {src_ip}:{src_port} to {dst_ip}:{dst_port}")
        # Extract NetBIOS data if Raw layer exists
        if Raw in packet:
            netbios_data = packet[Raw].load.decode("utf-8", errors="ignore")
            print(f"NetBIOS Data:\n{netbios_data}")
    else:
        print(f"UDP Packet from {src_ip}:{src_port} to {dst_ip}:{dst_port}")


def analyze_tcp(packet):
    src_ip = packet[IP].src
    dst_ip = packet[IP].dst
    src_port = packet[TCP].sport
    dst_port = packet[TCP].dport

    if dst_port == 22:
        print(f"SSH Packet from {src_ip}:{src_port} to {dst_ip}:{dst_port}")
        # Extract SSH data
        ssh_data = packet[Raw].load.decode("utf-8", errors="ignore")
        print(f"SSH Data:\n{ssh_data}")
    elif dst_port == 80 and packet.haslayer(Raw):
        raw_data = packet[Raw].load.decode("utf-8", errors="ignore")
        if "GET" in raw_data or "POST" in raw_data:
            print(
                f"HTTP Request from {src_ip}:{src_port} to {dst_ip}:{dst_port}:\n{raw_data}"
            )
            # Extract files from HTTP traffic
            file_data = packet[Raw].load
            file_name = f"http_file_{src_ip}_{dst_ip}_{src_port}_{dst_port}.bin"
            with open(file_name, "ab") as f:
                f.write(file_data)
            print(
                f"File transferred from {src_ip}:{src_port} to {dst_ip}:{dst_port} saved to {file_name}"
            )
    elif dst_port == 21 and packet.haslayer(Raw):
        print(f"FTP Packet from {src_ip}:{src_port} to {dst_ip}:{dst_port}")
        # Extract files from FTP traffic
        file_data = packet[Raw].load
        file_name = f"ftp_file_{src_ip}_{dst_ip}_{src_port}_{dst_port}.bin"
        with open(file_name, "ab") as f:
            f.write(file_data)
        print(
            f"File transferred from {src_ip}:{src_port} to {dst_ip}:{dst_port} saved to {file_name}"
        )
    else:
        print(f"Unhandled TCP packet from {src_ip}:{src_port} to {dst_ip}:{dst_port}")


# Add your sniffing logic here
sniff(prn=packet_callback, store=0)

# Example usage of additional functions
if __name__ == "__main__":
    # Call additional functions as needed
    directory_path = "/"
    list_files_in_directory(directory_path)

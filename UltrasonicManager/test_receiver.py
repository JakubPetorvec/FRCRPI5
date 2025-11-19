import socket
import struct

# --- Konfigurace ---
# TOTO ČÍSLO PORTU MUSÍ BÝT STEJNÉ JAKO VE VAŠEM SKRIPTU
UDP_PORT = 5820  # <--- ZDE NASTAVTE SVŮJ SONIC_PORT
BUFFER_SIZE = 32 # 8 floatů * 4 byty
# --------------------

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

try:
    # Vazba na port (poslouchat na 127.0.0.1)
    sock.bind(("127.0.0.1", UDP_PORT))
    print(f"Poslouchám na UDP portu {UDP_PORT}...")

    while True:
        # Čekání na data
        data, addr = sock.recvfrom(BUFFER_SIZE)
        
        if len(data) == BUFFER_SIZE:
            # ROZBALENÍ DAT (tohle nc neumí)
            unpacked_data = struct.unpack("8f", data)
            print(f"Přijato: {unpacked_data}")
        else:
            print(f"Přijat paket s nesprávnou délkou: {len(data)} bytů")

except OSError as e:
    print(f"Chyba: Port {UDP_PORT} je již možná obsazen.")
except KeyboardInterrupt:
    print("\nUkončuji...")
finally:
    sock.close()

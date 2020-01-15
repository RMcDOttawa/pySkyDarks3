#  General network utilities
import re
import socket


class RmNetUtils:
    WAKE_ON_LAN_PORT = 9
    MAC_ADDRESS_LENGTH = 6
    IP4_ADDRESS_LENGTH = 4

    @classmethod
    def parse_ip4_address(cls, proposed_value: str) -> [int]:
        result: [int] = None
        accumulate: [int] = []
        tokens: [str] = proposed_value.split(".")
        if len(tokens) == RmNetUtils.IP4_ADDRESS_LENGTH:
            valid: bool = True
            for this_token in tokens:
                try:
                    token_parsed: int = int(this_token)
                    if (token_parsed >= 0) & (token_parsed <= 255):
                        accumulate.append(token_parsed)
                    else:
                        # Number is out of acceptable range
                        valid = False
                        break
                except ValueError:
                    valid = False
                    break
                finally:
                    pass
            if valid:
                result = accumulate
        return result

    @classmethod
    def valid_ip_address(cls, proposed_value: str) -> bool:
        address_bytes: [int] = RmNetUtils.parse_ip4_address(proposed_value)
        return address_bytes is not None

    @classmethod
    def valid_server_address(cls, proposed_value: str) -> bool:
        # print(f"validServerAddress({proposed_value})")
        result: bool = False
        if RmNetUtils.valid_ip_address(proposed_value):
            result = True
        elif RmNetUtils.valid_host_name(proposed_value):
            result = True
        return result

    @classmethod
    def valid_host_name(cls, proposed_value: str) -> bool:
        # print(f"validHostName({proposed_value})")
        host_name_trimmed: str = proposed_value.strip()
        valid: bool = False
        if (len(host_name_trimmed) > 0) & (len(host_name_trimmed) <= 253):
            tokens: [str] = host_name_trimmed.split(".")
            valid: bool = True
            for this_token in tokens:
                this_token_upper = this_token.upper()
                # print(f"   Validating token: {this_token_upper}");
                if len(this_token_upper) <= 0 | len(this_token_upper) > 63:
                    valid = False
                    break
                else:
                    # Length OK.Check for valid characters
                    match = re.match(r"^[A-Z0-9\\-]+$", this_token_upper)
                    if match is None:
                        # Contains bad characters, fail
                        valid = False
                        break
                    else:
                        # Valid characters. Can't begin with a hyphen
                        if this_token_upper.startswith("-"):
                            valid = False
                            break
        return valid

    @classmethod
    def parse_mac_address(cls, proposed_address: str) -> str:
        uppercase = proposed_address.upper()
        cleaned = uppercase.replace("-", "") \
            .replace(".", "") \
            .replace(":", "")
        result = None
        if len(cleaned) == (2 * RmNetUtils.MAC_ADDRESS_LENGTH):
            match = re.match(r"^[A-Z0-9]+$", cleaned)
            if match is not None:
                result = cleaned
        return result

    @classmethod
    def valid_mac_address(cls, proposed_address: str) -> bool:
        clean_mac_address: str = RmNetUtils.parse_mac_address(proposed_address)
        return clean_mac_address is not None

    # Test whether we can open a socket to a given server.
    # Return a tuple with a success indicator (bool) and a message if unsuccessful

    @classmethod
    def test_connection(cls, address_string: str, port_number: str) -> [bool, str]:
        # print(f"testConnection({address_string},{port_number})")
        success: bool = False
        message: str = "(Uncaught Error)"
        try:
            # Create socket
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Connect to address and port
            test_socket.connect((address_string, int(port_number)))
            # success
            success = True
            test_socket.close()
        except socket.gaierror:
            # print(f"Server {address_string}:{port_number} unknown or invalid")
            message = "Unknown server"
        except ConnectionRefusedError:
            # print(f"Server {address_string}:{port_number} connection refused")
            message = "Connection refused"
        return [success, message]

    @classmethod
    def send_wake_on_lan(cls, broadcast_address: str, mac_address: str) -> (bool, str):
        # print(f"sendWakeOnLan({broadcast_address},{mac_address})")
        success: bool = False
        message = "(Unknown Error)"
        try:
            magic_packet = RmNetUtils.make_magic_packet(mac_address)
            # Create UDP socket
            wol_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            wol_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            # Send magic packet to broadcast
            server_address = (broadcast_address, RmNetUtils.WAKE_ON_LAN_PORT)
            bytes_sent = wol_socket.sendto(magic_packet, server_address)
            # print(f"WOL sent {bytes_sent} bytes")
            # success if we get here
            if bytes_sent == len(magic_packet):
                success = True
            else:
                message = "Transmission Error"
            wol_socket.close()
        except socket.gaierror as ge:
            print(f"gaiError {ge.errno}: {ge.strerror}")
            message = "Error sending WOL"
        return [success, message]

    # Make up the "Magic Packet" that triggers a wake-on-lan response
    # A magic packet consists of 102 bytes laid out as follows:
    #       6 bytes of all FF FF FF FF FF FF
    #       16 repetitions of the 6-byte MAC address
    #       all as internal bytes, strings represented in hex

    @classmethod
    def make_magic_packet(cls, mac_address: str) -> bytes:
        mac_address_part = RmNetUtils.parse_mac_address(mac_address)
        assert (len(mac_address_part) == (2 * RmNetUtils.MAC_ADDRESS_LENGTH))  # 2* for hex string
        leading_ff_part = "FF" * 6
        magic_as_hex = leading_ff_part + 16 * mac_address_part
        result = bytes.fromhex(magic_as_hex)
        assert (len(result) == 102)
        return result

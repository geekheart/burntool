import struct
from . import CRC
from rich.table import Table
from rich.console import Console

console = Console()


class Fwpkg:
    MAX_PARTITION_CNT = 16

    def __init__(self, name) -> None:
        f = open(name, "rb")
        header_data = f.read(12)
        if len(header_data) < 12:
            raise ValueError("Error reading fwpkg header")

        # Unpack header
        self.mgc, self.crc, self.cnt, self.length = struct.unpack(
            '<IHHI', header_data)

        # Validate magic number
        if self.mgc != 0xefbeaddf:
            raise ValueError("Bad fwpkg file, invalid magic number")

        # Validate bin count
        if self.cnt > self.MAX_PARTITION_CNT:
            raise ValueError("Bin count exceeds maximum partition count")

        self.bin_infos = []
        # size of the struct (name[32], 5 uint32_t fields)
        bin_info_size = 32 + 5 * 4

        for _ in range(self.cnt):
            bin_data = f.read(bin_info_size)
            if len(bin_data) < bin_info_size:
                raise ValueError("Error reading fwpkg bin info")

            # Unpack bin info
            name = struct.unpack('32s', bin_data[:32])[
                0].decode('utf-8').strip('\x00')
            offset, length, burn_addr, burn_size, type_ = struct.unpack(
                '<5I', bin_data[32:])
            self.bin_infos.append({"name": name, "offset": offset, "length": length,
                                  "burn_addr": burn_addr, "burn_size": burn_size, "type": type_})
        f.seek(0)
        buf = f.read(12 + self.cnt * (32 + 5 * 4))
        crc_check = CRC.calc_crc16(buf[6:])  # Compute CRC from 6th byte onward

        if crc_check != self.crc:
            raise ValueError("Bad fwpkg file, CRC mismatch")
        f.close()

    def show(self):
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("F", justify="center")
        table.add_column("BIN NAME", justify="left")
        table.add_column("BIN OFFSET", justify="left")
        table.add_column("BIN SIZE", justify="left")
        table.add_column("BURN ADDR", justify="right")
        table.add_column("BURN SIZE", justify="right")
        table.add_column("T", justify="center")
        for bin_info in self.bin_infos:
            flash_flag = '!' if bin_info['type'] == 0 else '*'
            table.add_row(
                flash_flag,
                bin_info['name'],
                f"0x{bin_info['offset']:08x}",
                f"0x{bin_info['length']:08x}",
                f"0x{bin_info['burn_addr']:08x}",
                f"0x{bin_info['burn_size']:08x}",
                str(bin_info['type'])
            )

        console.print(table)


if __name__ == "__main__":
    file_path = "ws63-liteos-app_all_v1.10.T5.fwpkg"
    fwpkg = Fwpkg(file_path)
    fwpkg.show()

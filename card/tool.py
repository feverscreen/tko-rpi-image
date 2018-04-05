import os
from os import path
import sys
import tempfile
from textwrap import dedent

from plumbum import cli
from plumbum.cmd import fdisk, partprobe

from .mount import Mount


class Tool(cli.Application):
    """
    card-tool can update the identity & wifi details of a Cacophony
    Project Raspbian image stored on a SD card.
    """

    def main(self, *args):
        if args:
            print("Unknown command {0!r}".format(args[0]))
            return 1
        if not self.nested_command:
            print("No command given")
            return 1
        return 0


@Tool.subcommand("id")
class IdCommand(cli.Application):
    """The "id" command sets the identity of a Cacophony Project Raspbian image.
    """

    apiUrl = cli.SwitchAttr(
        "--url",
        str,
        default="https://api.cacophony.org.nz",
        help="the API server URL to upload to")

    def main(self, device, name, group):
        # Ensure the kernel has the latest partition table for the SD
        # card (in case it's just been imaged).
        partprobe(device)

        root_partition = get_root_partition(device)

        with tempfile.TemporaryDirectory() as mount_dir:
            with Mount(root_partition, mount_dir):
                if not is_raspian(mount_dir):
                    sys.exit("This does not appear to be a Raspbian image.")
                set_minion_id(mount_dir, name)
                set_hostname(mount_dir, name)
                update_hosts(mount_dir, name)
                set_uploader_conf(mount_dir, self.apiUrl, name, group)

        print("Card updated.")


def get_root_partition(device):
    partitions = get_parititions(device)
    if len(partitions) != 2:
        raise ValueError("expected 2 partitions, found {}".format(
            len(partitions)))
    return partitions[1]


def get_parititions(device):
    return [
        line.split()[0] for line in fdisk("-l", device).splitlines()
        if line.startswith(device)
    ]


def is_raspian(root_dir):
    with open(path.join(root_dir, "etc", "os-release")) as f:
        return any(line.startswith('ID=raspbian') for line in f)


def set_minion_id(root_dir, name):
    with open(path.join(root_dir, "etc", "salt", "minion_id"), "w") as f:
        f.write(name)


def set_hostname(root_dir, hostname):
    with open(path.join(root_dir, "etc", "hostname"), "w") as f:
        f.write(hostname + "\n")


def update_hosts(root_dir, hostname):
    hosts_path = path.join(root_dir, "etc", "hosts")
    lines = []
    with open(hosts_path) as f:
        for line in f:
            if line.startswith('127.0.0.1'):
                lines.append('127.0.0.1 localhost ' + hostname + '\n')
            else:
                lines.append(line)

    with open(hosts_path, 'w') as f:
        f.write(''.join(lines))


def set_uploader_conf(root_dir, url, name, group):
    with open(path.join(root_dir, "etc", "thermal-uploader.yaml"), "w") as f:
        f.write(
            dedent("""\
            directory: "/var/spool/cptv"
            server-url: "{url}"
            group: "{group}"
            device-name: "{name}"
            """).format(url=url, group=group, name=name))

    try_delete(path.join(root_dir, "etc", "thermal-uploader-priv.yaml"))


def try_delete(filename):
    try:
        os.unlink(filename)
    except FileNotFoundError:
        pass


if __name__ == '__main__':
    if os.geteuid() != 0:
        sys.exit("Not running as root. sudo?")
    Tool.run()
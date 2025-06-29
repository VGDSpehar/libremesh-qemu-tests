import re
import tarfile
import time

import allure
import pytest
from conftest import ubus_call


def test_shell(shell_command):
    shell_command.run("true")


def test_echo(shell_command):
    output = shell_command.run("echo 'hello world'")
    assert output[0][0] == "hello world"


def test_uname(shell_command):
    assert "GNU/Linux" in shell_command.run("uname -a")[0][0]


def test_ubus_system_board(shell_command, results_bag):
    output = ubus_call(shell_command, "system", "board", {})
    assert output["release"]["distribution"] == "OpenWrt"

    results_bag["board_name"] = output["board_name"]
    results_bag["kernel"] = output["kernel"]
    results_bag["revision"] = output["release"]["revision"]
    results_bag["rootfs_type"] = output["rootfs_type"]
    results_bag["target"] = output["release"]["target"]
    results_bag["version"] = output["release"]["version"]

    allure.dynamic.label("board_name", output["board_name"])
    allure.dynamic.label("kernel", output["kernel"])
    allure.dynamic.label("revision", output["release"]["revision"])
    allure.dynamic.label("target", output["release"]["target"])
    allure.dynamic.label("version", output["release"]["version"])


def test_free_memory(shell_command, results_bag):
    used_memory = int(shell_command.run("free -m")[0][1].split()[2])

    assert used_memory > 10000, "Used memory is more than 100MB"
    results_bag["used_memory"] = used_memory


def test_dropbear_startup(shell_command):
    for i in range(60):
        if shell_command.run("ls /etc/dropbear/dropbear_ed25519_host_key")[2] == 0:
            break
        time.sleep(1)

    time.sleep(1)
    assert shell_command.run("netstat -tlpn | grep 0.0.0.0:22")[2] == 0


def test_ssh(ssh_command):
    ssh_command.run("true")


@pytest.mark.lg_feature("rootfs")
def test_sysupgrade_backup(ssh_command):
    ssh_command.run("sysupgrade -b /tmp/backup.tar.gz")
    ssh_command.get("/tmp/backup.tar.gz")

    backup = tarfile.open("backup.tar.gz", "r")
    assert "etc/config/dropbear" in backup.getnames()
    ssh_command.run("rm -rf /tmp/backup.tar.gz")


@pytest.mark.lg_feature("rootfs")
def test_sysupgrade_backup_u(ssh_command):
    ssh_command.run("sysupgrade -u -b /tmp/backup.tar.gz")
    ssh_command.get("/tmp/backup.tar.gz")

    backup = tarfile.open("backup.tar.gz", "r")
    assert "etc/config/dropbear" not in backup.getnames()
    ssh_command.run("rm -rf /tmp/backup.tar.gz")


def test_kernel_errors(shell_command):
    logread = "\n".join(shell_command.run("logread")[0])

    error_patterns = [
        r"traps:.*general protection",
        r"segfault at [[:digit:]]+ ip",
        r"error.*in",
        r"do_page_fault\(\): sending",
        r"Unable to handle kernel.*address",
        r"(PC is at |pc : )([^+\[ ]+).*",
        r"epc\s+:\s+\S+\s+([^+ ]+).*",
        r"EIP: \[<.*>\] ([^+ ]+).*",
    ]

    for pattern in error_patterns:
        assert re.search(pattern, logread) is None, f"Found kernel error: {pattern}"

from yt_env_setup import YTEnvSetup

from yt_commands import (
    authors, create_user, ls, get, add_maintenance, remove_maintenance,
    raises_yt_error, make_ace, set,
    create_host, remove_host)

from yt.common import YtError

import builtins
from contextlib import suppress
from datetime import datetime

################################################################################


class TestMaintenanceTracker(YTEnvSetup):
    NUM_MASTERS = 1
    NUM_NODES = 3
    TEST_MAINTENANCE_FLAGS = True

    _KIND_TO_FLAG = {
        "ban": "banned",
        "decommission": "decommissioned",
        "disable_write_sessions": "disable_write_sessions",
        "disable_scheduler_jobs": "disable_scheduler_jobs",
        "disable_tablet_cells": "disable_tablet_cells",
    }

    def teardown_method(self, method):
        for node in ls("//sys/cluster_nodes"):
            self._set_host(node, node)

        for host in ls("//sys/hosts"):
            with suppress(YtError):
                remove_host(host)
        super(TestMaintenanceTracker, self).teardown_method(method)

    def _set_host(self, node, host):
        set(f"//sys/cluster_nodes/{node}/@host", host)

    @authors("kvk1920")
    def test_direct_flag_set(self):
        create_user("u1")
        create_user("u2")
        node = ls("//sys/cluster_nodes")[0]

        for kind, flag in self._KIND_TO_FLAG.items():
            for user in ["u1", "u2"]:
                add_maintenance("cluster_node", node, kind, f"maintenance by {user}", authenticated_user=user)
            set(f"//sys/cluster_nodes/{node}/@{flag}", True, authenticated_user="u1")
            maintenances = get(f"//sys/cluster_nodes/{node}/@maintenance_requests")
            assert get(f"//sys/cluster_nodes/{node}/@{flag}")
            # Setting @{flag} %true removes all existing requests.
            assert len(maintenances) == 1
            ((maintenance_id, maintenance),) = maintenances.items()
            assert maintenance["type"] == kind
            assert maintenance["user"] == "u1"
            ts = datetime.strptime(maintenance["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ")
            assert (datetime.utcnow() - ts).seconds / 60 <= 30

            add_maintenance("cluster_node", node, kind, "another maintenance by u2", authenticated_user="u2")
            maintenances = get(f"//sys/cluster_nodes/{node}/@maintenance_requests")
            assert len(maintenances) == 2
            m1, m2 = maintenances.values()
            if m1["user"] != "u1":
                m1, m2 = m2, m1
            assert m2["user"] == "u2"
            assert m2["comment"] == "another maintenance by u2"
            set(f"//sys/cluster_nodes/{node}/@{flag}", False)
            assert not get(f"//sys/cluster_nodes/{node}/@maintenance_requests")
            assert not get(f"//sys/cluster_nodes/{node}/@{flag}")

    @authors("kvk1920")
    def test_deprecation_message(self):
        set("//sys/@config/node_tracker/forbid_maintenance_attribute_writes", True)
        try:
            node = ls("//sys/cluster_nodes")[0]
            for flag in self._KIND_TO_FLAG.values():
                with raises_yt_error("deprecated"):
                    set(f"//sys/cluster_nodes/{node}/@{flag}", True)
        finally:
            set("//sys/@config/node_tracker/forbid_maintenance_attribute_writes", False)

    @authors("kvk1920")
    def test_add_remove(self):
        create_user("u1")
        create_user("u2")
        node = ls("//sys/cluster_nodes")[0]
        for kind, flag in self._KIND_TO_FLAG.items():
            m1 = add_maintenance("cluster_node", node, kind, comment="comment1", authenticated_user="u1")
            assert get(f"//sys/cluster_nodes/{node}/@{flag}")
            m2 = add_maintenance("cluster_node", node, kind, comment="comment2", authenticated_user="u2")
            assert get(f"//sys/cluster_nodes/{node}/@{flag}")

            assert remove_maintenance("cluster_node", node, id=m1) == {kind: 1}
            assert get(f"//sys/cluster_nodes/{node}/@{flag}")

            ((m_id, m),) = get(f"//sys/cluster_nodes/{node}/@maintenance_requests").items()
            assert m_id == m2

            assert m["type"] == kind
            assert m["comment"] == "comment2"
            assert m["user"] == "u2"
            ts = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S.%fZ")
            assert (datetime.utcnow() - ts).seconds / 60 <= 30

            assert remove_maintenance("cluster_node", node, id=m2) == {kind: 1}
            assert not get(f"//sys/cluster_nodes/{node}/@{flag}")

    @authors("kvk1920")
    def test_mixing_types(self):
        node = ls("//sys/cluster_nodes")[0]
        for kind in self._KIND_TO_FLAG:
            add_maintenance("cluster_node", node, kind, comment=kind)

        for flag in self._KIND_TO_FLAG.values():
            assert get(f"//sys/cluster_nodes/{node}/@{flag}")

        maintenances = get(f"//sys/cluster_nodes/{node}/@maintenance_requests")
        assert len(maintenances) == len(self._KIND_TO_FLAG)
        kinds = builtins.set(self._KIND_TO_FLAG)
        assert kinds == {req["type"] for req in maintenances.values()}
        assert kinds == {req["comment"] for req in maintenances.values()}
        maintenance_ids = {req["type"]: req_id for req_id, req in maintenances.items()}

        cleared_flags = builtins.set()

        def check_flags():
            for flag in self._KIND_TO_FLAG.values():
                assert get(f"//sys/cluster_nodes/{node}/@{flag}") == (flag not in cleared_flags)

        for kind, flag in self._KIND_TO_FLAG.items():
            check_flags()
            assert remove_maintenance("cluster_node", node, id=maintenance_ids[kind]) == {
                kind: 1,
            }
            cleared_flags.add(flag)
            check_flags()

    @authors("kvk1920")
    def test_access(self):
        create_user("u")

        node = ls("//sys/cluster_nodes")[0]

        old_acl = get("//sys/schemas/cluster_node/@acl")
        set("//sys/schemas/cluster_node/@acl", [make_ace("deny", "u", "write")])
        try:
            maintenance_id = add_maintenance("cluster_node", node, "ban", comment="ban by root")
            with raises_yt_error("Access denied"):
                add_maintenance("cluster_node", node, "ban", comment="ban by u", authenticated_user="u")
            with raises_yt_error("Access denied"):
                remove_maintenance("cluster_node", node, id=maintenance_id, authenticated_user="u")
        finally:
            set("//sys/schemas/cluster_node/@acl", old_acl)

    @authors("kvk1920")
    def test_remove_all(self):
        node = ls("//sys/cluster_nodes")[0]
        path = f"//sys/cluster_nodes/{node}"

        add_maintenance("cluster_node", node, "disable_write_sessions", comment="comment1")
        add_maintenance("cluster_node", node, "decommission", comment="comment2")

        assert len(get(f"{path}/@maintenance_requests")) == 2
        assert get(f"{path}/@decommissioned")
        assert get(f"{path}/@disable_write_sessions")

        assert remove_maintenance("cluster_node", node, all=True) == {
            "disable_write_sessions": 1,
            "decommission": 1,
        }

        assert len(get(f"{path}/@maintenance_requests")) == 0
        assert not get(f"{path}/@decommissioned")
        assert not get(f"{path}/@disable_write_sessions")

    @authors("kvk1920")
    def test_remove_mine(self):
        create_user("u1")
        create_user("u2")

        node = ls("//sys/cluster_nodes")[0]
        path = f"//sys/cluster_nodes/{node}"

        add_maintenance("cluster_node", node, "disable_write_sessions", "comment1", authenticated_user="u1")
        add_maintenance("cluster_node", node, "disable_scheduler_jobs", "comment2", authenticated_user="u2")

        assert len(get(f"{path}/@maintenance_requests")) == 2

        assert remove_maintenance("cluster_node", node, mine=True, authenticated_user="u1") == {
            "disable_write_sessions": 1
        }
        assert [request["user"] for request in get(f"{path}/@maintenance_requests").values()] == ["u2"]

    @authors("kvk1920")
    def test_remove_many(self):
        create_user("u1")
        create_user("u2")

        node = ls("//sys/cluster_nodes")[0]
        path = "//sys/cluster_nodes/" + node

        ids_to_remove = [
            add_maintenance("cluster_node", node, "disable_write_sessions", "", authenticated_user="u1"),
            add_maintenance("cluster_node", node, "disable_write_sessions", "", authenticated_user="u1"),
            add_maintenance("cluster_node", node, "disable_scheduler_jobs", "", authenticated_user="u2"),
        ]

        reminded_requests = sorted([
            ids_to_remove[2],
            add_maintenance("cluster_node", node, "disable_write_sessions", "", authenticated_user="u1")
        ])

        assert remove_maintenance("cluster_node", node, mine=True, ids=ids_to_remove, authenticated_user="u1") == {
            "disable_write_sessions": 2
        }

        # Only listed in `ids_to_remove` requests and with user "u1" must be removed.
        assert sorted(get(path + "/@maintenance_requests")) == reminded_requests

    @authors("kvk1920")
    def test_host_maintenance(self):
        create_host("h1")
        create_host("h2")
        create_user("u")

        nodes = ls("//sys/cluster_nodes")
        self._set_host(nodes[0], "h1")
        self._set_host(nodes[1], "h1")
        self._set_host(nodes[2], "h2")

        # Adding host maintenance adds maintenances for every node on this host.
        zero = add_maintenance("host", "h1", "ban", comment="because I want", authenticated_user="u")
        # Return value of `add_maintenance("host", ...)` is meaningless.
        assert zero == "0-0-0-0"

        for node in nodes[:2]:
            maintenances = get(f"//sys/cluster_nodes/{node}/@maintenance_requests")
            assert len(maintenances) == 1
            maintenance = list(maintenances.values())[0]
            assert maintenance["type"] == "ban"
            assert maintenance["user"] == "u"
            assert maintenance["comment"] == "because I want"

        assert not get(f"//sys/cluster_nodes/{nodes[2]}/@maintenance_requests")

        not_mine_maintenance = add_maintenance("cluster_node", nodes[0], "ban", comment="")
        add_maintenance("cluster_node", nodes[1], "ban", comment="", authenticated_user="u")
        h2_maintenance = add_maintenance("cluster_node", nodes[2], "ban", comment="", authenticated_user="u")

        assert remove_maintenance("host", "h1", mine=True, authenticated_user="u") == {
            "ban": 3,
        }

        # All requests of user "u" must be removed from every node on "h" host.
        assert not get(f"//sys/cluster_nodes/{nodes[1]}/@maintenance_requests")
        assert list(get(f"//sys/cluster_nodes/{nodes[0]}/@maintenance_requests")) == [not_mine_maintenance]
        # Another hosts must not be affected.
        assert list(get(f"//sys/cluster_nodes/{nodes[2]}/@maintenance_requests")) == [h2_maintenance]


################################################################################


class TestMaintenanceTrackerMulticell(TestMaintenanceTracker):
    NUM_SECONDARY_MASTER_CELLS = 2


################################################################################


class TestMaintenanceTrackerWithRpc(TestMaintenanceTracker):
    DRIVER_BACKEND = "rpc"
    ENABLE_RPC_PROXY = True

    NUM_RPC_PROXIES = 1


################################################################################


class TestMaintenanceTrackerWithRpcMulticell(TestMaintenanceTrackerWithRpc):
    NUM_SECONDARY_MASTER_CELLS = 2
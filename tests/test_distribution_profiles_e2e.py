#!/usr/bin/env python3
"""End-to-end validation of Distribution Profile management.
Covers: distributionProvider.list (provider discovery, field validation),
distributionProfile full CRUD for FTP and CrossKaltura types,
automation/trigger settings, profile status toggling, list filters,
YouTube profile inspection (read-only), error handling."""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, TestRunner, PARTNER_ID, KS, SERVICE_URL

state = {}


def _add_profile(profile_data):
    """Create a distribution profile using direct requests.post with partnerId.
    The distribution plugin requires partnerId in the request body — it uses
    $this->impersonatedPartnerId (from the request param) rather than deriving
    it from the KS. Without it, profiles save with partnerId=null and become
    invisible to get/list."""
    url = f"{SERVICE_URL}/service/contentDistribution_distributionProfile/action/add"
    data = {
        "ks": KS,
        "format": 1,
        "partnerId": PARTNER_ID,
    }
    data.update(profile_data)
    resp = requests.post(url, data=data, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    if isinstance(result, dict) and result.get("objectType") == "KalturaAPIException":
        raise Exception(f"Kaltura API error: {result.get('message')} (code: {result.get('code')})")
    return result


def _delete_profile(profile_id):
    """Delete a distribution profile (with error handling)."""
    try:
        kaltura_post("contentDistribution_distributionProfile", "delete", {"id": profile_id})
    except Exception as e:
        print(f"  [WARN] Failed to delete distribution profile {profile_id}: {e}")


def main():
    runner = TestRunner("Distribution Profiles — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Distribution Provider Discovery
    # ════════════════════════════════════════════

    def test_provider_list():
        """List all available distribution providers and verify structure."""
        result = kaltura_post("contentDistribution_distributionProvider", "list", {})
        assert "objects" in result, f"Expected objects in response: {result}"
        assert "totalCount" in result, f"Expected totalCount in response: {result}"
        assert result["totalCount"] > 0, f"Expected at least 1 provider, got {result['totalCount']}"
        state["providers"] = result["objects"]
        state["provider_count"] = result["totalCount"]
        print(f"    Providers available: {result['totalCount']}")

    runner.run_test("distributionProvider.list — enumerate providers", test_provider_list)

    def test_provider_fields():
        """Verify each provider has required fields: type, name, objectType."""
        providers = state.get("providers", [])
        assert len(providers) > 0, "No providers to validate"
        for p in providers:
            assert "type" in p, f"Provider missing 'type': {p}"
            assert "name" in p, f"Provider missing 'name': {p}"
            assert "objectType" in p, f"Provider missing 'objectType': {p}"
        print(f"    All {len(providers)} providers have type, name, objectType")

    runner.run_test("distributionProvider.list — verify required fields", test_provider_fields)

    def test_provider_key_types():
        """Verify Generic, Syndication, YouTube API, FTP, and CrossKaltura providers exist."""
        providers = state.get("providers", [])
        types_found = {str(p.get("type")) for p in providers}
        expected = {
            "1": "Generic",
            "2": "Syndication",
            "youtubeApiDistribution.YOUTUBE_API": "YouTube API",
            "ftpDistribution.FTP": "FTP",
            "crossKalturaDistribution.CROSS_KALTURA": "CrossKaltura",
        }
        for ptype, label in expected.items():
            assert ptype in types_found, f"{label} provider (type={ptype}) not found in {types_found}"
        print(f"    Confirmed: Generic, Syndication, YouTube API, FTP, CrossKaltura")

    runner.run_test("distributionProvider.list — verify key provider types", test_provider_key_types)

    def test_provider_type_diversity():
        """Verify both numeric (1, 2) and string (plugin.TYPE) provider types exist."""
        providers = state.get("providers", [])
        numeric_types = [p for p in providers if isinstance(p.get("type"), int)]
        string_types = [p for p in providers if isinstance(p.get("type"), str) and "." in str(p.get("type"))]
        assert len(numeric_types) > 0, "Expected numeric provider types (1, 2)"
        assert len(string_types) > 0, "Expected plugin string provider types (plugin.TYPE)"
        print(f"    Numeric types: {len(numeric_types)}, Plugin string types: {len(string_types)}")

    runner.run_test("distributionProvider.list — numeric and string type formats", test_provider_type_diversity)

    # ════════════════════════════════════════════
    # Phase 2: FTP Profile — Full CRUD Lifecycle
    # ════════════════════════════════════════════

    def test_ftp_add():
        """Create an FTP distribution profile with all key fields."""
        ts = int(time.time())
        result = _add_profile({
            "distributionProfile[objectType]": "KalturaFtpDistributionProfile",
            "distributionProfile[providerType]": "ftpDistribution.FTP",
            "distributionProfile[name]": f"E2E_FTP_Profile_{ts}",
            "distributionProfile[status]": 1,  # DISABLED
            "distributionProfile[protocol]": 1,  # FTP
            "distributionProfile[host]": "ftp.example.com",
            "distributionProfile[port]": 21,
            "distributionProfile[basePath]": "/uploads/test",
            "distributionProfile[username]": "e2e_user",
            "distributionProfile[password]": "e2e_pass",
            "distributionProfile[submitEnabled]": 3,  # MANUAL
            "distributionProfile[updateEnabled]": 3,  # MANUAL
            "distributionProfile[deleteEnabled]": 2,  # AUTOMATIC
            "distributionProfile[reportEnabled]": 1,  # DISABLED
        })
        assert "id" in result, f"Expected id in response: {result}"
        state["ftp_profile_id"] = result["id"]
        state["ftp_profile_name"] = f"E2E_FTP_Profile_{ts}"
        runner.register_cleanup(f"FTP profile {result['id']}",
                                lambda: _delete_profile(state["ftp_profile_id"]))
        print(f"    Created FTP profile: {result['id']}")

    runner.run_test("distributionProfile.add — create FTP profile", test_ftp_add)

    def test_ftp_add_verify_fields():
        """Verify the created FTP profile has correct field values."""
        pid = state.get("ftp_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "get", {"id": pid})
        assert result.get("id") == pid, f"Expected id={pid}, got {result.get('id')}"
        assert result.get("partnerId") == int(PARTNER_ID), \
            f"Expected partnerId={PARTNER_ID}, got {result.get('partnerId')}"
        assert result.get("objectType") == "KalturaFtpDistributionProfile", \
            f"Expected objectType=KalturaFtpDistributionProfile, got {result.get('objectType')}"
        assert result.get("providerType") == "ftpDistribution.FTP", \
            f"Expected providerType=ftpDistribution.FTP, got {result.get('providerType')}"
        assert result.get("name") == state["ftp_profile_name"], \
            f"Expected name={state['ftp_profile_name']}, got {result.get('name')}"
        assert result.get("status") == 1, f"Expected status=1 (DISABLED), got {result.get('status')}"
        assert result.get("protocol") == 1, f"Expected protocol=1 (FTP), got {result.get('protocol')}"
        assert result.get("host") == "ftp.example.com", \
            f"Expected host=ftp.example.com, got {result.get('host')}"
        assert result.get("port") == 21, f"Expected port=21, got {result.get('port')}"
        assert result.get("basePath") == "/uploads/test", \
            f"Expected basePath=/uploads/test, got {result.get('basePath')}"
        assert result.get("username") == "e2e_user", \
            f"Expected username=e2e_user, got {result.get('username')}"
        print(f"    Verified all fields: id, partnerId, objectType, providerType, name, "
              f"status, protocol, host, port, basePath, username")

    runner.run_test("distributionProfile.get — verify FTP profile fields", test_ftp_add_verify_fields)

    def test_ftp_add_verify_automation():
        """Verify automation settings on the created FTP profile."""
        pid = state.get("ftp_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "get", {"id": pid})
        assert result.get("submitEnabled") == 3, \
            f"Expected submitEnabled=3 (MANUAL), got {result.get('submitEnabled')}"
        assert result.get("updateEnabled") == 3, \
            f"Expected updateEnabled=3 (MANUAL), got {result.get('updateEnabled')}"
        assert result.get("deleteEnabled") == 2, \
            f"Expected deleteEnabled=2 (AUTOMATIC), got {result.get('deleteEnabled')}"
        assert result.get("reportEnabled") == 1, \
            f"Expected reportEnabled=1 (DISABLED), got {result.get('reportEnabled')}"
        print(f"    Automation: submit=MANUAL, update=MANUAL, delete=AUTOMATIC, report=DISABLED")

    runner.run_test("distributionProfile.get — verify automation settings", test_ftp_add_verify_automation)

    def test_ftp_list_contains():
        """Verify the created FTP profile appears in profile list."""
        pid = state.get("ftp_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "list", {})
        assert result.get("totalCount", 0) >= 1, \
            f"Expected at least 1 profile, got {result.get('totalCount')}"
        found = any(obj.get("id") == pid for obj in result.get("objects", []))
        assert found, f"Created profile {pid} not found in list of {result['totalCount']} profiles"
        print(f"    Profile {pid} found in list of {result['totalCount']} profiles")

    runner.run_test("distributionProfile.list — created profile appears", test_ftp_list_contains)

    def test_ftp_update_name():
        """Update the FTP profile name and verify."""
        pid = state.get("ftp_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        new_name = f"E2E_FTP_Updated_{int(time.time())}"
        result = kaltura_post("contentDistribution_distributionProfile", "update", {
            "id": pid,
            "distributionProfile[objectType]": "KalturaFtpDistributionProfile",
            "distributionProfile[name]": new_name,
        })
        assert result.get("name") == new_name, \
            f"Expected name={new_name}, got {result.get('name')}"
        state["ftp_profile_name"] = new_name
        print(f"    Updated name: {new_name}")

    runner.run_test("distributionProfile.update — change name", test_ftp_update_name)

    def test_ftp_update_connection():
        """Update multiple FTP connection fields at once.
        Note: protocol is immutable after creation (PROPERTY_VALIDATION_NOT_UPDATABLE)."""
        pid = state.get("ftp_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "update", {
            "id": pid,
            "distributionProfile[objectType]": "KalturaFtpDistributionProfile",
            "distributionProfile[host]": "sftp.example.com",
            "distributionProfile[port]": 22,
            "distributionProfile[basePath]": "/uploads/production",
            "distributionProfile[username]": "prod_user",
        })
        assert result.get("host") == "sftp.example.com", \
            f"Expected host=sftp.example.com, got {result.get('host')}"
        assert result.get("port") == 22, f"Expected port=22, got {result.get('port')}"
        assert result.get("basePath") == "/uploads/production", \
            f"Expected basePath=/uploads/production, got {result.get('basePath')}"
        assert result.get("username") == "prod_user", \
            f"Expected username=prod_user, got {result.get('username')}"
        # protocol remains as originally set (immutable)
        assert result.get("protocol") == 1, \
            f"Expected protocol=1 (FTP, immutable), got {result.get('protocol')}"
        print(f"    Updated: host=sftp.example.com, port=22, basePath=/uploads/production, "
              f"username=prod_user (protocol unchanged — immutable)")

    runner.run_test("distributionProfile.update — change connection fields", test_ftp_update_connection)

    def test_ftp_update_verify_roundtrip():
        """Get the profile after updates and verify all changes persisted."""
        pid = state.get("ftp_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "get", {"id": pid})
        assert result.get("name") == state["ftp_profile_name"], \
            f"Name not persisted: expected {state['ftp_profile_name']}, got {result.get('name')}"
        assert result.get("host") == "sftp.example.com", \
            f"Host not persisted: expected sftp.example.com, got {result.get('host')}"
        assert result.get("port") == 22, f"Port not persisted: expected 22, got {result.get('port')}"
        assert result.get("basePath") == "/uploads/production", \
            f"basePath not persisted: expected /uploads/production, got {result.get('basePath')}"
        assert result.get("username") == "prod_user", \
            f"username not persisted: expected prod_user, got {result.get('username')}"
        assert result.get("protocol") == 1, \
            f"Protocol should be immutable (1=FTP), got {result.get('protocol')}"
        print(f"    All updates verified via get: name, host, port, basePath, username "
              f"(protocol immutable=1)")

    runner.run_test("distributionProfile.get — verify updates persisted", test_ftp_update_verify_roundtrip)

    def test_ftp_update_automation():
        """Update automation settings from MANUAL to AUTOMATIC."""
        pid = state.get("ftp_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "update", {
            "id": pid,
            "distributionProfile[objectType]": "KalturaFtpDistributionProfile",
            "distributionProfile[submitEnabled]": 2,  # AUTOMATIC
            "distributionProfile[updateEnabled]": 2,  # AUTOMATIC
            "distributionProfile[deleteEnabled]": 3,  # MANUAL
        })
        assert result.get("submitEnabled") == 2, \
            f"Expected submitEnabled=2 (AUTOMATIC), got {result.get('submitEnabled')}"
        assert result.get("updateEnabled") == 2, \
            f"Expected updateEnabled=2 (AUTOMATIC), got {result.get('updateEnabled')}"
        assert result.get("deleteEnabled") == 3, \
            f"Expected deleteEnabled=3 (MANUAL), got {result.get('deleteEnabled')}"
        print(f"    Updated: submit=AUTOMATIC, update=AUTOMATIC, delete=MANUAL")

    runner.run_test("distributionProfile.update — change automation settings", test_ftp_update_automation)

    def test_ftp_update_trigger():
        """Update distribution trigger setting."""
        pid = state.get("ftp_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "update", {
            "id": pid,
            "distributionProfile[objectType]": "KalturaFtpDistributionProfile",
            "distributionProfile[distributeTrigger]": 2,  # MODERATION_APPROVED
        })
        assert result.get("distributeTrigger") == 2, \
            f"Expected distributeTrigger=2 (MODERATION_APPROVED), got {result.get('distributeTrigger')}"
        print(f"    distributeTrigger=2 (MODERATION_APPROVED)")

    runner.run_test("distributionProfile.update — set distributeTrigger", test_ftp_update_trigger)

    def test_ftp_status_enable():
        """Enable the FTP profile via updateStatus."""
        pid = state.get("ftp_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "updateStatus", {
            "id": pid,
            "status": 2,  # ENABLED
        })
        assert result.get("status") == 2, f"Expected status=2 (ENABLED), got {result.get('status')}"
        print(f"    Enabled: status={result['status']}")

    runner.run_test("distributionProfile.updateStatus — enable profile", test_ftp_status_enable)

    def test_ftp_status_verify_enabled():
        """Verify enabled status persisted via get."""
        pid = state.get("ftp_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "get", {"id": pid})
        assert result.get("status") == 2, f"Expected status=2 (ENABLED), got {result.get('status')}"
        print(f"    Confirmed ENABLED via get")

    runner.run_test("distributionProfile.get — confirm enabled status", test_ftp_status_verify_enabled)

    def test_ftp_status_disable():
        """Disable the FTP profile via updateStatus."""
        pid = state.get("ftp_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "updateStatus", {
            "id": pid,
            "status": 1,  # DISABLED
        })
        assert result.get("status") == 1, f"Expected status=1 (DISABLED), got {result.get('status')}"
        print(f"    Disabled: status={result['status']}")

    runner.run_test("distributionProfile.updateStatus — disable profile", test_ftp_status_disable)

    def test_ftp_status_verify_disabled():
        """Verify disabled status persisted via get."""
        pid = state.get("ftp_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "get", {"id": pid})
        assert result.get("status") == 1, f"Expected status=1 (DISABLED), got {result.get('status')}"
        print(f"    Confirmed DISABLED via get")

    runner.run_test("distributionProfile.get — confirm disabled status", test_ftp_status_verify_disabled)

    def test_ftp_status_reenable():
        """Re-enable the FTP profile (toggle back to ENABLED)."""
        pid = state.get("ftp_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "updateStatus", {
            "id": pid,
            "status": 2,  # ENABLED
        })
        assert result.get("status") == 2, f"Expected status=2 (ENABLED), got {result.get('status')}"
        print(f"    Re-enabled: status={result['status']}")

    runner.run_test("distributionProfile.updateStatus — re-enable profile", test_ftp_status_reenable)

    def test_ftp_delete():
        """Delete the FTP profile."""
        pid = state.get("ftp_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        kaltura_post("contentDistribution_distributionProfile", "delete", {"id": pid})
        print(f"    Deleted profile: {pid}")
        # Remove from cleanup since we just deleted it
        runner._cleanup_actions = [
            (l, fn) for l, fn in runner._cleanup_actions
            if f"FTP profile {pid}" not in l
        ]

    runner.run_test("distributionProfile.delete — remove FTP profile", test_ftp_delete)

    def test_ftp_delete_verify():
        """Verify deleted FTP profile returns NOT_FOUND."""
        pid = state.get("ftp_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        try:
            kaltura_post("contentDistribution_distributionProfile", "get", {"id": pid})
            assert False, "Expected NOT_FOUND after delete"
        except Exception as e:
            assert "NOT_FOUND" in str(e).upper() or "not found" in str(e).lower(), \
                f"Expected NOT_FOUND error, got: {e}"
            print(f"    Confirmed deleted: {e}")

    runner.run_test("distributionProfile.get — verify NOT_FOUND after delete", test_ftp_delete_verify)

    # ════════════════════════════════════════════
    # Phase 3: Cross-Kaltura Profile Lifecycle
    # ════════════════════════════════════════════

    def test_crosskaltura_add():
        """Create a Cross-Kaltura distribution profile."""
        ts = int(time.time())
        result = _add_profile({
            "distributionProfile[objectType]": "KalturaCrossKalturaDistributionProfile",
            "distributionProfile[providerType]": "crossKalturaDistribution.CROSS_KALTURA",
            "distributionProfile[name]": f"E2E_CrossKaltura_{ts}",
            "distributionProfile[status]": 1,  # DISABLED
            "distributionProfile[targetServiceUrl]": "https://www.kaltura.com/api_v3",
            "distributionProfile[targetAccountId]": 12345,
            "distributionProfile[targetLoginId]": "test@example.com",
            "distributionProfile[targetLoginPassword]": "testpass",
            "distributionProfile[distributeCaptions]": "true",
            "distributionProfile[distributeCuePoints]": "true",
            "distributionProfile[distributeRemoteFlavorAssetContent]": "true",
            "distributionProfile[distributeRemoteThumbAssetContent]": "true",
        })
        assert "id" in result, f"Expected id in response: {result}"
        assert result.get("objectType") == "KalturaCrossKalturaDistributionProfile", \
            f"Expected objectType=KalturaCrossKalturaDistributionProfile, got {result.get('objectType')}"
        state["crosskaltura_profile_id"] = result["id"]
        runner.register_cleanup(f"CrossKaltura profile {result['id']}",
                                lambda: _delete_profile(state["crosskaltura_profile_id"]))
        print(f"    Created CrossKaltura profile: {result['id']}")

    runner.run_test("distributionProfile.add — create CrossKaltura profile", test_crosskaltura_add)

    def test_crosskaltura_verify_fields():
        """Verify Cross-Kaltura-specific fields on the created profile."""
        pid = state.get("crosskaltura_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "get", {"id": pid})
        assert result.get("partnerId") == int(PARTNER_ID), \
            f"Expected partnerId={PARTNER_ID}, got {result.get('partnerId')}"
        assert result.get("providerType") == "crossKalturaDistribution.CROSS_KALTURA", \
            f"Expected providerType=crossKalturaDistribution.CROSS_KALTURA, got {result.get('providerType')}"
        assert result.get("targetServiceUrl") == "https://www.kaltura.com/api_v3", \
            f"Expected targetServiceUrl, got {result.get('targetServiceUrl')}"
        assert result.get("targetAccountId") == 12345, \
            f"Expected targetAccountId=12345, got {result.get('targetAccountId')}"
        # Verify distribution flags
        assert "distributeCaptions" in result, f"Expected distributeCaptions in response"
        assert "distributeCuePoints" in result, f"Expected distributeCuePoints in response"
        assert "distributeRemoteFlavorAssetContent" in result, \
            f"Expected distributeRemoteFlavorAssetContent in response"
        assert "distributeRemoteThumbAssetContent" in result, \
            f"Expected distributeRemoteThumbAssetContent in response"
        print(f"    Verified CrossKaltura fields: targetServiceUrl, targetAccountId, "
              f"distributeCaptions, distributeCuePoints, flavor+thumb content")

    runner.run_test("distributionProfile.get — verify CrossKaltura fields", test_crosskaltura_verify_fields)

    def test_crosskaltura_update():
        """Update Cross-Kaltura profile target settings."""
        pid = state.get("crosskaltura_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "update", {
            "id": pid,
            "distributionProfile[objectType]": "KalturaCrossKalturaDistributionProfile",
            "distributionProfile[name]": f"E2E_CrossKaltura_Updated_{int(time.time())}",
            "distributionProfile[targetAccountId]": 67890,
        })
        assert result.get("targetAccountId") == 67890, \
            f"Expected targetAccountId=67890, got {result.get('targetAccountId')}"
        assert "Updated" in result.get("name", ""), \
            f"Expected updated name, got {result.get('name')}"
        print(f"    Updated: name={result['name']}, targetAccountId={result['targetAccountId']}")

    runner.run_test("distributionProfile.update — change CrossKaltura target", test_crosskaltura_update)

    def test_crosskaltura_delete():
        """Delete the CrossKaltura profile and verify."""
        pid = state.get("crosskaltura_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        kaltura_post("contentDistribution_distributionProfile", "delete", {"id": pid})
        try:
            kaltura_post("contentDistribution_distributionProfile", "get", {"id": pid})
            assert False, "Expected NOT_FOUND after delete"
        except Exception as e:
            assert "NOT_FOUND" in str(e).upper() or "not found" in str(e).lower(), \
                f"Expected NOT_FOUND error, got: {e}"
        print(f"    Deleted and verified: {pid}")
        runner._cleanup_actions = [
            (l, fn) for l, fn in runner._cleanup_actions
            if f"CrossKaltura profile {pid}" not in l
        ]

    runner.run_test("distributionProfile.delete — remove CrossKaltura profile", test_crosskaltura_delete)

    # ════════════════════════════════════════════
    # Phase 4: Profile Field Inspection
    # ════════════════════════════════════════════

    def test_inspect_add():
        """Create an FTP profile for detailed field inspection."""
        ts = int(time.time())
        result = _add_profile({
            "distributionProfile[objectType]": "KalturaFtpDistributionProfile",
            "distributionProfile[providerType]": "ftpDistribution.FTP",
            "distributionProfile[name]": f"E2E_Inspect_{ts}",
            "distributionProfile[status]": 2,  # ENABLED
            "distributionProfile[protocol]": 1,
            "distributionProfile[host]": "ftp.inspect.example.com",
            "distributionProfile[port]": 21,
            "distributionProfile[basePath]": "/inspect",
            "distributionProfile[username]": "inspector",
            "distributionProfile[password]": "pass",
            "distributionProfile[submitEnabled]": 3,  # MANUAL
            "distributionProfile[updateEnabled]": 2,  # AUTOMATIC
            "distributionProfile[deleteEnabled]": 1,  # DISABLED
            "distributionProfile[reportEnabled]": 1,  # DISABLED
            "distributionProfile[distributeTrigger]": 1,  # ENTRY_READY
        })
        assert "id" in result, f"Expected id: {result}"
        state["inspect_profile_id"] = result["id"]
        state["inspect_profile"] = result
        runner.register_cleanup(f"inspect profile {result['id']}",
                                lambda: _delete_profile(state["inspect_profile_id"]))
        print(f"    Created inspect profile: {result['id']}")

    runner.run_test("distributionProfile.add — create inspection profile", test_inspect_add)

    def test_inspect_base_fields():
        """Verify profile has all base distribution profile fields."""
        pid = state.get("inspect_profile_id")
        if not pid:
            print("    Skipped — no inspect profile")
            return
        p = kaltura_post("contentDistribution_distributionProfile", "get", {"id": pid})
        base_fields = ["id", "name", "status", "providerType", "submitEnabled",
                       "updateEnabled", "deleteEnabled", "reportEnabled",
                       "distributeTrigger", "partnerId", "createdAt", "updatedAt"]
        missing = [f for f in base_fields if f not in p]
        assert not missing, f"Missing base fields: {missing}"
        assert p.get("providerType") == "ftpDistribution.FTP", \
            f"Expected providerType=ftpDistribution.FTP, got {p.get('providerType')}"
        assert p.get("partnerId") == int(PARTNER_ID), \
            f"Expected partnerId={PARTNER_ID}, got {p.get('partnerId')}"
        print(f"    All base fields present: {', '.join(base_fields)}")

    runner.run_test("distributionProfile.get — base fields inspection", test_inspect_base_fields)

    def test_inspect_ftp_fields():
        """Verify FTP-specific fields: host, port, protocol, basePath, username."""
        pid = state.get("inspect_profile_id")
        if not pid:
            print("    Skipped — no inspect profile")
            return
        p = kaltura_post("contentDistribution_distributionProfile", "get", {"id": pid})
        ftp_fields = ["host", "port", "protocol", "basePath", "username"]
        missing = [f for f in ftp_fields if f not in p]
        assert not missing, f"Missing FTP fields: {missing}"
        assert p.get("host") == "ftp.inspect.example.com"
        assert p.get("port") == 21
        assert p.get("basePath") == "/inspect"
        print(f"    FTP fields: host={p.get('host')}, port={p.get('port')}, "
              f"basePath={p.get('basePath')}, username={p.get('username')}")

    runner.run_test("distributionProfile.get — FTP-specific fields", test_inspect_ftp_fields)

    def test_inspect_in_list():
        """Verify inspect profile appears in the profile list."""
        pid = state.get("inspect_profile_id")
        if not pid:
            print("    Skipped — no inspect profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "list", {})
        found = any(obj.get("id") == pid for obj in result.get("objects", []))
        assert found, f"Inspect profile {pid} not found in list"
        print(f"    Profile found in list of {result['totalCount']} profiles")

    runner.run_test("distributionProfile.list — inspect profile in results", test_inspect_in_list)

    # ════════════════════════════════════════════
    # Phase 5: Profile with Flavor/Thumb Requirements
    # ════════════════════════════════════════════

    def test_ftp_with_flavor_requirements():
        """Create an FTP profile with required and optional flavor params."""
        ts = int(time.time())
        result = _add_profile({
            "distributionProfile[objectType]": "KalturaFtpDistributionProfile",
            "distributionProfile[providerType]": "ftpDistribution.FTP",
            "distributionProfile[name]": f"E2E_FTP_Flavors_{ts}",
            "distributionProfile[status]": 1,
            "distributionProfile[protocol]": 1,
            "distributionProfile[host]": "ftp.example.com",
            "distributionProfile[port]": 21,
            "distributionProfile[basePath]": "/test",
            "distributionProfile[username]": "user",
            "distributionProfile[password]": "pass",
            "distributionProfile[requiredFlavorParamsIds]": "0",
            "distributionProfile[optionalFlavorParamsIds]": "487041,487071",
            "distributionProfile[autoCreateFlavors]": "true",
            "distributionProfile[autoCreateThumb]": "true",
        })
        assert "id" in result, f"Expected id: {result}"
        pid = result["id"]
        state["ftp_flavor_profile_id"] = pid
        runner.register_cleanup(f"FTP flavor profile {pid}",
                                lambda: _delete_profile(state["ftp_flavor_profile_id"]))
        # Verify flavor params persisted
        get_result = kaltura_post("contentDistribution_distributionProfile", "get", {"id": pid})
        assert get_result.get("requiredFlavorParamsIds") == "0", \
            f"Expected requiredFlavorParamsIds='0', got {get_result.get('requiredFlavorParamsIds')}"
        assert get_result.get("optionalFlavorParamsIds") == "487041,487071", \
            f"Expected optionalFlavorParamsIds='487041,487071', got {get_result.get('optionalFlavorParamsIds')}"
        print(f"    Created with requiredFlavors='0', optionalFlavors='487041,487071', "
              f"autoCreateFlavors=true, autoCreateThumb=true")

    runner.run_test("distributionProfile.add — with flavor requirements", test_ftp_with_flavor_requirements)

    def test_ftp_update_flavor_requirements():
        """Update flavor requirements on an existing profile."""
        pid = state.get("ftp_flavor_profile_id")
        if not pid:
            print("    Skipped — no profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "update", {
            "id": pid,
            "distributionProfile[objectType]": "KalturaFtpDistributionProfile",
            "distributionProfile[requiredFlavorParamsIds]": "0,487041",
            "distributionProfile[optionalFlavorParamsIds]": "487071",
        })
        assert result.get("requiredFlavorParamsIds") == "0,487041", \
            f"Expected requiredFlavorParamsIds='0,487041', got {result.get('requiredFlavorParamsIds')}"
        assert result.get("optionalFlavorParamsIds") == "487071", \
            f"Expected optionalFlavorParamsIds='487071', got {result.get('optionalFlavorParamsIds')}"
        print(f"    Updated: required='0,487041', optional='487071'")

    runner.run_test("distributionProfile.update — change flavor requirements", test_ftp_update_flavor_requirements)

    def test_ftp_flavor_profile_cleanup():
        """Delete the flavor-requirements profile."""
        pid = state.get("ftp_flavor_profile_id")
        if not pid:
            print("    Skipped — no profile")
            return
        kaltura_post("contentDistribution_distributionProfile", "delete", {"id": pid})
        print(f"    Deleted flavor profile: {pid}")
        runner._cleanup_actions = [
            (l, fn) for l, fn in runner._cleanup_actions
            if f"FTP flavor profile {pid}" not in l
        ]

    runner.run_test("distributionProfile.delete — cleanup flavor profile", test_ftp_flavor_profile_cleanup)

    # ════════════════════════════════════════════
    # Phase 6: Profile with Sunrise/Sunset Defaults
    # ════════════════════════════════════════════

    def test_ftp_with_sunrise_sunset():
        """Create an FTP profile with default sunrise/sunset offsets."""
        ts = int(time.time())
        result = _add_profile({
            "distributionProfile[objectType]": "KalturaFtpDistributionProfile",
            "distributionProfile[providerType]": "ftpDistribution.FTP",
            "distributionProfile[name]": f"E2E_FTP_SunriseSunset_{ts}",
            "distributionProfile[status]": 1,
            "distributionProfile[protocol]": 1,
            "distributionProfile[host]": "ftp.example.com",
            "distributionProfile[port]": 21,
            "distributionProfile[basePath]": "/test",
            "distributionProfile[username]": "user",
            "distributionProfile[password]": "pass",
            "distributionProfile[sunriseDefaultOffset]": 3600,  # 1 hour
            "distributionProfile[sunsetDefaultOffset]": 604800,  # 7 days
        })
        assert "id" in result, f"Expected id: {result}"
        pid = result["id"]
        state["ftp_sunset_profile_id"] = pid
        runner.register_cleanup(f"FTP sunset profile {pid}",
                                lambda: _delete_profile(state["ftp_sunset_profile_id"]))
        get_result = kaltura_post("contentDistribution_distributionProfile", "get", {"id": pid})
        assert get_result.get("sunriseDefaultOffset") == 3600, \
            f"Expected sunriseDefaultOffset=3600, got {get_result.get('sunriseDefaultOffset')}"
        assert get_result.get("sunsetDefaultOffset") == 604800, \
            f"Expected sunsetDefaultOffset=604800, got {get_result.get('sunsetDefaultOffset')}"
        print(f"    Sunrise offset: 3600s (1h), Sunset offset: 604800s (7d)")

    runner.run_test("distributionProfile.add — with sunrise/sunset offsets", test_ftp_with_sunrise_sunset)

    def test_ftp_sunset_profile_cleanup():
        """Delete the sunrise/sunset profile."""
        pid = state.get("ftp_sunset_profile_id")
        if not pid:
            print("    Skipped — no profile")
            return
        kaltura_post("contentDistribution_distributionProfile", "delete", {"id": pid})
        print(f"    Deleted sunset profile: {pid}")
        runner._cleanup_actions = [
            (l, fn) for l, fn in runner._cleanup_actions
            if f"FTP sunset profile {pid}" not in l
        ]

    runner.run_test("distributionProfile.delete — cleanup sunset profile", test_ftp_sunset_profile_cleanup)

    # ════════════════════════════════════════════
    # Phase 7: List Filters
    # ════════════════════════════════════════════

    def test_list_all():
        """List all distribution profiles (no filter)."""
        result = kaltura_post("contentDistribution_distributionProfile", "list", {})
        assert "totalCount" in result, f"Expected totalCount: {result}"
        assert "objects" in result, f"Expected objects: {result}"
        state["total_profiles"] = result["totalCount"]
        print(f"    Total profiles: {result['totalCount']}")

    runner.run_test("distributionProfile.list — all profiles", test_list_all)

    def test_list_filter_enabled():
        """List profiles filtered by status=ENABLED."""
        result = kaltura_post("contentDistribution_distributionProfile", "list", {
            "filter[objectType]": "KalturaDistributionProfileFilter",
            "filter[statusEqual]": 2,
        })
        for obj in result.get("objects", []):
            assert obj.get("status") == 2, \
                f"Filter leak: expected status=2, got {obj.get('status')} on profile {obj.get('id')}"
        print(f"    Enabled profiles: {result.get('totalCount', 0)}")

    runner.run_test("distributionProfile.list — filter status=ENABLED", test_list_filter_enabled)

    def test_list_filter_disabled():
        """List profiles filtered by status=DISABLED."""
        result = kaltura_post("contentDistribution_distributionProfile", "list", {
            "filter[objectType]": "KalturaDistributionProfileFilter",
            "filter[statusEqual]": 1,
        })
        for obj in result.get("objects", []):
            assert obj.get("status") == 1, \
                f"Filter leak: expected status=1, got {obj.get('status')} on profile {obj.get('id')}"
        print(f"    Disabled profiles: {result.get('totalCount', 0)}")

    runner.run_test("distributionProfile.list — filter status=DISABLED", test_list_filter_disabled)

    def test_list_with_pager():
        """List profiles with explicit pager (pageSize=1)."""
        result = kaltura_post("contentDistribution_distributionProfile", "list", {
            "pager[objectType]": "KalturaFilterPager",
            "pager[pageSize]": 1,
            "pager[pageIndex]": 1,
        })
        objects = result.get("objects", [])
        assert result.get("totalCount", 0) >= 1, \
            f"Expected totalCount >= 1, got {result.get('totalCount')}"
        print(f"    Page 1 (size=1): {len(objects)} results, "
              f"totalCount={result.get('totalCount')}")

    runner.run_test("distributionProfile.list — pagination (pageSize=1)", test_list_with_pager)

    # ════════════════════════════════════════════
    # Phase 8: Error Handling
    # ════════════════════════════════════════════

    def test_get_nonexistent():
        """Verify NOT_FOUND for non-existent profile ID."""
        try:
            kaltura_post("contentDistribution_distributionProfile", "get", {"id": 999999999})
            assert False, "Expected error for non-existent profile"
        except Exception as e:
            assert "NOT_FOUND" in str(e).upper() or "not found" in str(e).lower(), \
                f"Expected NOT_FOUND: {e}"
            print(f"    Correct error: {e}")

    runner.run_test("distributionProfile.get — NOT_FOUND error", test_get_nonexistent)

    def test_update_nonexistent():
        """Verify error for updating non-existent profile."""
        try:
            kaltura_post("contentDistribution_distributionProfile", "update", {
                "id": 999999999,
                "distributionProfile[objectType]": "KalturaFtpDistributionProfile",
                "distributionProfile[name]": "should_fail",
            })
            assert False, "Expected error for non-existent profile"
        except Exception as e:
            assert "NOT_FOUND" in str(e).upper() or "not found" in str(e).lower(), \
                f"Expected NOT_FOUND: {e}"
            print(f"    Correct error: {e}")

    runner.run_test("distributionProfile.update — NOT_FOUND error", test_update_nonexistent)

    def test_delete_nonexistent():
        """Verify error for deleting non-existent profile."""
        try:
            kaltura_post("contentDistribution_distributionProfile", "delete", {"id": 999999999})
            assert False, "Expected error for non-existent profile"
        except Exception as e:
            assert "NOT_FOUND" in str(e).upper() or "not found" in str(e).lower(), \
                f"Expected NOT_FOUND: {e}"
            print(f"    Correct error: {e}")

    runner.run_test("distributionProfile.delete — NOT_FOUND error", test_delete_nonexistent)

    def test_updatestatus_nonexistent():
        """Verify error for updateStatus on non-existent profile."""
        try:
            kaltura_post("contentDistribution_distributionProfile", "updateStatus", {
                "id": 999999999,
                "status": 2,
            })
            assert False, "Expected error for non-existent profile"
        except Exception as e:
            assert "NOT_FOUND" in str(e).upper() or "not found" in str(e).lower(), \
                f"Expected NOT_FOUND: {e}"
            print(f"    Correct error: {e}")

    runner.run_test("distributionProfile.updateStatus — NOT_FOUND error", test_updatestatus_nonexistent)

    def test_add_missing_required_fields():
        """Verify error when creating profile without required objectType."""
        try:
            url = f"{SERVICE_URL}/service/contentDistribution_distributionProfile/action/add"
            resp = requests.post(url, data={
                "ks": KS,
                "format": 1,
                "partnerId": PARTNER_ID,
                "distributionProfile[name]": "should_fail",
            }, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            if isinstance(result, dict) and result.get("objectType") == "KalturaAPIException":
                raise Exception(f"Kaltura API error: {result.get('message')} (code: {result.get('code')})")
            # If we get here, the API accepted it — verify and clean up
            if "id" in result:
                _delete_profile(result["id"])
            assert False, f"Expected error for missing objectType, but got: {result}"
        except Exception as e:
            if "Expected error" in str(e):
                raise
            print(f"    Correct error: {e}")

    runner.run_test("distributionProfile.add — missing objectType error", test_add_missing_required_fields)

    # ════════════════════════════════════════════
    # Phase 9: Second FTP Profile (Concurrent Profiles)
    # ════════════════════════════════════════════

    def test_concurrent_profiles():
        """Create a second FTP profile and verify both appear in list."""
        ts = int(time.time())
        result1 = _add_profile({
            "distributionProfile[objectType]": "KalturaFtpDistributionProfile",
            "distributionProfile[providerType]": "ftpDistribution.FTP",
            "distributionProfile[name]": f"E2E_FTP_A_{ts}",
            "distributionProfile[status]": 1,
            "distributionProfile[protocol]": 1,
            "distributionProfile[host]": "ftp-a.example.com",
            "distributionProfile[port]": 21,
            "distributionProfile[basePath]": "/a",
            "distributionProfile[username]": "a",
            "distributionProfile[password]": "a",
        })
        pid1 = result1["id"]
        runner.register_cleanup(f"concurrent profile A {pid1}",
                                lambda: _delete_profile(pid1))

        result2 = _add_profile({
            "distributionProfile[objectType]": "KalturaFtpDistributionProfile",
            "distributionProfile[providerType]": "ftpDistribution.FTP",
            "distributionProfile[name]": f"E2E_FTP_B_{ts}",
            "distributionProfile[status]": 1,
            "distributionProfile[protocol]": 1,
            "distributionProfile[host]": "ftp-b.example.com",
            "distributionProfile[port]": 21,
            "distributionProfile[basePath]": "/b",
            "distributionProfile[username]": "b",
            "distributionProfile[password]": "b",
        })
        pid2 = result2["id"]
        runner.register_cleanup(f"concurrent profile B {pid2}",
                                lambda: _delete_profile(pid2))

        # Verify both appear in list
        list_result = kaltura_post("contentDistribution_distributionProfile", "list", {})
        ids_in_list = {obj.get("id") for obj in list_result.get("objects", [])}
        assert pid1 in ids_in_list, f"Profile A ({pid1}) not in list"
        assert pid2 in ids_in_list, f"Profile B ({pid2}) not in list"
        print(f"    Created two profiles: A={pid1}, B={pid2}, both in list")

        # Clean up
        kaltura_post("contentDistribution_distributionProfile", "delete", {"id": pid1})
        kaltura_post("contentDistribution_distributionProfile", "delete", {"id": pid2})
        runner._cleanup_actions = [
            (l, fn) for l, fn in runner._cleanup_actions
            if f"concurrent profile" not in l
        ]
        print(f"    Cleaned up both profiles")

    runner.run_test("distributionProfile — multiple concurrent profiles", test_concurrent_profiles)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════
    keep = "--keep" in sys.argv
    if keep:
        print("\n--- Keeping resources (--keep flag) ---")
        for key, val in state.items():
            if "profile_id" in key:
                print(f"  {key}: {val}")
        print("  Run without --keep to clean up, or delete manually.")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up test resources...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

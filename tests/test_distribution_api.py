#!/usr/bin/env python3
"""End-to-end validation of the Content Distribution API.
Covers: distributionProvider.list, distributionProfile CRUD,
entryDistribution lifecycle (add, validate, get, list, update, submitAdd, serveSentData,
serveReturnedData, delete), genericDistributionProvider CRUD,
genericDistributionProviderAction CRUD (with XSLT/XSD/XPath uploads), error handling."""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(__file__))
from test_helpers import kaltura_post, create_test_entry, delete_test_entry, TestRunner, PARTNER_ID, KS, SERVICE_URL

state = {}


def _add_profile(profile_data):
    """Create a distribution profile using direct requests.post with partnerId."""
    url = f"{SERVICE_URL}/service/contentDistribution_distributionProfile/action/add"
    data = {"ks": KS, "format": 1, "partnerId": PARTNER_ID}
    data.update(profile_data)
    resp = requests.post(url, data=data, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    if isinstance(result, dict) and result.get("objectType") == "KalturaAPIException":
        raise Exception(f"Kaltura API error: {result.get('message')} (code: {result.get('code')})")
    return result


def main():
    runner = TestRunner("Content Distribution API — E2E Validation")

    # ════════════════════════════════════════════
    # Phase 1: Distribution Provider Discovery
    # ════════════════════════════════════════════

    def test_provider_list():
        """List available distribution provider types."""
        result = kaltura_post("contentDistribution_distributionProvider", "list", {})
        assert "objects" in result, f"Expected objects in response: {result}"
        assert "totalCount" in result, f"Expected totalCount in response: {result}"
        assert result["totalCount"] > 0, f"Expected at least 1 provider, got {result['totalCount']}"
        state["provider_count"] = result["totalCount"]
        print(f"    Providers available: {result['totalCount']}")

    runner.run_test("distributionProvider.list — available providers", test_provider_list)

    def test_provider_types():
        """Verify expected provider types exist (generic, syndication, FTP)."""
        result = kaltura_post("contentDistribution_distributionProvider", "list", {})
        objects = result.get("objects", [])
        types_found = set()
        for obj in objects:
            ptype = obj.get("type")
            if ptype:
                types_found.add(str(ptype))
        assert "1" in types_found, f"Generic provider (type=1) not found in {types_found}"
        assert "2" in types_found, f"Syndication provider (type=2) not found in {types_found}"
        assert "ftpDistribution.FTP" in types_found, \
            f"FTP provider not found in {types_found}"
        print(f"    Found generic, syndication, FTP providers")

    runner.run_test("distributionProvider.list — verify key provider types", test_provider_types)

    # ════════════════════════════════════════════
    # Phase 2: Distribution Profile CRUD
    # ════════════════════════════════════════════

    def test_profile_list():
        """List distribution profiles on the account."""
        result = kaltura_post("contentDistribution_distributionProfile", "list", {})
        assert "objects" in result, f"Expected objects: {result}"
        assert "totalCount" in result, f"Expected totalCount: {result}"
        state["profile_count"] = result["totalCount"]
        print(f"    Profiles: {result['totalCount']}")

    runner.run_test("distributionProfile.list — list profiles", test_profile_list)

    def test_profile_list_filter_status():
        """List distribution profiles filtered by status."""
        result = kaltura_post("contentDistribution_distributionProfile", "list", {
            "filter[objectType]": "KalturaDistributionProfileFilter",
            "filter[statusEqual]": 2,
        })
        assert "objects" in result, f"Expected objects: {result}"
        for obj in result.get("objects", []):
            assert obj.get("status") == 2, f"Expected status=2, got {obj.get('status')}"
        print(f"    Enabled profiles: {result['totalCount']}")

    runner.run_test("distributionProfile.list — filter by status=ENABLED", test_profile_list_filter_status)

    def test_profile_add():
        """Create an FTP distribution profile (requires partnerId in request)."""
        result = _add_profile({
            "distributionProfile[objectType]": "KalturaFtpDistributionProfile",
            "distributionProfile[providerType]": "ftpDistribution.FTP",
            "distributionProfile[name]": f"API_Test_FTP_{int(time.time())}",
            "distributionProfile[status]": 2,  # ENABLED
            "distributionProfile[protocol]": 1,  # FTP
            "distributionProfile[host]": "ftp.example.com",
            "distributionProfile[port]": 21,
            "distributionProfile[basePath]": "/test",
            "distributionProfile[username]": "testuser",
            "distributionProfile[password]": "testpass",
        })
        assert "id" in result, f"Expected id in response: {result}"
        assert result.get("partnerId") == int(PARTNER_ID), (
            f"Expected partnerId={PARTNER_ID}, got {result.get('partnerId')}"
        )
        state["created_profile_id"] = result["id"]
        runner.register_cleanup(f"created profile {result['id']}",
                                lambda: _delete_profile(state["created_profile_id"]))
        print(f"    Created profile: {result['id']}, partnerId={result['partnerId']}")

    runner.run_test("distributionProfile.add — create FTP profile", test_profile_add)

    def test_profile_get():
        """Retrieve the created FTP profile by ID and verify fields."""
        pid = state.get("created_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "get", {
            "id": pid,
        })
        assert result.get("id") == pid, f"Expected id={pid}, got {result.get('id')}"
        assert "providerType" in result, f"Expected providerType in response: {result}"
        assert "name" in result, f"Expected name in response: {result}"
        assert "status" in result, f"Expected status in response: {result}"
        assert result.get("objectType") == "KalturaFtpDistributionProfile", \
            f"Expected KalturaFtpDistributionProfile, got {result.get('objectType')}"
        assert "submitEnabled" in result, f"Expected submitEnabled: {list(result.keys())}"
        assert "distributeTrigger" in result, f"Expected distributeTrigger: {list(result.keys())}"
        print(f"    Profile: {result['name']}, provider={result['providerType']}, status={result['status']}")

    runner.run_test("distributionProfile.get — FTP profile details and fields", test_profile_get)

    def test_profile_update():
        """Update the created distribution profile name."""
        pid = state.get("created_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "update", {
            "id": pid,
            "distributionProfile[objectType]": "KalturaFtpDistributionProfile",
            "distributionProfile[name]": f"API_Test_FTP_Updated_{int(time.time())}",
        })
        assert "Updated" in result.get("name", ""), f"Expected updated name, got {result.get('name')}"
        print(f"    Updated: name={result['name']}")

    runner.run_test("distributionProfile.update — change name", test_profile_update)

    def test_profile_update_status():
        """Disable then re-enable the created distribution profile."""
        pid = state.get("created_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        result = kaltura_post("contentDistribution_distributionProfile", "updateStatus", {
            "id": pid,
            "status": 1,  # DISABLED
        })
        assert result.get("status") == 1, f"Expected status=1, got {result.get('status')}"
        result = kaltura_post("contentDistribution_distributionProfile", "updateStatus", {
            "id": pid,
            "status": 2,  # ENABLED
        })
        assert result.get("status") == 2, f"Expected status=2, got {result.get('status')}"
        print(f"    Toggled DISABLED→ENABLED: status={result['status']}")

    runner.run_test("distributionProfile.updateStatus — toggle status", test_profile_update_status)

    # ════════════════════════════════════════════
    # Phase 3: Entry Distribution Lifecycle
    # ════════════════════════════════════════════

    def test_create_test_entry():
        """Create a test media entry for distribution testing."""
        entry_id = create_test_entry()
        state["test_entry_id"] = entry_id
        runner.register_cleanup(f"test entry {entry_id}",
                                lambda: delete_test_entry(entry_id))
        print(f"    Entry: {entry_id}")

    runner.run_test("media.add — create test entry", test_create_test_entry)

    def test_entry_distribution_add():
        """Bind test entry to our FTP distribution profile."""
        result = kaltura_post("contentDistribution_entryDistribution", "add", {
            "entryDistribution[objectType]": "KalturaEntryDistribution",
            "entryDistribution[entryId]": state["test_entry_id"],
            "entryDistribution[distributionProfileId]": state["created_profile_id"],
        })
        assert "id" in result, f"Expected id in response: {result}"
        assert result.get("entryId") == state["test_entry_id"], \
            f"Expected entryId={state['test_entry_id']}, got {result.get('entryId')}"
        assert result.get("status") == 0, f"Expected PENDING status=0, got {result.get('status')}"
        state["entry_dist_id"] = result["id"]
        runner.register_cleanup(f"entry distribution {result['id']}",
                                lambda: _delete_entry_distribution(result["id"]))
        print(f"    EntryDistribution: id={result['id']}, status={result['status']} (PENDING)")

    runner.run_test("entryDistribution.add — bind entry to profile", test_entry_distribution_add)

    def test_entry_distribution_validate():
        """Validate entry against distribution profile requirements."""
        result = kaltura_post("contentDistribution_entryDistribution", "validate", {
            "id": state["entry_dist_id"],
        })
        assert "validationErrors" in result, f"Expected validationErrors: {result}"
        errors = result["validationErrors"]
        state["validation_error_count"] = len(errors)
        if errors:
            error_types = [e.get("objectType", "?") for e in errors]
            print(f"    Validation errors: {len(errors)} — {error_types}")
        else:
            print(f"    No validation errors (profile has no required flavors)")

    runner.run_test("entryDistribution.validate — check requirements", test_entry_distribution_validate)

    def test_entry_distribution_get():
        """Retrieve entry distribution by ID."""
        result = kaltura_post("contentDistribution_entryDistribution", "get", {
            "id": state["entry_dist_id"],
        })
        assert result.get("id") == state["entry_dist_id"], \
            f"Expected id={state['entry_dist_id']}, got {result.get('id')}"
        assert "entryId" in result, f"Expected entryId: {result}"
        assert "distributionProfileId" in result, f"Expected distributionProfileId: {result}"
        assert "status" in result, f"Expected status: {result}"
        print(f"    Got: id={result['id']}, entry={result['entryId']}, status={result['status']}")

    runner.run_test("entryDistribution.get — retrieve by ID", test_entry_distribution_get)

    def test_entry_distribution_list_by_entry():
        """List entry distributions filtered by entry ID."""
        result = kaltura_post("contentDistribution_entryDistribution", "list", {
            "filter[objectType]": "KalturaEntryDistributionFilter",
            "filter[entryIdEqual]": state["test_entry_id"],
        })
        assert result.get("totalCount", 0) >= 1, \
            f"Expected at least 1 distribution for entry, got {result.get('totalCount')}"
        found = any(obj.get("id") == state["entry_dist_id"] for obj in result.get("objects", []))
        assert found, f"Expected entry_dist_id={state['entry_dist_id']} in results"
        print(f"    Found {result['totalCount']} distributions for entry {state['test_entry_id']}")

    runner.run_test("entryDistribution.list — filter by entryId", test_entry_distribution_list_by_entry)

    def test_entry_distribution_list_by_profile():
        """List entry distributions filtered by distribution profile ID."""
        result = kaltura_post("contentDistribution_entryDistribution", "list", {
            "filter[objectType]": "KalturaEntryDistributionFilter",
            "filter[distributionProfileIdEqual]": state["created_profile_id"],
        })
        assert result.get("totalCount", 0) >= 1, \
            f"Expected at least 1 distribution for profile, got {result.get('totalCount')}"
        print(f"    Found {result['totalCount']} distributions for profile {state['created_profile_id']}")

    runner.run_test("entryDistribution.list — filter by profileId", test_entry_distribution_list_by_profile)

    def test_entry_distribution_list_by_status():
        """List entry distributions filtered by status."""
        result = kaltura_post("contentDistribution_entryDistribution", "list", {
            "filter[objectType]": "KalturaEntryDistributionFilter",
            "filter[statusEqual]": 0,
        })
        assert "totalCount" in result, f"Expected totalCount: {result}"
        assert result["totalCount"] >= 1, \
            f"Expected at least 1 PENDING distribution, got {result['totalCount']}"
        print(f"    PENDING distributions: {result['totalCount']}")

    runner.run_test("entryDistribution.list — filter by status=PENDING", test_entry_distribution_list_by_status)

    def test_entry_distribution_update():
        """Update entry distribution sunrise/sunset timestamps."""
        future_sunrise = int(time.time()) + 86400
        future_sunset = int(time.time()) + 172800
        result = kaltura_post("contentDistribution_entryDistribution", "update", {
            "id": state["entry_dist_id"],
            "entryDistribution[objectType]": "KalturaEntryDistribution",
            "entryDistribution[sunrise]": future_sunrise,
            "entryDistribution[sunset]": future_sunset,
        })
        assert result.get("sunrise") == future_sunrise, \
            f"Expected sunrise={future_sunrise}, got {result.get('sunrise')}"
        assert result.get("sunset") == future_sunset, \
            f"Expected sunset={future_sunset}, got {result.get('sunset')}"
        print(f"    Updated: sunrise={result['sunrise']}, sunset={result['sunset']}")

    runner.run_test("entryDistribution.update — set sunrise/sunset", test_entry_distribution_update)

    def test_entry_distribution_submit_add():
        """Submit entry distribution to remote platform (queues for processing)."""
        result = kaltura_post("contentDistribution_entryDistribution", "submitAdd", {
            "id": state["entry_dist_id"],
            "submitWhenReady": "true",
        })
        assert result.get("id") == state["entry_dist_id"], \
            f"Expected id={state['entry_dist_id']}, got {result.get('id')}"
        status_names = {0: "PENDING", 1: "QUEUED", 4: "SUBMITTING", 7: "ERROR_SUBMITTING"}
        status = result.get("status")
        assert status in [0, 1, 4, 7], \
            f"Expected valid distribution status, got {status}"
        state["post_submit_status"] = status
        print(f"    Submitted: status={status} ({status_names.get(status, 'UNKNOWN')})")

    runner.run_test("entryDistribution.submitAdd — submit to remote", test_entry_distribution_submit_add)

    # ════════════════════════════════════════════
    # Phase 4: Distribution Debugging
    # ════════════════════════════════════════════

    def test_serve_sent_data():
        """Retrieve raw XML sent to remote platform (empty for pending)."""
        url = f"{SERVICE_URL}/service/contentDistribution_entryDistribution/action/serveSentData"
        resp = requests.post(url, data={
            "ks": KS, "format": 1,
            "id": state["entry_dist_id"],
            "actionType": 1,
        }, timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print(f"    serveSentData: status={resp.status_code}, body_len={len(resp.content)}")

    runner.run_test("entryDistribution.serveSentData — debug XML (SUBMIT)", test_serve_sent_data)

    def test_serve_returned_data():
        """Retrieve raw XML returned from remote platform (empty for pending)."""
        url = f"{SERVICE_URL}/service/contentDistribution_entryDistribution/action/serveReturnedData"
        resp = requests.post(url, data={
            "ks": KS, "format": 1,
            "id": state["entry_dist_id"],
            "actionType": 1,
        }, timeout=30)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        print(f"    serveReturnedData: status={resp.status_code}, body_len={len(resp.content)}")

    runner.run_test("entryDistribution.serveReturnedData — debug XML (SUBMIT)", test_serve_returned_data)

    # ════════════════════════════════════════════
    # Phase 5: Existing Distribution Inspection
    # ════════════════════════════════════════════

    def test_list_all_distributions():
        """List all entry distributions on the account."""
        result = kaltura_post("contentDistribution_entryDistribution", "list", {})
        assert "totalCount" in result, f"Expected totalCount: {result}"
        assert result["totalCount"] >= 1, f"Expected at least 1 distribution, got {result['totalCount']}"
        state["total_distributions"] = result["totalCount"]
        for obj in result.get("objects", [])[:5]:
            status_name = {0: "PENDING", 1: "QUEUED", 2: "READY", 3: "DELETED",
                           7: "ERROR_SUBMITTING"}.get(obj.get("status"), str(obj.get("status")))
            remote = f", remoteId={obj['remoteId']}" if obj.get("remoteId") else ""
            print(f"    id={obj['id']}, entry={obj['entryId']}, status={status_name}{remote}")

    runner.run_test("entryDistribution.list — all distributions", test_list_all_distributions)

    def test_ready_distribution():
        """Verify a READY distribution has a remoteId (external platform ID)."""
        result = kaltura_post("contentDistribution_entryDistribution", "list", {
            "filter[objectType]": "KalturaEntryDistributionFilter",
            "filter[statusEqual]": 2,
        })
        ready_dists = result.get("objects", [])
        if not ready_dists:
            print("    No READY distributions on account — skipping remoteId check")
            return
        dist = ready_dists[0]
        assert dist.get("remoteId"), f"Expected remoteId on READY distribution: {dist}"
        state["ready_dist_id"] = dist["id"]
        print(f"    READY: id={dist['id']}, remoteId={dist['remoteId']}")

    runner.run_test("entryDistribution.list — READY distribution has remoteId", test_ready_distribution)

    # ════════════════════════════════════════════
    # Phase 6: Generic Distribution Provider CRUD
    # ════════════════════════════════════════════

    def test_generic_provider_add():
        """Create a custom generic distribution provider.
        The genericDistributionProvider service may require additional account-level
        permissions beyond the base Content Distribution plugin. If SERVICE_FORBIDDEN
        is returned, remaining generic provider tests are skipped."""
        try:
            result = kaltura_post("contentDistribution_genericDistributionProvider", "add", {
                "genericDistributionProvider[name]": f"API_Test_Generic_{int(time.time())}",
                "genericDistributionProvider[isDefault]": "false",
                "genericDistributionProvider[requiredFlavorParamsIds]": "0",
            })
        except Exception as e:
            if "SERVICE_FORBIDDEN" in str(e):
                state["generic_provider_forbidden"] = True
                print("    genericDistributionProvider service not enabled on this account")
                print("    Contact your Kaltura account manager to enable Generic Distribution")
                return
            raise
        assert "id" in result, f"Expected id in response: {result}"
        assert result.get("objectType") == "KalturaGenericDistributionProvider", \
            f"Expected KalturaGenericDistributionProvider, got {result.get('objectType')}"
        assert result.get("status") == 1, f"Expected status=1 (ACTIVE), got {result.get('status')}"
        state["generic_provider_id"] = result["id"]
        runner.register_cleanup(f"generic provider {result['id']}",
                                lambda: _delete_generic_provider(state["generic_provider_id"]))
        print(f"    Created generic provider: {result['id']}, name={result['name']}")

    runner.run_test("genericDistributionProvider.add — create custom provider", test_generic_provider_add)

    def test_generic_provider_get():
        """Retrieve the created generic provider by ID."""
        pid = state.get("generic_provider_id")
        if not pid:
            if state.get("generic_provider_forbidden"):
                print("    Skipped — service not enabled on this account")
            else:
                print("    Skipped — no created provider")
            return
        result = kaltura_post("contentDistribution_genericDistributionProvider", "get", {"id": pid})
        assert result.get("id") == pid, f"Expected id={pid}, got {result.get('id')}"
        assert result.get("requiredFlavorParamsIds") == "0", \
            f"Expected requiredFlavorParamsIds='0', got {result.get('requiredFlavorParamsIds')}"
        assert result.get("partnerId") == int(PARTNER_ID), \
            f"Expected partnerId={PARTNER_ID}, got {result.get('partnerId')}"
        print(f"    Got provider: id={result['id']}, name={result['name']}")

    runner.run_test("genericDistributionProvider.get — retrieve by ID", test_generic_provider_get)

    def test_generic_provider_list():
        """List generic distribution providers."""
        if state.get("generic_provider_forbidden"):
            print("    Skipped — service not enabled on this account")
            return
        result = kaltura_post("contentDistribution_genericDistributionProvider", "list", {})
        assert "totalCount" in result, f"Expected totalCount: {result}"
        pid = state.get("generic_provider_id")
        if pid:
            found = any(obj.get("id") == pid for obj in result.get("objects", []))
            assert found, f"Created provider {pid} not in list"
        print(f"    Generic providers: {result['totalCount']}")

    runner.run_test("genericDistributionProvider.list — list providers", test_generic_provider_list)

    def test_generic_provider_update():
        """Update the generic provider name."""
        pid = state.get("generic_provider_id")
        if not pid:
            if state.get("generic_provider_forbidden"):
                print("    Skipped — service not enabled on this account")
            else:
                print("    Skipped — no created provider")
            return
        new_name = f"API_Test_Generic_Updated_{int(time.time())}"
        result = kaltura_post("contentDistribution_genericDistributionProvider", "update", {
            "id": pid,
            "genericDistributionProvider[name]": new_name,
        })
        assert result.get("name") == new_name, f"Expected name={new_name}, got {result.get('name')}"
        print(f"    Updated: name={result['name']}")

    runner.run_test("genericDistributionProvider.update — change name", test_generic_provider_update)

    def test_generic_provider_action_add():
        """Create a SUBMIT action for the generic provider."""
        pid = state.get("generic_provider_id")
        if not pid:
            if state.get("generic_provider_forbidden"):
                print("    Skipped — service not enabled on this account")
            else:
                print("    Skipped — no created provider")
            return
        result = kaltura_post("contentDistribution_genericDistributionProviderAction", "add", {
            "genericDistributionProviderAction[genericDistributionProviderId]": pid,
            "genericDistributionProviderAction[action]": 1,  # SUBMIT
            "genericDistributionProviderAction[protocol]": 3,  # SFTP
            "genericDistributionProviderAction[serverAddress]": "sftp.example.com",
            "genericDistributionProviderAction[remotePath]": "/ingest/incoming",
            "genericDistributionProviderAction[remoteUsername]": "testuser",
            "genericDistributionProviderAction[remotePassword]": "testpass",
        })
        assert "id" in result, f"Expected id in response: {result}"
        assert result.get("action") == 1, f"Expected action=1 (SUBMIT), got {result.get('action')}"
        assert result.get("protocol") == 3, f"Expected protocol=3 (SFTP), got {result.get('protocol')}"
        assert result.get("genericDistributionProviderId") == pid, \
            f"Expected genericDistributionProviderId={pid}, got {result.get('genericDistributionProviderId')}"
        state["generic_action_id"] = result["id"]
        runner.register_cleanup(f"generic action {result['id']}",
                                lambda: _delete_generic_action(state["generic_action_id"]))
        print(f"    Created SUBMIT action: {result['id']}, protocol=SFTP")

    runner.run_test("genericDistributionProviderAction.add — create SUBMIT action", test_generic_provider_action_add)

    def test_generic_action_add_mrss_transform():
        """Upload an MRSS transform XSLT to the action."""
        aid = state.get("generic_action_id")
        if not aid:
            print("    Skipped — " + ("service not enabled" if state.get("generic_provider_forbidden") else "no created action"))
            return
        xsl = '''<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="xml" indent="yes"/>
  <xsl:template match="/">
    <item>
      <title><xsl:value-of select="//item/title"/></title>
      <description><xsl:value-of select="//item/description"/></description>
    </item>
  </xsl:template>
</xsl:stylesheet>'''
        result = kaltura_post("contentDistribution_genericDistributionProviderAction", "addMrssTransform", {
            "id": aid,
            "xslData": xsl,
        })
        assert result.get("id") == aid, f"Expected id={aid}, got {result.get('id')}"
        assert result.get("mrssTransformer"), "Expected mrssTransformer to be set"
        print(f"    Uploaded MRSS transform XSLT to action {aid}")

    runner.run_test("genericDistributionProviderAction.addMrssTransform — upload XSLT", test_generic_action_add_mrss_transform)

    def test_generic_action_add_mrss_validate():
        """Upload an MRSS validation XSD to the action."""
        aid = state.get("generic_action_id")
        if not aid:
            print("    Skipped — " + ("service not enabled" if state.get("generic_provider_forbidden") else "no created action"))
            return
        xsd = '''<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="item">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="title" type="xs:string"/>
        <xs:element name="description" type="xs:string"/>
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>'''
        result = kaltura_post("contentDistribution_genericDistributionProviderAction", "addMrssValidate", {
            "id": aid,
            "xsdData": xsd,
        })
        assert result.get("id") == aid, f"Expected id={aid}, got {result.get('id')}"
        assert result.get("mrssValidator"), "Expected mrssValidator to be set"
        print(f"    Uploaded MRSS validation XSD to action {aid}")

    runner.run_test("genericDistributionProviderAction.addMrssValidate — upload XSD", test_generic_action_add_mrss_validate)

    def test_generic_action_add_results_transform():
        """Upload a results transform (XPath) to the action."""
        aid = state.get("generic_action_id")
        if not aid:
            print("    Skipped — " + ("service not enabled" if state.get("generic_provider_forbidden") else "no created action"))
            return
        result = kaltura_post("contentDistribution_genericDistributionProviderAction", "addResultsTransform", {
            "id": aid,
            "transformData": "//response/id",
        })
        assert result.get("id") == aid, f"Expected id={aid}, got {result.get('id')}"
        assert result.get("resultsTransformer"), "Expected resultsTransformer to be set"
        print(f"    Uploaded results transform (XPath) to action {aid}")

    runner.run_test("genericDistributionProviderAction.addResultsTransform — upload XPath", test_generic_action_add_results_transform)

    def test_generic_action_get():
        """Retrieve the created action and verify all fields."""
        aid = state.get("generic_action_id")
        if not aid:
            print("    Skipped — " + ("service not enabled" if state.get("generic_provider_forbidden") else "no created action"))
            return
        result = kaltura_post("contentDistribution_genericDistributionProviderAction", "get", {"id": aid})
        assert result.get("id") == aid, f"Expected id={aid}, got {result.get('id')}"
        assert result.get("serverAddress") == "sftp.example.com", \
            f"Expected serverAddress=sftp.example.com, got {result.get('serverAddress')}"
        assert result.get("mrssTransformer"), "Expected mrssTransformer content"
        assert result.get("mrssValidator"), "Expected mrssValidator content"
        assert result.get("resultsTransformer"), "Expected resultsTransformer content"
        print(f"    Verified action {aid}: serverAddress, mrssTransformer, mrssValidator, resultsTransformer")

    runner.run_test("genericDistributionProviderAction.get — verify all transforms attached", test_generic_action_get)

    def test_generic_action_get_by_provider():
        """Retrieve action by provider ID and action type."""
        pid = state.get("generic_provider_id")
        if not pid:
            if state.get("generic_provider_forbidden"):
                print("    Skipped — service not enabled on this account")
            else:
                print("    Skipped — no created provider")
            return
        result = kaltura_post("contentDistribution_genericDistributionProviderAction", "getByProviderId", {
            "genericDistributionProviderId": pid,
            "actionType": 1,  # SUBMIT
        })
        assert result.get("genericDistributionProviderId") == pid, \
            f"Expected genericDistributionProviderId={pid}, got {result.get('genericDistributionProviderId')}"
        assert result.get("action") == 1, f"Expected action=1, got {result.get('action')}"
        print(f"    Got action by provider {pid} + SUBMIT type: id={result['id']}")

    runner.run_test("genericDistributionProviderAction.getByProviderId — lookup by provider+type", test_generic_action_get_by_provider)

    def test_generic_action_delete():
        """Delete the generic provider action."""
        aid = state.get("generic_action_id")
        if not aid:
            print("    Skipped — " + ("service not enabled" if state.get("generic_provider_forbidden") else "no created action"))
            return
        kaltura_post("contentDistribution_genericDistributionProviderAction", "delete", {"id": aid})
        runner._cleanup_actions = [
            (l, fn) for l, fn in runner._cleanup_actions
            if f"generic action {aid}" not in l
        ]
        print(f"    Deleted action: {aid}")

    runner.run_test("genericDistributionProviderAction.delete — remove action", test_generic_action_delete)

    def test_generic_provider_delete():
        """Delete the generic distribution provider."""
        pid = state.get("generic_provider_id")
        if not pid:
            if state.get("generic_provider_forbidden"):
                print("    Skipped — service not enabled on this account")
            else:
                print("    Skipped — no created provider")
            return
        kaltura_post("contentDistribution_genericDistributionProvider", "delete", {"id": pid})
        runner._cleanup_actions = [
            (l, fn) for l, fn in runner._cleanup_actions
            if f"generic provider {pid}" not in l
        ]
        print(f"    Deleted provider: {pid}")

    runner.run_test("genericDistributionProvider.delete — remove provider", test_generic_provider_delete)

    def test_generic_provider_delete_verify():
        """Verify deleted provider returns NOT_FOUND."""
        pid = state.get("generic_provider_id")
        if not pid:
            if state.get("generic_provider_forbidden"):
                print("    Skipped — service not enabled on this account")
            else:
                print("    Skipped — no created provider")
            return
        try:
            kaltura_post("contentDistribution_genericDistributionProvider", "get", {"id": pid})
            assert False, "Expected NOT_FOUND after delete"
        except Exception as e:
            assert "NOT_FOUND" in str(e).upper() or "not found" in str(e).lower(), \
                f"Expected NOT_FOUND: {e}"
            print(f"    Confirmed deleted: {e}")

    runner.run_test("genericDistributionProvider.get — verify NOT_FOUND after delete", test_generic_provider_delete_verify)

    # ════════════════════════════════════════════
    # Phase 7: Error Handling
    # ════════════════════════════════════════════

    def test_entry_dist_not_found():
        """Verify error for non-existent entry distribution ID."""
        try:
            kaltura_post("contentDistribution_entryDistribution", "get", {"id": 999999999})
            assert False, "Expected error for non-existent ID"
        except Exception as e:
            assert "ENTRY_DISTRIBUTION_NOT_FOUND" in str(e), f"Expected ENTRY_DISTRIBUTION_NOT_FOUND: {e}"
            print(f"    Correct error: {e}")

    runner.run_test("entryDistribution.get — NOT_FOUND error", test_entry_dist_not_found)

    def test_retry_not_found():
        """Verify error for retrySubmit on non-existent entry distribution."""
        try:
            kaltura_post("contentDistribution_entryDistribution", "retrySubmit", {"id": 999999999})
            assert False, "Expected error for non-existent ID"
        except Exception as e:
            assert "ENTRY_DISTRIBUTION_NOT_FOUND" in str(e), f"Expected ENTRY_DISTRIBUTION_NOT_FOUND: {e}"
            print(f"    Correct error: {e}")

    runner.run_test("entryDistribution.retrySubmit — NOT_FOUND error", test_retry_not_found)

    def test_profile_not_found():
        """Verify error for non-existent distribution profile ID."""
        try:
            kaltura_post("contentDistribution_distributionProfile", "get", {"id": 999999999})
            assert False, "Expected error for non-existent ID"
        except Exception as e:
            assert "NOT_FOUND" in str(e) or "not found" in str(e).lower(), \
                f"Expected NOT_FOUND error: {e}"
            print(f"    Correct error: {e}")

    runner.run_test("distributionProfile.get — NOT_FOUND error", test_profile_not_found)

    def test_entry_dist_invalid_entry():
        """Verify error for binding non-existent entry to distribution."""
        pid = state.get("created_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        try:
            kaltura_post("contentDistribution_entryDistribution", "add", {
                "entryDistribution[objectType]": "KalturaEntryDistribution",
                "entryDistribution[entryId]": "0_nonexistent",
                "entryDistribution[distributionProfileId]": pid,
            })
            assert False, "Expected error for non-existent entry"
        except Exception as e:
            assert "ENTRY_NOT_FOUND" in str(e) or "not found" in str(e).lower(), \
                f"Expected ENTRY_NOT_FOUND error: {e}"
            print(f"    Correct error: {e}")

    runner.run_test("entryDistribution.add — ENTRY_NOT_FOUND error", test_entry_dist_invalid_entry)

    # ════════════════════════════════════════════
    # Phase 7: Entry Distribution Delete Verification
    # ════════════════════════════════════════════

    def test_entry_dist_delete_and_verify():
        """Delete an entry distribution and verify it is removed."""
        pid = state.get("created_profile_id")
        if not pid:
            print("    Skipped — no created profile")
            return
        entry_id = create_test_entry()
        runner.register_cleanup(f"delete-test entry {entry_id}",
                                lambda: delete_test_entry(entry_id))
        result = kaltura_post("contentDistribution_entryDistribution", "add", {
            "entryDistribution[objectType]": "KalturaEntryDistribution",
            "entryDistribution[entryId]": entry_id,
            "entryDistribution[distributionProfileId]": pid,
        })
        dist_id = result["id"]
        print(f"    Created entry distribution to delete: {dist_id}")

        kaltura_post("contentDistribution_entryDistribution", "delete", {"id": dist_id})
        print(f"    Deleted entry distribution: {dist_id}")

        # Hard delete — returns NOT_FOUND
        try:
            kaltura_post("contentDistribution_entryDistribution", "get", {"id": dist_id})
            assert False, "Expected NOT_FOUND error after delete"
        except Exception as e:
            assert "ENTRY_DISTRIBUTION_NOT_FOUND" in str(e), \
                f"Expected ENTRY_DISTRIBUTION_NOT_FOUND: {e}"
            print(f"    Verified deleted: {e}")

    runner.run_test("entryDistribution.delete — delete and verify", test_entry_dist_delete_and_verify)

    # ════════════════════════════════════════════
    # Phase 8: Profile Delete Verification
    # ════════════════════════════════════════════

    def test_profile_delete_verify():
        """Delete the FTP profile and verify NOT_FOUND."""
        pid = state.get("created_profile_id")
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
            if f"created profile {pid}" not in l
        ]

    runner.run_test("distributionProfile.delete — remove and verify", test_profile_delete_verify)

    # ════════════════════════════════════════════
    # Cleanup & Summary
    # ════════════════════════════════════════════
    keep = "--keep" in sys.argv
    if keep:
        print("\n--- Keeping resources (--keep flag) ---")
        if state.get("test_entry_id"):
            print(f"  Test entry: {state['test_entry_id']}")
        if state.get("entry_dist_id"):
            print(f"  Entry distribution: {state['entry_dist_id']}")
        print("  Run without --keep to clean up, or delete manually.")
    else:
        if sys.stdin.isatty():
            input("\nPress Enter to clean up test resources...")
        runner.cleanup()

    success = runner.summary()
    sys.exit(0 if success else 1)


def _delete_entry_distribution(dist_id):
    """Delete an entry distribution (with error handling)."""
    try:
        kaltura_post("contentDistribution_entryDistribution", "delete", {"id": dist_id})
    except Exception as e:
        print(f"  [WARN] Failed to delete entry distribution {dist_id}: {e}")


def _delete_profile(profile_id):
    """Delete a distribution profile (with error handling)."""
    try:
        kaltura_post("contentDistribution_distributionProfile", "delete", {"id": profile_id})
    except Exception as e:
        print(f"  [WARN] Failed to delete distribution profile {profile_id}: {e}")


def _delete_generic_provider(provider_id):
    """Delete a generic distribution provider (with error handling)."""
    try:
        kaltura_post("contentDistribution_genericDistributionProvider", "delete", {"id": provider_id})
    except Exception as e:
        print(f"  [WARN] Failed to delete generic provider {provider_id}: {e}")


def _delete_generic_action(action_id):
    """Delete a generic distribution provider action (with error handling)."""
    try:
        kaltura_post("contentDistribution_genericDistributionProviderAction", "delete", {"id": action_id})
    except Exception as e:
        print(f"  [WARN] Failed to delete generic action {action_id}: {e}")


if __name__ == "__main__":
    main()

from digisnap_mcp.server import mcp


def test_mcp_server_is_created() -> None:
    assert mcp.name == "DigiSnap-MCP"

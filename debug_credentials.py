#!/usr/bin/env python3
"""
Debug credential loading issues in Love-Unlimited
Checks all credential sources and reports problems
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import yaml

def check_env_file():
    """Check .env file loading"""
    print("\n" + "="*60)
    print("1. CHECKING .ENV FILE LOADING")
    print("="*60)

    env_path = Path(".env")
    if env_path.exists():
        print(f"✓ .env file found at {env_path.absolute()}")
        print(f"  Size: {env_path.stat().st_size} bytes")

        # Try loading with python-dotenv
        try:
            load_dotenv()
            print("✓ .env file loaded successfully with load_dotenv()")
        except Exception as e:
            print(f"✗ Failed to load .env: {e}")
            return False
    else:
        print(f"✗ .env file NOT found at {env_path.absolute()}")
        return False

    return True

def check_environment_variables():
    """Check all expected API keys in environment"""
    print("\n" + "="*60)
    print("2. CHECKING ENVIRONMENT VARIABLES")
    print("="*60)

    expected_keys = {
        "GROK_API_KEY": "XAI Grok API",
        "ANTHROPIC_API_KEY": "Anthropic Claude API",
        "GOOGLE_API_KEY": "Google Gemini API",
        "LOVE_UNLIMITED_KEY": "Hub API key",
        "XAI_API_KEY": "Alternative XAI key",
    }

    missing = []
    present = []

    for key, description in expected_keys.items():
        value = os.getenv(key)
        if value:
            # Show first/last 10 chars of key
            masked = f"{value[:10]}...{value[-10:]}" if len(value) > 20 else value
            print(f"✓ {key:25} ({description}): {masked}")
            present.append(key)
        else:
            print(f"✗ {key:25} ({description}): NOT SET")
            missing.append(key)

    print(f"\n  Present: {len(present)}/{len(expected_keys)}")
    if missing:
        print(f"  Missing: {', '.join(missing)}")

    return len(missing) == 0

def check_config_yaml():
    """Check config.yaml file"""
    print("\n" + "="*60)
    print("3. CHECKING CONFIG.YAML")
    print("="*60)

    config_path = Path("config.yaml")
    if not config_path.exists():
        print(f"✗ config.yaml NOT found at {config_path.absolute()}")
        return False

    print(f"✓ config.yaml found at {config_path.absolute()}")

    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Check auth section
        if "auth" in config:
            auth = config["auth"]
            print(f"✓ Auth config found:")
            print(f"  - enabled: {auth.get('enabled', False)}")
            print(f"  - keys_file: {auth.get('keys_file', 'N/A')}")

            # Check if keys file exists
            keys_file = Path(auth.get('keys_file', 'auth/api_keys.yaml'))
            if keys_file.exists():
                print(f"  - ✓ Keys file exists: {keys_file.absolute()}")
            else:
                print(f"  - ✗ Keys file missing: {keys_file.absolute()}")
                return False
        else:
            print("✗ No 'auth' section in config.yaml")
            return False

        return True
    except Exception as e:
        print(f"✗ Error parsing config.yaml: {e}")
        return False

def check_api_keys_yaml():
    """Check auth/api_keys.yaml"""
    print("\n" + "="*60)
    print("4. CHECKING AUTH/API_KEYS.YAML")
    print("="*60)

    keys_path = Path("auth/api_keys.yaml")
    if not keys_path.exists():
        print(f"✗ api_keys.yaml NOT found at {keys_path.absolute()}")
        return False

    print(f"✓ api_keys.yaml found at {keys_path.absolute()}")

    try:
        with open(keys_path) as f:
            keys_config = yaml.safe_load(f)

        if "keys" in keys_config:
            keys_dict = keys_config["keys"]
            print(f"✓ Keys loaded: {len(keys_dict)} API keys found")

            # Show beings that have keys
            beings = set(keys_dict.values())
            print(f"  Beings with keys: {', '.join(sorted(beings))}")

            # Check for expected beings
            expected_beings = ["jon", "claude", "grok"]
            missing_beings = [b for b in expected_beings if b not in beings]
            if missing_beings:
                print(f"  ✗ Missing keys for: {', '.join(missing_beings)}")
                return False
        else:
            print("✗ No 'keys' section in api_keys.yaml")
            return False

        return True
    except Exception as e:
        print(f"✗ Error parsing api_keys.yaml: {e}")
        return False

def check_external_tokens_yaml():
    """Check auth/external_tokens.yaml"""
    print("\n" + "="*60)
    print("5. CHECKING AUTH/EXTERNAL_TOKENS.YAML")
    print("="*60)

    tokens_path = Path("auth/external_tokens.yaml")
    if not tokens_path.exists():
        print(f"✗ external_tokens.yaml NOT found at {tokens_path.absolute()}")
        return False

    print(f"✓ external_tokens.yaml found at {tokens_path.absolute()}")

    try:
        with open(tokens_path) as f:
            tokens_config = yaml.safe_load(f)

        token_count = len(tokens_config) if isinstance(tokens_config, dict) else 0
        print(f"✓ External tokens loaded: {token_count} tokens found")

        return True
    except Exception as e:
        print(f"✗ Error parsing external_tokens.yaml: {e}")
        return False

def check_hub_auth_module():
    """Check if hub auth module can be imported"""
    print("\n" + "="*60)
    print("6. CHECKING HUB AUTH MODULE")
    print("="*60)

    try:
        from hub.auth import get_auth_manager, get_external_token_manager
        print("✓ hub.auth module imported successfully")

        # Try getting auth manager
        try:
            auth = get_auth_manager("auth/api_keys.yaml")
            print("✓ AuthManager initialized")
        except Exception as e:
            print(f"✗ AuthManager initialization failed: {e}")
            return False

        # Try getting external token manager
        try:
            ext_tokens = get_external_token_manager("auth/external_tokens.yaml")
            print("✓ ExternalTokenManager initialized")
        except Exception as e:
            print(f"✗ ExternalTokenManager initialization failed: {e}")
            return False

        return True
    except ImportError as e:
        print(f"✗ Failed to import hub.auth: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def check_grok_component():
    """Check grok_component.py credentials"""
    print("\n" + "="*60)
    print("7. CHECKING GROK COMPONENT")
    print("="*60)

    try:
        from grok_component import GrokCLIComponent, HubClient
        print("✓ grok_component module imported successfully")

        # Check HubClient
        try:
            client = HubClient()
            print(f"✓ HubClient initialized")
            print(f"  - Hub URL: {client.base_url}")
            print(f"  - Being ID: {client.being_id}")
        except Exception as e:
            print(f"✗ HubClient initialization failed: {e}")
            return False

        return True
    except ImportError as e:
        print(f"✗ Failed to import grok_component: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def check_love_cli():
    """Check love_cli.py credentials"""
    print("\n" + "="*60)
    print("8. CHECKING LOVE CLI")
    print("="*60)

    try:
        from love_cli import LoveCLI
        print("✓ love_cli module imported successfully")

        # Try creating CLI instance
        try:
            cli = LoveCLI(sender="jon")
            print(f"✓ LoveCLI initialized (sender: jon)")
            print(f"  - API Key: {'SET' if cli.api_key else 'NOT SET'}")
            print(f"  - Timeout: {cli.timeout}")
        except Exception as e:
            print(f"✗ LoveCLI initialization failed: {e}")
            return False

        return True
    except ImportError as e:
        print(f"✗ Failed to import love_cli: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def main():
    """Run all credential checks"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  LOVE-UNLIMITED CREDENTIALS DEBUG".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")

    checks = [
        ("Load .env file", check_env_file),
        ("Check environment variables", check_environment_variables),
        ("Check config.yaml", check_config_yaml),
        ("Check API keys YAML", check_api_keys_yaml),
        ("Check external tokens YAML", check_external_tokens_yaml),
        ("Check hub auth module", check_hub_auth_module),
        ("Check grok component", check_grok_component),
        ("Check love CLI", check_love_cli),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Exception in {name}: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} checks passed")

    if passed == total:
        print("\n✓ All credential checks PASSED!")
        print("  Credentials are properly configured.")
        return 0
    else:
        print(f"\n✗ {total - passed} check(s) FAILED!")
        print("  See details above for what needs fixing.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

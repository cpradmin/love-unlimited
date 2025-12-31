"""
Love-Unlimited Authentication
API key-based authentication for beings and external read-only access.
"""

import yaml
import secrets
import logging
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN

logger = logging.getLogger(__name__)


# API key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class AuthManager:
    """
    Manages API keys and authentication for beings.
    """

    def __init__(self, keys_file: str = "./auth/api_keys.yaml"):
        self.keys_file = Path(keys_file)
        self.api_keys: Dict[str, str] = {}  # {api_key: being_id}
        self.load_keys()

    def load_keys(self):
        """Load API keys from file."""
        if self.keys_file.exists():
            with open(self.keys_file, "r") as f:
                data = yaml.safe_load(f) or {}
                self.api_keys = data.get("keys", {})
        else:
            # Create empty keys file
            self.keys_file.parent.mkdir(parents=True, exist_ok=True)
            self.save_keys()

    def save_keys(self):
        """Save API keys to file."""
        with open(self.keys_file, "w") as f:
            yaml.dump({"keys": self.api_keys}, f)

    def generate_key(self, being_id: str, prefix: str = "lu") -> str:
        """
        Generate a new API key for a being.

        Args:
            being_id: The being's ID
            prefix: Key prefix (default: "lu")

        Returns:
            Generated API key
        """
        # Generate random key
        random_part = secrets.token_urlsafe(16)
        api_key = f"{prefix}_{being_id}_{random_part}"

        # Store mapping
        self.api_keys[api_key] = being_id
        self.save_keys()

        return api_key

    def verify_key(self, api_key: str) -> Optional[str]:
        """
        Verify an API key and return the associated being_id.

        Args:
            api_key: The API key to verify

        Returns:
            being_id if valid, None otherwise
        """
        return self.api_keys.get(api_key)

    def revoke_key(self, api_key: str):
        """
        Revoke an API key.

        Args:
            api_key: The API key to revoke
        """
        if api_key in self.api_keys:
            del self.api_keys[api_key]
            self.save_keys()

    def get_keys_for_being(self, being_id: str) -> list:
        """
        Get all API keys for a being.

        Args:
            being_id: The being's ID

        Returns:
            List of API keys
        """
        return [key for key, bid in self.api_keys.items() if bid == being_id]

    def get_api_key_for_being(self, being_id: str) -> Optional[str]:
        """
        Get the first API key for a being.

        Args:
            being_id: The being's ID

        Returns:
            First API key for the being, or None if none exist
        """
        keys = self.get_keys_for_being(being_id)
        return keys[0] if keys else None


class ExternalTokenManager:
    """
    Manages external read-only access tokens.

    External tokens provide limited, read-only access to memory recall
    for external integrations (like Cloudflare Workers, webhooks, etc.)
    """

    def __init__(self, tokens_file: str = "./auth/external_tokens.yaml"):
        self.tokens_file = Path(tokens_file)
        self.tokens: Dict[str, Dict] = {}  # {token: token_data}
        self.load_tokens()

    def load_tokens(self):
        """Load external tokens from file."""
        if self.tokens_file.exists():
            with open(self.tokens_file, "r") as f:
                data = yaml.safe_load(f) or {}
                # Filter out comments and load tokens
                self.tokens = {k: v for k, v in data.items() if k.startswith("ext_")}
                logger.info(f"Loaded {len(self.tokens)} external tokens")
        else:
            # Create empty tokens file
            self.tokens_file.parent.mkdir(parents=True, exist_ok=True)
            self.save_tokens()

    def save_tokens(self):
        """Save external tokens to file."""
        # Add header comment
        header = (
            "# External API Tokens for Love-Unlimited Hub\n"
            "# These tokens provide READ-ONLY access to memory recall\n"
            "# Format: token_value: { name, description, created, permissions }\n\n"
        )

        with open(self.tokens_file, "w") as f:
            f.write(header)
            yaml.dump(self.tokens, f, default_flow_style=False)

    def generate_token(
        self,
        name: str,
        description: str = "",
        allowed_beings: Optional[List[str]] = None,
        rate_limit: int = 100
    ) -> str:
        """
        Generate a new external access token.

        Args:
            name: Token name/identifier
            description: Token description
            allowed_beings: List of beings this token can access (None = all)
            rate_limit: Requests per hour limit

        Returns:
            Generated token
        """
        # Generate secure random token
        random_part = secrets.token_urlsafe(24)
        token = f"ext_{random_part}"

        # Store token data
        self.tokens[token] = {
            "name": name,
            "description": description,
            "created": datetime.now().strftime("%Y-%m-%d"),
            "permissions": ["recall"],
            "rate_limit": rate_limit,
            "allowed_beings": allowed_beings or ["claude", "jon", "grok"],
            "enabled": True
        }

        self.save_tokens()
        logger.info(f"Generated external token: {name}")

        return token

    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verify an external token and return its data.

        Args:
            token: The token to verify

        Returns:
            Token data if valid and enabled, None otherwise
        """
        token_data = self.tokens.get(token)

        if token_data is None:
            logger.warning(f"External token verification failed: token not found")
            return None

        if not token_data.get("enabled", False):
            logger.warning(f"External token verification failed: token disabled ({token_data.get('name')})")
            return None

        return token_data

    def revoke_token(self, token: str):
        """
        Revoke an external token (disable it).

        Args:
            token: The token to revoke
        """
        if token in self.tokens:
            self.tokens[token]["enabled"] = False
            self.save_tokens()
            logger.info(f"Revoked external token: {self.tokens[token].get('name')}")

    def delete_token(self, token: str):
        """
        Permanently delete an external token.

        Args:
            token: The token to delete
        """
        if token in self.tokens:
            name = self.tokens[token].get("name")
            del self.tokens[token]
            self.save_tokens()
            logger.info(f"Deleted external token: {name}")

    def has_permission(self, token_data: Dict, permission: str) -> bool:
        """
        Check if token has a specific permission.

        Args:
            token_data: Token data dict
            permission: Permission to check

        Returns:
            True if token has permission
        """
        permissions = token_data.get("permissions", [])
        return permission in permissions

    def can_access_being(self, token_data: Dict, being_id: str) -> bool:
        """
        Check if token can access a specific being's memories.

        Args:
            token_data: Token data dict
            being_id: Being ID to check

        Returns:
            True if token can access being
        """
        allowed_beings = token_data.get("allowed_beings", [])
        return being_id in allowed_beings


# Global auth manager instances
auth_manager: Optional[AuthManager] = None
external_token_manager: Optional[ExternalTokenManager] = None


def get_auth_manager(keys_file: str = "./auth/api_keys.yaml") -> AuthManager:
    """Get or create global auth manager instance."""
    global auth_manager
    if auth_manager is None:
        auth_manager = AuthManager(keys_file)
    return auth_manager


def get_external_token_manager(tokens_file: str = "./auth/external_tokens.yaml") -> ExternalTokenManager:
    """Get or create global external token manager instance."""
    global external_token_manager
    if external_token_manager is None:
        external_token_manager = ExternalTokenManager(tokens_file)
    return external_token_manager


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    FastAPI dependency to verify API key.

    Args:
        api_key: API key from request header

    Returns:
        being_id if authenticated

    Raises:
        HTTPException: If authentication fails
    """
    if not api_key:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Missing API key. Include X-API-Key header."
        )

    auth = get_auth_manager()
    being_id = auth.verify_key(api_key)

    if being_id is None:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    return being_id


async def optional_api_key(api_key: str = Security(api_key_header)) -> Optional[str]:
    """
    FastAPI dependency for optional API key (for public endpoints).

    Args:
        api_key: API key from request header

    Returns:
        being_id if authenticated, None otherwise
    """
    if not api_key:
        return None

    auth = get_auth_manager()
    return auth.verify_key(api_key)

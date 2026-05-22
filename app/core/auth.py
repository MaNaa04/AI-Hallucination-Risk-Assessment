"""
JWT Verification helper — app/core/auth.py

Design constraints (from task spec):
  - We ONLY verify tokens; we NEVER mint them.
  - Tokens are generated client-side by the Chrome Extension using a third-party
    provider (Supabase Auth / Firebase Auth) and passed to us as standard JWTs.
  - This module is instantiated once inside the FastAPI lifespan and stored as
    app.state.auth_verifier so every request handler can reuse it cheaply.

Algorithm support:
  - Default: HS256 (symmetric) — shared secret copied from the provider dashboard.
  - RS256 / ES256 (asymmetric) — set JWT_ALGORITHM=RS256 and supply the provider's
    public key as JWT_SECRET.  python-jose handles both transparently.
"""

from __future__ import annotations

from typing import Any

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError

from app.core.logging import get_logger

logger = get_logger(__name__)


class JWTVerifier:
    """
    Thin, stateless wrapper around python-jose's ``jwt.decode``.

    Attributes:
        secret:    Shared secret (HS256) or PEM-encoded public key (RS256/ES256).
        algorithm: Expected signing algorithm; must match the token header.

    Usage::

        verifier = JWTVerifier(secret=settings.jwt_secret, algorithm=settings.jwt_algorithm)
        claims = verifier.decode("Bearer eyJ…")  # raises HTTPException on failure
    """

    def __init__(self, *, secret: str, algorithm: str = "HS256") -> None:
        if not secret:
            logger.warning(
                "JWTVerifier initialised with an empty secret — all token "
                "verifications will fail.  Set JWT_SECRET in your .env."
            )
        self.secret = secret
        self.algorithm = algorithm
        logger.info(f"JWTVerifier ready (algorithm={algorithm})")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def decode(self, raw_token: str) -> dict[str, Any]:
        """
        Verify and decode a raw JWT string.

        Strips a ``Bearer `` prefix if present so callers can pass the
        Authorization header value directly.

        Args:
            raw_token: Raw JWT string, optionally prefixed with ``Bearer ``.

        Returns:
            Decoded claims dictionary (e.g. ``{"sub": "user_id", "exp": …}``).

        Raises:
            ValueError: If the token is expired, has invalid claims, or fails
                        signature verification.  Callers (FastAPI dependencies)
                        should catch this and raise an HTTPException(401).
        """
        token = raw_token.removeprefix("Bearer ").strip()

        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                options={"verify_aud": False},  # audience check delegated to caller
            )
            logger.debug(f"JWT verified — sub={claims.get('sub')!r}")
            return claims

        except ExpiredSignatureError as exc:
            raise ValueError("Token has expired") from exc
        except JWTClaimsError as exc:
            raise ValueError(f"Invalid JWT claims: {exc}") from exc
        except JWTError as exc:
            raise ValueError(f"JWT verification failed: {exc}") from exc

    def extract_user_id(self, raw_token: str) -> str:
        """
        Convenience wrapper: verify the token and return the ``sub`` claim.

        Args:
            raw_token: Raw JWT string (``Bearer …`` prefix optional).

        Returns:
            The ``sub`` claim string, i.e. the provider's user ID.

        Raises:
            ValueError: If verification fails or ``sub`` is absent.
        """
        claims = self.decode(raw_token)
        sub = claims.get("sub")
        if not sub:
            raise ValueError("JWT is missing the required 'sub' claim")
        return str(sub)

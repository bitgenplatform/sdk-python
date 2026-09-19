"""The API keys of the organization and the journal of their calls, read-only (`client.apikeys`)."""

from __future__ import annotations

from bitgen._http.client import HttpClient
from bitgen._support import path, reference, values
from bitgen.models import _cast
from bitgen.models.apikeys import Apikey, ApikeyLog
from bitgen.page import Page


class ApikeysResource:
    """The keys of the organization and what was called with them — a key cannot be created through the API, and the
    SDK does not revoke. Wherever the API expects the organization, the SDK sends the key's scope. Every method raises
    a `BitgenError` when the API answers an error or no HTTP answer is received; an invalid argument raises a
    `ValueError` (or a `TypeError`) before any request."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(
        self, *, includeRevoked: bool | None = None, offset: int | None = None, limit: int | None = None
    ) -> Page[Apikey]:
        """The keys of the organization — the `REVOKED` ones with `includeRevoked`"""
        query = {
            "includeRevoked": values.optional_bool(includeRevoked, "includeRevoked"),
            "offset": values.optional_int(offset, "offset"),
            "limit": values.optional_int(limit, "limit"),
        }
        answer = self._http.get(f"/organization/{self._organization()}/apikeys", query)
        return Page.from_dict(_cast.answer(answer), Apikey.from_dict)

    def get(self, apikey: str | Apikey) -> Apikey:
        """One key, by uuid or by model"""
        answer = self._http.get(f"/organization/{self._organization()}/apikeys/{_apikey(apikey)}")
        return Apikey.from_dict(_cast.answer(answer))

    def logs(self, apikey: str | Apikey, *, offset: int | None = None, limit: int | None = None) -> Page[ApikeyLog]:
        """The calls made with a key: path, inputs (personal data masked), status, error"""
        query = {"offset": values.optional_int(offset, "offset"), "limit": values.optional_int(limit, "limit")}
        answer = self._http.get(f"/organization/{self._organization()}/apikeys/{_apikey(apikey)}/logs", query)
        return Page.from_dict(_cast.answer(answer), ApikeyLog.from_dict)

    def _organization(self) -> str:
        """The scope of the key, as the `{organization}` path segment"""
        return path.segment(self._http.scope, "scope")


def _apikey(apikey: str | Apikey) -> str:
    return path.segment(reference.resolve(apikey, Apikey, "apikey"), "apikey")

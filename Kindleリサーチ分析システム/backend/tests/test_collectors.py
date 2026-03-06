"""データ収集クライアントの単体テスト。"""
import pytest

from src.collectors.autocomplete_client import AutocompleteClient
from src.collectors.helium10_client import Helium10Client
from src.collectors.merchantwords_client import MerchantWordsClient


class TestAutocompleteClient:
    def test_calculate_volume_estimate_high_score(self):
        client = AutocompleteClient()
        vol = client.calculate_volume_estimate(0.9)
        assert vol > 0

    def test_calculate_volume_estimate_zero_score(self):
        client = AutocompleteClient()
        vol = client.calculate_volume_estimate(0.0)
        assert vol == 0

    def test_calculate_volume_proportional(self):
        client = AutocompleteClient()
        high = client.calculate_volume_estimate(0.9)
        low = client.calculate_volume_estimate(0.1)
        assert high > low


class TestHelium10Client:
    def test_returns_none_without_api_key(self):
        """APIキー未設定時はNoneを返す（graceful degradation）。"""
        client = Helium10Client(api_key=None)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            client.get_keyword_volume("ビジネス")
        )
        assert result is None

    def test_returns_empty_list_without_api_key(self):
        client = Helium10Client(api_key=None)
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            client.get_related_keywords("ビジネス")
        )
        assert result == []


class TestMerchantWordsClient:
    def test_instantiation_without_key(self):
        """APIキー未設定でもインスタンス化できる。"""
        client = MerchantWordsClient(api_key=None)
        assert client is not None

"""
test_adaptive_network.py
adaptive_network.py のユニットテスト（Ollamaをモック）
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import patch


class TestConnectionWeights:
    """Connectionのflow_weight更新テスト"""

    def test_initial_weight(self):
        from adaptive_network import Connection, INITIAL_WEIGHT
        conn = Connection(1, 2)
        assert conn.flow_weight == INITIAL_WEIGHT

    def test_weight_increases_on_success(self):
        from adaptive_network import Connection
        conn = Connection(1, 2)
        old_weight = conn.flow_weight
        conn.update_weight(success=True)
        assert conn.flow_weight > old_weight

    def test_weight_decreases_on_failure(self):
        from adaptive_network import Connection
        conn = Connection(1, 2)
        old_weight = conn.flow_weight
        conn.update_weight(success=False)
        assert conn.flow_weight < old_weight

    def test_weight_increase_formula(self):
        """new = old + 0.1 * (1.0 - old)"""
        from adaptive_network import Connection
        conn = Connection(1, 2)
        conn.flow_weight = 0.5
        conn.update_weight(success=True)
        expected = 0.5 + 0.1 * (1.0 - 0.5)
        assert abs(conn.flow_weight - expected) < 1e-6

    def test_weight_decrease_formula(self):
        """new = old * 0.7"""
        from adaptive_network import Connection
        conn = Connection(1, 2)
        conn.flow_weight = 0.5
        conn.update_weight(success=False)
        expected = 0.5 * 0.7
        assert abs(conn.flow_weight - expected) < 1e-6

    def test_weight_never_exceeds_1(self):
        """weightは1.0を超えない"""
        from adaptive_network import Connection
        conn = Connection(1, 2)
        conn.flow_weight = 0.99
        for _ in range(100):
            conn.update_weight(success=True)
        assert conn.flow_weight <= 1.0

    def test_weight_never_goes_to_zero(self):
        """weightは0以下にならない（最小0.01）"""
        from adaptive_network import Connection
        conn = Connection(1, 2)
        conn.flow_weight = 0.01
        for _ in range(100):
            conn.update_weight(success=False)
        assert conn.flow_weight > 0

    def test_weight_history_recorded(self):
        from adaptive_network import Connection
        conn = Connection(1, 2)
        conn.update_weight(success=True)
        conn.update_weight(success=False)
        assert len(conn.history) == 2

    def test_to_dict(self):
        from adaptive_network import Connection
        conn = Connection(1, 2)
        d = conn.to_dict()
        assert d["from_node"] == 1
        assert d["to_node"] == 2
        assert "flow_weight" in d
        assert "history" in d


class TestAdaptiveNetworkStructure:
    """AdaptiveNetworkの構造テスト"""

    def test_import(self):
        from adaptive_network import AdaptiveNetwork
        assert AdaptiveNetwork is not None

    def test_has_three_nodes(self):
        from adaptive_network import AdaptiveNetwork
        network = AdaptiveNetwork()
        assert 1 in network.nodes
        assert 2 in network.nodes
        assert 3 in network.nodes

    def test_has_six_connections(self):
        from adaptive_network import AdaptiveNetwork
        network = AdaptiveNetwork()
        assert len(network.connections) == 6

    def test_all_connections_present(self):
        from adaptive_network import AdaptiveNetwork
        network = AdaptiveNetwork()
        expected = [(1, 2), (2, 1), (2, 3), (3, 2), (1, 3), (3, 1)]
        for key in expected:
            assert key in network.connections, f"接続 {key} が見つかりません"

    def test_parse_prediction_consistent(self):
        from adaptive_network import AdaptiveNetwork
        network = AdaptiveNetwork()
        assert network._parse_prediction("矛盾しない") is True

    def test_parse_prediction_inconsistent(self):
        from adaptive_network import AdaptiveNetwork
        network = AdaptiveNetwork()
        assert network._parse_prediction("矛盾する") is False

    def test_parse_prediction_unknown_default_false(self):
        from adaptive_network import AdaptiveNetwork
        network = AdaptiveNetwork()
        assert network._parse_prediction("不明") is False


class TestAdaptiveNetworkPrediction:
    """AdaptiveNetworkの予測テスト（Ollamaモック）"""

    def _make_network_predict(self, mock_output: str = "矛盾しない"):
        from adaptive_network import AdaptiveNetwork
        with patch("adaptive_network.call_ollama", return_value=mock_output):
            network = AdaptiveNetwork()
            result = network.predict("この世界では空は緑色である", "緑色の空が広がる")
        return network, result

    def test_predict_returns_dict(self):
        _, result = self._make_network_predict()
        assert isinstance(result, dict)
        assert "prediction" in result
        assert "raw_output" in result
        assert "path_used" in result
        assert "node_results" in result
        assert "used_feedback" in result
        assert "flow_weights" in result

    def test_predict_consistent(self):
        _, result = self._make_network_predict("矛盾しない")
        assert result["prediction"] is True

    def test_predict_inconsistent(self):
        _, result = self._make_network_predict("矛盾する")
        assert result["prediction"] is False

    def test_predict_has_path(self):
        _, result = self._make_network_predict()
        assert len(result["path_used"]) > 0

    def test_predict_flow_weights_snapshot(self):
        _, result = self._make_network_predict()
        weights = result["flow_weights"]
        assert "1->2" in weights or "1->3" in weights


class TestAdaptiveNetworkWeightUpdate:
    """flow_weight更新の統合テスト"""

    def test_weights_change_after_success(self):
        from adaptive_network import AdaptiveNetwork
        network = AdaptiveNetwork()
        initial = dict(network.get_weights_snapshot())

        with patch("adaptive_network.call_ollama", return_value="矛盾しない"):
            result = network.predict("ルール", "質問")
            network.update_weights(True, result["path_used"], result["used_feedback"])

        updated = network.get_weights_snapshot()
        # 少なくとも1つの接続のweightが変わっていること
        changed = any(
            abs(updated[k] - initial.get(k, 0.5)) > 1e-5
            for k in updated
        )
        assert changed, "成功後もweightが変化していません"

    def test_weights_change_after_failure(self):
        from adaptive_network import AdaptiveNetwork
        network = AdaptiveNetwork()
        initial = dict(network.get_weights_snapshot())

        with patch("adaptive_network.call_ollama", return_value="矛盾する"):
            result = network.predict("ルール", "質問")
            network.update_weights(False, result["path_used"], result["used_feedback"])

        updated = network.get_weights_snapshot()
        changed = any(
            abs(updated[k] - initial.get(k, 0.5)) > 1e-5
            for k in updated
        )
        assert changed, "失敗後もweightが変化していません"

    def test_weight_log_grows(self):
        from adaptive_network import AdaptiveNetwork
        network = AdaptiveNetwork()

        with patch("adaptive_network.call_ollama", return_value="矛盾しない"):
            for _ in range(3):
                result = network.predict("ルール", "質問")
                network.update_weights(True, result["path_used"], result["used_feedback"])

        assert len(network.weight_log) == 3

    def test_get_weight_history(self):
        from adaptive_network import AdaptiveNetwork
        network = AdaptiveNetwork()
        history = network.get_weight_history()
        for key in ["1->2", "2->1", "2->3", "3->2", "1->3", "3->1"]:
            assert key in history
            assert isinstance(history[key], list)

    def test_repeated_success_increases_path_weight(self):
        """成功が続くとパスのweightが上昇する"""
        from adaptive_network import AdaptiveNetwork
        network = AdaptiveNetwork()

        # フルパスを使うようにweightを調整（1->3をやや下げる）
        network.connections[(1, 3)].flow_weight = 0.3
        initial_12 = network.connections[(1, 2)].flow_weight

        with patch("adaptive_network.call_ollama", return_value="矛盾しない"):
            for _ in range(5):
                result = network.predict("ルール", "質問")
                network.update_weights(True, result["path_used"], result["used_feedback"])

        # 1->2が使われていれば上昇しているはず
        assert network.connections[(1, 2)].flow_weight >= initial_12

    def test_repeated_failure_decreases_weight(self):
        """失敗が続くとweightが下降する"""
        from adaptive_network import AdaptiveNetwork
        network = AdaptiveNetwork()
        network.connections[(1, 3)].flow_weight = 0.3
        initial = network.connections[(1, 2)].flow_weight

        with patch("adaptive_network.call_ollama", return_value="矛盾する"):
            for _ in range(5):
                result = network.predict("ルール", "質問")
                network.update_weights(False, result["path_used"], result["used_feedback"])

        assert network.connections[(1, 2)].flow_weight <= initial


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
test_fixed_network.py
fixed_network.py のユニットテスト（Ollamaをモック）
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import patch, MagicMock


class TestFixedNetworkStructure:
    """FixedNetworkの構造テスト（Ollamaなし）"""

    def test_import(self):
        from fixed_network import FixedNetwork
        assert FixedNetwork is not None

    def test_has_three_nodes(self):
        from fixed_network import FixedNetwork, Node1, Node2, Node3
        network = FixedNetwork()
        assert isinstance(network.node1, Node1)
        assert isinstance(network.node2, Node2)
        assert isinstance(network.node3, Node3)

    def test_parse_prediction_consistent(self):
        from fixed_network import FixedNetwork
        network = FixedNetwork()
        assert network._parse_prediction("矛盾しない") is True
        assert network._parse_prediction("この文章はルールと矛盾しないと判断します") is True

    def test_parse_prediction_inconsistent(self):
        from fixed_network import FixedNetwork
        network = FixedNetwork()
        assert network._parse_prediction("矛盾する") is False
        assert network._parse_prediction("この文章はルールと矛盾するため") is False

    def test_parse_prediction_priority(self):
        """「矛盾しない」が「矛盾する」より優先される"""
        from fixed_network import FixedNetwork
        network = FixedNetwork()
        # 「矛盾しない」が含まれている場合はTrueを返す
        assert network._parse_prediction("矛盾しないとも矛盾するとも言えます") is True

    def test_parse_prediction_unknown(self):
        """不明な回答はFalseを返す"""
        from fixed_network import FixedNetwork
        network = FixedNetwork()
        assert network._parse_prediction("わかりません") is False
        assert network._parse_prediction("") is False


class TestFixedNetworkWithMock:
    """OllamaをモックしたFixedNetworkのテスト"""

    def _mock_predict(self, world_rule: str, question: str, mock_outputs: list):
        """モックを使ってpredictを呼び出す"""
        from fixed_network import FixedNetwork

        call_count = [0]
        def fake_call_ollama(prompt, system=""):
            idx = min(call_count[0], len(mock_outputs) - 1)
            result = mock_outputs[idx]
            call_count[0] += 1
            return result

        with patch("fixed_network.call_ollama", side_effect=fake_call_ollama):
            network = FixedNetwork()
            return network.predict(world_rule, question)

    def test_predict_returns_dict(self):
        result = self._mock_predict(
            "この世界では空は緑色である",
            "空を見上げると緑色が広がっていた",
            ["空は緑色である", "緑色を示している", "矛盾しない"],
        )
        assert isinstance(result, dict)
        assert "prediction" in result
        assert "raw_output" in result
        assert "node_results" in result

    def test_predict_consistent(self):
        result = self._mock_predict(
            "この世界では空は緑色である",
            "空を見上げると緑色が広がっていた",
            ["空は緑色", "緑色を示す", "矛盾しない"],
        )
        assert result["prediction"] is True

    def test_predict_inconsistent(self):
        result = self._mock_predict(
            "この世界では空は緑色である",
            "空を見上げると青色が広がっていた",
            ["空は緑色", "青色を示す", "矛盾する"],
        )
        assert result["prediction"] is False

    def test_predict_has_three_node_results(self):
        result = self._mock_predict(
            "この世界では空は緑色である",
            "テスト",
            ["出力1", "出力2", "矛盾しない"],
        )
        assert len(result["node_results"]) == 3

    def test_predict_node_order(self):
        result = self._mock_predict(
            "この世界では空は緑色である",
            "テスト",
            ["出力1", "出力2", "矛盾しない"],
        )
        nodes = [r["node"] for r in result["node_results"]]
        assert nodes == [1, 2, 3], f"期待: [1,2,3], 実際: {nodes}"

    def test_predict_error_handling(self):
        """エラーが発生しても例外を投げずに結果を返す"""
        from fixed_network import FixedNetwork

        def error_call(prompt, system=""):
            raise ConnectionError("Ollamaに接続できません")

        with patch("fixed_network.call_ollama", side_effect=error_call):
            network = FixedNetwork()
            result = network.predict("ルール", "質問")

        assert "prediction" in result
        assert result["prediction"] is False  # エラー時はFalse


class TestNodeStructure:
    """各ノードの単体テスト"""

    def test_node1_id(self):
        from fixed_network import Node1
        assert Node1.node_id == 1

    def test_node2_id(self):
        from fixed_network import Node2
        assert Node2.node_id == 2

    def test_node3_id(self):
        from fixed_network import Node3
        assert Node3.node_id == 3

    def test_node1_process_with_mock(self):
        from fixed_network import Node1
        with patch("fixed_network.call_ollama", return_value="ルールの要約"):
            node = Node1()
            result = node.process("ルール", "質問")
        assert result.node_id == 1
        assert result.output_text == "ルールの要約"
        assert result.success is True

    def test_node1_process_error(self):
        from fixed_network import Node1
        with patch("fixed_network.call_ollama", side_effect=Exception("テストエラー")):
            node = Node1()
            result = node.process("ルール", "質問")
        assert result.success is False
        assert "ERROR" in result.output_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
adaptive_network.py
可変構造ネットワーク：Node1 ⇄ Node2 ⇄ Node3 の双方向接続
flow_weightが動的に変化し、高い接続が優先される
"""

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:3b"
TIMEOUT = 60.0

# flow_weight 更新パラメータ
WEIGHT_INCREASE_RATE = 0.1   # 成功時: new = old + 0.1 * (1.0 - old)
WEIGHT_DECREASE_RATE = 0.7   # 失敗時: new = old * 0.7
INITIAL_WEIGHT = 0.5


def call_ollama(prompt: str, system: str = "") -> str:
    """Ollamaのモデルを呼び出す（標準ライブラリのみ使用）"""
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
    }
    if system:
        payload["system"] = system

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        body = resp.read().decode("utf-8")
        result = json.loads(body)
        return result.get("response", "").strip()


@dataclass
class Connection:
    """ノード間の接続（flow_weightを持つ）"""
    from_node: int
    to_node: int
    flow_weight: float = INITIAL_WEIGHT
    history: List[float] = field(default_factory=list)

    def update_weight(self, success: bool):
        """結果に基づいてflow_weightを更新する"""
        self.history.append(self.flow_weight)
        if success:
            self.flow_weight = self.flow_weight + WEIGHT_INCREASE_RATE * (1.0 - self.flow_weight)
        else:
            self.flow_weight = self.flow_weight * WEIGHT_DECREASE_RATE

        # 数値安定のためにクランプ
        self.flow_weight = max(0.01, min(0.99, self.flow_weight))

    def to_dict(self) -> dict:
        return {
            "from_node": self.from_node,
            "to_node": self.to_node,
            "flow_weight": self.flow_weight,
            "history": self.history,
        }


class AdaptiveNode:
    """可変ネットワークの各ノード"""

    def __init__(self, node_id: int):
        self.node_id = node_id

    def process_as_analyzer(self, world_rule: str, question: str, context: str = "") -> str:
        """ルール解析ノードとして動作"""
        system = "あなたはワールドルールを分析する専門家です。簡潔に回答してください。"
        prompt = (
            f"ワールドルール：{world_rule}\n"
            f"文章：「{question}」\n"
            f"{f'前のノードの分析: {context}' if context else ''}\n"
            f"このルールの核心と文章との関係を一文で分析してください。"
        )
        return call_ollama(prompt, system)

    def process_as_validator(self, rule_context: str, question: str, prev_analysis: str = "") -> str:
        """検証ノードとして動作"""
        system = "あなたは論理検証の専門家です。簡潔に回答してください。"
        prompt = (
            f"ルールの文脈：{rule_context}\n"
            f"文章：「{question}」\n"
            f"{f'前の分析: {prev_analysis}' if prev_analysis else ''}\n"
            f"文章はルールと整合していますか？一文で判断してください。"
        )
        return call_ollama(prompt, system)

    def process_as_judge(self, all_context: str, question: str) -> str:
        """最終判定ノードとして動作"""
        system = "「矛盾しない」または「矛盾する」とだけ答えてください。"
        prompt = (
            f"これまでの分析：{all_context}\n"
            f"元の文章：「{question}」\n"
            f"最終判定：「矛盾しない」または「矛盾する」のどちらか一つだけ答えてください。"
        )
        return call_ollama(prompt, system)


class AdaptiveNetwork:
    """
    可変構造ネットワーク
    Node1 ⇄ Node2 ⇄ Node3 の双方向接続
    flow_weightが高い接続が優先される
    """

    def __init__(self):
        self.nodes = {
            1: AdaptiveNode(1),
            2: AdaptiveNode(2),
            3: AdaptiveNode(3),
        }

        # 双方向接続の初期化
        self.connections: Dict[Tuple[int, int], Connection] = {
            (1, 2): Connection(1, 2),
            (2, 1): Connection(2, 1),
            (2, 3): Connection(2, 3),
            (3, 2): Connection(3, 2),
            (1, 3): Connection(1, 3),  # スキップ接続
            (3, 1): Connection(3, 1),  # スキップ接続（逆方向）
        }

        # 実験ログ
        self.weight_log: List[dict] = []

    def _get_active_path(self) -> List[Tuple[int, int]]:
        """
        現在のflow_weightに基づいて最適な処理パスを選択する
        高いflow_weightの接続が優先される
        """
        # 前進パスの候補: (1→2→3) vs (1→3) ショートカット
        path_full = [(1, 2), (2, 3)]
        path_short = [(1, 3)]

        weight_full = min(
            self.connections[(1, 2)].flow_weight,
            self.connections[(2, 3)].flow_weight,
        )
        weight_short = self.connections[(1, 3)].flow_weight

        if weight_full >= weight_short:
            return path_full
        else:
            return path_short

    def _should_use_feedback(self) -> bool:
        """逆方向フィードバック（Node3→Node2 or Node2→Node1）を使うか判定"""
        feedback_weight = self.connections[(3, 2)].flow_weight
        return feedback_weight > 0.5

    def predict(self, world_rule: str, question: str) -> dict:
        """
        flow_weightに基づく動的パスで予測する
        Returns: {
            'prediction': bool,
            'raw_output': str,
            'path_used': list,
            'node_results': list,
            'used_feedback': bool,
        }
        """
        active_path = self._get_active_path()
        use_feedback = self._should_use_feedback()
        node_outputs = {}
        node_results = []

        try:
            if active_path == [(1, 3)]:
                # ショートカットパス: Node1 → Node3
                output1 = self.nodes[1].process_as_analyzer(world_rule, question)
                node_outputs[1] = output1
                node_results.append({"node": 1, "output": output1, "role": "analyzer"})

                final_output = self.nodes[3].process_as_judge(output1, question)
                node_outputs[3] = final_output
                node_results.append({"node": 3, "output": final_output, "role": "judge"})

            else:
                # フルパス: Node1 → Node2 → Node3
                output1 = self.nodes[1].process_as_analyzer(world_rule, question)
                node_outputs[1] = output1
                node_results.append({"node": 1, "output": output1, "role": "analyzer"})

                output2 = self.nodes[2].process_as_validator(output1, question)
                node_outputs[2] = output2
                node_results.append({"node": 2, "output": output2, "role": "validator"})

                # フィードバックループが有効な場合: Node2の結果をNode1に戻して再解析
                if use_feedback:
                    refined_output1 = self.nodes[1].process_as_analyzer(
                        world_rule, question, context=output2
                    )
                    node_outputs[1] = refined_output1
                    node_results.append({"node": 1, "output": refined_output1, "role": "re-analyzer"})
                    all_context = f"{refined_output1} | {output2}"
                else:
                    all_context = f"{output1} | {output2}"

                final_output = self.nodes[3].process_as_judge(all_context, question)
                node_outputs[3] = final_output
                node_results.append({"node": 3, "output": final_output, "role": "judge"})

        except Exception as e:
            final_output = f"ERROR: {e}"
            node_results.append({"node": "error", "output": final_output, "role": "error"})

        prediction = self._parse_prediction(final_output)

        return {
            "prediction": prediction,
            "raw_output": final_output,
            "path_used": active_path,
            "node_results": node_results,
            "used_feedback": use_feedback,
            "flow_weights": self.get_weights_snapshot(),
        }

    def update_weights(self, success: bool, path_used: List[Tuple[int, int]], used_feedback: bool):
        """予測結果に基づいてflow_weightを更新する"""
        # 使用したパスの接続を更新
        for edge in path_used:
            if edge in self.connections:
                self.connections[edge].update_weight(success)

        # フィードバックループの接続も更新
        if used_feedback:
            self.connections[(3, 2)].update_weight(success)
            self.connections[(2, 1)].update_weight(success)

        # 使用しなかった接続は逆方向に緩やかに更新
        # （使わないルートは少しずつ減衰）
        for key, conn in self.connections.items():
            if key not in path_used:
                if not (used_feedback and key in [(3, 2), (2, 1)]):
                    # 非常に緩やかな減衰
                    conn.flow_weight = conn.flow_weight * 0.99

        # ウェイトをログに記録
        self.weight_log.append(self.get_weights_snapshot())

    def get_weights_snapshot(self) -> dict:
        """現在のflow_weightのスナップショットを取得"""
        return {
            f"{k[0]}->{k[1]}": round(v.flow_weight, 4)
            for k, v in self.connections.items()
        }

    def get_weight_history(self) -> dict:
        """全接続のweight履歴を取得"""
        return {
            f"{k[0]}->{k[1]}": v.history
            for k, v in self.connections.items()
        }

    def _parse_prediction(self, output: str) -> bool:
        """出力テキストから予測値を取得する"""
        if "矛盾しない" in output:
            return True
        if "矛盾する" in output:
            return False
        return False


if __name__ == "__main__":
    network = AdaptiveNetwork()
    result = network.predict(
        world_rule="この世界では空は緑色である",
        question="空を見上げると緑色が広がっていた",
    )
    print(f"予測: {'矛盾しない' if result['prediction'] else '矛盾する'}")
    print(f"パス: {result['path_used']}")
    print(f"フィードバック使用: {result['used_feedback']}")
    print(f"flow_weights: {result['flow_weights']}")

    # 成功として更新
    network.update_weights(True, result["path_used"], result["used_feedback"])
    print(f"更新後weights: {network.get_weights_snapshot()}")

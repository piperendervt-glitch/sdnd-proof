"""
test_task_generator.py
task_generator.py のユニットテスト
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from task_generator import generate_tasks, format_prompt, Task, WORLD_RULES, SENTENCES


class TestGenerateTasks:
    def test_generates_100_tasks(self):
        tasks = generate_tasks()
        assert len(tasks) == 100, f"期待: 100問, 実際: {len(tasks)}問"

    def test_50_consistent_50_inconsistent(self):
        tasks = generate_tasks()
        consistent = [t for t in tasks if t.label is True]
        inconsistent = [t for t in tasks if t.label is False]
        assert len(consistent) == 50, f"矛盾しない: {len(consistent)}問"
        assert len(inconsistent) == 50, f"矛盾する: {len(inconsistent)}問"

    def test_task_ids_are_unique(self):
        tasks = generate_tasks()
        ids = [t.task_id for t in tasks]
        assert len(ids) == len(set(ids)), "task_idに重複があります"

    def test_task_ids_sequential(self):
        tasks = generate_tasks()
        for i, task in enumerate(tasks):
            assert task.task_id == i, f"task_id={task.task_id}, 期待={i}"

    def test_all_tasks_have_world_rule(self):
        tasks = generate_tasks()
        for task in tasks:
            assert task.world_rule, f"task_id={task.task_id}: world_ruleが空です"
            assert task.world_rule in WORLD_RULES, \
                f"task_id={task.task_id}: 未知のworld_rule={task.world_rule}"

    def test_all_tasks_have_question(self):
        tasks = generate_tasks()
        for task in tasks:
            assert task.question, f"task_id={task.task_id}: questionが空です"
            assert len(task.question) > 5, f"task_id={task.task_id}: questionが短すぎます"

    def test_labels_are_bool(self):
        tasks = generate_tasks()
        for task in tasks:
            assert isinstance(task.label, bool), \
                f"task_id={task.task_id}: labelがboolではありません ({type(task.label)})"

    def test_reproducibility(self):
        """同じ順序で生成されること"""
        tasks1 = generate_tasks()
        tasks2 = generate_tasks()
        for t1, t2 in zip(tasks1, tasks2):
            assert t1.task_id == t2.task_id
            assert t1.question == t2.question
            assert t1.label == t2.label

    def test_covers_all_world_rules(self):
        tasks = generate_tasks()
        used_rules = set(t.world_rule for t in tasks)
        for rule in WORLD_RULES:
            assert rule in used_rules, f"ルールが使われていません: {rule}"

    def test_each_rule_has_20_tasks(self):
        tasks = generate_tasks()
        from collections import Counter
        rule_counts = Counter(t.world_rule for t in tasks)
        for rule in WORLD_RULES:
            assert rule_counts[rule] == 20, \
                f"ルール '{rule[:20]}...' のタスク数: {rule_counts[rule]} (期待: 20)"


class TestFormatPrompt:
    def test_format_contains_rule(self):
        task = Task(0, "テスト文章", True, "この世界では空は緑色である")
        prompt = format_prompt(task)
        assert "この世界では空は緑色である" in prompt

    def test_format_contains_question(self):
        task = Task(0, "テスト文章", True, "この世界では空は緑色である")
        prompt = format_prompt(task)
        assert "テスト文章" in prompt

    def test_format_contains_instructions(self):
        task = Task(0, "テスト文章", True, "この世界では空は緑色である")
        prompt = format_prompt(task)
        assert "矛盾" in prompt

    def test_format_is_string(self):
        task = Task(0, "テスト文章", True, "この世界では空は緑色である")
        prompt = format_prompt(task)
        assert isinstance(prompt, str)
        assert len(prompt) > 20


class TestTask:
    def test_task_creation(self):
        task = Task(
            task_id=0,
            question="テスト",
            label=True,
            world_rule="テストルール",
        )
        assert task.task_id == 0
        assert task.question == "テスト"
        assert task.label is True
        assert task.world_rule == "テストルール"

    def test_task_label_false(self):
        task = Task(0, "テスト", False, "ルール")
        assert task.label is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

import unittest
import uuid
import sys
import os

# Project root (one level above this file)
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

# Add project root to Python path
sys.path.append(PROJECT_ROOT)

from lxml import etree as ET

from utils.process_io import (
    load_process,
    save_process
)

from change_operations.operations import *

from utils.change_operations_utils import (
    find_unique_by_label,
    get_label
)

# Dynamic paths
TEST_PROCESS = os.path.join(
    PROJECT_ROOT,
    "to_test_change_operations",
    "to_test_change_operations.xml"
)

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "test_results"
)

class TestChangeOperations(unittest.TestCase):

    # =====================================================
    # LOGGING
    # =====================================================

    def setUp(self):

        print("\n" + "=" * 70)
        print(f"RUNNING TEST: {self._testMethodName}")
        print("=" * 70)

    def tearDown(self):

        print(f"FINISHED: {self._testMethodName}")

    def log(self, message):

        print(f"[INFO] {message}")

    def print_change(self, change):

        print("[CHANGE]")
        for k, v in change.items():
            print(f"  {k}: {v}")

    # =====================================================
    # LOAD PROCESS
    # =====================================================

    def load(self):
        return load_process(TEST_PROCESS)

    # =====================================================
    # SAVE RESULT TREE
    # =====================================================

    def save_result(self, tree):

        os.makedirs(OUTPUT_DIR, exist_ok=True)

        output_file = os.path.join(
            OUTPUT_DIR,
            f"{self._testMethodName}.xml"
        )

        save_process(tree, output_file)

        print(f"[SAVED] {output_file}")

    # =====================================================
    # BASIC STRUCTURAL CHANGES
    # =====================================================

    def test_insert_after_label(self):

        tree, root = self.load()

        node = clone_call_template(
            root,
            f"n_{uuid.uuid4().hex[:6]}",
            "NEW"
        )

        change = insert_after_label(root, "A", node)

        self.print_change(change)

        self.save_result(tree)

        self.assertIsNotNone(
            find_unique_by_label(root, "NEW")
        )

    def test_insert_before_label(self):

        tree, root = self.load()

        node = clone_call_template(
            root,
            f"n_{uuid.uuid4().hex[:6]}",
            "NEW"
        )

        change = insert_before_label(root, "A", node)

        self.print_change(change)

        self.save_result(tree)

        self.assertIsNotNone(
            find_unique_by_label(root, "NEW")
        )

    def test_remove_by_label(self):

        tree, root = self.load()

        change = remove_by_label(root, "C")

        self.print_change(change)

        self.save_result(tree)

        with self.assertRaises(ValueError):
            find_unique_by_label(root, "C")

    def test_rename_by_label(self):

        tree, root = self.load()

        change = rename_by_label(root, "A", "A_NEW")

        self.print_change(change)

        self.save_result(tree)

        self.assertIsNotNone(
            find_unique_by_label(root, "A_NEW")
        )

    def test_move_after_label(self):

        tree, root = self.load()

        change = move_after_label(root, "A", "C")

        self.print_change(change)

        self.save_result(tree)

        self.assertIsNotNone(
            find_unique_by_label(root, "A")
        )

    def test_move_before_label(self):

        tree, root = self.load()

        change = move_before_label(root, "C", "A")

        self.print_change(change)

        self.save_result(tree)

        self.assertIsNotNone(
            find_unique_by_label(root, "C")
        )

    def test_swap_by_label(self):

        tree, root = self.load()

        change = swap_by_label(root, "A", "B")

        self.print_change(change)

        self.save_result(tree)

        self.assertIsNotNone(
            find_unique_by_label(root, "A")
        )

    def test_copy_after_label(self):

        tree, root = self.load()

        change = copy_after_label(root, "A", "C")

        self.print_change(change)

        self.save_result(tree)

        matches = []

        for node in root.iter():
            try:
                if get_label(node) == "A":
                    matches.append(node)
            except:
                pass

        self.assertEqual(len(matches), 2)

    def test_copy_before_label(self):

        tree, root = self.load()

        change = copy_before_label(root, "A", "B")

        self.print_change(change)

        self.save_result(tree)

        matches = []

        for node in root.iter():
            try:
                if get_label(node) == "A":
                    matches.append(node)
            except:
                pass

        self.assertEqual(len(matches), 2)

    # =====================================================
    # MERGE / SPLIT
    # =====================================================

    def test_merge_by_label(self):

        tree, root = self.load()

        change = merge_by_label(root, "R", "T")

        self.print_change(change)

        self.save_result(tree)

        self.assertIsNotNone(
            find_unique_by_label(root, "R and T")
        )

    def test_split_by_label(self):

        tree, root = self.load()

        change = split_by_label(root, "U and V")

        self.print_change(change)

        self.save_result(tree)

        self.assertIsNotNone(
            find_unique_by_label(root, "U")
        )

        self.assertIsNotNone(
            find_unique_by_label(root, "V")
        )

    # =====================================================
    # XOR
    # =====================================================

    def test_modify_condition_by_label(self):

        tree, root = self.load()

        change = modify_condition_by_label(
            root,
            "D",
            "data.changed"
        )

        self.print_change(change)

        self.save_result(tree)

        alternatives = root.xpath(
            ".//d:alternative",
            namespaces=NS
        )

        conditions = [
            alt.get("condition")
            for alt in alternatives
        ]

        self.assertIn(
            "data.changed",
            conditions
        )

    def test_add_branch_to_xor(self):

        tree, root = self.load()

        change = add_branch_to_xor(
            root,
            "data.condition1",
            "data.new",
            "NEW_ACTIVITY"
        )

        self.print_change(change)

        self.save_result(tree)

        self.assertIsNotNone(
            find_unique_by_label(
                root,
                "NEW_ACTIVITY"
            )
        )

    def test_remove_branch_by_condition(self):

        tree, root = self.load()

        change = remove_branch_by_condition(
            root,
            "data.condition1"
        )

        self.print_change(change)

        self.save_result(tree)

        with self.assertRaises(ValueError):
            find_unique_by_label(root, "D")

    def test_embed_activity_in_new_xor(self):

        tree, root = self.load()

        change = embed_activity_in_new_xor(
            root,
            "A",
            "data.embed",
            mode="skip"
        )

        self.print_change(change)

        self.save_result(tree)

        chooses = root.xpath(
            ".//d:choose",
            namespaces=NS
        )

        self.assertTrue(len(chooses) > 0)

    # =====================================================
    # PARALLEL
    # =====================================================

    def test_parallelize(self):

        tree, root = self.load()

        parallelize_by_label_test(
            root,
            "W",
            "X"
        )

        self.save_result(tree)

        parallels = root.xpath(
            ".//d:parallel",
            namespaces=NS
        )

        self.assertTrue(len(parallels) > 0)

    def test_sequentialize_parallel(self):

        tree, root = self.load()

        change = sequentialize_parallel_activities(
            root,
            "G",
            "H"
        )

        self.print_change(change)

        self.save_result(tree)

        self.assertIsNotNone(
            find_unique_by_label(root, "G")
        )

    def test_remove_branch_by_activity_label(self):

        tree, root = self.load()

        change = remove_branch_by_activity_label(
            root,
            "G"
        )

        self.print_change(change)

        self.save_result(tree)

        with self.assertRaises(ValueError):
            find_unique_by_label(root, "G")

    # =====================================================
    # LOOPS
    # =====================================================

    def test_embed_pre_loop(self):

        tree, root = self.load()

        change = embed_fragment_in_pre_loop(
            root,
            "A",
            "B",
            "data.loop"
        )

        self.print_change(change)

        self.save_result(tree)

        loops = root.xpath(
            ".//d:loop",
            namespaces=NS
        )

        self.assertTrue(len(loops) > 0)

    def test_embed_post_loop(self):

        tree, root = self.load()

        change = embed_fragment_in_post_loop(
            root,
            "B",
            "C",
            "data.loop"
        )

        self.print_change(change)

        self.save_result(tree)

        loops = root.xpath(
            ".//d:loop",
            namespaces=NS
        )

        self.assertTrue(len(loops) > 0)

    def test_remove_loop_by_activity(self):

        tree, root = self.load()

        change = remove_loop_by_activity_label(
            root,
            "M"
        )

        self.print_change(change)

        self.save_result(tree)

        loops = root.xpath(
            ".//d:loop",
            namespaces=NS
        )

        self.assertEqual(len(loops), 1)

    def test_modify_loop_condition(self):

        tree, root = self.load()

        change = modify_loop_condition_by_activity(
            root,
            "M",
            "data.changed"
        )

        self.print_change(change)

        self.save_result(tree)

        loops = root.xpath(
            ".//d:loop",
            namespaces=NS
        )

        conditions = [
            l.get("condition")
            for l in loops
        ]

        self.assertIn(
            "data.changed",
            conditions
        )

    # =====================================================
    # RESOURCE / DATA
    # =====================================================

    def test_modify_resource(self):

        tree, root = self.load()

        change = modify_resource_by_label(
            root,
            "A",
            "NEW_RESOURCE"
        )

        self.print_change(change)

        self.save_result(tree)

        activity = find_unique_by_label(root, "A")

        resource = activity.find(
            ".//{*}Resource"
        )

        self.assertEqual(
            resource.text,
            "NEW_RESOURCE"
        )

    def test_modify_write(self):

        tree, root = self.load()

        change = modify_write_by_label(
            root,
            "A",
            "data.y = 1"
        )

        self.print_change(change)

        self.save_result(tree)

        activity = find_unique_by_label(root, "A")

        finalize = activity.find(
            ".//{*}finalize"
        )

        self.assertIn(
            "data.y",
            finalize.text
        )

    def test_add_write(self):

        tree, root = self.load()

        change = add_write_by_label(
            root,
            "A",
            "data.z = 2"
        )

        self.print_change(change)

        self.save_result(tree)

        activity = find_unique_by_label(root, "A")

        finalize = activity.find(
            ".//{*}finalize"
        )

        self.assertIn(
            "data.z",
            finalize.text
        )

    def test_remove_write(self):

        tree, root = self.load()

        change = remove_write_by_label(
            root,
            "A",
            "data.x"
        )

        self.print_change(change)

        self.save_result(tree)

        activity = find_unique_by_label(root, "A")

        finalize = activity.find(
            ".//{*}finalize"
        )

        self.assertNotIn(
            "data.x",
            finalize.text or ""
        )

    def test_modify_read(self):

        tree, root = self.load()

        change = modify_read_by_label(
            root,
            "A",
            "data.x",
            "data.changed"
        )

        self.print_change(change)

        self.save_result(tree)

        activity = find_unique_by_label(root, "A")

        finalize = activity.find(
            ".//{*}finalize"
        )

        self.assertIn(
            "data.changed",
            finalize.text
        )

    # =====================================================
    # TIMEOUT
    # =====================================================

    def test_modify_timeout(self):

        tree, root = self.load()

        change = modify_timeout_by_label(
            root,
            "Q",
            1200
        )

        self.print_change(change)

        self.save_result(tree)

        activity = find_unique_by_label(root, "Q")

        timeout = activity.find(
            ".//{*}timeout"
        )

        self.assertEqual(
            timeout.text,
            "1200"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
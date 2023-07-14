import unittest

from shtool import ShellTool


class TestShellTool(unittest.TestCase):
    def setUp(self):
        self.shell_tool = ShellTool()

    def test_persistence(self):
        # Test initial working directory
        initial_dir = self.shell_tool("pwd").strip()
        self.assertTrue(initial_dir)

        # Change directory
        self.shell_tool("cd ..")

        # Check if change persisted
        changed_dir = self.shell_tool("pwd").strip()
        self.assertNotEqual(initial_dir, changed_dir)

        # Change back to initial directory
        self.shell_tool(f"cd {initial_dir}")

        # Check if change persisted
        final_dir = self.shell_tool("pwd").strip()
        self.assertEqual(initial_dir, final_dir)


if __name__ == "__main__":
    unittest.main()

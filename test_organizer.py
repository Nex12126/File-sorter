import tempfile
import unittest
from pathlib import Path

from organizer import apply_plan, build_plan, count_protected_files


class BuildPlanTests(unittest.TestCase):
    def test_groups_same_names_across_types_and_copy_variants(self):
        with tempfile.TemporaryDirectory() as temporary_folder:
            folder = Path(temporary_folder)
            for filename in ("Urlaub.jpg", "Urlaub.txt", "Urlaub (1).jpg", "Notizen.pdf"):
                (folder / filename).touch()

            plan = build_plan(folder)
            destinations = {move.source.name: move.destination for move in plan}

            self.assertEqual(destinations["Urlaub.jpg"].parent, destinations["Urlaub.txt"].parent)
            self.assertEqual(destinations["Urlaub.jpg"].parent, destinations["Urlaub (1).jpg"].parent)
            self.assertEqual(destinations["Notizen.pdf"].parent.name, "Documents")

    def test_existing_destination_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary_folder:
            folder = Path(temporary_folder)
            (folder / "Unsorted" / "Documents").mkdir(parents=True)
            (folder / "Unsorted" / "Documents" / "Notizen.pdf").touch()
            (folder / "Notizen.pdf").touch()

            plan = build_plan(folder)

            self.assertEqual(plan[0].destination.name, "Notizen (2).pdf")
            self.assertEqual(plan[0].destination.parent.name, "Documents")

    def test_rules_route_screenshots_and_school_subjects(self):
        with tempfile.TemporaryDirectory() as temporary_folder:
            folder = Path(temporary_folder)
            (folder / "Screenshot_2026.png").touch()
            (folder / "Mathe_Analysis.pdf").touch()
            (folder / "random-file.xyz").touch()

            plan = build_plan(folder)
            destinations = {move.source.name: move.destination for move in plan}

            self.assertEqual(destinations["Screenshot_2026.png"].parent.relative_to(folder).as_posix(), "Media/Screenshots")
            self.assertEqual(destinations["Mathe_Analysis.pdf"].parent.relative_to(folder).as_posix(), "Education/Mathematics")
            self.assertEqual(destinations["random-file.xyz"].parent.relative_to(folder).as_posix(), "Unsorted/Other")

    def test_app_files_shortcuts_and_scripts_are_not_moved(self):
        with tempfile.TemporaryDirectory() as temporary_folder:
            folder = Path(temporary_folder)
            for filename in ("setup.exe", "start.lnk", "install.bat", "tool.dll", "keep.pdf"):
                (folder / filename).touch()

            plan = build_plan(folder)

            self.assertEqual([move.source.name for move in plan], ["keep.pdf"])
            self.assertEqual(count_protected_files(folder), 4)
            self.assertEqual(apply_plan(plan), 1)
            self.assertTrue((folder / "keep.pdf").exists() is False)
            self.assertTrue((folder / "Unsorted" / "Documents" / "keep.pdf").is_file())
            self.assertTrue((folder / "setup.exe").is_file())
            self.assertTrue((folder / "start.lnk").is_file())


if __name__ == "__main__":
    unittest.main()
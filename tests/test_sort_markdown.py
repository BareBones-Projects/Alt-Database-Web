# BareBones Projects, Designed by: Justin Levesque-Welsch.
import json
import tempfile
import unittest
from pathlib import Path
from tools.sort_markdown import classify, process, slugify

class IntakeTests(unittest.TestCase):
    def test_explicit_section_wins(self):
        self.assertEqual(classify('planet', '---\nsection: fandom-db\n---\n# Planet', '')[0], 'fandom-db')

    def test_character_goes_to_fandom(self):
        self.assertEqual(classify('Remedy', '# Remedy\nCharacter and faction biography', '')[0], 'fandom-db')

    def test_planet_goes_to_alt(self):
        self.assertEqual(classify('primus', '# Primus\nPlanet orbit and star system.', '')[0], 'alt-db')

    def test_encyclopedia_goes_to_wiki(self):
        self.assertEqual(classify('terminology', '# Terminology\nGlossary and reference', '')[0], 'wiki-db')

    def test_ambiguous_requires_review(self):
        self.assertTrue(classify('notes', '# Miscellaneous notes', '')[2])

    def test_filename_sanitization(self):
        self.assertEqual(slugify('../../BAD Name'), 'bad-name')

    def test_process_generates_copies_and_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            incoming = root / 'in'
            incoming.mkdir()
            (incoming / 'Bones.md').write_text('# Bones\nCharacter biography', encoding='utf8')
            (incoming / 'Atlas.md').write_text('---\nsection: alt-db\n---\n# Atlas', encoding='utf8')
            (incoming / 'notes.txt').write_text('ignore')
            output = root / 'out'
            manifest = process(incoming, output)
            self.assertEqual(len(manifest['files']), 2)
            self.assertTrue((output / 'fandom-db' / 'bones.md').exists())
            self.assertTrue((output / 'alt-db' / 'atlas.md').exists())
            self.assertEqual((incoming / 'Bones.md').read_bytes(), (output / 'fandom-db' / 'bones.md').read_bytes())
            self.assertEqual(json.loads((output / 'manifest.json').read_text())['files'], manifest['files'])

    def test_duplicate_slug_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            incoming = root / 'in'
            incoming.mkdir()
            (incoming / 'One.md').write_text('---\nsection: wiki-db\nslug: same\n---\n# One')
            (incoming / 'Two.md').write_text('---\nsection: wiki-db\nslug: same\n---\n# Two')
            with self.assertRaisesRegex(ValueError, 'Duplicate destination'):
                process(incoming, root / 'out')

    def test_unsupported_section_requires_review(self):
        self.assertTrue(classify('x', '---\nsection: ../../../other\n---\n# Example', '')[2])

if __name__ == '__main__':
    unittest.main()

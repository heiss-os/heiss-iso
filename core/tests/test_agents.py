import os
import re
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR = os.path.join(REPO, ".claude", "agents")
EXPECTED = {"reviewer", "security-reviewer", "qa-verifier", "docs-keeper"}
READ_ONLY_TOOLS = {"Read", "Grep", "Glob", "Bash"}


def parse(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "%s: no front matter" % path
    meta = {}
    for line in m.group(1).splitlines():
        k, sep, v = line.partition(":")
        assert sep, "%s: bad front matter line %r" % (path, line)
        meta[k.strip()] = v.strip()
    return meta, text[m.end():], text


class Agents(unittest.TestCase):
    def files(self):
        return sorted(os.path.join(DIR, f) for f in os.listdir(DIR) if f.endswith(".md"))

    def test_the_expected_agents_exist(self):
        names = {parse(p)[0]["name"] for p in self.files()}
        self.assertEqual(names, EXPECTED)

    def test_front_matter_is_valid_and_names_are_unique(self):
        seen = set()
        for p in self.files():
            meta, body, _ = parse(p)
            self.assertEqual(set(meta), {"name", "description", "tools", "model"}, p)
            self.assertEqual(meta["name"] + ".md", os.path.basename(p))
            self.assertRegex(meta["name"], r"^[a-z][a-z-]*$")
            self.assertNotIn(meta["name"], seen)
            seen.add(meta["name"])
            self.assertGreater(len(meta["description"]), 40, p)
            self.assertTrue(body.strip(), p)

    def test_agents_are_read_only_by_tools(self):
        for p in self.files():
            tools = {t.strip() for t in parse(p)[0]["tools"].split(",")}
            self.assertEqual(tools, READ_ONLY_TOOLS, p)      # no Edit, Write, NotebookEdit

    def test_no_tabs_and_each_says_it_is_read_only_and_ends_with_a_verdict(self):
        for p in self.files():
            _, body, text = parse(p)
            self.assertNotIn("\t", text, p)
            self.assertIn("read-only", body, p)
            self.assertIn("never edit", body.lower(), p)
            self.assertIn("Verdict:", body, p)
            for sev in ("HIGH", "MEDIUM", "LOW"):
                self.assertIn(sev, body, p)

    def test_claude_md_lists_every_agent_and_the_rules(self):
        with open(os.path.join(REPO, "CLAUDE.md"), encoding="utf-8") as f:
            text = f.read()
        for name in EXPECTED:
            self.assertIn("`%s`" % name, text, name)
        self.assertIn("агенты: reviewer ok, security ok, qa ok, docs ok", text)


if __name__ == "__main__":
    unittest.main()

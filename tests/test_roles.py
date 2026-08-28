import unittest
from riftsense.draft.roles import canonical_role, role_display
class RoleTests(unittest.TestCase):
    def test_raw_roles(self):
        self.assertEqual(canonical_role("MIDDLE"),"MID"); self.assertEqual(canonical_role("BOTTOM"),"ADC"); self.assertEqual(canonical_role("UTILITY"),"SUPPORT")
    def test_display(self): self.assertEqual(role_display("MID"),"Mid")

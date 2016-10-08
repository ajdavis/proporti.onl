import unittest

from analyze import declared_gender


class TestDeclaredGender(unittest.TestCase):
    def test_declared_gender(self):
        for description, expected_gender in [
            ('pronoun: she', 'female'),
            ('she,her', 'female'),
            ('she/her', 'female'),
            ('she/her/hers', 'female'),
            ('she,her,hers', 'female'),
            ('pronouns: she/her', 'female'),
            ('i am a nonbinary person', 'nonbinary'),
            ('hi i\'m non-binary', 'nonbinary'),
            ('non binary human', 'nonbinary'),
            ('just a guy living life', 'male'),
            ('a southern gal', 'female'),
            ('he', 'male'),
            ('he/him', 'male'),
            ('he,him', 'male'),
            ('he/his', 'male'),
            ('he,his', 'male'),
            ('he is a man', 'male'),
            ('i go by they', 'nonbinary'),
            ('them/they', 'nonbinary'),
            ('them,they', 'nonbinary'),
            ('xe', 'nonbinary'),
            ('ze', 'nonbinary'),
            ('zie', 'nonbinary'),
            ('hir', 'nonbinary'),
            ('pronoun.is/she', 'female'),
            ('pronoun.is/he', 'male'),
            ('pronoun.is/they', 'nonbinary'),
            ('pronoun.is/foo', 'nonbinary'),
            ('pronoun.is/zie', 'nonbinary'),
            ('pronoun.is/hir', 'nonbinary'),
            ('the empire state building', 'andy'),
        ]:
            guess = declared_gender(description)
            assert guess == expected_gender, (
                "Should have guessed profile '%s' was '%s', not '%s'" % (
                    description, expected_gender, guess))

"""igkit: the shared library behind the creator-content-kit skills.

Standard library only. Python 3.8+.

Modules
  paths     where the core, its config and the creator's data live
  schema    a small JSON-Schema-subset validator
  text      tokenising, sentence stats, emoji/hashtag/link detection, speech timing
  lexicon   the slop / hedge / greeting / spam term lists and invisible characters
  claims    finds numbers and achievement claims, checks them against verified facts
  features  named text features that rubrics score
  engine    the JSON-rubric scoring engine
  profile   loading and checking the shared creator profile
  report    plain-text formatting helpers
"""

__version__ = "1.0.0"

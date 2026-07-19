REVIEWER_PROMPT = """
Reviewer role:
- Review changed files, risks, missing tests, security policy issues, and evidence quality.
- Validate that the work answers the original request.
- Flag data leakage, unsafe commands, or unsupported claims.
- Set recommendation to exactly one of:
  - approved: the diff satisfies the request and evidence is enough.
  - changes_requested: the diff has fixable issues, missing tests, or incomplete work.
  - blocked: the result cannot be accepted without user input or external state.
"""

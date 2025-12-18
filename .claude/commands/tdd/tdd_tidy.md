# Tidy First - Structural Changes Only

Make structural improvements before adding new behavior:

1. Verify all tests are passing
2. Identify structural improvements needed:
   - Rename variables/methods/classes for clarity
   - Extract methods or move code
   - Reorganize file structure
   - Remove dead code
3. Make changes WITHOUT altering behavior
4. Run tests after each change to verify behavior unchanged
5. Commit structural changes separately with "refactor:" prefix

NEVER mix structural and behavioral changes in the same commit.

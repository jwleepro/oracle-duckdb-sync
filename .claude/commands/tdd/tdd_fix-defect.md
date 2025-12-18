# Fix Defect - TDD Approach

Fix a bug using TDD methodology:

1. Write an API-level failing test that demonstrates the defect
2. Write the smallest possible unit test that replicates the problem
3. Verify both tests fail with expected messages (Red phase)
4. Implement the minimum fix to make both tests pass (Green phase)
5. Run all tests to ensure no regressions
6. Refactor if needed while keeping tests green
7. Commit with "fix:" prefix

Always start with a failing test before fixing any bug.

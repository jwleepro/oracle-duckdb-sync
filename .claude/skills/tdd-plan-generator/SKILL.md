---
name: tdd-plan-generator
description: Generate development plan (plan.md) from CLAUDE.md and PRD with test IDs and requirement cross-references. Use when user asks to create or update plan.md, generate test plan, or mentions CLAUDE.md and prd.md together.
allowed-tools: Read, Write, Glob
---

# TDD Plan Generator

## Purpose
Automatically generate a structured development plan (plan.md) by analyzing:
- CLAUDE.md (TDD and Tidy First methodology)
- prd.md or docs/prd.md (Product Requirements Document)

## Instructions

1. **Locate and read source files**:
   - Read CLAUDE.md from project root
   - Search for prd.md (check both root directory and docs/ subdirectory)
   - If files don't exist, inform user and exit

2. **Extract requirements from PRD**:
   - Identify all functional requirements (FR-XXX format)
   - Extract requirement descriptions and details
   - Note technical stack, constraints, and non-functional requirements
   - Understand project scope and objectives

3. **Generate plan structure**:
   - Follow TDD principles from CLAUDE.md (Red → Green → Refactor)
   - Create logical development phases
   - Break down each functional requirement (FR-XXX) into specific, testable increments
   - Assign sequential TEST-IDs starting from TEST-001
   - Each test should be small and focused on a single behavior

4. **Add cross-references**:
   - Link each test item to its corresponding PRD requirement (FR-XXX)
   - Include requirement context in test descriptions
   - Group related tests under the same development phase
   - Ensure traceability from requirements to tests

5. **Format output**:
   - Use markdown checklist format: `- [ ] **TEST-XXX** (Category): Description`
   - Include purpose/goal for each test: `*목표*: [Goal]`
   - Add requirement references: `*요구사항*: FR-XXX`
   - Follow the template structure from templates/plan-template.md
   - Use clear, descriptive test names that explain the behavior being tested

6. **Generate plan.md**:
   - Write the plan to project root as plan.md
   - Preserve Korean language if PRD is in Korean, English if PRD is in English
   - Maintain TDD cycle emphasis (Red → Green → Refactor)
   - Include core development principles section
   - Ensure all tests are initially unchecked (ready for TDD workflow)

## Expected Output Format

```markdown
# 개발 계획: Oracle-DuckDB 데이터 동기화 시스템

이 계획은 TDD 및 Tidy First 원칙에 따른 개발 프로세스를 개략적으로 설명합니다.
각 단계는 작고 검증 가능한 증분을 나타냅니다.

## 핵심 개발 원칙
- **TDD 주기**: Red(실패) -> Green(성공) -> Refactor(리팩터링)
- **Tidy First (정리 우선)**: 구조적 변경과 동작 변경을 분리합니다.
- **커밋**: 테스트가 통과하고 린팅에 문제가 없을 때만 커밋합니다.

## 1. 로컬 환경/기본 설정
> 기술적 전제조건 (PRD 요구사항 구현을 위한 기반)

- [ ] **TEST-001**: pytest 기본 실행 확인
- [ ] **TEST-002**: python-oracledb import 가능
- [ ] **TEST-003**: duckdb import 가능

---

## 2. 환경 설정(Config)
> 기술적 전제조건 (FR-001, FR-002 구현을 위한 기반)

- [ ] **TEST-010**: .env에서 Oracle 연결 정보 로드
- [ ] **TEST-011**: 필수 설정 누락 시 명확한 오류 메시지 반환

---

## 3. 동기화 엔진

- [ ] **TEST-070**: Oracle 전체 추출 → DuckDB 적재 파이프라인 (FR-001)
- [ ] **TEST-071**: 진행률·로그 기록 검증 (FR-001, FR-003)
- [ ] **TEST-080**: 마지막 동기화 시각 이후 데이터 조회 (FR-002)

...
```

## When to Use This Skill

Activate this Skill when user:
- Says "CLAUDE.md와 prd.md를 읽고, plan.md 생성해줘"
- Asks to "generate plan from PRD"
- Mentions "create development plan with test IDs"
- Requests "update plan.md from requirements"
- Says "make a test plan based on requirements"
- Asks to "create TDD plan from PRD"

## Key Guidelines

### Test Granularity
- Each test should verify ONE specific behavior
- Tests should be ordered from simple to complex
- Setup tests come before feature tests
- Integration tests come after unit-level tests

### Requirement Coverage
- Every functional requirement (FR-XXX) must have at least one test
- Complex requirements should be broken into multiple tests
- Tests should cover happy path, error cases, and edge cases

### Phase Organization
- Use numbered sections: `## 1. 섹션명` (not "1단계")
- Add blockquotes for technical prerequisites: `> 기술적 전제조건 (PRD 요구사항 구현을 위한 기반)`
- For prerequisites supporting specific FRs: `> 기술적 전제조건 (FR-001, FR-002 구현을 위한 기반)`
- Early phases: Setup, configuration, basic infrastructure
- Middle phases: Core features and business logic
- Later phases: Integration, UI, and end-to-end scenarios

### Test Format
- Basic format: `- [ ] **TEST-XXX**: 테스트 설명`
- With FR reference: `- [ ] **TEST-XXX**: 테스트 설명 (FR-XXX)`
- Multiple FRs: `- [ ] **TEST-XXX**: 테스트 설명 (FR-001, FR-003)`
- Technical prerequisite tests have NO FR reference

### Language Consistency
- Match the language of the PRD (Korean or English)
- Keep technical terms in original language
- Maintain consistent terminology throughout

## Notes

- Respect existing plan.md structure if updating (preserve checked items)
- Maintain language consistency with source documents
- Ensure test IDs are sequential and unique
- Always cross-reference requirements for traceability
- If PRD has non-functional requirements (NFR), consider adding tests for performance, scalability, etc.
- The plan should be comprehensive but not overwhelming - focus on logical increments

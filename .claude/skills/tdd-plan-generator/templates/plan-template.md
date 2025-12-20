# 개발 계획: [Project Name]

이 계획은 TDD 및 Tidy First 원칙에 따른 개발 프로세스를 개략적으로 설명합니다.
각 단계는 작고 검증 가능한 증분을 나타냅니다.

## 핵심 개발 원칙
- **TDD 주기**: Red(실패) -> Green(성공) -> Refactor(리팩터링)
- **Tidy First (정리 우선)**: 구조적 변경과 동작 변경을 분리합니다.
- **커밋**: 테스트가 통과하고 린팅에 문제가 없을 때만 커밋합니다.

## X. [Subsection Name - e.g., 로컬 환경/기본 설정]
> 기술적 전제조건 (PRD 요구사항 구현을 위한 기반)

- [ ] **TEST-00X**: [Test description for technical prerequisite]
- [ ] **TEST-00X**: [Test description for technical prerequisite]

---

## X. [Subsection Name - e.g., 데이터 소스]
> 기술적 전제조건 (FR-00X 구현을 위한 기반)

- [ ] **TEST-00X**: [Test description for technical prerequisite]
- [ ] **TEST-00X**: [Test description for technical prerequisite]

---

## X. [Subsection Name - e.g., UI/조회]

- [ ] **TEST-00X**: [Another test with functional requirement] (FR-00X)
- [ ] **TEST-00X**: [Another test with functional requirement] (FR-00X, FR-00X)

---

---

## 템플릿 작성 가이드

### 섹션 구성
- 번호 매기기: `## X. 섹션명`
- 기술적 전제조건: `> 기술적 전제조건 (PRD 요구사항 구현을 위한 기반)`
- 특정 FR 지원: `> 기술적 전제조건 (FR-00X 구현을 위한 기반)`

### 테스트 작성
- 기본 형식: `- [ ] **TEST-XXX**: 테스트 설명`
- FR 참조: `- [ ] **TEST-XXX**: 테스트 설명 (FR-XXX)`
- 기술적 전제조건 테스트는 FR 참조 생략
- TEST-ID는 순차적으로 001부터 시작

### 요구사항 매핑
- 기능 요구사항 테스트: FR-XXX를 괄호 안에 표시
- 인프라/환경 테스트: FR 참조 없이 작성
- 복수 요구사항: (FR-001, FR-003) 형식

글로벌 기업의 요구사항-문서 일관성 관리 방법

  말씀하신 문제(요구사항 ID 없는 테스트, 문서 일관성 깨짐)는 업계 전반의 공통 과제입니다. 글로벌 기업들이 이를 해결하는 방법을 정리했습니다.

  1. Google: Design Docs 중심 문화

  Google은 전통적인 SRS(요구사항 명세서)를 거의 사용하지 않습니다. 대신:

  - https://www.industrialempathy.com/posts/design-docs-at-google/: 구현 전 설계 문서 작성이 필수
  - 목표, 대안 설계, 트레이드오프를 명시
  - 보안, 국제화, 저장소, 프라이버시 검토가 템플릿에 포함
  - 설계 리뷰 회의를 통해 조직의 경험이 설계에 반영됨
  - https://google.github.io/eng-practices/에서 CL(Changelist) 단위로 추적

  핵심 철학: 상세한 요구사항 문서보다 설계 의도와 트레이드오프 기록에 집중

  ---
  2. Microsoft: Azure DevOps 양방향 추적성

  Microsoft는 https://learn.microsoft.com/en-us/azure/devops/cross-service/end-to-end-traceability?view=azure-devops 기능을 Azure DevOps에 내장했습니다:

  Work Item ↔ Branch ↔ Commit ↔ Pull Request ↔ Build ↔ Release

  주요 기능:
  - 양방향 추적성(Bi-directional): 요구사항 → 테스트 케이스 → 결함 (정방향/역방향 모두)
  - 테스트 결과가 자동으로 Work Item에 연결
  - https://learn.microsoft.com/en-us/azure/devops/pipelines/test/requirements-traceability?view=azure-devops 자동 생성
  - 대시보드 위젯으로 실시간 추적 현황 시각화

  ---
  3. Meta (Facebook): 경량 문서 + 강력한 도구 체인

  Meta는 "Move Fast" 문화로 유명하며, https://engineering.fb.com/에 따르면:

  - Phabricator: 코드 리뷰 + CI 도구 (Diff 단위 추적)
  - Workplace: 위키 + 문서 + 소셜 통합 플랫폼
  - https://engineering.fb.com/2025/08/11/security/federation-platform-privacy-waves-meta-distributes-compliance-tasks/: 컴플라이언스 작업을 구조화된 태스크로 관리
    - "wizard-like workflow"로 작업 안내
    - 명확한 기한, 문서 링크, 해결 단계 포함

  핵심: 무거운 요구사항 문서 대신 도구 자동화 + 구조화된 태스크로 추적

  ---
  4. Apple: 베타 피드백 기반 반복

  Apple의 내부 프로세스는 공개되지 않았지만, 알려진 바로는:
  - 개발자 베타 시드 → 피드백 수집 → 반복 개선
  - 품질에 대한 높은 기준 유지
  - 규제 산업(의료기기 등)에서는 표준 RTM 활용

  ---
  5. NVIDIA: 장기 지원 + 버전별 문서화

  - LTS(Long-Term Support) 버전에서 API/ABI 안정성 보장
  - SDK별 https://docs.nvidia.com
  - 릴리스 노트를 통한 업데이트 알림

  ---
  업계 공통 해결책: Requirements Traceability Matrix (RTM)

  https://www.perforce.com/resources/alm/requirements-traceability-matrix은 대부분의 글로벌 기업이 사용하 는 표준 접근법입니다:
  ┌─────────────┬────────┬─────────────┬────────────────┬─────────┐
  │ 요구사항 ID │  설계  │    코드     │ 테스트 케이스  │  결함   │
  ├─────────────┼────────┼─────────────┼────────────────┼─────────┤
  │ REQ-001     │ DS-001 │ src/auth.ts │ TC-001, TC-002 │ BUG-003 │
  ├─────────────┼────────┼─────────────┼────────────────┼─────────┤
  │ REQ-002     │ DS-002 │ src/user.ts │ TC-003         │ -       │
  └─────────────┴────────┴─────────────┴────────────────┴─────────┘
  Best Practices:

  1. 고유 ID 체계: 모든 요구사항에 REQ-XXX 형태의 고유 ID 부여
  2. 양방향 링크: 요구사항 ↔ 테스트 ↔ 결함 연결
  3. 자동화 도구 활용: https://marketplace.atlassian.com/apps/1220294/requirements-test-management-for-jira, Azure DevOps, HP ALM
  4. CI/CD 통합: 테스트 결과 자동 연결
  5. 정기 감사: 고아(orphan) 테스트, 미커버 요구사항 식별

  ---
  현대적 접근: Living Documentation

  https://codelucky.com/agile-documentation-living-approach/은 최신 트렌드입니다:

  코드 변경 → 문서 자동 업데이트 → 단일 진실 원천(Single Source of Truth)

  구현 방법:
  - BDD (Behavior-Driven Development): Cucumber, SpecFlow로 실행 가능한 명세 작성
  - 코드에서 문서 생성: 테스트가 곧 문서
  - CI/CD 파이프라인 통합: 문서 빌드 자동화
  - AWS는 https://repost.aws/articles/AROjWKtr5RTjy6T2HbFJD_Mw/%F0%9F%91%BB-kiro-agentic-ai-ide-beyond-a-coding-assistant-full-stack-software-development-with-spec-driven-ai에서 "명세 기반 개발"을 지원

  ---
  실무 권장사항
  ┌──────────────────────────┬───────────────────────────────────────────────────┐
  │           문제           │                      해결책                       │
  ├──────────────────────────┼───────────────────────────────────────────────────┤
  │ 요구사항 ID 없는 테스트  │ 테스트 생성 시 요구사항 링크 필수화 (도구로 강제) │
  ├──────────────────────────┼───────────────────────────────────────────────────┤
  │ 문서 일관성 깨짐         │ 단일 진실 원천(SSOT) + 자동 동기화                │
  ├──────────────────────────┼───────────────────────────────────────────────────┤
  │ 나중에 등장하는 요구사항 │ 변경 요청(CR) 프로세스 + 영향 분석                │
  ├──────────────────────────┼───────────────────────────────────────────────────┤
  │ 추적 누락                │ CI에서 커버리지 게이트 설정                       │
  └──────────────────────────┴───────────────────────────────────────────────────┘
  Sources:
  - https://www.industrialempathy.com/posts/design-docs-at-google/
  - https://learn.microsoft.com/en-us/azure/devops/cross-service/end-to-end-traceability?view=azure-devops
  - https://newsletter.pragmaticengineer.com/p/facebook
  - https://www.perforce.com/resources/alm/requirements-traceability-matrix
  - https://codelucky.com/agile-documentation-living-approach/